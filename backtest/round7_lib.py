"""
Round 7 — livello stagionale: contesto dati aggiornato, previsioni walk-forward del modello di produzione (gol v6 e statistiche s4),
livello dinamico di lega (moltiplicatore con media esponenziale e shrinkage) e metriche. Definizioni in backtest/round7_parts/prereg.md.
Solo backtest: nessun file di produzione viene modificato.
"""
import os

import numpy as np
import pandas as pd
from scipy.stats import nbinom, poisson

from backtest import eloodds, features, models, refeffect, round2_lib as R2L, round3_ctx as C3, round6_lib as R6, stack, stats_model as sm, stats_v3
from config import REFEREE_K

HERE = os.path.dirname(os.path.abspath(__file__))
P7 = os.path.join(HERE, "round7_parts")
os.makedirs(P7, exist_ok=True)
CTX7 = os.path.join(R2L.CACHE, "round7", "ctx7.pkl")
os.makedirs(os.path.dirname(CTX7), exist_ok=True)
VALIDATION = C3.VALIDATION
LEAGUES = ["I1", "E0", "D1", "SP1", "F1"]
STATS = ["tiri", "sot", "corner", "falli", "gialli"]
KEYS = {"tiri": "Tiri", "sot": "Tiri in porta", "corner": "Corner", "falli": "Falli", "gialli": "Gialli"}
FIRST_TEST = 2019
FIRST_TRAIN = 2016


def build_ctx7(rebuild=False):
    """Dati aggiornati (download), feature di produzione (core, xG, Elo-Odds, statistiche, GAP, arbitro), giornata di campionato."""
    if not rebuild and os.path.exists(CTX7):
        return pd.read_pickle(CTX7)
    df = R2L.load_all(verbose=False)
    feat = R2L.baseline_frame(df)
    feat[eloodds.FEATURE] = eloodds.build_features(df).reindex(feat.index)
    feat = feat.join(features.build_stat_features(df))
    keys = refeffect.load_history_keys(df).reindex(feat.index)
    feat["ref_logR"], _ = refeffect.compute(feat, keys, REFEREE_K)
    pri = stats_v3.gap_priors(df)
    gf = stats_v3.gap_features(df, pri)
    for col in gf.columns:
        feat[col] = gf[col].reindex(feat.index)
    mhf, maf = stats_v3.base_predictions(feat, "falli")
    feat["ref_logR_f"], _ = refeffect.compute_stat(feat, keys, mhf, maf, feat["HF"] + feat["AF"], REFEREE_K)
    # giornata di campionato: partite già giocate dalla squadra in casa/fuori nella stagione + 1 (massimo tra le due)
    feat = feat.sort_values(["Division", "date"], kind="stable")
    n_prev_h = pd.Series(0, index=feat.index)
    n_prev_a = pd.Series(0, index=feat.index)
    for (lg, s), g in feat.groupby(["Division", "season"]):
        cnt = {}
        for i, h, a in zip(g.index, g.HomeTeam.to_numpy(), g.AwayTeam.to_numpy()):
            n_prev_h[i], n_prev_a[i] = cnt.get(h, 0), cnt.get(a, 0)
            cnt[h], cnt[a] = cnt.get(h, 0) + 1, cnt.get(a, 0) + 1
    feat["gday"] = np.maximum(n_prev_h, n_prev_a) + 1
    feat = feat.sort_index()
    pd.to_pickle(feat, CTX7)
    return feat


# ───────────────────────────── previsioni walk-forward dei gol (v6) ─────────────────────────────
def goals_walk_forward(feat, cols=None, extra_shift=None):
    """Stack 1X2 di produzione (with_xg + Elo-Odds), walk-forward per stagione dal 2019/20 (training dal 2016/17); in campione per il 2016/17-2018/19
    (previsioni del primo fold, come per le statistiche). Restituisce DataFrame mu, nu, rho per riga (NaN dove le feature mancano).
    extra_shift: DataFrame opzionale con colonne di feature da SOMMARE (in log) a dc_lmu / dc_lnu prima del fit (variante L2)."""
    cols = cols or stack.XG_FEATURES_EO
    X = feat[cols].copy()
    if extra_shift is not None:
        X["dc_lmu"] = X["dc_lmu"] + extra_shift["dc_lmu"].reindex(X.index).fillna(0.0)
        X["dc_lnu"] = X["dc_lnu"] + extra_shift["dc_lnu"].reindex(X.index).fillna(0.0)
    ok = X.notna().all(axis=1) & np.isfinite(X).all(axis=1)
    out = pd.DataFrame(np.nan, index=feat.index, columns=["mu", "nu", "rho"])
    for s in sorted(feat.season.unique()):
        if s < FIRST_TEST:
            continue
        tr = ok & (feat.season >= FIRST_TRAIN) & (feat.season < s)
        te = ok & (feat.season == s)
        if not te.any():
            continue
        m = stack.fit_stack(X[tr], feat.hg[tr], feat.ag[tr])
        out.loc[te, "mu"], out.loc[te, "nu"], out.loc[te, "rho"] = m["home"].predict(X[te]), m["away"].predict(X[te]), m["rho"]
        if s == FIRST_TEST:
            out.loc[tr, "mu"], out.loc[tr, "nu"], out.loc[tr, "rho"] = m["home"].predict(X[tr]), m["away"].predict(X[tr]), m["rho"]
    return out


