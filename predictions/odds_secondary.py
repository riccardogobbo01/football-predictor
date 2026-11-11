"""Registro delle quote dei mercati secondari (cartellini e corner) di The Odds API, piano gratuito, per misurare nel tempo il margine del modello
su gialli e corner. NON influisce sulle previsioni: scrive solo docs/odds_secondary.csv e docs/odds_secondary_status.json e alimenta una sezione del resoconto.

Regole (decise il 11/11/2026):
  - UNA sola istantanea per partita, mercati alternate_totals_cards e alternate_totals_corners, regione `eu` (la chiamata costa 1 credito per mercato che
    restituisce quote; una risposta vuota costa 0): al massimo 2 crediti a partita.
  - Quando: tra 40 e 3 ore prima del calcio d'inizio, cioe' di norma il giorno prima. Per la Serie A si aspetta la designazione dell'arbitro finche' mancano
    piu' di 16 ore; poi si registra comunque (colonna referee_known). Le partite senza quote vengono ritentate ai passaggi successivi (l'elenco partite /events e' gratuito).
  - Limite di sicurezza: se i crediti usati nel mese raggiungerebbero il 90 % del totale, nessuna chiamata a pagamento e lo si scrive nel log.
  - Chiave mancante o non valida, rete assente, risposte inattese: si scrive nel log e la generazione del sito prosegue (nessuna eccezione verso l'esterno).
  - La chiave e' letta da ODDS_API_KEY (variabile d'ambiente, in GitHub Actions il secret) o dal file .env locale; non viene mai scritta nei log, nei file o nei messaggi d'errore.

docs/odds_secondary.csv (una riga per partita, mercato, linea e bookmaker; mai riscritta tranne `real_total`):
  snapshot_utc, league, match_date, kickoff_utc, home, away, market (cards|corners), line, bookmaker, odds_over, odds_under,
  p_over_mkt (probabilita' dell'Over senza margine, metodo power, escluso il rimborso sulle linee intere), p_over_model (P(totale > linea)), p_push_model (P(totale = linea),
  0 sulle linee .5), hours_to_kickoff, referee_known, model_used, real_total (gialli o corner reali della partita, completato a partita giocata).
  Cartellini: il mercato del bookmaker puo' contare diversamente i rossi; real_total sono i gialli totali del CSV (HY+AY)."""
import difflib
import json
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import requests
from scipy.stats import nbinom

from backtest import eloodds
from predictions.paper_monitor import _block_ci

BASE = "https://api.the-odds-api.com/v4"
SPORT_KEYS = {"serie_a": "soccer_italy_serie_a", "premier_league": "soccer_epl", "bundesliga": "soccer_germany_bundesliga",
              "la_liga": "soccer_spain_la_liga", "ligue_1": "soccer_france_ligue_one"}
MARKETS = {"alternate_totals_cards": ("cards", "yellows"), "alternate_totals_corners": ("corners", "corners")}
REGIONS = "eu"
WINDOW_MAX_H, WINDOW_MIN_H = 40.0, 3.0
SERIE_A_WAIT_H = 16.0
BUDGET_STOP = 0.90
CREDITS_PER_MATCH = len(MARKETS) * len(REGIONS.split(","))          # costo massimo di una partita
MIN_EVAL = 200                                                      # partite con risultato per mercato prima di mostrare log-loss e calibrazione
COLUMNS = ["snapshot_utc", "league", "match_date", "kickoff_utc", "home", "away", "market", "line", "bookmaker", "odds_over", "odds_under",
           "p_over_mkt", "p_over_model", "p_push_model", "hours_to_kickoff", "referee_known", "model_used", "real_total"]
KEY = ["league", "match_date", "home", "away"]
PREFERRED_BOOK = "pinnacle"
CSV_NAME, STATUS_NAME = "odds_secondary.csv", "odds_secondary_status.json"
REAL_COL = {"cards": "yellow_real", "corners": "corners_real"}


