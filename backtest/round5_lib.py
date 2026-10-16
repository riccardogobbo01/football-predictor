"""
Round 5 (solo backtest): effetto arbitro nel modello delle statistiche attese (gialli; corner come controllo).
Vedi backtest/round5_parts/prereg.md per le definizioni fissate prima dei risultati.
"""
import numpy as np
import pandas as pd
from scipy.stats import nbinom

from backtest import round3_ctx as C3, stats_model as sm

FIRST_TRAIN = sm.FIRST_TRAIN_SEASON          # 2016
FIRST_TEST = 2019
LINES = {"gialli": [2.5, 3.5, 4.5, 5.5], "corner": [8.5, 9.5, 10.5, 11.5]}
MBAR_SEASONS = (2016, 2017, 2018)


# ───────────────────────────── stadio 0: modello attuale ─────────────────────────────
class Stage0:
    """Previsioni del modello attuale (variante with_xg), walk-forward per stagione, più i fit dei fold."""
    def __init__(self, feat, stat):
        self.feat, self.stat = feat, stat
        self.hc, self.ac = sm.STATS[stat][:2]
        self.X = sm.design(feat, stat, True)
        self.hasX = self.X.notna().all(axis=1)
        self.ok = self.hasX & feat[self.hc].notna() & feat[self.ac].notna()
        self.mh = pd.Series(np.nan, index=feat.index)
        self.ma = pd.Series(np.nan, index=feat.index)
        self.alpha = pd.Series(np.nan, index=feat.index)       # alpha del fold (solo righe di test)
        self.fits = {}
        for s in sorted(feat.season.unique()):
            if s < FIRST_TEST:
                continue
            tr = self.ok & (feat.season >= FIRST_TRAIN) & (feat.season < s)
            te = self.hasX & (feat.season == s)
            if not te.any():
                continue
            m = sm.fit_stat_model(self.X[tr], feat[self.hc][tr], feat[self.ac][tr])
            mh, ma = sm.predict_means(m, self.X[te])
            self.mh[te], self.ma[te], self.alpha[te] = mh, ma, m["alpha"]
            self.fits[s] = (m, tr)
            if s == FIRST_TEST:                                # previsioni in campione per il 2016/17-2018/19 (storico degli arbitri)
                a, b = sm.predict_means(m, self.X[tr])
                self.mh[tr], self.ma[tr] = a, b
        self.y = feat[self.hc] + feat[self.ac]


# ───────────────────────────── effetto arbitro ─────────────────────────────
def mbar_by_league(feat, m_tot):
    sel = feat.season.isin(MBAR_SEASONS) & m_tot.notna()
    return m_tot[sel].groupby(feat.Division[sel]).mean().to_dict()


def referee_ratio(feat, y, m, keys, k, mbar):
    """R per riga (indice di feat): (Σy + k m̄)/(Σm + k m̄) sulle partite PRECEDENTI dello stesso arbitro
    (chiave = (campionato, arbitro)), storico dal 2016/17. Arbitro sconosciuto o senza storico -> 1."""
    order = np.argsort(feat.date.to_numpy(), kind="stable")
    Sy, Sm = {}, {}
    out = np.ones(len(feat))
    div = feat.Division.to_numpy()
    yv, mv = y.to_numpy(float), m.to_numpy(float)
    kv = keys.to_numpy(dtype=object)
    for i in order:
        key = kv[i]
        if key is None or (isinstance(key, float) and np.isnan(key)):
            continue
        kk = (div[i], key)
        mb = mbar.get(div[i], np.nanmean(list(mbar.values())))
        out[i] = (Sy.get(kk, 0.0) + k * mb) / (Sm.get(kk, 0.0) + k * mb)
        if np.isfinite(yv[i]) and np.isfinite(mv[i]):
            Sy[kk] = Sy.get(kk, 0.0) + yv[i]
            Sm[kk] = Sm.get(kk, 0.0) + mv[i]
    return pd.Series(out, index=feat.index)


def permute_keys(feat, keys, seed=5):
    """Placebo: permuta gli arbitri tra le partite dello stesso campionato e stagione."""
    rng = np.random.default_rng(seed)
    out = keys.copy()
    for _, idx in feat.groupby(["Division", "season"]).groups.items():
        idx = list(idx)
        out.loc[idx] = keys.loc[idx].to_numpy()[rng.permutation(len(idx))]
    return out


