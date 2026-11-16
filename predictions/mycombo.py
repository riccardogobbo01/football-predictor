"""MyCombo: simulazione congiunta per partita e proposta di combo (solo campionati). Nessun collegamento a bookmaker, nessuna quota reale: tutto e' probabilita' del modello.

Scenari coerenti (N = 20.000 per partita):
  1. punteggio dalla matrice di Dixon-Coles dello stack (mu, nu, rho): gol casa e ospite esatti;
  2. primo tempo: i gol di ciascuna squadra si «assottigliano» con probabilita' = quota di lega dei gol del primo tempo (Binomiale);
  3. tiri, tiri in porta, corner, gialli e falli di ciascuna squadra: marginali Binomiali Negative dei modelli delle statistiche (medie con livello stagionale e arbitro,
     dispersioni per squadra), legate tra loro e ai gol da una COPULA GAUSSIANA a 12 variabili (gol, tiri, tiri in porta, corner, gialli, falli, casa e ospite).
     La matrice di correlazione e' stimata sui residui (PIT) delle previsioni fuori campione dei modelli (backtest/run_mycombo.py → models/mycombo_corr.json): comprende
     la dipendenza casa-ospite di ogni statistica (copula gia' presente nelle statistiche), quella tra statistiche diverse e quella tra gol e statistiche (stato di gara:
     chi segna tira, batte corner e subisce falli in modo diverso). I gol campionati dalla matrice restano esatti: le statistiche dipendono dai loro punteggi normali.
  4. ogni giocata e' un evento sullo stesso scenario: la probabilita' di una combo e' la frazione di scenari in cui tutte le sue giocate sono vere.

La generazione propone 2-3 combo da 3-5 giocate con quota equa (1/probabilita' congiunta) tra 2,0 e 3,0, senza giocate ridondanti e senza combo quasi identiche."""
import numpy as np
from scipy.special import ndtr, ndtri
from scipy.stats import nbinom

from backtest import models

VARS = ["gol_c", "gol_o", "tiri_c", "tiri_o", "sot_c", "sot_o", "corner_c", "corner_o", "gialli_c", "gialli_o", "falli_c", "falli_o"]
STATS = ("tiri", "sot", "corner", "gialli", "falli")
KMAX = {"tiri": 70, "sot": 35, "corner": 40, "gialli": 18, "falli": 50}
N_SIM = 20000
G = 10
ODDS_MIN, ODDS_MAX = 2.0, 3.0
MIN_LEGS, MAX_LEGS = 3, 5
N_CAND = {3: 2000, 4: 4000, 5: 6000}     # candidate per numero di giocate
MAX_COMBOS = 3
REDUNDANT = 0.97            # P(B | A) >= 0,97 con A la meno probabile: A implica (quasi) B → giocata ridondante
MAX_SHARED_LEGS = 1         # due combo proposte per la stessa partita condividono al massimo una giocata
_POP = np.array([bin(i).count("1") for i in range(256)], dtype=np.int32)


# ───────────────────────────── simulazione ─────────────────────────────
def goal_latents(hg, ag, M, rng):
    """Punteggi normali (PIT randomizzata) dei gol campionati rispetto alle loro marginali della matrice dei punteggi (M: (G+1, G+1))."""
    out = []
    for g, marg in ((hg, M.sum(1)), (ag, M.sum(0))):
        F = np.cumsum(marg)
        lo = np.where(g > 0, F[np.maximum(g - 1, 0)], 0.0)
        hi = F[g]
        u = lo + rng.random(len(g)) * (hi - lo)
        out.append(ndtri(np.clip(u, 1e-9, 1 - 1e-9)))
    return np.column_stack(out)


def prepare_corr(corr) -> dict:
    """Pre-calcola la distribuzione condizionata delle 10 variabili delle statistiche dati i due punteggi normali dei gol."""
    C = np.asarray(corr, float)
    g, s = [0, 1], list(range(2, 12))
    Sgg, Ssg, Sss = C[np.ix_(g, g)], C[np.ix_(s, g)], C[np.ix_(s, s)]
    A = Ssg @ np.linalg.inv(Sgg)
    cond = Sss - A @ Ssg.T
    cond = (cond + cond.T) / 2
    w, V = np.linalg.eigh(cond)
    L = V @ np.diag(np.sqrt(np.maximum(w, 1e-9)))
    return {"A": A, "L": L}


