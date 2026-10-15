"""
Coppe europee (Champions League, Europa League, Conference League).

Modello (models/cups_model.json, validato fuori dal repo su 1.796 partite di coppa 2011-2026):
  elo_diff = (Elo casa - Elo ospite) / 100                  [rating ClubElo del giorno]
  gol attesi casa    = exp(intercept_home + coef_home * elo_diff)
  gol attesi ospite  = exp(intercept_away + coef_away * elo_diff)
poi la stessa matrice dei punteggi Dixon-Coles dei campionati (con il rho del file), da cui 1X2, O/U,
BTTS, porta inviolata e risultati esatti. Per la finale (campo neutro) si fa la media delle due
orientazioni (casa/ospite scambiate).

Dati (ClubElo ha disattivato l'API, il sito funziona):
  - rating:  https://clubelo.com/Ranking   (array JS con tutti i club; tabelle HTML per lega come ripiego)
  - partite: https://clubelo.com/Fixtures  (prima tabella, sezioni "UCL ...", "UEL ...", "UECL ...")
I club si identificano con lo "slug" del link (es. /Lens), uguale nelle due pagine. Le pagine si scaricano
una volta al giorno (cache in data/cache/clubelo_cups.json) con uno User-Agent descrittivo. Se clubelo.com
non risponde la funzione solleva CupsError e il resto del sito si genera normalmente.

Solo libreria standard + requests/numpy: in CI non ci sono beautifulsoup4/lxml.
"""
import json
import logging
import os
import re
import sys
import time
import unicodedata
from datetime import date, datetime, timedelta
from difflib import SequenceMatcher
from html import unescape

import numpy as np
import requests

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backtest import models  # noqa: E402

log = logging.getLogger(__name__)

RANKING_URL = "https://clubelo.com/Ranking"
FIXTURES_URL = "https://clubelo.com/Fixtures"
USER_AGENT = ("football-predictor/1.0 (progetto personale; una scaricata al giorno; "
              "https://github.com/riccardogobbo01/football-predictor)")
CACHE_PATH = os.path.join(REPO_ROOT, "data", "cache", "clubelo_cups.json")
MODEL_PATH = os.path.join(REPO_ROOT, "models", "cups_model.json")

# chiave pagina/storico -> prefisso della sezione su ClubElo, nome, codice football-data.org, icona
CUPS = {
    "ucl":  {"prefix": "UCL",  "name": "Champions League",  "fdo": "CL",  "flag": "🏆"},
    "uel":  {"prefix": "UEL",  "name": "Europa League",     "fdo": "EL",  "flag": "🟧"},
    "uecl": {"prefix": "UECL", "name": "Conference League", "fdo": "ECL", "flag": "🟩"},
}
PREFIX_TO_CUP = {v["prefix"]: k for k, v in CUPS.items()}
CACHE_VERSION = 2            # da incrementare se cambia il parser: la cache contiene partite già lette
MIN_RANKING_CLUBS = 500        # sotto questa soglia il ranking scaricato non è valido
NOT_AVAILABLE_MSG = "Dati delle coppe non disponibili oggi"
NO_STATS_MSG = "Statistiche e quote non disponibili per le coppe europee"
RETURN_LEG_NOTE = "Previsione della singola partita, non tiene conto del risultato dell'andata"


class CupsError(RuntimeError):
    pass


# ── Download e cache ───────────────────────────────────────────────────────────────

def _download(url: str) -> str:
    last = None
    for attempt in range(3):
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            last = e
            time.sleep(2 * (attempt + 1))
    raise CupsError(f"clubelo.com non raggiungibile ({url}): {last}")


# ── Parsing ranking ─────────────────────────────────────────────────────────────────

_JS_ROW = re.compile(r"""<small>\s*(\d+)\s*</small><a href="/([^"/]+)">(.*?)</a></td>',\s*'(\d+)'""", re.S)
_TABLE_ROW = re.compile(r'<a href="/([^"/]+)"><span class="NonAst">[^<]*</span>'
                        r'<span class="Ast">([^<]*)</span></a></td><td class="r">(\d+)</td>')


