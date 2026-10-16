"""
Round 6 (solo backtest): modelli delle statistiche attese (tiri, tiri in porta, corner, gialli, falli), distribuzioni per squadra e
sul totale, copula gaussiana, GAP ratings e metriche. Definizioni fissate in backtest/round6_parts/prereg.md.
Niente di qui modifica la produzione: `stats_model.STATS` non viene toccato (le statistiche nuove hanno specifiche locali).
"""
import os

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.special import ndtr, ndtri
from scipy.stats import nbinom

from backtest import data, features, models, refeffect, round3_ctx as C3, stack, stats_model as sm
from config import REFEREE_K

FIRST_TRAIN, FIRST_TEST = 2016, 2019
R6_DIR = C3.R3_DIR

SPECS = {
    "tiri":   dict(hc="HS", ac="AS", own=("tiri_lh", "tiri_la"), aux=("sot_lmu", "sot_lnu"), M=60,
                   lines_T=[23.5, 25.5, 27.5], lines_t=[10.5, 12.5, 14.5]),
    "sot":    dict(hc="HST", ac="AST", own=("sot_lh", "sot_la"), aux=("tiri_lh", "tiri_la"), M=30,
                   lines_T=[7.5, 8.5, 9.5, 10.5], lines_t=[3.5, 4.5, 5.5]),
    "corner": dict(hc="HC", ac="AC", own=("corner_lh", "corner_la"), aux=("tiri_lh", "tiri_la"), M=36,
                   lines_T=[8.5, 9.5, 10.5, 11.5], lines_t=[3.5, 4.5, 5.5, 6.5]),
    "gialli": dict(hc="HY", ac="AY", own=("gialli_lh", "gialli_la"), aux=("falli_lh", "falli_la"), M=16,
                   lines_T=[2.5, 3.5, 4.5, 5.5], lines_t=[1.5, 2.5]),
    "falli":  dict(hc="HF", ac="AF", own=("falli_lh", "falli_la"), aux=("gialli_lh", "gialli_la"), M=44,
                   lines_T=[22.5, 24.5, 26.5], lines_t=[10.5, 12.5, 14.5]),
}


# ───────────────────────────── dati e feature ─────────────────────────────
def _sot_job(g):
    return models.walk_forward_dc(g, features.STAT_XI, start=features.XG_START, use_tau=False, gx="HST", gy="AST",
                                  ridge=features.STAT_RIDGE)


def sot_features(df):
    st = features.build_stat_features(df, verbose=False)
    if {"sot_lh", "sot_la"} <= set(st.columns):                       # dalla produzione s3-gap: stesso Poisson (xi, ridge, finestra) dei tiri in porta
        return st[["sot_lh", "sot_la"]]
    path = os.path.join(R6_DIR, "r6_sot.pkl")
    key = (len(df), str(df.date.max()))
    if os.path.exists(path):
        d = pd.read_pickle(path)
        if d["key"] == key:
            return d["v"]
    res = Parallel(n_jobs=8)(delayed(_sot_job)(g) for _, g in df.groupby("Division"))
    r = pd.concat(res).sort_index()
    v = pd.DataFrame({"sot_lh": np.log(r.mu), "sot_la": np.log(r.nu)}, index=r.index)
    pd.to_pickle(dict(key=key, v=v), path)
    return v


def ht_columns(df):
    """HTHG / HTAG (punteggio al riposo) dai CSV di football-data.co.uk, abbinati per (campionato, stagione, casa, ospite)."""
    parts = []
    for s in range(data.FIRST_SEASON, data.current_season() + 1):
        for lg in data.LEAGUES:
            p = os.path.join(data.CACHE_DIR, f"{data.season_code(s)}_{lg}.csv")
            if not os.path.exists(p):
                continue
            d = pd.read_csv(p, encoding="latin-1", on_bad_lines="skip", low_memory=False).dropna(subset=["FTHG"])
            if "HTHG" not in d.columns:
                continue
            parts.append(pd.DataFrame({"Division": lg, "season": s, "HomeTeam": d.HomeTeam.astype(str).str.strip(),
                                       "AwayTeam": d.AwayTeam.astype(str).str.strip(),
                                       "HTHG": pd.to_numeric(d.HTHG, errors="coerce"), "HTAG": pd.to_numeric(d.HTAG, errors="coerce")}))
    ht = pd.concat(parts).drop_duplicates(["Division", "season", "HomeTeam", "AwayTeam"])
    m = df[["Division", "season", "HomeTeam", "AwayTeam"]].reset_index().merge(
        ht, on=["Division", "season", "HomeTeam", "AwayTeam"], how="left").set_index("index")
    return m[["HTHG", "HTAG"]].reindex(df.index)