def nb_table(m, alpha, K):
    n = 1.0 / alpha
    return nbinom.cdf(np.arange(K + 1), n, n / (n + m))


def simulate(p: dict, cc: dict, n: int = N_SIM, seed: int = 0) -> dict:
    """p = {mu, nu, rho, share, stats: {stat: (mh, ma, alpha_casa, alpha_ospite)}}; cc = prepare_corr(...). Restituisce gli scenari (array int16 di lunghezza n)."""
    rng = np.random.default_rng(seed)
    M = models.score_matrix(np.array([p["mu"]], float), np.array([p["nu"]], float), np.array([p["rho"]], float), G)[0]
    c = np.cumsum(M.ravel())
    idx = np.minimum(np.searchsorted(c, rng.random(n) * c[-1]), M.size - 1)
    hg, ag = idx // (G + 1), idx % (G + 1)
    zg = goal_latents(hg, ag, M, rng)
    Z = zg @ cc["A"].T + rng.standard_normal((n, 10)) @ cc["L"].T
    U = ndtr(Z)
    out = {"hg": hg.astype(np.int16), "ag": ag.astype(np.int16)}
    for j, stat in enumerate(STATS):
        mh, ma, ah, aa = p["stats"][stat]
        K = KMAX[stat]
        for side, m, a, col in (("c", mh, ah, 2 * j), ("o", ma, aa, 2 * j + 1)):
            cdf = nb_table(float(m), float(a), K)
            out[f"{stat}_{side}"] = np.minimum(np.searchsorted(cdf, U[:, col], side="left"), K).astype(np.int16)
    out["hth"] = rng.binomial(hg, p["share"]).astype(np.int16)
    out["ath"] = rng.binomial(ag, p["share"]).astype(np.int16)
    return out


# ───────────────────────────── giocate ─────────────────────────────
def _num(x):
    return f"{x:.1f}".replace(".", ",")


def eval_spec(spec, v):
    """Valuta una giocata su scenari o su valori reali. v: dict hg, ag, hth, ath, tiri_c, tiri_o, sot_c, sot_o, corner_c, corner_o, gialli_c, gialli_o (array o scalari)."""
    kind = spec[0]
    if kind == "res":
        hg, ag = v["hg"], v["ag"]
        r = np.where(hg > ag, 0, np.where(hg == ag, 1, 2))
        return np.isin(r, spec[1])
    if kind == "htres":
        h, a = v["hth"], v["ath"]
        r = np.where(h > a, 0, np.where(h == a, 1, 2))
        return np.isin(r, spec[1])
    if kind == "gtot":
        t = v["hg"] + v["ag"]
        return (t > spec[2]) if spec[1] == "over" else (t < spec[2])
    if kind == "btts":
        b = (v["hg"] > 0) & (v["ag"] > 0)
        return b if spec[1] else ~b
    if kind == "htou":
        return (v["hth"] + v["ath"]) > spec[1]
    if kind == "team":
        x = v[f"{spec[1]}_{spec[2]}"]
        return (x > spec[4]) if spec[3] == "over" else (x < spec[4])
    if kind == "tot":
        x = v[f"{spec[1]}_c"] + v[f"{spec[1]}_o"]
        return (x > spec[3]) if spec[2] == "over" else (x < spec[3])
    raise ValueError(spec)


STAT_LABEL = {"tiri": "tiri", "sot": "tiri in porta", "corner": "corner", "gialli": "gialli"}
SIDE_LABEL = {"c": "Casa", "o": "Ospite"}
RES_LABEL = {(0,): "1", (1,): "X", (2,): "2", (0, 1): "1X", (0, 2): "12", (1, 2): "X2"}


def label(spec) -> str:
    k = spec[0]
    if k == "res":
        return RES_LABEL[tuple(spec[1])]
    if k == "htres":
        return "1T: " + RES_LABEL[tuple(spec[1])]
    if k == "gtot":
        return f"{'Over' if spec[1] == 'over' else 'Under'} {_num(spec[2])} gol"
    if k == "btts":
        return "Gol" if spec[1] else "No Gol"
    if k == "htou":
        return f"1T Over {_num(spec[1])} gol"
    if k == "team":
        return f"{SIDE_LABEL[spec[2]]} {'Over' if spec[3] == 'over' else 'Under'} {_num(spec[4])} {STAT_LABEL[spec[1]]}"
    if k == "tot":
        tail = " (indicativo)" if spec[1] == "corner" else ""
        return f"{'Over' if spec[2] == 'over' else 'Under'} {_num(spec[3])} {STAT_LABEL[spec[1]]} totali{tail}"
    raise ValueError(spec)