# ───────────────────────────── chiave e rete ─────────────────────────────
def load_key() -> str:
    k = os.environ.get("ODDS_API_KEY", "").strip()
    if k:
        return k
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(here, ".env")
    if os.path.exists(path):
        try:
            for line in open(path, encoding="utf-8"):
                if line.strip().startswith("ODDS_API_KEY="):
                    return line.strip().split("=", 1)[1].strip().strip('"').strip("'")
        except OSError:
            pass
    return ""


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def http_get(path: str, key: str, **params):
    """GET su The Odds API. Restituisce (json | None, {'used','remaining','last'}, errore | None, status HTTP). La chiave non compare mai nei messaggi."""
    try:
        r = requests.get(f"{BASE}{path}", params={"apiKey": key, **params}, timeout=30)
    except requests.RequestException as e:
        return None, {}, f"{type(e).__name__} (dettaglio omesso)", None
    hdr = {"used": _int(r.headers.get("x-requests-used")), "remaining": _int(r.headers.get("x-requests-remaining")), "last": _int(r.headers.get("x-requests-last"))}
    if r.status_code != 200:
        try:
            msg = str(r.json().get("message"))
        except Exception:
            msg = r.text[:100]
        return None, hdr, f"HTTP {r.status_code}: {msg.replace(key, '***')}", r.status_code
    try:
        return r.json(), hdr, None, 200
    except ValueError:
        return None, hdr, "risposta non JSON", 200


# ───────────────────────────── abbinamento partite ─────────────────────────────
_STOP = {"fc", "cf", "afc", "ac", "as", "sc", "ud", "rc", "rcd", "us", "ssc", "cd", "ca", "sv", "vfb", "vfl", "tsg", "fsv", "sd", "de", "the", "calcio", "club", "1", "04", "05", "09", "1899", "1907", "1909", "1913", "1900", "1846"}


def norm(name: str) -> str:
    s = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    toks = [t for t in s.split() if t not in _STOP]
    s = " ".join(toks)
    return s.replace("munchen", "munich").replace("koln", "cologne").replace("saint ", "st ")


def team_sim(fix_names, api_name: str) -> float:
    b = norm(api_name)
    best = 0.0
    for n in fix_names:
        a = norm(n)
        if not a or not b:
            continue
        r = difflib.SequenceMatcher(None, a, b).ratio()
        ta, tb = set(a.split()), set(b.split())
        cont = 1.0 if (ta <= tb or tb <= ta) else 0.0                      # un nome contenuto nell'altro ("Marseille" / "Olympique Marseille")
        best = max(best, r, 0.9 * cont)
    return best