def _plain(html_fragment: str) -> str:
    return " ".join(unescape(re.sub(r"<[^>]+>", "", html_fragment)).split())


def parse_ranking(html: str) -> dict:
    """{slug: {"name", "elo", "rank"}}. Fonte principale: l'array JS con tutti i club della pagina Ranking
    (il nome è spezzato in più tag: si ricompone); ripiego: le tabelle HTML per lega (solo ~500 club)."""
    out = {}
    for rank, slug, name_html, elo in _JS_ROW.findall(html):
        out[slug] = {"name": _plain(name_html), "elo": float(elo), "rank": int(rank)}
    if len(out) >= MIN_RANKING_CLUBS:
        return out
    out = {}
    for slug, name, elo in _TABLE_ROW.findall(html):
        out[slug] = {"name": unescape(name).strip(), "elo": float(elo), "rank": None}
    return out


# ── Parsing partite ────────────────────────────────────────────────────────────────

_SECTION = re.compile(r"<i>\s*([^<]+?)\s*</i>")
_TIME = re.compile(r'data-utc-time="(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})Z"')
_TEAM = re.compile(r'(?:<a href="/([^"/]+)">)?<span class="max640">[^<]*</span><span class="min641">([^<]*)</span>')
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_PCT = re.compile(r'<span class="min1081">([^<]*)</span>')


def _first_table(html: str) -> str:
    i = html.find("<table")
    j = html.find("</table>", i)
    if i < 0 or j < 0:
        raise CupsError("pagina Fixtures: tabella delle partite non trovata")
    return html[i:j]


def _pct(cell_html: str):
    m = _PCT.search(cell_html)
    if not m:
        return None
    txt = m.group(1).strip().lstrip("<")
    try:
        return float(txt) / 100
    except ValueError:
        return None


def _team_idx(cells):
    for i, c in enumerate(cells):
        m = _TEAM.search(c)
        if m:
            return i, m.group(1), unescape(m.group(2)).strip()
    return None


def _so_far(cell_html: str):
    t = _plain(cell_html)
    return int(t) if t.isdigit() else None


def _stage_flags(stage: str):
    s = stage.lower()
    league_stage = "league stage" in s or "group" in s
    final = bool(re.search(r"\bfinal\b", s)) and not any(w in s for w in ("semi", "quarter"))
    return (not league_stage), final


def parse_fixtures(html: str) -> list:
    """Partite delle sezioni UCL/UEL/UECL della prima tabella di /Fixtures."""
    table = _first_table(html)
    out, cup, stage, agg_label, pending = [], None, "", "", None
    for chunk in re.split(r"<tr[ >]", table)[1:]:
        sec = _SECTION.search(chunk)
        if sec:                                         # intestazione di sezione
            label = sec.group(1).strip()
            first, _, rest = label.partition(" ")
            cup = PREFIX_TO_CUP.get(first)
            stage = rest.strip()
            cells = _CELL.findall(chunk)
            agg_label = _plain(cells[1]) if len(cells) > 1 else ""
            pending = None
            continue
        if cup is None:
            continue
        cells = _CELL.findall(chunk)
        t = _TIME.search(chunk)
        if t:                                           # prima riga della partita (con data e ora)
            ti = _team_idx(cells)
            if not ti:
                log.warning("clubelo Fixtures: riga di partita %s %s senza squadra riconoscibile, scartata", cup, t.group(1))
                pending = None
                continue
            idx, slug, name = ti
            pending = {"cup": cup, "stage": stage, "agg_label": agg_label, "date": t.group(1), "time": t.group(2),
                       "home_slug": slug, "home_name": name,
                       "so_far_home": _so_far(cells[idx + 1]) if idx + 1 < len(cells) else None,
                       "clubelo_p1": _pct(cells[idx + 2]) if idx + 2 < len(cells) else None,
                       "clubelo_px": _pct(cells[idx + 3]) if idx + 3 < len(cells) else None}
        elif pending:                                   # seconda riga: squadra ospite
            ti = _team_idx(cells)
            if not ti:
                log.warning("clubelo Fixtures: %s - squadra ospite non riconoscibile, partita scartata", pending["home_name"])
                pending = None
                continue
            idx, slug, name = ti
            pending.update(away_slug=slug, away_name=name,
                           so_far_away=_so_far(cells[idx + 1]) if idx + 1 < len(cells) else None,
                           clubelo_p2=_pct(cells[idx + 2]) if idx + 2 < len(cells) else None)
            pending["knockout"], pending["final"] = _stage_flags(stage)
            out.append(pending)
            pending = None
    return out