def goal_markets(mu, nu, rho, G=10):
    """Probabilità 1X2, Over 1,5/2,5/3,5, BTTS dalla matrice dei punteggi (Dixon-Coles con rho)."""
    M = models.score_matrix(np.asarray(mu, float), np.asarray(nu, float), np.asarray(rho, float), G)
    i, j = np.indices((G + 1, G + 1))
    tot = i + j
    return {"P": models.probs_1x2(M), "o15": (M * (tot >= 2)).sum((1, 2)), "o25": (M * (tot >= 3)).sum((1, 2)),
            "o35": (M * (tot >= 4)).sum((1, 2)), "btts": (M * ((i >= 1) & (j >= 1))).sum((1, 2))}


def goal_metrics(mk, hg, ag):
    """Vettori per partita: log-loss 1X2, RPS, log-loss Over 2,5, log-loss O1,5/O3,5/BTTS."""
    hg, ag = np.asarray(hg, int), np.asarray(ag, int)
    y = np.where(hg > ag, 0, np.where(hg == ag, 1, 2))
    P = np.clip(mk["P"], 1e-12, 1)
    P = P / P.sum(1, keepdims=True)
    Y = np.eye(3)[y]
    out = {"ll": -np.log(P[np.arange(len(y)), y]),
           "rps": ((np.cumsum(P, 1)[:, :2] - np.cumsum(Y, 1)[:, :2]) ** 2).sum(1) / 2}
    tot = hg + ag
    for k, o in (("o15", tot >= 2), ("o25", tot >= 3), ("o35", tot >= 4), ("btts", (hg >= 1) & (ag >= 1))):
        p = np.clip(mk[k], 1e-9, 1 - 1e-9)
        out[f"ou_{k}"] = -(o * np.log(p) + (~o) * np.log(1 - p))
    out["ou"] = out["ou_o25"]
    return out


# ───────────────────────────── livello dinamico di lega ─────────────────────────────
def dynamic_level(dates, leagues, side_pred, side_obs, half_life_weeks, k, valid_from=None):
    """Moltiplicatore pre-partita per riga: per ogni lega, R = (Σ w·y + k·m̄) / (Σ w·μ + k·m̄) sulle partite PRECEDENTI (data strettamente minore) della
    stessa lega, con peso w = 0.5^(Δgiorni / (7·emivita)); m̄ = media pesata di μ delle partite precedenti (k = pseudo-partite a rapporto 1).
    Righe senza previsione (NaN) non entrano. Restituisce un array R (1.0 se non c'è storico)."""
    dates = pd.to_datetime(pd.Series(dates)).to_numpy("datetime64[D]").astype("int64").astype(float)
    leagues = np.asarray(leagues)
    mu = np.asarray(side_pred, float)
    y = np.asarray(side_obs, float)
    lam = np.log(2) / (7.0 * half_life_weeks)
    out = np.ones(len(mu))
    for lg in np.unique(leagues):
        idx = np.where(leagues == lg)[0]
        idx = idx[np.argsort(dates[idx], kind="stable")]
        d = dates[idx]
        ok = np.isfinite(mu[idx]) & np.isfinite(y[idx])
        # decadimento ricorsivo per giorno: S_y, S_m, S_w al giorno precedente, aggiornati con le partite dei giorni precedenti
        Sy = Sm = Sw = 0.0
        last = None
        i = 0
        n = len(idx)
        while i < n:
            j = i
            while j < n and d[j] == d[i]:
                j += 1
            if last is not None:
                f = np.exp(-lam * (d[i] - last))
                Sy, Sm, Sw = Sy * f, Sm * f, Sw * f
            last = d[i]
            if Sw > 0:
                mbar = Sm / Sw
                out[idx[i:j]] = (Sy + k * mbar) / (Sm + k * mbar)
            for t in range(i, j):                          # le partite del giorno entrano solo dopo (stesso giorno = non ancora note)
                if ok[t]:
                    Sy += y[idx[t]]
                    Sm += mu[idx[t]]
                    Sw += 1.0
            i = j
    return out


def early_mask(feat, upto=10):
    return (feat["gday"] <= upto).to_numpy()


# ───────────────────────────── bootstrap e tabelle ─────────────────────────────
def ci_block_mean(x, weeks, n_boot=3000, seed=21):
    """Media e IC 95% a blocchi per settimana ISO (ricampionamento delle settimane)."""
    x = np.asarray(x, float)
    ok = np.isfinite(x)
    x, w = x[ok], np.asarray(weeks)[ok]
    wk, inv = np.unique(w, return_inverse=True)
    s, c = np.bincount(inv, x), np.bincount(inv)
    rng = np.random.default_rng(seed)
    b = rng.integers(0, len(wk), size=(n_boot, len(wk)))
    est = s[b].sum(1) / c[b].sum(1)
    return float(x.mean()), float(np.percentile(est, 2.5)), float(np.percentile(est, 97.5))


def ratio_ci(pred, obs, weeks, n_boot=3000, seed=22):
    """Rapporto osservato/previsto (Σobs / Σpred) con IC 95% a blocchi per settimana."""
    pred, obs = np.asarray(pred, float), np.asarray(obs, float)
    ok = np.isfinite(pred) & np.isfinite(obs)
    pred, obs, w = pred[ok], obs[ok], np.asarray(weeks)[ok]
    wk, inv = np.unique(w, return_inverse=True)
    sp, so = np.bincount(inv, pred), np.bincount(inv, obs)
    rng = np.random.default_rng(seed)
    b = rng.integers(0, len(wk), size=(n_boot, len(wk)))
    est = so[b].sum(1) / sp[b].sum(1)
    return float(obs.sum() / pred.sum()), float(np.percentile(est, 2.5)), float(np.percentile(est, 97.5))
