"""
Round 2 — Esperimento 3: ricalibrazione 1X2 walk-forward.

Il ricalibratore viene rifittato ogni settimana SOLO sulle previsioni out-of-sample del modello di partenza
per partite già concluse (data < data del rifit), con espansione della finestra. Finché ci sono meno di
N_MIN partite concluse si usa l'identità (nessuna ricalibrazione).

Input per partita: lambda casa/ospite del modello (mu, nu) e le sue probabilità 1X2.
  x1 = log(mu/nu),  x2 = mu + nu - 2.7
Modelli:
  ol      ordered logit        eta = b1*x1 + b2*x2;  P(2)=s(t1-eta), P(2 o X)=s(t2-eta);  t2-t1 = exp(w0)
  olflex  ordered logit con ampiezza della banda del pareggio  exp(w0 + w1*x2 + w2*x1^2)
  ts      temperature scaling globale          p_k ~ p_k^(1/T)
  ts_d    temperatura separata per il pareggio  p_H, p_A ~ ^(1/T);  p_X ~ ^(1/T_d)
  ts_b    temperatura globale + bias additivo (log) sul pareggio
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, log_softmax

N_MIN = 600


def _feats(mu, nu):
    return np.log(mu / nu), (mu + nu) - 2.7


def _ol_probs(par, x1, x2, flex):
    b1, b2, c0, w0 = par[:4]
    w1, w2 = (par[4], par[5]) if flex else (0.0, 0.0)
    w = np.exp(w0 + w1 * x2 + w2 * x1 ** 2)
    eta = b1 * x1 + b2 * x2
    pa = expit(c0 - 0.5 * w - eta)
    pad = expit(c0 + 0.5 * w - eta)
    P = np.column_stack([1 - pad, pad - pa, pa])
    return np.clip(P, 1e-9, 1)


def _ts_probs(par, L, kind):
    """L: log-probabilità del modello (n,3) in ordine H, D, A."""
    if kind == "ts":
        z = L / np.exp(par[0])
    elif kind == "ts_d":
        z = np.column_stack([L[:, 0] / np.exp(par[0]), L[:, 1] / np.exp(par[1]), L[:, 2] / np.exp(par[0])])
    elif kind == "ts_b":
        z = L / np.exp(par[0])
        z = z + np.array([0.0, par[1], 0.0])
    return np.exp(log_softmax(z, axis=1))


INIT = {"ol": [1.0, 0.0, 0.0, 0.4], "olflex": [1.0, 0.0, 0.0, 0.4, 0.0, 0.0],
        "ts": [0.0], "ts_d": [0.0, 0.0], "ts_b": [0.0, 0.0]}


def _probs(kind, par, x1, x2, L):
    if kind in ("ol", "olflex"):
        return _ol_probs(par, x1, x2, kind == "olflex")
    return _ts_probs(par, L, kind)


def fit_one(kind, x1, x2, L, y, x0=None):
    def nll(par):
        P = _probs(kind, par, x1, x2, L)
        return -np.log(P[np.arange(len(y)), y]).mean()
    r = minimize(nll, INIT[kind] if x0 is None else x0, method="L-BFGS-B")
    return r.x


def walk_forward_recal(dates, mu, nu, P_model, y, kinds, n_min=N_MIN, step_days=7):
    """dates: Series datetime (ordinato non necessario); mu, nu, P_model (n,3), y (n,) numpy.
    Restituisce {kind: (n,3) probabilità ricalibrate, nello stesso ordine di ingresso} e il numero di partite
    con identità (burn-in)."""
    order = np.argsort(dates.to_numpy(), kind="stable")
    d = dates.to_numpy()[order]
    x1, x2 = _feats(mu[order], nu[order])
    Pm = P_model[order]
    L = np.log(np.clip(Pm, 1e-9, 1))
    yy = y[order]
    out = {k: Pm.copy() for k in kinds}
    params = {k: None for k in kinds}
    cuts = pd.date_range(pd.Timestamp(d.min()).normalize(), pd.Timestamp(d.max()) + pd.Timedelta(days=1),
                         freq=f"{step_days}D")
    burn = 0
    hist = {k: [] for k in kinds}
    for c0, c1 in zip(cuts[:-1], cuts[1:]):
        te = (d >= c0.to_datetime64()) & (d < c1.to_datetime64())
        if not te.any():
            continue
        tr = d < c0.to_datetime64()
        if tr.sum() < n_min:
            burn += int(te.sum())
            continue
        for k in kinds:
            params[k] = fit_one(k, x1[tr], x2[tr], L[tr], yy[tr], params[k])
            out[k][te] = _probs(k, params[k], x1[te], x2[te], L[te])
            hist[k].append((c0, params[k].copy()))
    res = {}
    inv = np.empty_like(order)
    inv[order] = np.arange(len(order))
    for k in kinds:
        res[k] = out[k][inv]
    return res, burn, hist


# ───────────────────── coerenza: matrice dei punteggi riponderata ─────────────────────
def tilt_matrix(M, P_old, P_new):
    """M: (n,G,G) matrice dei punteggi (indici [gol casa, gol ospite]); P_old/P_new (n,3) probabilità 1X2
    prima/dopo la ricalibrazione. Ogni cella viene moltiplicata per P_new/P_old della sua classe di esito:
    le probabilità 1X2 diventano esattamente P_new, la forma dei punteggi DENTRO ciascun esito è invariata,
    quindi punteggio consigliato, Over/Under, BTTS ecc. si ricalcolano dalla matrice riponderata."""
    G = M.shape[1]
    ii, jj = np.indices((G, G))
    cls = np.where(ii > jj, 0, np.where(ii == jj, 1, 2))
    ratio = P_new / np.maximum(P_old, 1e-12)
    return M * ratio[:, cls]
