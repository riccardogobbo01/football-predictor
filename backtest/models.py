"""
Modelli e metriche per il backtest, portati da backtest/riferimento_fplib.py:
Dixon-Coles con gradiente analitico (L-BFGS-B), matrice dei punteggi, pi-ratings,
quote senza margine, metriche 1X2. Il Poisson-stack (sklearn) arriva allo Step 3.
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln
from scipy.stats import poisson


# ─────────────────────────────── quote ───────────────────────────────────────
def market_probs(oh, od, oa, method="power"):
    """Probabilità implicite senza margine. method: 'norm' o 'power'."""
    inv = np.column_stack([1 / oh, 1 / od, 1 / oa])
    if method == "norm":
        return inv / inv.sum(1, keepdims=True)
    out = np.full_like(inv, np.nan)
    for i, row in enumerate(inv):
        if not np.all(np.isfinite(row)):
            continue
        lo, hi = 0.5, 3.0
        for _ in range(60):
            k = (lo + hi) / 2
            s = (row ** k).sum()
            lo, hi = (k, hi) if s > 1 else (lo, k)
        p = row ** k
        out[i] = p / p.sum()
    return out


# ─────────────────────────────── metriche ────────────────────────────────────
def metrics(P, y):
    P = np.clip(P, 1e-12, 1)
    P = P / P.sum(1, keepdims=True)
    Y = np.eye(3)[y]
    ll = -np.log(P[np.arange(len(y)), y])
    brier = ((P - Y) ** 2).sum(1)
    cP, cY = np.cumsum(P, 1)[:, :2], np.cumsum(Y, 1)[:, :2]
    rps = ((cP - cY) ** 2).sum(1) / 2
    acc = (P.argmax(1) == y).astype(float)
    return dict(logloss=ll.mean(), rps=rps.mean(), brier=brier.mean(), acc=acc.mean(), n=len(y)), ll


# ─────────────────────────────── Dixon-Coles ─────────────────────────────────
def _dc_negll_grad(p, hi, ai, x, y, w, n, use_tau):
    H, rho = p[0], p[1]
    a, d = p[2:2 + n], p[2 + n:]
    lmu = a[hi] + d[ai] + H
    lnu = a[ai] + d[hi]
    mu, nu = np.exp(lmu), np.exp(lnu)
    ll = x * lmu - mu - gammaln(x + 1) + y * lnu - nu - gammaln(y + 1)
    gmu = x - mu          # d ll / d log mu
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
    g[2 + n:] = -(np.bincount(ai, wgmu, n) + np.bincount(hi, wgnu, n))
    # vincolo di identificabilità come penalità: sum(attack)=0
    pen = 100.0
    s = a.sum()
    f += pen * s * s
    g[2:2 + n] += 2 * pen * s
    return f, g


def fit_dc(home, away, x, y, days_ago, xi, use_tau=True, x0=None, teams=None):
    if teams is None:
        teams = sorted(set(home) | set(away))
    idx = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    hi = np.array([idx[t] for t in home]); ai = np.array([idx[t] for t in away])
    w = np.exp(-xi * np.asarray(days_ago, float))
    if x0 is None:
        x0 = np.zeros(2 + 2 * n); x0[0] = 0.25; x0[1] = -0.05
    bounds = [(-1, 1.5), (-0.4, 0.4) if use_tau else (0, 0)] + [(-3, 3)] * (2 * n)
    r = minimize(_dc_negll_grad, x0, args=(hi, ai, np.asarray(x, float), np.asarray(y, float), w, n, use_tau),
                 jac=True, method="L-BFGS-B", bounds=bounds, options=dict(maxiter=500))
    p = r.x
    return dict(teams=teams, idx=idx, H=p[0], rho=p[1], a=p[2:2 + n], d=p[2 + n:], x=p)


def dc_lambdas(m, home, away):
    """Gol attesi; squadre nuove (neopromosse senza storico) = media delle 3 peggiori."""
    a, d = m["a"], m["d"]
    worst = np.argsort(a - d)[:3]
    a_new, d_new = a[worst].mean(), d[worst].mean()
    ga = lambda t: a[m["idx"][t]] if t in m["idx"] else a_new
    gd = lambda t: d[m["idx"][t]] if t in m["idx"] else d_new
    mu = np.array([np.exp(ga(h) + gd(w) + m["H"]) for h, w in zip(home, away)])
    nu = np.array([np.exp(ga(w) + gd(h)) for h, w in zip(home, away)])
    return mu, nu


def score_matrix(mu, nu, rho, G=10):
    k = np.arange(G + 1)
    pm = poisson.pmf(k[None, :], mu[:, None])
    pn = poisson.pmf(k[None, :], nu[:, None])
    M = pm[:, :, None] * pn[:, None, :]
    M[:, 0, 0] *= np.maximum(1 - mu * nu * rho, 1e-10)
    M[:, 1, 0] *= np.maximum(1 + nu * rho, 1e-10)
    M[:, 0, 1] *= np.maximum(1 + mu * rho, 1e-10)
    M[:, 1, 1] *= np.maximum(1 - rho, 1e-10)
    M /= M.sum((1, 2), keepdims=True)
    return M


def probs_1x2(M):
    ph = np.array([np.tril(m, -1).sum() for m in M])
    pd_ = np.array([np.trace(m) for m in M])
    pa = np.array([np.triu(m, 1).sum() for m in M])
    return np.column_stack([ph, pd_, pa])


def walk_forward_dc(df, xi, years_window=5, step_days=7, start=None, use_tau=True,
                    gx="hg", gy="ag"):
    """Previsioni out-of-sample: rifit ogni step_days usando solo partite precedenti.
    Restituisce DataFrame con mu, nu, rho, H per ogni partita da start in poi."""
    out = []
    for lg, g in df.groupby("Division"):
        g = g.sort_values("date")
        t0 = pd.Timestamp(start) if start else g.date.min() + pd.Timedelta(days=365 * 2)
        cuts = pd.date_range(t0, g.date.max() + pd.Timedelta(days=1), freq=f"{step_days}D")
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
            m = fit_dc(tr.HomeTeam.values, tr.AwayTeam.values, tr[gx].values, tr[gy].values,
                       (c0 - tr.date).dt.days.values, xi, use_tau=use_tau, x0=x0, teams=teams)
            x0, prev_teams = m["x"], teams
            mu, nu = dc_lambdas(m, test.HomeTeam.values, test.AwayTeam.values)
            o = pd.DataFrame(dict(mu=mu, nu=nu, rho=m["rho"], H=m["H"]), index=test.index)
            out.append(o)
    return pd.concat(out).sort_index()


def add_dc_probs(o, rho=None, prefix=""):
    M = score_matrix(o.mu.values, o.nu.values, o.rho.values if rho is None else rho)
    P = probs_1x2(M)
    o[prefix + "pH"], o[prefix + "pD"], o[prefix + "pA"] = P.T
    return o


# ─────────────────────────────── pi-ratings ──────────────────────────────────
def pi_ratings(df, lam=0.06, gam=0.6, c=3.0):
    """Pi-ratings (Constantinou & Fenton 2013). Restituisce rating PRE-partita."""
    R = {}  # team -> [home_rating, away_rating]
    cols = np.zeros((len(df), 4))
    for k, (i, r) in enumerate(df.iterrows()):
        h, a = r.HomeTeam, r.AwayTeam
        Rh, Ra = R.setdefault(h, [0.0, 0.0]), R.setdefault(a, [0.0, 0.0])
        cols[k] = [Rh[0], Rh[1], Ra[0], Ra[1]]
        eh = np.sign(Rh[0]) * (10 ** (abs(Rh[0]) / c) - 1)
        ea = np.sign(Ra[1]) * (10 ** (abs(Ra[1]) / c) - 1)
        e = (r.hg - r.ag) - (eh - ea)
        psi = np.sign(e) * c * np.log10(1 + abs(e))
        dh, da = psi * lam, -psi * lam
        Rh[0] += dh; Rh[1] += dh * gam
        Ra[1] += da; Ra[0] += da * gam
    return pd.DataFrame(cols, index=df.index, columns=["pi_hh", "pi_ha", "pi_ah", "pi_aa"])