def v6_goals(feat):
    """log gol attesi del modello 1X2 v6 (stack with_xg + Elo-Odds): fuori campione dal 2019/20, in campione per il 2016/17-2018/19."""
    X = feat[stack.XG_FEATURES_EO]
    ok = X.notna().all(axis=1)
    out = pd.DataFrame(np.nan, index=feat.index, columns=["v6_lmu", "v6_lnu"])
    for s in sorted(feat.season.unique()):
        if s < FIRST_TEST:
            continue
        tr = ok & (feat.season >= FIRST_TRAIN) & (feat.season < s)
        te = ok & (feat.season == s)
        if not te.any():
            continue
        m = stack.fit_stack(X[tr], feat.hg[tr], feat.ag[tr])
        out.loc[te, "v6_lmu"] = np.log(m["home"].predict(X[te]))
        out.loc[te, "v6_lnu"] = np.log(m["away"].predict(X[te]))
        if s == FIRST_TEST:
            out.loc[tr, "v6_lmu"] = np.log(m["home"].predict(X[tr]))
            out.loc[tr, "v6_lnu"] = np.log(m["away"].predict(X[tr]))
    return out


def gap_ratings(df, hc, ac, eta, gamma, prior_n=20):
    """GAP ratings (Wheatcroft): previsioni PRIMA di ogni partita per la statistica (hc, ac). Restituisce DataFrame gap_h, gap_a (indice df)."""
    out_h = pd.Series(np.nan, index=df.index)
    out_a = pd.Series(np.nan, index=df.index)
    old = df[df.date < pd.Timestamp("2014-01-01")]
    prior_h, prior_a = float(old[hc].mean()), float(old[ac].mean())
    for lg, g in df.groupby("Division"):
        g = g.sort_values("date", kind="stable")
        AH, DH, AA, DA = {}, {}, {}, {}
        sh = sa = 0.0
        n = 0
        for i, h, a, xh, xa in zip(g.index, g.HomeTeam.to_numpy(), g.AwayTeam.to_numpy(), g[hc].to_numpy(float), g[ac].to_numpy(float)):
            mu_h = (sh + prior_n * prior_h) / (n + prior_n)
            mu_a = (sa + prior_n * prior_a) / (n + prior_n)
            ph = max(mu_h + AH.get(h, 0.0) + DA.get(a, 0.0), 0.5)
            pa = max(mu_a + AA.get(a, 0.0) + DH.get(h, 0.0), 0.5)
            out_h[i], out_a[i] = ph, pa
            if np.isfinite(xh) and np.isfinite(xa):
                eh, ea = xh - ph, xa - pa
                AH[h] = AH.get(h, 0.0) + eta * eh
                DA[a] = DA.get(a, 0.0) + eta * eh
                AA[a] = AA.get(a, 0.0) + eta * ea
                DH[h] = DH.get(h, 0.0) + eta * ea
                if gamma:
                    AA[h] = AA.get(h, 0.0) + gamma * eta * eh
                    DH[a] = DH.get(a, 0.0) + gamma * eta * eh
                    AH[a] = AH.get(a, 0.0) + gamma * eta * ea
                    DA[h] = DA.get(h, 0.0) + gamma * eta * ea
                sh += xh
                sa += xa
                n += 1
    return pd.DataFrame({"gap_h": out_h, "gap_a": out_a})


def prepare():
    """feat con tutte le colonne necessarie ai round 6 (statistiche, sot, HT, arbitro, gol attesi v6)."""
    c = C3.get_ctx3()
    df = c.df
    feat = c.feat.join(features.build_stat_features(df).drop(columns=["sot_lh", "sot_la"], errors="ignore")).join(sot_features(df)).join(ht_columns(df)).join(v6_goals(c.feat))
    keys = refeffect.load_history_keys(df).reindex(feat.index)
    mh0, ma0 = refeffect.base_predictions(feat)
    R, _ = refeffect.referee_ratio(feat, feat.HY + feat.AY, mh0 + ma0, keys, REFEREE_K, refeffect.mbar_by_league(feat, mh0 + ma0))
    feat["ref_logR"] = np.log(R)
    return feat, keys, c


