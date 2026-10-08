"""
Poisson-stack (Step 3): due PoissonRegressor (gol casa, gol trasferta) su feature
standardizzate + rho per massima verosimiglianza, dal riferimento_fplib.

Valutazione walk-forward: per ogni stagione di test lo stack viene stimato su tutte le
partite con feature delle stagioni PRECEDENTI (dal 2013/14), tutti i campionati insieme.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from sklearn.linear_model import PoissonRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import models

STACK_FEATURES = ["dc_lmu", "dc_lnu", "sot_lmu", "sot_lnu", "elo_diff", "pi_gd", "pi_diff"]


def fit_stack(X_train, hg, ag):
    """Due regressioni di Poisson (gol casa, gol trasferta) + rho stimato per max verosimiglianza."""
    mh = make_pipeline(StandardScaler(), PoissonRegressor(alpha=1e-4, max_iter=1000)).fit(X_train, hg)
    ma = make_pipeline(StandardScaler(), PoissonRegressor(alpha=1e-4, max_iter=1000)).fit(X_train, ag)
    mu, nu = mh.predict(X_train), ma.predict(X_train)
    hg, ag = np.asarray(hg), np.asarray(ag)

    def nll(r):
        t = np.ones(len(hg))
        m00 = (hg == 0) & (ag == 0); m10 = (hg == 1) & (ag == 0)
        m01 = (hg == 0) & (ag == 1); m11 = (hg == 1) & (ag == 1)
        t[m00] = 1 - mu[m00] * nu[m00] * r; t[m10] = 1 + nu[m10] * r
        t[m01] = 1 + mu[m01] * r; t[m11] = 1 - r
        return -np.log(np.maximum(t, 1e-10)).sum()

    rho = minimize_scalar(nll, bounds=(-0.3, 0.3), method="bounded").x
    return dict(home=mh, away=ma, rho=rho)


def predict_stack(model, X_new):
    mu, nu = model["home"].predict(X_new), model["away"].predict(X_new)
    M = models.score_matrix(mu, nu, np.full(len(mu), model["rho"]))
    return mu, nu, M


def walk_forward_stack(feat, features, first_test_season=2019):
    """Probabilità 1X2 out-of-sample, rifit di stagione in stagione (finestra espansiva).
    Restituisce DataFrame (pH, pD, pA, mu, nu, rho) indicizzato come le partite di test."""
    cols = feat[features].copy()
    if "elo_diff" in cols:
        cols["elo_diff"] = cols["elo_diff"].fillna(0.0)
    usable = cols.notna().all(axis=1)

    out = []
    for s in sorted(feat.season.unique()):
        if s < first_test_season:
            continue
        tr_mask = (feat.season < s) & usable
        te_mask = (feat.season == s) & usable
        if not te_mask.any():
            continue
        m = fit_stack(cols[tr_mask], feat.hg[tr_mask], feat.ag[tr_mask])
        mu, nu, M = predict_stack(m, cols[te_mask])
        P = models.probs_1x2(M)
        out.append(pd.DataFrame({"pH": P[:, 0], "pD": P[:, 1], "pA": P[:, 2],
                                 "mu": mu, "nu": nu, "rho": m["rho"]}, index=feat.index[te_mask]))
    return pd.concat(out).sort_index()
