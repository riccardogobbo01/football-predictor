"""
Round 2 — Dixon-Coles / Poisson attacco-difesa ESTESO: stessa funzione obiettivo di backtest/models.py,
più (opzionale) una dummy "porte chiuse" sul vantaggio casa: lmu = a[casa] + d[ospite] + H + delta*closed.

Con closed=None il risultato è identico a models.walk_forward_dc (verificato in test).
Il vantaggio casa H risulta stimato di fatto solo sulle partite con closed=0, perché delta è libero
(piccola ridge solo per tenerlo determinato quando non ci sono partite a porte chiuse nel campione).
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln

from backtest import models

DELTA_RIDGE = 0.5


def _negll_grad(p, hi, ai, x, y, w, n, use_tau, ridge, closed):
    H, rho = p[0], p[1]
    a, d = p[2:2 + n], p[2 + n:2 + 2 * n]
    delta = p[2 + 2 * n] if closed is not None else 0.0
    lmu = a[hi] + d[ai] + H + (delta * closed if closed is not None else 0.0)
    lnu = a[ai] + d[hi]
    mu, nu = np.exp(lmu), np.exp(lnu)
    ll = x * lmu - mu - gammaln(x + 1) + y * lnu - nu - gammaln(y + 1)
    gmu = x - mu
    gnu = y - nu
    grho = np.zeros_like(mu)
    if use_tau:
        t = np.ones_like(mu)
        m00 = (x == 0) & (y == 0); m10 = (x == 1) & (y == 0)
        m01 = (x == 0) & (y == 1); m11 = (x == 1) & (y == 1)
        t[m00] = 1 - mu[m00] * nu[m00] * rho
        t[m10] = 1 + nu[m10] * rho
        t[m01] = 1 + mu[m01] * rho
        t[m11] = 1 - rho
        t = np.maximum(t, 1e-10)
        ll = ll + np.log(t)
        q = -mu[m00] * nu[m00] * rho / t[m00]
        gmu[m00] += q; gnu[m00] += q; grho[m00] = -mu[m00] * nu[m00] / t[m00]
        gnu[m10] += nu[m10] * rho / t[m10]; grho[m10] = nu[m10] / t[m10]
        gmu[m01] += mu[m01] * rho / t[m01]; grho[m01] = mu[m01] / t[m01]
        grho[m11] = -1 / t[m11]
    f = -(w * ll).sum()
    wgmu, wgnu = w * gmu, w * gnu
    g = np.zeros_like(p)
    g[0] = -wgmu.sum()
    g[1] = -(w * grho).sum()
    g[2:2 + n] = -(np.bincount(hi, wgmu, n) + np.bincount(ai, wgnu, n))
    g[2 + n:2 + 2 * n] = -(np.bincount(ai, wgmu, n) + np.bincount(hi, wgnu, n))
    if closed is not None:
        g[2 + 2 * n] = -(wgmu * closed).sum() + 2 * DELTA_RIDGE * delta
        f += DELTA_RIDGE * delta * delta
    pen = 100.0
    s = a.sum()
    f += pen * s * s
    g[2:2 + n] += 2 * pen * s
    if ridge:
        f += ridge * (np.dot(a, a) + np.dot(d, d))
        g[2:2 + n] += 2 * ridge * a
        g[2 + n:2 + 2 * n] += 2 * ridge * d
    return f, g


def fit_dc_ext(home, away, x, y, days_ago, xi, use_tau=True, x0=None, teams=None, ridge=0.0, closed=None):
    if teams is None:
        teams = sorted(set(home) | set(away))
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    hi = np.array([idx[t] for t in home]); ai = np.array([idx[t] for t in away])
    w = np.exp(-xi * np.asarray(days_ago, float))
    npar = 2 + 2 * n + (1 if closed is not None else 0)
    if x0 is None:
        x0 = np.zeros(npar); x0[0] = 0.25; x0[1] = -0.05
    bounds = [(-1, 1.5), (-0.4, 0.4) if use_tau else (0, 0)] + [(-3, 3)] * (2 * n)
    if closed is not None:
        bounds += [(-1.0, 1.0)]
        closed = np.asarray(closed, float)
    r = minimize(_negll_grad, x0, args=(hi, ai, np.asarray(x, float), np.asarray(y, float), w, n, use_tau,
                                        ridge, closed),
                 jac=True, method="L-BFGS-B", bounds=bounds, options=dict(maxiter=500))
    p = r.x
    return dict(teams=teams, idx=idx, H=p[0], rho=p[1], a=p[2:2 + n], d=p[2 + n:2 + 2 * n],
                delta=(p[2 + 2 * n] if closed is not None else 0.0), x=p)


def walk_forward_ext(g, xi, start, use_tau=True, gx="hg", gy="ag", ridge=0.0, closed_col=None,
                     predict_closed=True, years_window=5, step_days=7):
    """Come models.walk_forward_dc per UN campionato (g = partite di quel campionato).
    closed_col: nome della colonna 0/1 "porte chiuse" (None = modello senza dummy).
    predict_closed: True = nelle previsioni si usa il flag reale della partita (noto prima del calcio
    d'inizio, è lo scenario corretto per il backtest); False = si prevede sempre con closed=0 (scenario
    "futuro normale").
    Restituisce DataFrame mu, nu, rho, H, delta (indicizzato come le partite previste)."""
    g = g.sort_values("date")
    t0 = pd.Timestamp(start)
    cuts = pd.date_range(t0, g.date.max() + pd.Timedelta(days=1), freq=f"{step_days}D")
    out = []
    x0 = None; prev_teams = None
    for c0, c1 in zip(cuts[:-1], cuts[1:]):
        test = g[(g.date >= c0) & (g.date < c1)]
        if test.empty:
            continue
        tr = g[(g.date < c0) & (g.date >= c0 - pd.Timedelta(days=365 * years_window))]
        tr = tr.dropna(subset=[gx, gy])
        teams = sorted(set(tr.HomeTeam) | set(tr.AwayTeam))
        if teams != prev_teams:
            x0 = None
        clo = tr[closed_col].to_numpy(float) if closed_col else None
        m = fit_dc_ext(tr.HomeTeam.values, tr.AwayTeam.values, tr[gx].values, tr[gy].values,
                       (c0 - tr.date).dt.days.values, xi, use_tau=use_tau, x0=x0, teams=teams,
                       ridge=ridge, closed=clo)
        x0, prev_teams = m["x"], teams
        mu, nu = models.dc_lambdas(m, test.HomeTeam.values, test.AwayTeam.values)
        if closed_col and predict_closed:
            mu = mu * np.exp(m["delta"] * test[closed_col].to_numpy(float))
        out.append(pd.DataFrame(dict(mu=mu, nu=nu, rho=m["rho"], H=m["H"], delta=m["delta"]), index=test.index))
    return pd.concat(out).sort_index()


# configurazioni dei tre modelli di forza del baseline (stesse di backtest/features.py)
SETS = {
    "goals": dict(xi=0.0018, start="2013-07-01", use_tau=True, gx="hg", gy="ag", ridge=0.0),
    "sot": dict(xi=0.0018, start="2013-07-01", use_tau=False, gx="HST", gy="AST", ridge=0.0),
    "xg": dict(xi=0.003, start="2016-07-04", use_tau=False, gx="xg_h", gy="xg_a", ridge=2.0),
}


def build_set(kind, g, closed_col=None, predict_closed=True):
    """Walk-forward di un modello di forza (goals / sot / xg) su UN campionato, con o senza dummy."""
    return walk_forward_ext(g, closed_col=closed_col, predict_closed=predict_closed, **SETS[kind])