def family(spec) -> str:
    k = spec[0]
    if k == "team":
        return f"{spec[1]}_{spec[2]}"
    if k == "tot":
        return f"{spec[1]}_t"
    return {"res": "res", "htres": "htres", "gtot": "gtot", "btts": "btts", "htou": "htou"}[k]


def _lines(m, lo=0.5):
    b = int(np.floor(m))
    return [b + d + 0.5 for d in (-1, 0, 1) if b + d + 0.5 >= lo]


def catalog(p: dict) -> list:
    """Giocate candidate di una partita (linee intorno alla media attesa per le statistiche): [spec, ...]."""
    specs = []
    for r in ((0,), (1,), (2,), (0, 1), (0, 2), (1, 2)):
        specs.append(("res", r))
    for line in (1.5, 2.5, 3.5):
        specs += [("gtot", "over", line), ("gtot", "under", line)]
    specs += [("btts", True), ("btts", False)]
    for r in ((0,), (1,), (2,)):
        specs.append(("htres", r))
    specs += [("htou", 0.5), ("htou", 1.5)]
    for stat in ("tiri", "sot"):
        mh, ma = p["stats"][stat][:2]
        for side, m in (("c", mh), ("o", ma)):
            for line in _lines(m):
                specs += [("team", stat, side, "over", line), ("team", stat, side, "under", line)]
    for stat in ("corner", "gialli"):
        mt = p["stats"][stat][0] + p["stats"][stat][1]
        for line in _lines(mt):
            specs += [("tot", stat, "over", line), ("tot", stat, "under", line)]
    return specs


# ───────────────────────────── generazione ─────────────────────────────
def _jaccard_shared(a, b):
    return len(set(a) & set(b))


def generate(sim: dict, specs: list, seed: int = 0, n_cand: dict | None = None, max_combos: int = MAX_COMBOS) -> dict:
    """Combo candidate (3-5 giocate di famiglie diverse, giocate piu' probabili campionate piu' spesso, quota equa tra 2,0 e 3,0, senza ridondanze), scelte con punteggio
    |ln(p congiunta / prodotto delle p singole)| / (k - 1) (quanto contano le correlazioni): prima la migliore per ciascun numero di giocate (3, 4, 5), poi le migliori restanti,
    fino a `max_combos`, con al piu' MAX_SHARED_LEGS giocate in comune tra due combo. Restituisce {'p_legs': ..., 'combos': [...]} (indici nelle giocate)."""
    n_cand = n_cand or N_CAND
    rng = np.random.default_rng(seed + 7919)
    B = np.stack([eval_spec(s, sim) for s in specs])                       # (L, N) bool
    L, N = B.shape
    pl = B.mean(1)
    Bf = B.astype(np.float32)
    J = (Bf @ Bf.T) / N
    with np.errstate(divide="ignore", invalid="ignore"):
        cond_ab = np.where(pl[:, None] > 0, J / pl[:, None], 0.0)          # P(B | A)
    bad = (cond_ab >= REDUNDANT) & (pl[:, None] <= pl[None, :] + 1e-12)    # A (meno probabile) implica B
    bad = bad | bad.T
    np.fill_diagonal(bad, False)
    fams = [family(s) for s in specs]
    fam_names = sorted(set(fams))
    members, cumw = {}, {}
    for f in fam_names:
        mem = np.array([i for i, x in enumerate(fams) if x == f])
        w = np.where((pl[mem] > 0.02) & (pl[mem] < 0.98), pl[mem], 0.0)
        if w.sum() > 0:
            members[f], cumw[f] = mem, np.cumsum(w) / w.sum()
    usable = sorted(members)
    Bp = np.packbits(B, axis=1)
    cands = {k: [] for k in range(MIN_LEGS, MAX_LEGS + 1)}
    for k in range(MIN_LEGS, MAX_LEGS + 1):
        n_k = n_cand[k]
        F = len(usable)
        per_fam = np.empty((n_k, F), dtype=np.int64)
        for fi, f in enumerate(usable):
            per_fam[:, fi] = members[f][np.minimum(np.searchsorted(cumw[f], rng.random(n_k)), len(members[f]) - 1)]
        pick = np.argsort(rng.random((n_k, F)), axis=1)[:, :k]            # k famiglie distinte per candidato
        idx = np.take_along_axis(per_fam, pick, axis=1)
        acc = Bp[idx[:, 0]].copy()
        for j in range(1, k):
            acc &= Bp[idx[:, j]]
        pj = _POP[acc].sum(1) / N
        pind = np.prod(pl[idx], axis=1)
        ok = (pj >= 1.0 / ODDS_MAX) & (pj <= 1.0 / ODDS_MIN)
        for a in range(k):
            for b in range(a + 1, k):
                ok &= ~bad[idx[:, a], idx[:, b]]
        for r in np.where(ok)[0]:
            score = abs(np.log(pj[r] / max(pind[r], 1e-12))) / (k - 1)
            cands[k].append((float(score), tuple(sorted(idx[r].tolist())), float(pj[r]), float(pind[r])))
        cands[k].sort(key=lambda x: -x[0])
    chosen, seen = [], set()

    def take(item, k):
        score, legs, pj, pind = item
        if legs in seen or any(_jaccard_shared(legs, c["legs"]) > MAX_SHARED_LEGS for c in chosen):
            return False
        seen.add(legs)
        chosen.append({"legs": list(legs), "p": pj, "fair": 1.0 / pj, "p_indep": pind, "score": score, "k": k})
        return True

    for k in range(MIN_LEGS, MAX_LEGS + 1):                               # la migliore per ciascun numero di giocate
        for item in cands[k]:
            if len(chosen) < max_combos and take(item, k):
                break
    rest = sorted([(it, k) for k in cands for it in cands[k]], key=lambda x: -x[0][0])
    for item, k in rest:                                                  # poi le migliori restanti
        if len(chosen) >= max_combos:
            break
        take(item, k)
    chosen.sort(key=lambda c: c["k"])
    return {"p_legs": pl, "combos": chosen}


