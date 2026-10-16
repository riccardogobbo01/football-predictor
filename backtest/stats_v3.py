"""
Modelli delle statistiche attese, versione s3-gap (config.STATS_VERSION): produzione del round 6.

  tiri, tiri in porta   Poisson attacco/difesa sostituito dai GAP ratings (backtest/gap.py) come feature proprie; ausiliaria = l'altra
                        statistica; feature comuni; Binomiale Negativa (alpha totale + alpha per squadra a momenti)
  corner                come prima (forze Poisson attacco/difesa sui corner, ausiliaria = tiri)
  gialli                come prima, con l'effetto arbitro (regressore ref_logR)
  falli                 nuovo: forze sui falli, ausiliaria = gialli, effetto arbitro sui falli (regressore ref_logR_f)
  copula gaussiana      ρ per statistica (tiri: per lega; corner e gialli: unica) per i mercati «chi ne fa di più» e gli handicap
  primo tempo           quota dei gol nel primo tempo per lega (training) applicata ai gol attesi del modello 1X2

Tutte le feature sono PRE-partita. Le due varianti (with_xg / without_xg) funzionano come per il modello 1X2.
"""
import numpy as np
import pandas as pd
from scipy.special import ndtr, ndtri
from scipy.stats import nbinom, poisson

from backtest import gap as G, stats_model as sm
from config import GAP_PARAMS

STATS3 = {
    "tiri":   dict(hc="HS", ac="AS", key="shots", own=("gap", "tiri"), aux=("sot_lmu", "sot_lnu"), lines=[23.5, 25.5, 27.5], M=60, team_interval=True),
    "sot":    dict(hc="HST", ac="AST", key="sot", own=("gap", "sot"), aux=("tiri_lh", "tiri_la"), lines=[7.5, 8.5, 9.5, 10.5], M=30, team_interval=True),
    "corner": dict(hc="HC", ac="AC", key="corners", own=("corner_lh", "corner_la"), aux=("tiri_lh", "tiri_la"), lines=[8.5, 9.5, 10.5, 11.5], M=36, team_interval=False),
    "gialli": dict(hc="HY", ac="AY", key="yellows", own=("gialli_lh", "gialli_la"), aux=("falli_lh", "falli_la"), lines=[2.5, 3.5, 4.5, 5.5], M=16,
                   referee="ref_logR", team_interval=False),
    "falli":  dict(hc="HF", ac="AF", key="fouls", own=("falli_lh", "falli_la"), aux=("gialli_lh", "gialli_la"), lines=[22.5, 24.5, 26.5], M=44,
                   referee="ref_logR_f", team_interval=False),
}
ORDER = ["tiri", "sot", "corner", "gialli", "falli"]
COPULA_PER_LEAGUE = {"tiri": True, "corner": False, "gialli": False}      # scelta del round 6 (regola J3 in validazione)
FIRST_TRAIN = sm.FIRST_TRAIN_SEASON
XG_COLS = sm.XG_COLS
GAP_STATS = {"tiri": ("HS", "AS"), "sot": ("HST", "AST")}
PAGE_NOTE = ("Modello validato con backtest. Queste statistiche variano molto da partita a partita: "
             "guarda l'intervallo e le probabilità, non solo il numero medio.")


# ───────────────────────────── feature ─────────────────────────────
def gap_priors(df: pd.DataFrame) -> dict:
    return {s: G.priors(df, hc, ac) for s, (hc, ac) in GAP_STATS.items()}


def gap_features(df: pd.DataFrame, priors: dict) -> pd.DataFrame:
    """log delle previsioni GAP pre-partita (tiri e tiri in porta) per tutte le partite di df."""
    out = {}
    for s, (hc, ac) in GAP_STATS.items():
        eta, gam = GAP_PARAMS[s]
        g = G.pre_match(df, hc, ac, eta, gam, priors[s])
        out[f"gap_{s}_lh"], out[f"gap_{s}_la"] = np.log(g.gap_h), np.log(g.gap_a)
    return pd.DataFrame(out, index=df.index)