# ───────────────────────────── stadio 2: con effetto arbitro ─────────────────────────────
def with_referee(st: Stage0, keys, k, form, extra=None):
    """Medie attese e alpha per riga di test con l'effetto arbitro. form 'a' (moltiplicativa) o 'b' (regressore).
    extra: lista di Series (log R aggiuntivi, per G2) usati solo nella forma b.
    Restituisce DataFrame mh, ma, alpha (NaN fuori dal test) e la serie R."""
    feat = st.feat
    m_tot = st.mh + st.ma
    R = referee_ratio(feat, st.y, m_tot, keys, k, mbar_by_league(feat, m_tot))
    out = pd.DataFrame(np.nan, index=feat.index, columns=["mh", "ma", "alpha"])
    for s, (model, tr) in st.fits.items():
        te = st.hasX & (feat.season == s)
        if form == "a":
            mh_tr, ma_tr = sm.predict_means(model, st.X[tr])
            adj = (mh_tr + ma_tr) * R[tr].to_numpy()
            y = st.y[tr].to_numpy()
            alpha = max(float(((y - adj) ** 2 - adj).sum() / (adj ** 2).sum()), 1e-4)
            mh, ma = sm.predict_means(model, st.X[te])
            out.loc[te, ["mh", "ma"]] = np.column_stack([mh * R[te].to_numpy(), ma * R[te].to_numpy()])
            out.loc[te, "alpha"] = alpha
        else:
            Xb = st.X.copy()
            Xb["ref_logR"] = np.log(R)
            for j, e in enumerate(extra or []):
                Xb[f"ref_logR_x{j}"] = e
            m = sm.fit_stat_model(Xb[tr], st.feat[st.hc][tr], st.feat[st.ac][tr])
            mh, ma = sm.predict_means(m, Xb[te])
            out.loc[te, ["mh", "ma"]] = np.column_stack([mh, ma])
            out.loc[te, "alpha"] = m["alpha"]
    return out, R


# ───────────────────────────── metriche ─────────────────────────────
def vectors(st: Stage0, pred: pd.DataFrame, mask):
    """Vettori per partita (sulle righe di `mask`) delle metriche del totale."""
    y_h, y_a = st.feat[st.hc][mask].to_numpy(float), st.feat[st.ac][mask].to_numpy(float)
    mh, ma, al = pred.mh[mask].to_numpy(float), pred.ma[mask].to_numpy(float), pred.alpha[mask].to_numpy(float)
    y = y_h + y_a
    m = mh + ma
    n = 1.0 / al
    p = n / (n + m)
    v = dict(nb=-nbinom.logpmf(y, n, p), mae=np.abs(m - y),
             cover=((y >= nbinom.ppf(0.10, n, p)) & (y <= nbinom.ppf(0.90, n, p))).astype(float))
    lines = LINES[st.stat]
    ou = []
    for L in lines:
        po = np.clip(1 - nbinom.cdf(np.floor(L), n, p), 1e-9, 1 - 1e-9)
        o = (y > L).astype(float)
        ll = -(o * np.log(po) + (1 - o) * np.log(1 - po))
        v[f"ou{L:g}"] = ll
        ou.append(ll)
    v["ou"] = np.mean(ou, axis=0)
    v["pred"] = (mh, ma)
    v["obs"] = (y_h, y_a)
    return v


def corr_team(v):
    mh, ma = v["pred"]
    yh, ya = v["obs"]
    return float(np.corrcoef(np.r_[mh, ma], np.r_[yh, ya])[0, 1])


def corr_total(v):
    mh, ma = v["pred"]
    yh, ya = v["obs"]
    return float(np.corrcoef(mh + ma, yh + ya)[0, 1])


def compare5(vb, vv, weeks, is_val, n_boot=1000):
    """Metriche di baseline e variante e Δ (baseline − variante per le perdite; variante − baseline per correlazioni e copertura)
    con IC per partita e a blocchi. Il log-loss del totale ha anche validazione / held-out."""
    out = {}
    for key in ("nb", "ou", "mae", "cover") + tuple(k for k in vb if k.startswith("ou") and k != "ou"):
        sign = 1.0
        d = (vb[key] - vv[key]) if key != "cover" else (vv[key] - vb[key])
        m, lo, hi = C3.ci_match(d)
        _, lob, hib = C3.ci_block(d, weeks)
        out[key] = dict(base=float(vb[key].mean()), var=float(vv[key].mean()), d=m, lo=lo, hi=hi, lob=lob, hib=hib)
    for sub, mask in (("val", is_val), ("held", ~is_val)):
        d = vb["nb"][mask] - vv["nb"][mask]
        m, lo, hi = C3.ci_match(d)
        _, lob, hib = C3.ci_block(d, weeks[mask])
        out[f"nb_{sub}"] = dict(d=m, lo=lo, hi=hi, lob=lob, hib=hib, n=int(mask.sum()))
    # correlazioni: Δ = variante − baseline, IC a blocchi (ricampionamento delle settimane)
    codes, uniq = pd.factorize(weeks)
    rows_by_block = [np.where(codes == b)[0] for b in range(len(uniq))]
    rng = np.random.default_rng(21)
    for name, fn in (("corr_team", corr_team), ("corr_total", corr_total)):
        cb, cv = fn(vb), fn(vv)
        est = []
        for _ in range(n_boot):
            idx = np.concatenate([rows_by_block[b] for b in rng.integers(0, len(uniq), len(uniq))])
            sb = {k: (tuple(x[idx] for x in vb[k]) if k in ("pred", "obs") else None) for k in ("pred", "obs")}
            sv = {k: (tuple(x[idx] for x in vv[k]) if k in ("pred", "obs") else None) for k in ("pred", "obs")}
            est.append(fn(sv) - fn(sb))
        out[name] = dict(base=cb, var=cv, d=cv - cb, lob=float(np.percentile(est, 2.5)), hib=float(np.percentile(est, 97.5)))
    return out