# ── Caricamento (una volta al giorno) ──────────────────────────────────────────────────

def load_cup_data(today: date, use_cache: bool = True) -> dict:
    """{"fetched_on", "ranking": {slug: {...}}, "fixtures": [...]} per oggi. Scarica clubelo.com al massimo
    una volta al giorno (cache su disco, valida solo se scaricata oggi). Solleva CupsError se non raggiungibile."""
    today_s = today.isoformat()
    if use_cache and os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, encoding="utf-8") as fh:
                cached = json.load(fh)
            if cached.get("fetched_on") == today_s and cached.get("version") == CACHE_VERSION:
                return cached
        except (OSError, ValueError):
            pass

    ranking_html = _download(RANKING_URL)
    time.sleep(1.0)
    fixtures_html = _download(FIXTURES_URL)

    ranking = parse_ranking(ranking_html)
    if len(ranking) < MIN_RANKING_CLUBS:                 # ripiego: le stesse tabelle sono nella pagina Fixtures
        ranking = parse_ranking(fixtures_html)
    if len(ranking) < MIN_RANKING_CLUBS:
        raise CupsError(f"ranking ClubElo non valido ({len(ranking)} club): struttura della pagina cambiata?")
    fixtures = parse_fixtures(fixtures_html)

    data = {"version": CACHE_VERSION, "fetched_on": today_s, "ranking": ranking, "fixtures": fixtures}
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False)
    return data


# ── Modello ────────────────────────────────────────────────────────────────────────────