# ───────────────────────────── modello della statistica ─────────────────────────────
def design(feat, spec, extra=(), own=None):
    own = own or spec["own"]
    aux = spec["aux"]
    X = pd.DataFrame({"own_lh": feat[own[0]], "own_la": feat[own[1]], "aux_lh": feat[aux[0]], "aux_la": feat[aux[1]]}, index=feat.index)
    X = X.join(sm.common_frame(feat))
    for c in extra:
        X[c] = feat[c]
    return X


class Run:
    """Medie attese fuori campione (dal 2019/20) e medie in campione dei fold, per le stime degli alpha."""
    def __init__(self, feat, spec, mh, ma, folds):
        self.feat, self.spec, self.mh, self.ma, self.folds = feat, spec, mh, ma, folds


def run_model(feat, spec, X):
    hc, ac = spec["hc"], spec["ac"]
    yh, ya = feat[hc], feat[ac]
    has = X.notna().all(axis=1)
    ok = has & yh.notna() & ya.notna()
    mh = pd.Series(np.nan, index=feat.index)
    ma = pd.Series(np.nan, index=feat.index)
    folds = {}
    for s in sorted(feat.season.unique()):
        if s < FIRST_TEST:
            continue
        tr = ok & (feat.season >= FIRST_TRAIN) & (feat.season < s)
        te = has & (feat.season == s)
        if not te.any() or tr.sum() < 100:
            continue
        m = sm.fit_stat_model(X[tr], yh[tr], ya[tr])
        mh[te], ma[te] = sm.predict_means(m, X[te])
        a, b = sm.predict_means(m, X[tr])
        folds[s] = dict(idx=X.index[tr], mh=a, ma=b)
    return Run(feat, spec, mh, ma, folds)


# ───────────────────────────── dispersione ─────────────────────────────
def moments(y, m):
    y, m = np.asarray(y, float), np.asarray(m, float)
    ok = np.isfinite(y) & np.isfinite(m)
    y, m = y[ok], m[ok]
    return max(float(((y - m) ** 2 - m).sum() / (m ** 2).sum()), 1e-4)