def combo_hit(legs, specs, actual) -> bool:
    return bool(all(eval_spec(specs[i], actual) for i in legs))


# ───────────────────────────── produzione: una partita ─────────────────────────────
import json
import os
import re
import zlib

import pandas as pd

N_WEB = 4000                  # scenari salvati per il browser («componi tu»): i primi N_WEB dei 20.000 (stessa simulazione); errore standard <= 0,8 punti
WEB_DAYS = 4                  # file di scenari solo per le partite dei prossimi WEB_DAYS giorni (il repository non deve crescere inutilmente)
WEB_COLS = ["hg", "ag", "hth", "ath", "tiri_c", "tiri_o", "sot_c", "sot_o", "corner_t", "gialli_t"]
STAT_KEYS = {"tiri": "shots", "sot": "sot", "corner": "corners", "gialli": "yellows", "falli": "fouls"}


def fixture_params(pred, stats, share):
    """Parametri della simulazione dalla previsione di una partita (predictions.json): None se mancano."""
    sim = (pred or {}).get("sim")
    if not sim or not stats or share is None:
        return None
    st = {}
    for stat, key in STAT_KEYS.items():
        row = stats.get(key)
        if not row or "sim" not in row:
            return None
        st[stat] = tuple(float(x) for x in row["sim"])
    return {"mu": float(sim["mu"]), "nu": float(sim["nu"]), "rho": float(sim["rho"]), "share": float(share), "stats": st}


def seed_for(league: str, date: str, home: str, away: str) -> int:
    return zlib.crc32(f"{league}|{date}|{home}|{away}".encode("utf-8")) % (2 ** 31)


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def compact(sim: dict, n: int = N_WEB) -> bytes:
    """Scenari per il browser: file binario, una riga di 10 byte per scenario (gol, gol primo tempo, tiri e tiri in porta per squadra, corner e gialli totali)."""
    cols = [sim["hg"], sim["ag"], sim["hth"], sim["ath"], sim["tiri_c"], sim["tiri_o"], sim["sot_c"], sim["sot_o"],
            sim["corner_c"] + sim["corner_o"], sim["gialli_c"] + sim["gialli_o"]]
    arr = np.stack([np.minimum(c[:n], 255).astype(np.uint8) for c in cols], axis=1)          # (n, 10), riga = scenario
    return arr.tobytes()