def feature_names(stat: str, with_xg: bool = True, referee: bool = True) -> list:
    spec = STATS3[stat]
    names = ["own_lh", "own_la", "aux_lh", "aux_la"] + [c for c in sm.COMMON if with_xg or c not in XG_COLS]
    return names + ([spec["referee"]] if referee and "referee" in spec else [])


def design(feat: pd.DataFrame, stat: str, with_xg: bool = True, referee: bool = True) -> pd.DataFrame:
    spec = STATS3[stat]
    if spec["own"][0] == "gap":
        own = (f"gap_{spec['own'][1]}_lh", f"gap_{spec['own'][1]}_la")
    else:
        own = spec["own"]
    X = pd.DataFrame({"own_lh": feat[own[0]], "own_la": feat[own[1]], "aux_lh": feat[spec["aux"][0]], "aux_la": feat[spec["aux"][1]]}, index=feat.index)
    X = X.join(sm.common_frame(feat))
    if referee and "referee" in spec:
        X[spec["referee"]] = feat[spec["referee"]]
    return X[feature_names(stat, with_xg, referee)]


# ───────────────────────────── training ─────────────────────────────
FIRST_TEST = 2019


def base_predictions(feat: pd.DataFrame, stat: str):
    """Medie attese (mh, ma) del modello SENZA arbitro (variante with_xg): walk-forward per stagione dal 2019/20, in campione per il
    2016/17-2018/19 (previsioni del primo fold). Servono a calcolare l'effetto arbitro senza usare le partite future."""
    spec = STATS3[stat]
    X = design(feat, stat, True, referee=False)
    has = X.notna().all(axis=1)
    ok = has & feat[spec["hc"]].notna() & feat[spec["ac"]].notna()
    mh = pd.Series(np.nan, index=feat.index)
    ma = pd.Series(np.nan, index=feat.index)
    for s in sorted(feat.season.unique()):
        if s < FIRST_TEST:
            continue
        tr = ok & (feat.season >= FIRST_TRAIN) & (feat.season < s)
        te = has & (feat.season == s)
        if not te.any() or tr.sum() < 100:
            continue
        m = sm.fit_stat_model(X[tr], feat[spec["hc"]][tr], feat[spec["ac"]][tr])
        mh[te], ma[te] = sm.predict_means(m, X[te])
        if s == FIRST_TEST:
            mh[tr], ma[tr] = sm.predict_means(m, X[tr])
    return mh, ma


def moments(y, m) -> float:
    y, m = np.asarray(y, float), np.asarray(m, float)
    ok = np.isfinite(y) & np.isfinite(m)
    y, m = y[ok], m[ok]
    return max(float(((y - m) ** 2 - m).sum() / (m ** 2).sum()), 1e-4)


def estimate_rho(yh, ya, mh, ma, alpha, division=None, seed=17):
    """Correlazione tra i punteggi normali di una PIT randomizzata dei residui (campione di training). Scalare, oppure dict per lega."""
    rng = np.random.default_rng(seed)
    zs = []
    for y, m in ((yh.astype(int), mh), (ya.astype(int), ma)):
        n = 1.0 / alpha
        p = n / (n + m)
        lo, hi = nbinom.cdf(y - 1, n, p), nbinom.cdf(y, n, p)
        zs.append(ndtri(np.clip(lo + rng.uniform(size=len(y)) * (hi - lo), 1e-9, 1 - 1e-9)))
    if division is None:
        return float(np.corrcoef(zs[0], zs[1])[0, 1])
    return {str(lg): float(np.corrcoef(zs[0][division == lg], zs[1][division == lg])[0, 1]) for lg in np.unique(division)}