def alphas(run: Run, mode="global", shrink=30):
    """DataFrame (righe di test) con alpha per la squadra di casa (ah), l'ospite (aa) e per il totale (aT). Stimati a momenti sulle
    partite di training del fold con le medie in campione. mode: global | league | team."""
    feat, spec = run.feat, run.spec
    hc, ac = spec["hc"], spec["ac"]
    out = pd.DataFrame(np.nan, index=feat.index, columns=["ah", "aa", "aT"])
    for s, f in run.folds.items():
        idx = f["idx"]
        yh, ya = feat.loc[idx, hc].to_numpy(float), feat.loc[idx, ac].to_numpy(float)
        te = run.mh.notna() & (feat.season == s)
        dv_tr = feat.loc[idx, "Division"].to_numpy()
        a_team_g = moments(np.r_[yh, ya], np.r_[f["mh"], f["ma"]])
        a_tot_g = moments(yh + ya, f["mh"] + f["ma"])
        if mode == "global":
            out.loc[te, ["ah", "aa"]] = a_team_g
            out.loc[te, "aT"] = a_tot_g
            continue
        a_team_l, a_tot_l = {}, {}
        for lg in np.unique(dv_tr):
            m = dv_tr == lg
            a_team_l[lg] = moments(np.r_[yh[m], ya[m]], np.r_[f["mh"][m], f["ma"][m]])
            a_tot_l[lg] = moments(yh[m] + ya[m], f["mh"][m] + f["ma"][m])
        dv_te = feat.loc[te, "Division"]
        if mode == "league":
            out.loc[te, "ah"] = dv_te.map(a_team_l).fillna(a_team_g).to_numpy()
            out.loc[te, "aa"] = out.loc[te, "ah"]
            out.loc[te, "aT"] = dv_te.map(a_tot_l).fillna(a_tot_g).to_numpy()
            continue
        # team: shrinkage verso la lega
        hn, an = feat.loc[idx, "HomeTeam"].to_numpy(), feat.loc[idx, "AwayTeam"].to_numpy()
        long = pd.DataFrame({"team": np.r_[hn, an], "y": np.r_[yh, ya], "m": np.r_[f["mh"], f["ma"]],
                             "yT": np.r_[yh + ya, yh + ya], "mT": np.r_[f["mh"] + f["ma"], f["mh"] + f["ma"]],
                             "lg": np.r_[dv_tr, dv_tr]})
        long["s1"] = (long.y - long.m) ** 2 - long.m
        long["s2"] = long.m ** 2
        long["t1"] = (long.yT - long.mT) ** 2 - long.mT
        long["t2"] = long.mT ** 2
        g = long.groupby("team")
        agg = g.agg(n=("y", "size"), s1=("s1", "sum"), s2=("s2", "sum"), t1=("t1", "sum"), t2=("t2", "sum"), lg=("lg", "first"))
        raw = np.maximum(agg.s1 / agg.s2, 1e-4)
        rawT = np.maximum(agg.t1 / agg.t2, 1e-4)
        aL = agg.lg.map(a_team_l)
        aLT = agg.lg.map(a_tot_l)
        a_t = (agg.n * raw + shrink * aL) / (agg.n + shrink)
        a_T = (agg.n * rawT + shrink * aLT) / (agg.n + shrink)
        h, a = feat.loc[te, "HomeTeam"], feat.loc[te, "AwayTeam"]
        dflt = dv_te.map(a_team_l).fillna(a_team_g)
        dfltT = dv_te.map(a_tot_l).fillna(a_tot_g)
        ah = h.map(a_t).fillna(dflt)
        aa = a.map(a_t).fillna(dflt)
        out.loc[te, "ah"], out.loc[te, "aa"] = ah.to_numpy(), aa.to_numpy()
        out.loc[te, "aT"] = (0.5 * (h.map(a_T).fillna(dfltT) + a.map(a_T).fillna(dfltT))).to_numpy()
    return out


# ───────────────────────────── distribuzioni ─────────────────────────────
class NBDist:
    def __init__(self, m, alpha):
        self.m = np.asarray(m, float)
        self.n = 1.0 / np.asarray(alpha, float)
        self.p = self.n / (self.n + self.m)

    def logpmf(self, y):
        return nbinom.logpmf(y, self.n, self.p)

    def sf(self, L):
        return 1 - nbinom.cdf(np.floor(L), self.n, self.p)

    def ppf(self, q):
        return nbinom.ppf(q, self.n, self.p)


class GridDist:
    """Distribuzione data da una matrice di pmf (n, K)."""
    def __init__(self, pmf):
        self.pmf = np.clip(pmf, 0, None)
        self.pmf = self.pmf / self.pmf.sum(1, keepdims=True)
        self.cdf = np.cumsum(self.pmf, 1)

    def logpmf(self, y):
        return np.log(np.clip(self.pmf[np.arange(len(y)), np.minimum(y.astype(int), self.pmf.shape[1] - 1)], 1e-12, 1))

    def sf(self, L):
        return 1 - self.cdf[:, min(int(np.floor(L)), self.cdf.shape[1] - 1)]

    def ppf(self, q):
        return (self.cdf < q - 1e-12).sum(1).astype(float)


def _ece(p, o, nb=10):
    p, o = np.asarray(p), np.asarray(o)
    order = np.argsort(p, kind="stable")
    tot = 0.0
    for ix in np.array_split(order, nb):
        tot += len(ix) * abs(p[ix].mean() - o[ix].mean())
    return float(tot / len(p))