def kickoff(fix: dict):
    try:
        return datetime.strptime(f"{fix['date']} {fix['time']}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
    except (KeyError, TypeError, ValueError):
        return None


def match_events(cands, events, min_sim=0.6, max_dt_h=3.0):
    """Abbina le partite candidate agli eventi di The Odds API: stesso orario (entro 3 ore) e nomi simili per entrambe le squadre. Restituisce {indice candidato: evento}."""
    pairs = []
    for i, (fix, ko, _h, _r) in enumerate(cands):
        for ev in events:
            try:
                t = datetime.fromisoformat(ev["commence_time"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            if abs((t - ko).total_seconds()) / 3600 > max_dt_h:
                continue
            sh = team_sim([fix.get("home"), fix.get("home_full"), fix.get("home_dc")], ev.get("home_team"))
            sa = team_sim([fix.get("away"), fix.get("away_full"), fix.get("away_dc")], ev.get("away_team"))
            if min(sh, sa) >= min_sim:
                pairs.append((sh + sa, i, ev))
    out, used = {}, set()
    for sc, i, ev in sorted(pairs, key=lambda x: -x[0]):                     # abbinamento univoco, prima i migliori
        if i in out or ev["id"] in used:
            continue
        out[i] = ev
        used.add(ev["id"])
    return out


# ───────────────────────────── probabilità ─────────────────────────────
def model_probs(nb, line: float):
    """(P(totale > linea), P(totale = linea)) dalla Binomiale Negativa del modello (media e dispersione del totale). NaN se mancano i parametri o la linea e' di quarto."""
    if not nb or nb[0] is None or not np.isfinite(nb[0]) or nb[0] <= 0:
        return float("nan"), float("nan")
    if abs(line * 2 - round(line * 2)) > 1e-9:
        return float("nan"), float("nan")
    m, alpha = float(nb[0]), float(nb[1])
    n = 1.0 / alpha
    p = n / (n + m)
    if abs(line - round(line)) < 1e-9:
        k = int(round(line))
        return float(1 - nbinom.cdf(k, n, p)), float(nbinom.pmf(k, n, p))
    return float(1 - nbinom.cdf(int(np.floor(line)), n, p)), 0.0


def fair_over(over, under):
    if over is None or under is None or not (over > 1 and under > 1):
        return float("nan")
    return float(eloodds.power_devig(np.array([[over, under]]))[0, 0])


def parse_odds(odds: dict, fix: dict, league: str, snapshot: str, hours: float, ref_known: bool, model_used) -> list:
    """Righe del CSV da una risposta /events/{id}/odds."""
    stats = fix.get("expected_stats") or {}
    rows = []
    for b in odds.get("bookmakers", []) or []:
        for m in b.get("markets", []) or []:
            if m.get("key") not in MARKETS:
                continue
            market, statkey = MARKETS[m["key"]]
            nb = (stats.get(statkey) or {}).get("nb")
            by = {}
            for o in m.get("outcomes", []) or []:
                if o.get("point") is None or o.get("price") is None:
                    continue
                by.setdefault(float(o["point"]), {})[o.get("name")] = float(o["price"])
            for line, sides in sorted(by.items()):
                ov, un = sides.get("Over"), sides.get("Under")
                po, pp = model_probs(nb, line)
                rows.append({"snapshot_utc": snapshot, "league": league, "match_date": fix["date"], "kickoff_utc": f"{fix['date']} {fix['time']}", "home": fix["home"],
                             "away": fix["away"], "market": market, "line": line, "bookmaker": b.get("key"), "odds_over": ov, "odds_under": un,
                             "p_over_mkt": fair_over(ov, un), "p_over_model": po, "p_push_model": pp, "hours_to_kickoff": round(hours, 1),
                             "referee_known": int(bool(ref_known)), "model_used": model_used, "real_total": np.nan})
    return rows


# ───────────────────────────── file ─────────────────────────────
def load(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(path, dtype={"league": str, "match_date": str, "kickoff_utc": str, "home": str, "away": str, "market": str, "bookmaker": str,
                                  "snapshot_utc": str, "model_used": str})
    for c in COLUMNS:
        if c not in df:
            df[c] = np.nan
    return df[COLUMNS]


def save(df: pd.DataFrame, path: str):
    out = df.copy()
    for c in ("p_over_mkt", "p_over_model", "p_push_model"):
        out[c] = out[c].astype(float).round(5)
    out.to_csv(path, index=False)


def fill_results(df: pd.DataFrame, history: pd.DataFrame) -> int:
    """real_total (gialli o corner reali) dalle righe dello storico con la partita giocata. Restituisce le righe aggiornate."""
    if df.empty or history is None or not len(history):
        return 0
    h = history[KEY + list(REAL_COL.values())].drop_duplicates(KEY)
    n = 0
    for market, col in REAL_COL.items():
        m = df["market"] == market
        need = m & df["real_total"].isna()
        if not need.any():
            continue
        merged = df.loc[need, KEY].merge(h[KEY + [col]], on=KEY, how="left")
        vals = merged[col].to_numpy(float)
        ok = np.isfinite(vals)
        idx = df.index[need][ok]
        df.loc[idx, "real_total"] = vals[ok]
        n += int(ok.sum())
    return n


# ───────────────────────────── raccolta ─────────────────────────────
def _budget_ok(hdr: dict):
    """(ok, usati, totale): non si chiama se la chiamata piu' costosa porterebbe oltre il 90 % del totale mensile."""
    used, rem = hdr.get("used"), hdr.get("remaining")
    if used is None or rem is None:
        return True, used, None
    total = used + rem
    return (used + CREDITS_PER_MATCH) <= BUDGET_STOP * total, used, total


def run(all_data: dict, history, today, out_dir: str, log, now=None, key=None, http=http_get) -> dict:
    """Raccoglie le istantanee dovute, completa i risultati e scrive CSV e stato. Non solleva mai eccezioni verso il chiamante."""
    now = now or datetime.now(timezone.utc)
    path, spath = os.path.join(out_dir, CSV_NAME), os.path.join(out_dir, STATUS_NAME)
    st = {"at": now.strftime("%Y-%m-%d %H:%M UTC"), "enabled": False, "reason": None, "used": None, "remaining": None, "calls": 0, "credits_spent": 0, "due": 0,
          "recorded": 0, "no_data": 0, "unmatched": [], "waiting_referee": 0, "budget_stop": False}
    try:
        df = load(path)
        key = load_key() if key is None else key
        if not key:
            st["reason"] = "ODDS_API_KEY non impostata: raccolta saltata"
        else:
            st["enabled"] = True
            done = set(map(tuple, df[KEY].drop_duplicates().to_numpy())) if len(df) else set()
            new_rows = []
            stop = False
            for league, sk in SPORT_KEYS.items():
                if stop:
                    break
                cands = []
                for fix in (all_data.get(league) or {}).get("fixtures", []):
                    ko = kickoff(fix)
                    if ko is None or (league, fix["date"], fix["home"], fix["away"]) in done:
                        continue
                    hrs = (ko - now).total_seconds() / 3600
                    if not (WINDOW_MIN_H < hrs <= WINDOW_MAX_H):
                        continue
                    ref = bool(fix.get("referee"))
                    if league == "serie_a" and not ref and hrs > SERIE_A_WAIT_H:
                        st["waiting_referee"] += 1
                        continue
                    cands.append((fix, ko, hrs, ref))
                if not cands:
                    continue
                st["due"] += len(cands)
                events, hdr, err, code = http(f"/sports/{sk}/events", key)
                st["calls"] += 1
                if code in (401, 403):
                    st["enabled"], st["reason"] = False, f"chiave non valida o non autorizzata ({err})"
                    break
                if err or not events:
                    log.warning("  Mercati secondari %s: elenco partite non disponibile (%s)", league, err or "vuoto")
                    continue
                st["used"], st["remaining"] = hdr.get("used", st["used"]), hdr.get("remaining", st["remaining"])
                matched = match_events(cands, events)
                for i, (fix, ko, hrs, ref) in enumerate(cands):
                    if i not in matched:
                        st["unmatched"].append(f"{league}: {fix['home']} - {fix['away']}")
                for i, ev in matched.items():
                    fix, ko, hrs, ref = cands[i]
                    ok, used, total = _budget_ok({"used": st["used"], "remaining": st["remaining"]})
                    if not ok:
                        st["budget_stop"] = True
                        stop = True
                        log.warning("Mercati secondari: crediti usati %s su %s: oltre la soglia del %d %%, chiamate saltate fino a nuovo mese", used, total, int(BUDGET_STOP * 100))
                        break
                    odds, hdr, err, code = http(f"/sports/{sk}/events/{ev['id']}/odds", key, regions=REGIONS, markets=",".join(MARKETS), oddsFormat="decimal")
                    st["calls"] += 1
                    if code in (401, 403):
                        st["enabled"], st["reason"] = False, f"chiave non valida o non autorizzata ({err})"
                        stop = True
                        break
                    if hdr.get("used") is not None:
                        st["credits_spent"] += hdr.get("last") or 0
                        st["used"], st["remaining"] = hdr["used"], hdr.get("remaining")
                    if err or not odds:
                        log.warning("  Mercati secondari: %s - %s: %s", fix["home"], fix["away"], err or "nessuna risposta")
                        continue
                    stats_model = (fix.get("expected_stats") or {}).get("model")
                    rows = parse_odds(odds, fix, league, now.strftime("%Y-%m-%d %H:%M"), hrs, ref, stats_model)
                    if not rows:
                        st["no_data"] += 1
                        continue
                    new_rows += rows
                    done.add((league, fix["date"], fix["home"], fix["away"]))
                    st["recorded"] += 1
            if new_rows:
                df = pd.concat([df, pd.DataFrame(new_rows, columns=COLUMNS)], ignore_index=True)
        n_fill = fill_results(df, history)
        if len(df) or n_fill:
            save(df, path)
        st["rows"], st["matches"] = int(len(df)), int(len(df[KEY].drop_duplicates())) if len(df) else 0
        st["results_filled"] = n_fill
    except Exception as e:                                        # mai bloccare la generazione del sito
        st["enabled"] = False
        st["reason"] = f"errore {type(e).__name__}: {str(e)[:120]}".replace(key or "\0", "***")
    try:
        with open(spath, "w", encoding="utf-8") as fh:
            json.dump(st, fh, ensure_ascii=False, indent=1)
    except OSError:
        pass
    if st["enabled"]:
        log.info("Mercati secondari: %d partite da registrare, %d registrate (%d senza quote), %d chiamate, crediti usati %s / rimasti %s%s",
                 st["due"], st["recorded"], st["no_data"], st["calls"], st["used"], st["remaining"],
                 f"; {st['waiting_referee']} in attesa dell'arbitro" if st["waiting_referee"] else "")
        if st["unmatched"]:
            log.warning("Mercati secondari: %d partite non abbinate agli eventi: %s", len(st["unmatched"]), "; ".join(st["unmatched"][:6]))
    else:
        log.warning("Mercati secondari non raccolti: %s", st["reason"])
    return st


# ───────────────────────────── resoconto ─────────────────────────────
def main_line(df: pd.DataFrame) -> pd.DataFrame:
    """Una riga per partita e mercato: bookmaker preferito (Pinnacle, altrimenti quello con piu' linee) e linea con probabilita' di mercato piu' vicina a 0,5."""
    d = df[df["p_over_mkt"].notna() & df["p_over_model"].notna()].copy()
    if d.empty:
        return d
    d["_pref"] = (d["bookmaker"] != PREFERRED_BOOK).astype(int)
    d["_cnt"] = d.groupby(KEY + ["market", "bookmaker"])["line"].transform("size")
    d["_gap"] = (d["p_over_mkt"] - 0.5).abs()
    d = d.sort_values(KEY + ["market", "_pref", "_cnt", "_gap"], ascending=[True] * 5 + [True, False, True])
    return d.drop_duplicates(KEY + ["market"]).drop(columns=["_pref", "_cnt", "_gap"])


def evaluate(d: pd.DataFrame) -> dict:
    """Log-loss del modello e delle quote senza margine sull'Over della linea principale (rimborsi esclusi), con IC a blocchi per settimana, e calibrazione a fasce."""
    d = d[d["real_total"].notna() & (d["real_total"] != d["line"])].copy()
    out = {"n": int(len(d))}
    if not len(d):
        return out
    y = (d["real_total"] > d["line"]).to_numpy(float)
    pm = np.clip((d["p_over_model"] / (1 - d["p_push_model"])).to_numpy(float), 1e-4, 1 - 1e-4)
    pk = np.clip(d["p_over_mkt"].to_numpy(float), 1e-4, 1 - 1e-4)
    ll = lambda p: -(y * np.log(p) + (1 - y) * np.log(1 - p))
    weeks = pd.to_datetime(d["match_date"]).dt.strftime("%G-%V").to_numpy()
    lm, lk = ll(pm), ll(pk)
    out.update(ll_model=float(lm.mean()), ll_market=float(lk.mean()), delta=_block_ci(lk - lm, np.ones(len(d)), weeks, 7))
    bins = [0, 0.35, 0.45, 0.55, 0.65, 1.0001]
    for name, p in (("cal_model", pm), ("cal_market", pk)):
        rows = []
        for lo, hi in zip(bins[:-1], bins[1:]):
            s = (p >= lo) & (p < hi)
            rows.append([f"{int(lo * 100)}-{min(int(hi * 100), 100)}%", int(s.sum()), float(p[s].mean()) if s.any() else None, float(y[s].mean()) if s.any() else None])
        out[name] = rows
    return out


def summary(out_dir: str) -> dict:
    """Dati per la sezione del resoconto: partite registrate e con risultato per mercato, metriche dal 200ª partita con risultato, stato dell'ultima raccolta."""
    res = {"status": None, "markets": {}, "min_eval": MIN_EVAL, "matches": 0}
    try:
        res["status"] = json.load(open(os.path.join(out_dir, STATUS_NAME), encoding="utf-8"))
    except (OSError, ValueError):
        pass
    df = load(os.path.join(out_dir, CSV_NAME))
    if df.empty:
        return res
    res["matches"] = int(len(df[KEY].drop_duplicates()))
    ml = main_line(df)
    for market in ("cards", "corners"):
        dm = df[df["market"] == market]
        reg = dm[KEY].drop_duplicates()
        with_res = dm[dm["real_total"].notna()][KEY].drop_duplicates()
        r = {"registered": int(len(reg)), "with_result": int(len(with_res)), "bookmakers": sorted(dm["bookmaker"].dropna().unique().tolist())}
        r["lines"] = float(round(dm.groupby(KEY)["line"].nunique().mean(), 1)) if len(dm) else 0
        e = evaluate(ml[ml["market"] == market])
        r["n_eval"] = e.get("n", 0)
        if e.get("n", 0) >= MIN_EVAL:
            r["eval"] = e
        res["markets"][market] = r
    return res