def build_fixture(league: str, fix: dict, share, cc: dict, with_file: bool = True):
    """(vista per la pagina, nome file, byte degli scenari) di una partita di campionato; None se mancano i parametri. Seed fisso per partita: stesso input, stesse combo.
    with_file=False: nessun file di scenari (partite oltre WEB_DAYS giorni): la vista porta file = None."""
    p = fixture_params(fix.get("prediction"), fix.get("expected_stats"), share)
    if p is None:
        return None
    seed = seed_for(league, fix["date"], fix["home"], fix["away"])
    sim = simulate(p, cc, N_SIM, seed)
    specs = catalog(p)
    gen = generate(sim, specs, seed)
    combos = [{"specs": [list(specs[i]) for i in c["legs"]], "p": round(c["p"], 5), "fair": round(c["fair"], 3), "p_indep": round(c["p_indep"], 5), "k": c["k"]} for c in gen["combos"]]
    name = f"{league}_{fix['date']}_{slug(fix['home'])}_{slug(fix['away'])}.bin"
    view = {"combos": combos, "file": f"mycombo/{name}" if with_file else None, "n": N_SIM, "n_web": N_WEB, "web_days": WEB_DAYS, "referee": fix.get("referee")}
    return view, name, (compact(sim) if with_file else None)


def write_scenarios(out_dir: str, payloads: dict) -> int:
    """Scrive docs/mycombo/*.bin (solo i file nuovi o cambiati) e rimuove quelli di partite non piu' in elenco. Restituisce i file scritti."""
    d = os.path.join(out_dir, "mycombo")
    os.makedirs(d, exist_ok=True)
    n = 0
    for name, data in payloads.items():
        fp = os.path.join(d, name)
        if os.path.exists(fp) and open(fp, "rb").read() == data:
            continue
        open(fp, "wb").write(data)
        n += 1
    for f in os.listdir(d):
        if (f.endswith(".bin") or f.endswith(".json")) and f not in payloads:
            os.remove(os.path.join(d, f))
    return n


# ───────────────────────────── registro a carta ─────────────────────────────
REG_COLS = ["issued_on", "league", "match_date", "kickoff_utc", "home", "away", "home_dc", "away_dc", "idx", "k", "legs", "specs", "p_joint", "fair_odds", "p_indep",
            "settled", "hit", "leg_hits", "settled_on"]
REG_KEY = ["league", "match_date", "home", "away"]
LEAGUE_DIV = {"serie_a": "I1", "premier_league": "E0", "bundesliga": "D1", "la_liga": "SP1", "ligue_1": "F1"}
NEEDS = {"res": ("hg", "ag"), "htres": ("hth", "ath"), "gtot": ("hg", "ag"), "btts": ("hg", "ag"), "htou": ("hth", "ath")}


def spec_needs(spec):
    if spec[0] == "team":
        return (f"{spec[1]}_{spec[2]}",)
    if spec[0] == "tot":
        return (f"{spec[1]}_c", f"{spec[1]}_o")
    return NEEDS[spec[0]]


def canon(spec):
    """Specifica da JSON (liste) a tuple, come nel catalogo."""
    return tuple(tuple(x) if isinstance(x, list) else x for x in spec)