def vectors(spec, y_h, y_a, dh, da, dT):
    """Vettori per partita delle metriche (squadra e totale) date le distribuzioni dh, da (casa, ospite) e dT (totale)."""
    yT = y_h + y_a
    v = {}
    v["ll_team"] = -(dh.logpmf(y_h) + da.logpmf(y_a)) / 2
    v["ll_tot"] = -dT.logpmf(yT)
    mh = getattr(dh, "m", None)
    v["mean_h"], v["mean_a"] = (dh.mean() if mh is None else dh.m), (da.mean() if getattr(da, "m", None) is None else da.m)
    v["mean_T"] = v["mean_h"] + v["mean_a"] if not hasattr(dT, "pmf") else (dT.pmf * np.arange(dT.pmf.shape[1])).sum(1)
    v["mae_team"] = (np.abs(v["mean_h"] - y_h) + np.abs(v["mean_a"] - y_a)) / 2
    v["mae_tot"] = np.abs(v["mean_T"] - yT)
    for q, tag in ((0.80, "80"), (0.90, "90")):
        lo, hi = (1 - q) / 2, 1 - (1 - q) / 2
        c_h = (y_h >= dh.ppf(lo)) & (y_h <= dh.ppf(hi))
        c_a = (y_a >= da.ppf(lo)) & (y_a <= da.ppf(hi))
        v[f"c{tag}_team"] = (c_h.astype(float) + c_a.astype(float)) / 2
        v[f"c{tag}_tot"] = ((yT >= dT.ppf(lo)) & (yT <= dT.ppf(hi))).astype(float)
    # Over/Under: log-loss medio per partita sulle linee + probabilita'/esiti per la calibrazione
    pt, ot, lt = [], [], []
    for L in spec["lines_t"]:
        for d, yy in ((dh, y_h), (da, y_a)):
            p = np.clip(d.sf(L), 1e-9, 1 - 1e-9)
            o = (yy > L).astype(float)
            lt.append(-(o * np.log(p) + (1 - o) * np.log(1 - p)))
            pt.append(p)
            ot.append(o)
    v["ou_team"] = np.mean(lt, axis=0)
    v["cal_team"] = (np.concatenate(pt), np.concatenate(ot))
    pT, oT, lT = [], [], []
    for L in spec["lines_T"]:
        p = np.clip(dT.sf(L), 1e-9, 1 - 1e-9)
        o = (yT > L).astype(float)
        lT.append(-(o * np.log(p) + (1 - o) * np.log(1 - p)))
        pT.append(p)
        oT.append(o)
    v["ou_tot"] = np.mean(lT, axis=0)
    v["cal_tot"] = (np.concatenate(pT), np.concatenate(oT))
    v["y"] = (y_h, y_a)
    return v


def corr_team(v):
    return float(np.corrcoef(np.r_[v["mean_h"], v["mean_a"]], np.r_[v["y"][0], v["y"][1]])[0, 1])


def corr_tot(v):
    return float(np.corrcoef(v["mean_T"], v["y"][0] + v["y"][1])[0, 1])


def summarize(v):
    """Valori medi delle metriche."""
    s = {k: float(v[k].mean()) for k in v if k.startswith(("ll_", "mae_", "c80", "c90", "ou_")) and not k.startswith("cal")}
    for lvl in ("team", "tot"):
        p, o = v[f"cal_{lvl}"]
        s[f"ece_{lvl}"] = _ece(p, o)
        s[f"bias_{lvl}"] = float(p.mean() - o.mean())
    s["corr_team"], s["corr_tot"] = corr_team(v), corr_tot(v)
    return s


def make_dists(run: Run, al: pd.DataFrame, rows):
    mh, ma = run.mh[rows].to_numpy(), run.ma[rows].to_numpy()
    dh = NBDist(mh, al.loc[rows, "ah"].to_numpy())
    da = NBDist(ma, al.loc[rows, "aa"].to_numpy())
    dT = NBDist(mh + ma, al.loc[rows, "aT"].to_numpy())
    return dh, da, dT


def evaluate(run: Run, rows, al=None, dT=None, mode="global"):
    al = al if al is not None else alphas(run, mode)
    dh, da, dT0 = make_dists(run, al, rows)
    f = run.feat
    y_h, y_a = f.loc[rows, run.spec["hc"]].to_numpy(float), f.loc[rows, run.spec["ac"]].to_numpy(float)
    return vectors(run.spec, y_h, y_a, dh, da, dT if dT is not None else dT0)


# ───────────────────────────── confronti con IC ─────────────────────────────
def _d(base, var, higher_better=False):
    return (var - base) if higher_better else (base - var)