def train_stat(feat: pd.DataFrame, stat: str, with_xg: bool):
    """Modello finale su tutto lo storico dal 2016/17. Restituisce (dict JSON, medie in campione mh, ma, maschera di training)."""
    spec = STATS3[stat]
    X = design(feat, stat, with_xg)
    ok = X.notna().all(axis=1) & np.isfinite(X).all(axis=1) & feat[spec["hc"]].notna() & feat[spec["ac"]].notna() & (feat.season >= FIRST_TRAIN)
    model = sm.fit_stat_model(X[ok], feat[spec["hc"]][ok], feat[spec["ac"]][ok])
    d = sm.model_to_dict(model, X.columns, meta={"n_train": int(ok.sum())})
    mh, ma = sm.predict_means(model, X[ok])
    d["alpha_team"] = moments(np.r_[feat[spec["hc"]][ok], feat[spec["ac"]][ok]], np.r_[mh, ma])
    sample = X[ok].iloc[:: max(int(ok.sum()) // 500, 1)]
    a, b = sm.means_from_dict(d, sample.to_numpy())
    pa, pb = sm.predict_means(model, sample)
    if not (np.allclose(a, pa) and np.allclose(b, pb)):
        raise SystemExit(f"ERRORE: il modello {stat}/{'with_xg' if with_xg else 'without_xg'} serializzato non coincide con scikit-learn")
    return d, mh, ma, ok


def train_first_half(feat: pd.DataFrame) -> dict:
    """Quota dei gol segnati nel primo tempo, per lega (stagioni dal 2016/17 con punteggio al riposo)."""
    f = feat[(feat.season >= FIRST_TRAIN) & feat.HTHG.notna() & feat.HTAG.notna()]
    share = {str(lg): float((g.HTHG + g.HTAG).sum() / (g.hg + g.ag).sum()) for lg, g in f.groupby("Division")}
    return {"share": share, "all": float((f.HTHG + f.HTAG).sum() / (f.hg + f.ag).sum()), "n": int(len(f))}


# ───────────────────────────── serving ─────────────────────────────
def team_alpha_arrays(d: dict, n: int):
    return np.full(n, d["alpha_team"]), np.full(n, d["alpha"])


def _q(m, alpha, q):
    n = 1.0 / alpha
    return nbinom.ppf(q, n, n / (n + m))


def page_rows(stat: str, mh, ma, d: dict) -> list:
    """Una riga per partita: valore per squadra, totale, intervallo all'80% del totale (e delle squadre per tiri e tiri in porta),
    probabilità Over delle linee del totale (Binomiale Negativa)."""
    spec = STATS3[stat]
    mh, ma = np.asarray(mh, float), np.asarray(ma, float)
    at, aT = d["alpha_team"], d["alpha"]
    m = mh + ma
    n = 1.0 / aT
    p = n / (n + m)
    lo, hi = nbinom.ppf(0.10, n, p), nbinom.ppf(0.90, n, p)
    over = {L: 1 - nbinom.cdf(np.floor(L), n, p) for L in spec["lines"]}
    rows = []
    for i in range(len(m)):
        r = {"home": round(float(mh[i]), 1), "away": round(float(ma[i]), 1), "total": round(float(m[i]), 1),
             "lo80": int(lo[i]), "hi80": int(hi[i]), "over": {f"{L:g}": round(float(over[L][i]), 4) for L in spec["lines"]}}
        if spec["team_interval"]:
            r["home_lo80"], r["home_hi80"] = int(_q(mh[i], at, 0.10)), int(_q(mh[i], at, 0.90))
            r["away_lo80"], r["away_hi80"] = int(_q(ma[i], at, 0.10)), int(_q(ma[i], at, 0.90))
        rows.append(r)
    return rows


# ───────────────────────────── copula gaussiana ─────────────────────────────
Z_GRID = np.linspace(-7.0, 7.0, 561)
_DZ = Z_GRID[1] - Z_GRID[0]
_WZ = np.exp(-0.5 * Z_GRID ** 2) / np.sqrt(2 * np.pi) * _DZ


def _joint_pmf(F_h, F_a, rho):
    pm_h, pm_a = np.diff(np.r_[0.0, F_h]), np.diff(np.r_[0.0, F_a])
    if abs(rho) < 1e-9:
        return np.outer(pm_h, pm_a)
    a = ndtri(np.clip(F_h, 1e-12, 1 - 1e-12))
    b = ndtri(np.clip(F_a, 1e-12, 1 - 1e-12))
    s = np.sqrt(1 - rho ** 2)
    C = ndtr((b[None, :] - rho * Z_GRID[:, None]) / s)
    H = np.cumsum(_WZ[:, None] * C, axis=0)
    pos = np.clip(np.searchsorted(Z_GRID, a), 1, len(Z_GRID) - 1)
    t = np.clip((a - Z_GRID[pos - 1]) / _DZ, 0, 1)
    P2 = np.pad(H[pos - 1, :] * (1 - t)[:, None] + H[pos, :] * t[:, None], ((1, 0), (1, 0)))
    return P2[1:, 1:] - P2[:-1, 1:] - P2[1:, :-1] + P2[:-1, :-1]


def diff_pmf(mh, ma, alpha_team, rho, M):
    """pmf di (casa − ospite) per ogni partita (indice M = differenza 0), marginali NB(media, alpha_team) e copula gaussiana."""
    mh, ma = np.asarray(mh, float), np.asarray(ma, float)
    n = len(mh)
    rho = np.broadcast_to(np.asarray(rho, float), (n,))
    k = np.arange(M + 1)
    i, j = np.meshgrid(k, k, indexing="ij")
    idx = (i - j + M).ravel()
    nb = 1.0 / alpha_team
    Fh = nbinom.cdf(k[None, :], nb, (nb / (nb + mh))[:, None])
    Fa = nbinom.cdf(k[None, :], nb, (nb / (nb + ma))[:, None])
    out = np.zeros((n, 2 * M + 1))
    for r in range(n):
        pmf = np.clip(_joint_pmf(Fh[r], Fa[r], rho[r]), 0, None)
        out[r] = np.bincount(idx, weights=(pmf / pmf.sum()).ravel(), minlength=2 * M + 1)
    return out


def who_more(dif, M) -> np.ndarray:
    """(n, 3): P(casa > ospite), P(pari), P(ospite > casa)."""
    return np.column_stack([dif[:, M + 1:].sum(1), dif[:, M], dif[:, :M].sum(1)])


def handicap_15(dif, M) -> dict:
    """Handicap ±1,5: casa −1,5 = casa vince di almeno 2; ospite −1,5 = ospite vince di almeno 2; i lati +1,5 sono i complementari."""
    h = dif[:, M + 2:].sum(1)
    a = dif[:, :M - 1].sum(1)
    return {"home_m15": h, "home_p15": 1 - a, "away_m15": a, "away_p15": 1 - h}


def rho_for(copula: dict, stat: str, division: str) -> float:
    c = copula[stat]
    if isinstance(c["rho"], dict):
        v = c["rho"].get(division)
        return float(v) if v is not None else float(np.mean(list(c["rho"].values())))
    return float(c["rho"])


# ───────────────────────────── primo tempo ─────────────────────────────
def first_half(mu, nu, share: float, G_=8) -> dict:
    """1X2 al riposo e Over 0.5 / 1.5 del primo tempo (Poisson indipendenti con media = quota × gol attesi della partita)."""
    m1, n1 = share * np.asarray(mu, float), share * np.asarray(nu, float)
    k = np.arange(G_ + 1)
    pm, pn = poisson.pmf(k[None, :], m1[:, None]), poisson.pmf(k[None, :], n1[:, None])
    J = pm[:, :, None] * pn[:, None, :]
    J /= J.sum((1, 2), keepdims=True)
    i, j = np.indices((G_ + 1, G_ + 1))
    lam = m1 + n1
    return {"home": (J * (i > j)).sum((1, 2)), "draw": (J * (i == j)).sum((1, 2)), "away": (J * (i < j)).sum((1, 2)),
            "o05": 1 - np.exp(-lam), "o15": 1 - np.exp(-lam) * (1 + lam), "exp_home": m1, "exp_away": n1, "exp_total": lam}