def reg_load(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame(columns=REG_COLS)
    df = pd.read_csv(path, dtype={c: str for c in ("issued_on", "league", "match_date", "kickoff_utc", "home", "away", "home_dc", "away_dc", "legs", "specs", "leg_hits", "settled_on")})
    for c in REG_COLS:
        if c not in df:
            df[c] = np.nan
    return df[REG_COLS]


def reg_save(df: pd.DataFrame, path: str):
    out = df.copy()
    for c in ("p_joint", "p_indep"):
        out[c] = out[c].astype(float).round(5)
    out["fair_odds"] = out["fair_odds"].astype(float).round(3)
    out.to_csv(path, index=False)


def reg_update(df: pd.DataFrame, items: list, now) -> pd.DataFrame:
    """items: [(league, fix, view)] delle partite con combo. Fino al calcio d'inizio le combo della partita si aggiornano a ogni emissione (resta l'ultima prima della partita,
    come lo storico delle previsioni); dopo il calcio d'inizio la riga e' congelata."""
    now = pd.Timestamp(now)
    now = now.tz_localize("UTC") if now.tzinfo is None else now.tz_convert("UTC")
    rows = []
    for league, fix, view in items:
        ko = pd.Timestamp(f"{fix['date']} {fix['time']}", tz="UTC")
        if ko <= now:
            continue
        if len(df):
            same = (df["league"] == league) & (df["match_date"] == fix["date"]) & (df["home"] == fix["home"]) & (df["away"] == fix["away"])
            df = df[~(same & (df["settled"].fillna(0).astype(int) == 0))]
        for i, c in enumerate(view["combos"]):
            labels = [label(canon(s)) for s in c["specs"]]
            rows.append({"issued_on": now.strftime("%Y-%m-%d"), "league": league, "match_date": fix["date"], "kickoff_utc": f"{fix['date']} {fix['time']}",
                         "home": fix["home"], "away": fix["away"], "home_dc": fix.get("home_dc"), "away_dc": fix.get("away_dc"), "idx": i, "k": c["k"], "legs": " + ".join(labels),
                         "specs": json.dumps(c["specs"], separators=(",", ":")), "p_joint": c["p"], "fair_odds": c["fair"], "p_indep": c["p_indep"],
                         "settled": 0, "hit": np.nan, "leg_hits": np.nan, "settled_on": np.nan})
    if rows:
        df = pd.concat([df, pd.DataFrame(rows, columns=REG_COLS)], ignore_index=True)
    return df


def reg_settle(df: pd.DataFrame, matches: pd.DataFrame, now) -> int:
    """Esito delle combo di partite finite, dal CSV di football-data.co.uk (serve ogni dato delle giocate: gol, primo tempo, tiri, tiri in porta, corner, gialli).
    Una combo senza tutti i dati resta in attesa. Restituisce le combo chiuse."""
    if df.empty or matches is None or not len(matches):
        return 0
    m = matches.copy()
    m["dday"] = pd.to_datetime(m["date"]).dt.normalize()
    idx = {}
    for r in m.itertuples(index=False):
        idx.setdefault((r.Division, r.HomeTeam, r.AwayTeam), []).append(r)
    n = 0
    for i in df.index[df["settled"].fillna(0).astype(int) == 0]:
        row = df.loc[i]
        cand = idx.get((LEAGUE_DIV.get(row["league"]), row["home_dc"], row["away_dc"]), [])
        day = pd.Timestamp(row["match_date"])
        r = next((c for c in cand if abs((c.dday - day).days) <= 1), None)
        if r is None:
            continue
        v = {"hg": r.hg, "ag": r.ag, "hth": r.HTHG, "ath": r.HTAG, "tiri_c": r.HS, "tiri_o": r.AS, "sot_c": r.HST, "sot_o": r.AST,
             "corner_c": r.HC, "corner_o": r.AC, "gialli_c": r.HY, "gialli_o": r.AY}
        specs = [canon(s) for s in json.loads(row["specs"])]
        if any(not np.isfinite(float(v[k])) for s in specs for k in spec_needs(s)):
            continue
        hits = [bool(eval_spec(s, {k: float(x) for k, x in v.items()})) for s in specs]
        df.at[i, "settled"], df.at[i, "hit"] = 1, int(all(hits))
        df.at[i, "leg_hits"] = "|".join("1" if h else "0" for h in hits)
        df.at[i, "settled_on"] = pd.Timestamp(now).strftime("%Y-%m-%d")
        n += 1
    return n


def reg_summary(path: str) -> dict:
    """Per il resoconto: combo proposte, chiuse e vinte, probabilita' prevista media contro frequenza reale (IC a blocchi per settimana da 100 combo chiuse)."""
    from predictions.paper_monitor import _block_ci
    df = reg_load(path)
    out = {"proposed": int(len(df)), "matches": int(len(df[REG_KEY].drop_duplicates())) if len(df) else 0, "settled": 0, "won": 0}
    s = df[df["settled"].fillna(0).astype(int) == 1].copy()
    if s.empty:
        return out
    s["hit"] = s["hit"].astype(float)
    out.update(settled=int(len(s)), won=int(s["hit"].sum()), p_mean=float(s["p_joint"].mean()), real=float(s["hit"].mean()), p_indep=float(s["p_indep"].mean()),
               fair_mean=float(s["fair_odds"].mean()), roi_fair=float((s["hit"] * s["fair_odds"] - 1).mean()))
    if len(s) >= 100:
        weeks = pd.to_datetime(s["match_date"]).dt.strftime("%G-%V").to_numpy()
        out["gap_ci"] = _block_ci((s["hit"] - s["p_joint"]).to_numpy(), np.ones(len(s)), weeks, 3)
    out["by_k"] = {int(k): {"n": int(len(g)), "p": float(g["p_joint"].mean()), "real": float(g["hit"].mean())} for k, g in s.groupby("k")}
    return out