def compare(vb, vv, weeks, is_val, n_boot_corr=1000):
    """Δ (baseline − variante per le perdite; variante − baseline per le coperture) con IC per partita e a blocchi."""
    out = {}
    for key in ("ll_tot", "ll_team", "mae_tot", "mae_team", "ou_tot", "ou_team", "c80_tot", "c80_team", "c90_tot", "c90_team"):
        d = _d(vb[key], vv[key], higher_better=key.startswith("c"))
        m, lo, hi = C3.ci_match(d)
        _, lob, hib = C3.ci_block(d, weeks)
        out[key] = dict(base=float(vb[key].mean()), var=float(vv[key].mean()), d=m, lo=lo, hi=hi, lob=lob, hib=hib)
    for key in ("ll_tot", "ll_team"):
        for sub, mask in (("val", is_val), ("held", ~is_val)):
            d = vb[key][mask] - vv[key][mask]
            m, lo, hi = C3.ci_match(d)
            _, lob, hib = C3.ci_block(d, weeks[mask])
            out[f"{key}_{sub}"] = dict(d=m, lo=lo, hi=hi, lob=lob, hib=hib, n=int(mask.sum()))
    codes, uniq = pd.factorize(weeks)
    blocks = [np.where(codes == b)[0] for b in range(len(uniq))]
    rng = np.random.default_rng(31)
    for name, fn in (("corr_team", corr_team), ("corr_tot", corr_tot)):
        cb, cv = fn(vb), fn(vv)
        est = []
        for _ in range(n_boot_corr):
            idx = np.concatenate([blocks[b] for b in rng.integers(0, len(uniq), len(uniq))])
            sb = {k: (vb[k] if k == "y" else None) for k in ()}
            vb_i = {"mean_h": vb["mean_h"][idx], "mean_a": vb["mean_a"][idx], "mean_T": vb["mean_T"][idx],
                    "y": (vb["y"][0][idx], vb["y"][1][idx])}
            vv_i = {"mean_h": vv["mean_h"][idx], "mean_a": vv["mean_a"][idx], "mean_T": vv["mean_T"][idx],
                    "y": (vv["y"][0][idx], vv["y"][1][idx])}
            est.append(fn(vv_i) - fn(vb_i))
        out[name] = dict(base=cb, var=cv, d=cv - cb, lob=float(np.percentile(est, 2.5)), hib=float(np.percentile(est, 97.5)))
    for lvl in ("team", "tot"):
        sb, sv = summarize_cal(vb, lvl), summarize_cal(vv, lvl)
        out[f"ece_{lvl}"] = dict(base=sb[0], var=sv[0])
        out[f"bias_{lvl}"] = dict(base=sb[1], var=sv[1])
    return out


def summarize_cal(v, lvl):
    p, o = v[f"cal_{lvl}"]
    return _ece(p, o), float(p.mean() - o.mean())


def verdict(res, primary="ll_tot", secondary="ll_team"):
    h = res[f"{primary}_held"]
    sec = res[f"{secondary}_held"]["d"] if f"{secondary}_held" in res else 0.0
    if h["d"] > 0 and h["lob"] > 0 and sec >= 0:
        return "migliora"
    if h["d"] < 0 and h["hib"] < 0:
        return "peggiora"
    return "non distinguibile dal rumore"


# ───────────────────────────── copula gaussiana ─────────────────────────────
Z_GRID = np.linspace(-7.0, 7.0, 561)
_DZ = Z_GRID[1] - Z_GRID[0]
_WZ = np.exp(-0.5 * Z_GRID ** 2) / np.sqrt(2 * np.pi) * _DZ