def load_model(path: str = MODEL_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        m = json.load(fh)
    for k in ("home_goals", "away_goals", "rho"):
        if k not in m:
            raise ValueError(f"{path}: manca '{k}'")
    return m


def _matrix(model: dict, elo_diff: float):
    d = elo_diff / 100.0
    mu = float(np.exp(model["home_goals"]["intercept"] + model["home_goals"]["coef_elo_diff"] * d))
    nu = float(np.exp(model["away_goals"]["intercept"] + model["away_goals"]["coef_elo_diff"] * d))
    M = models.score_matrix(np.array([mu]), np.array([nu]), np.full(1, model["rho"]))[0]
    return mu, nu, M


def predict_match(model: dict, elo_home: float, elo_away: float, neutral: bool = False) -> dict:
    """Mercati da UNA matrice dei punteggi (stesso formato dei campionati). Su campo neutro (finale)
    si fa la media delle due orientazioni."""
    from predictions import stack_predictor as sp   # per markets(): stessi mercati e arrotondamenti dei campionati
    mu, nu, M = _matrix(model, elo_home - elo_away)
    if neutral:
        mu2, nu2, M2 = _matrix(model, elo_away - elo_home)   # squadre scambiate: M2[x, y] = P(ospite x, casa y)
        M = 0.5 * (M + M2.T)
        mu, nu = 0.5 * (mu + nu2), 0.5 * (nu + mu2)
    pred = sp.markets(M, mu, nu)
    pred["model"] = "cups_elo"
    pred["fallback_reason"] = None
    return pred


# ── Costruzione delle partite per la pagina ──────────────────────────────────────────────

def is_return_leg(m: dict, all_fixtures: list, known_pairs: dict) -> bool:
    """Gara di ritorno di un turno a eliminazione diretta. Riconosciuta se (a) l'andata è nello stesso elenco,
    (b) l'andata è già in docs/history.csv (emessa nelle ultime 8 settimane), (c) la colonna "So Far" mostra gol già
    segnati nella doppia sfida. Mai per la fase a girone/campionato né per la finale."""
    if not m["knockout"] or m["final"]:
        return False
    if any(o is not m and o["cup"] == m["cup"] and o["home_name"] == m["away_name"]
           and o["away_name"] == m["home_name"] and o["date"] < m["date"] for o in all_fixtures):
        return True
    prev = known_pairs.get((m["cup"], m["away_name"], m["home_name"]))      # data più recente in cui la coppia (a ruoli invertiti) era in calendario
    if prev and prev < m["date"] and (datetime.strptime(m["date"], "%Y-%m-%d") - datetime.strptime(prev, "%Y-%m-%d")).days <= 60:
        return True
    return bool((m.get("so_far_home") or 0) + (m.get("so_far_away") or 0) > 0)


def _norm_key(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", s).split())


def build_fixtures(data: dict, model: dict, today: date, days_ahead: int = 14, known_pairs=None):
    """known_pairs: {(coppa, casa, ospite): data più recente in storico} per riconoscere le gare di ritorno."""
    """({cup: [partite con previsione]}, [partite scartate per Elo mancante])."""
    known_pairs = known_pairs or {}
    ranking, fixtures = data["ranking"], data["fixtures"]
    by_name = {_norm_key(v["name"]): v for v in ranking.values()}

    def lookup(slug, name):
        return ranking.get(slug) if slug else by_name.get(_norm_key(name))

    end = (today + timedelta(days=days_ahead)).isoformat()
    out, skipped = {k: [] for k in CUPS}, []
    for m in fixtures:
        if not (today.isoformat() <= m["date"] <= end):
            continue
        h, a = lookup(m["home_slug"], m["home_name"]), lookup(m["away_slug"], m["away_name"])
        if not h or not a:
            missing = " e ".join(n for n, x in ((m["home_name"], h), (m["away_name"], a)) if not x)
            skipped.append({"cup": m["cup"], "date": m["date"],
                            "text": f"{m['home_name']} - {m['away_name']} ({m['date']}): Elo mancante per {missing}"})
            continue
        pred = predict_match(model, h["elo"], a["elo"], neutral=m["final"])
        out[m["cup"]].append({
            "date": m["date"], "time": m["time"], "home": h["name"], "away": a["name"],
            "home_full": h["name"], "away_full": a["name"], "matchday": None, "stage": m["stage"],
            "home_dc": None, "away_dc": None, "new_team": False,
            "prediction": pred, "market": None, "expected_stats": None, "context": None,
            "cup": m["cup"], "elo": {"home": h["elo"], "away": a["elo"]}, "home_elo": h["elo"], "away_elo": a["elo"],
            "neutral": m["final"],
            "return_leg": is_return_leg(m, fixtures, known_pairs),
            "clubelo_1x2": [m.get("clubelo_p1"), m.get("clubelo_px"), m.get("clubelo_p2")],
        })
    for k in out:
        out[k].sort(key=lambda f: (f["date"], f["time"], f["home"]))
    return out, skipped


# ── Abbinamento nomi con football-data.org (controllo incrociato e risultati) ────────────

_STOP = {"fc", "cf", "ac", "sc", "fk", "sk", "bk", "afc", "club", "de", "del", "di", "da", "do", "the", "cd", "ud",
         "calcio", "sv", "rc", "as", "ss", "ssc", "us", "og", "ogc", "vfb", "vfl", "tsg", "fsv", "nk", "hnk", "sl",
         "kv", "krc", "if"}
# sostituzioni di frase (dopo la normalizzazione) per i nomi che ClubElo e football-data.org scrivono in modo diverso
_PHRASES = [
    (r"\bsaint germain\b", "sg"),
    (r"\binternazionale( milano)?\b", "inter"),
    (r"\bmanchester\b", "man"),
    (r"\batletico( de| madrid)*\b", "atletico"),
    (r"\bsporting clube de portugal\b", "sporting"),
    (r"\bsporting cp\b", "sporting"),
    (r"\bolympique (de )?(lyonnais|lyon)\b", "lyon"),
    (r"\bolympique (de )?marseille\b", "marseille"),
    (r"\bborussia\b", ""),
    (r"\bbayer 04\b", ""),
    (r"\bhotspur\b", ""),
    (r"\bunited\b", "utd"),
]


def _tokens(name: str) -> tuple:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = " ".join(re.sub(r"[^a-z0-9 ]+", " ", s).split())
    for pat, rep in _PHRASES:
        s = " ".join(re.sub(pat, rep, s).split())
    toks = [t for t in s.split() if t not in _STOP and not t.isdigit()] or s.split()
    return tuple(toks)


def name_similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    if set(ta) == set(tb):
        return 1.0
    if set(ta) <= set(tb) or set(tb) <= set(ta):
        return 0.92
    return SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio()


def match_to_fdo(fixture: dict, candidates: list, max_days: int = 1, threshold: float = 0.8):
    """Partita di football-data.org (dict con date, home_full/away_full o home/away) corrispondente a
    una di ClubElo: stessa data (±max_days) e nomi simili per entrambe le squadre. None se non c'è."""
    d0 = datetime.strptime(fixture["date"], "%Y-%m-%d")
    best, best_score = None, threshold
    for c in candidates:
        if abs((datetime.strptime(c["date"], "%Y-%m-%d") - d0).days) > max_days:
            continue
        sh = max(name_similarity(fixture["home"], c.get("home_full") or c["home"]),
                 name_similarity(fixture["home"], c["home"]))
        sa = max(name_similarity(fixture["away"], c.get("away_full") or c["away"]),
                 name_similarity(fixture["away"], c["away"]))
        score = min(sh, sa)
        if score > best_score:
            best, best_score = c, score
    return best


def cross_check(cup_fixtures: list, fdo_fixtures: list) -> dict:
    """Controllo incrociato per la Champions: quante partite di ClubElo hanno un riscontro su
    football-data.org nella stessa finestra (e viceversa)."""
    window = {f["date"] for f in cup_fixtures}
    if not window:
        return {"clubelo": 0, "fdo": len(fdo_fixtures), "matched": 0, "only_clubelo": [], "only_fdo": []}
    lo, hi = min(window), max(window)
    fdo_in = [c for c in fdo_fixtures if lo <= c["date"] <= hi]
    used, only_clubelo = set(), []
    matched = 0
    for f in cup_fixtures:
        c = match_to_fdo(f, [x for x in fdo_in if id(x) not in used])
        if c is None:
            only_clubelo.append(f"{f['home']} - {f['away']} ({f['date']})")
        else:
            used.add(id(c))
            matched += 1
    only_fdo = [f"{c['home']} - {c['away']} ({c['date']})" for c in fdo_in if id(c) not in used]
    return {"clubelo": len(cup_fixtures), "fdo": len(fdo_in), "matched": matched,
            "only_clubelo": only_clubelo, "only_fdo": only_fdo}


def apply_results(history, finished: list, today, max_days: int = 1):
    """Risultati delle coppe nello storico (football-data.org, solo dove l'API li fornisce): per le righe di
    coppa giocate e senza risultato cerca la partita con data e nomi corrispondenti. Il risultato è quello
    dei 90 minuti (regularTime se c'è supplementari/rigori)."""
    import pandas as pd

    h = history.copy()
    today = pd.Timestamp(today)
    n_new = 0
    for i, row in h.iterrows():
        if row["league"] not in CUPS or pd.notna(row["result"]) or pd.Timestamp(row["match_date"]) > today:
            continue
        cand = [c for c in finished if c.get("cup") == row["league"]]
        m = match_to_fdo({"date": row["match_date"], "home": row["home"], "away": row["away"]}, cand, max_days)
        if m is None:
            continue
        h.at[i, "hg"], h.at[i, "ag"] = int(m["hg"]), int(m["ag"])
        h.at[i, "result"] = "H" if m["hg"] > m["ag"] else ("D" if m["hg"] == m["ag"] else "A")
        n_new += 1
    if n_new:
        log.info("Coppe: %d risultati nuovi nello storico", n_new)
    return h