def _joint_pmf(F_h, F_a, rho):
    """pmf congiunta (M+1, M+1) con marginali date dalle CDF (F_h, F_a) e copula gaussiana di correlazione rho."""
    pm_h = np.diff(np.r_[0.0, F_h])
    pm_a = np.diff(np.r_[0.0, F_a])
    if abs(rho) < 1e-9:
        return np.outer(pm_h, pm_a)
    a = ndtri(np.clip(F_h, 1e-12, 1 - 1e-12))
    b = ndtri(np.clip(F_a, 1e-12, 1 - 1e-12))
    s = np.sqrt(1 - rho ** 2)
    C = ndtr((b[None, :] - rho * Z_GRID[:, None]) / s)               # P(Y <= j | z), (K, M+1)
    H = np.cumsum(_WZ[:, None] * C, axis=0)                          # P(Z <= z_k, Y <= j)
    pos = np.clip(np.searchsorted(Z_GRID, a), 1, len(Z_GRID) - 1)
    t = np.clip((a - Z_GRID[pos - 1]) / _DZ, 0, 1)
    P2 = H[pos - 1, :] * (1 - t)[:, None] + H[pos, :] * t[:, None]   # CDF congiunta (i, j)
    P2 = np.pad(P2, ((1, 0), (1, 0)))
    pmf = P2[1:, 1:] - P2[:-1, 1:] - P2[1:, :-1] + P2[:-1, :-1]
    return pmf


def joint_dists(mh, ma, ah, aa, rho, M):
    """Per ogni partita: pmf del totale e pmf di (casa − ospite) dalla copula gaussiana con marginali NB.
    rho: scalare o array per partita. Restituisce (pmf_total (n, 2M+1), pmf_diff (n, 2M+1), indice della differenza 0 = M)."""
    n = len(mh)
    rho = np.broadcast_to(np.asarray(rho, float), (n,))
    k = np.arange(M + 1)
    i, j = np.meshgrid(k, k, indexing="ij")
    idx_sum, idx_diff = (i + j).ravel(), (i - j + M).ravel()
    Fh = nbinom.cdf(k[None, :], (1 / np.asarray(ah))[:, None], (1 / np.asarray(ah) / (1 / np.asarray(ah) + np.asarray(mh)))[:, None])
    Fa = nbinom.cdf(k[None, :], (1 / np.asarray(aa))[:, None], (1 / np.asarray(aa) / (1 / np.asarray(aa) + np.asarray(ma)))[:, None])
    tot = np.zeros((n, 2 * M + 1))
    dif = np.zeros((n, 2 * M + 1))
    for r in range(n):
        pmf = np.clip(_joint_pmf(Fh[r], Fa[r], rho[r]), 0, None)
        pmf = pmf / pmf.sum()
        tot[r] = np.bincount(idx_sum, weights=pmf.ravel(), minlength=2 * M + 1)
        dif[r] = np.bincount(idx_diff, weights=pmf.ravel(), minlength=2 * M + 1)
    return tot, dif


def estimate_rho(run: Run, al_mode_alpha, per_league=False, seed=17):
    """Correlazione tra i punteggi normali di una PIT randomizzata dei residui nelle partite di training di ogni fold.
    Restituisce {fold: rho} oppure {fold: {lega: rho}}. al_mode_alpha: DataFrame alpha 'global' (usa l'alpha del fold)."""
    feat, spec = run.feat, run.spec
    rng = np.random.default_rng(seed)
    out = {}
    for s, f in run.folds.items():
        idx = f["idx"]
        yh, ya = feat.loc[idx, spec["hc"]].to_numpy(int), feat.loc[idx, spec["ac"]].to_numpy(int)
        a = moments(np.r_[yh, ya], np.r_[f["mh"], f["ma"]])
        zs = []
        for y, m in ((yh, f["mh"]), (ya, f["ma"])):
            d = NBDist(m, np.full(len(m), a))
            n_, p_ = d.n, d.p
            lo = nbinom.cdf(y - 1, n_, p_)
            hi = nbinom.cdf(y, n_, p_)
            u = lo + rng.uniform(size=len(y)) * (hi - lo)
            zs.append(ndtri(np.clip(u, 1e-9, 1 - 1e-9)))
        if per_league:
            dv = feat.loc[idx, "Division"].to_numpy()
            out[s] = {lg: float(np.corrcoef(zs[0][dv == lg], zs[1][dv == lg])[0, 1]) for lg in np.unique(dv)}
        else:
            out[s] = float(np.corrcoef(zs[0], zs[1])[0, 1])
    return out


def rho_rows(run: Run, rho_by_fold, rows, per_league=False):
    feat = run.feat
    if per_league:
        return np.array([rho_by_fold[s].get(lg, np.nan) for s, lg in zip(feat.loc[rows, "season"], feat.loc[rows, "Division"])])
    return feat.loc[rows, "season"].map(rho_by_fold).to_numpy(float)
