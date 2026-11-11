"""Round 11 — margine sul mercato. Solo backtest. Criteri in backtest/round11_parts/prereg.md.
Caricamento delle quote (pre-partita e chiusura, 1X2 e Over/Under 2,5) dai CSV football-data in cache e utilità statistiche
(conditional logit, bootstrap a blocchi per settimana ISO)."""
import os

import numpy as np
import pandas as pd

from backtest import data, round7_lib as L7
from backtest.round2_lib import CACHE, devig

# (fonte → colonne 1X2 / colonne O/U 2,5 (Over, Under))
PRE = {"avg": (("AvgH", "AvgD", "AvgA"), ("Avg>2.5", "Avg<2.5")),
       "b365": (("B365H", "B365D", "B365A"), ("B365>2.5", "B365<2.5")),
       "max": (("MaxH", "MaxD", "MaxA"), ("Max>2.5", "Max<2.5"))}
CLO = {"avg": (("AvgCH", "AvgCD", "AvgCA"), ("AvgC>2.5", "AvgC<2.5")),
       "ps": (("PSCH", "PSCD", "PSCA"), ("PC>2.5", "PC<2.5")),
       "max": (("MaxCH", "MaxCD", "MaxCA"), ("MaxC>2.5", "MaxC<2.5"))}
OUTC = ["1", "X", "2"]


def _one(season, league):
    path = os.path.join(CACHE, f"{data.season_code(season)}_{league}.csv")
    if not os.path.exists(path):
        return None
    raw = pd.read_csv(path, encoding="latin-1", on_bad_lines="skip", low_memory=False)
    raw = raw.dropna(subset=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"])
    out = pd.DataFrame({"Division": league, "season": season, "HomeTeam": raw["HomeTeam"].astype(str).str.strip(),
                        "AwayTeam": raw["AwayTeam"].astype(str).str.strip()})
    for tag, table in (("pre", PRE), ("clo", CLO)):
        for src, (c3, c2) in table.items():
            for j, c in enumerate(c3):
                out[f"{tag}_{src}_x{j}"] = pd.to_numeric(raw[c], errors="coerce") if c in raw.columns else np.nan
            for j, c in enumerate(c2):
                out[f"{tag}_{src}_o{j}"] = pd.to_numeric(raw[c], errors="coerce") if c in raw.columns else np.nan
    return out


def load_odds(feat: pd.DataFrame) -> dict:
    """Quote allineate alle righe di `feat` (stesso ordine). Chiavi: ('pre'|'clo', fonte) → {'x': (n,3) quote 1X2, 'o': (n,2) quote (Over, Under)}."""
    parts = [p for s in range(L7.FIRST_TEST, data.current_season() + 1) for lg in L7.LEAGUES if (p := _one(s, lg)) is not None]
    ex = pd.concat(parts, ignore_index=True).drop_duplicates(["Division", "season", "HomeTeam", "AwayTeam"])
    keys = feat[["Division", "season", "HomeTeam", "AwayTeam"]].reset_index(drop=True)
    m = keys.merge(ex, on=["Division", "season", "HomeTeam", "AwayTeam"], how="left")
    assert len(m) == len(feat)
    out = {}
    for tag, table in (("pre", PRE), ("clo", CLO)):
        for src in table:
            out[(tag, src)] = {"x": np.column_stack([m[f"{tag}_{src}_x{j}"].to_numpy(float) for j in range(3)]),
                               "o": np.column_stack([m[f"{tag}_{src}_o{j}"].to_numpy(float) for j in range(2)])}
    return out


def fair(odds):
    """Probabilità senza margine (metodo power); righe non valide → NaN."""
    return devig(odds, "power")


# ───────────────────────────── conditional logit ─────────────────────────────
def logsumexp(z, axis=1):
    m = z.max(axis=axis, keepdims=True)
    return (m + np.log(np.exp(z - m).sum(axis=axis, keepdims=True))).squeeze(axis)


def fit_clogit(feats, y, k, weights=None, w0=None, offset=None, w_init=None):
    """Utilità della classe c: a_c (a_0 = 0) + Σ_f w_f · F_f[:, c]. feats: lista di array (n,k) (log-probabilità).
    Restituisce (a (k-1,), w (nf,)) a massima verosimiglianza (pesi per riga opzionali).
    offset (n,k): termine fisso sommato all'utilità (es. log p del modello: si stimano solo correzioni). feats può essere vuoto (solo intercette)."""
    n = len(y)
    nf = len(feats)
    F = np.stack(feats, axis=2) if nf else np.zeros((n, k, 0))   # n, k, nf
    off = np.zeros((n, k)) if offset is None else np.asarray(offset, float)
    Y = np.zeros((n, k)); Y[np.arange(n), y] = 1.0
    wt = np.ones(n) if weights is None else np.asarray(weights, float)

    # design completo per riga e classe: [dummy classi 1..k-1, feature]  (n, k, q)
    D = np.zeros((n, k, k - 1))
    for c in range(1, k):
        D[:, c, c - 1] = 1.0
    X = np.concatenate([D, F], axis=2)
    q = X.shape[2]
    th = np.zeros(q) if w0 is None else np.asarray(w0, float).copy()
    if w0 is None and nf:
        th[k - 1:] = (1.0 / nf) if w_init is None else w_init
    ll_old = -np.inf
    for _ in range(50):                                       # Newton con hessiana analitica
        z = X @ th + off
        lse = logsumexp(z, axis=1)
        P = np.exp(z - lse[:, None])
        ll = (wt * ((Y * z).sum(1) - lse)).sum()
        R_ = wt[:, None] * (Y - P)
        g = np.einsum("nc,ncq->q", R_, X)
        xb = np.einsum("nc,ncq->nq", P, X)
        Xs = (X * np.sqrt(wt[:, None] * P)[:, :, None]).reshape(-1, q)
        xbs = xb * np.sqrt(wt)[:, None]
        H = -(Xs.T @ Xs - xbs.T @ xbs)
        try:
            step = np.linalg.solve(H - 1e-9 * np.eye(q), -g)
        except np.linalg.LinAlgError:
            break
        t = 1.0
        while t > 1e-4:                                       # ricerca lineare (backtracking)
            thn = th + t * step
            zn = X @ thn + off
            lln = (wt * ((Y * zn).sum(1) - logsumexp(zn, axis=1))).sum()
            if lln >= ll - 1e-12:
                break
            t /= 2
        th = thn
        if np.abs(t * step).max() < 1e-8:
            break
    return th[:k - 1], th[k - 1:]


def predict_clogit(feats, a, w, offset=None, k=None):
    F = np.stack(feats, axis=2) if len(feats) else np.zeros((len(offset), k, 0))
    k = F.shape[1]
    z = np.concatenate([[0.0], a])[None, :] + F @ w + (0.0 if offset is None else np.asarray(offset, float))
    return np.exp(z - logsumexp(z, axis=1)[:, None])


def boot_weights(feats, y, k, weeks, n_boot=2000, seed=31):
    """IC 95% a blocchi (settimane ISO) dei pesi, RIFACENDO la stima a ogni ricampionamento (pesi per riga = quante volte è estratta la sua settimana)."""
    a0, w0 = fit_clogit(feats, y, k)
    th0 = np.concatenate([a0, w0])
    wk, inv = np.unique(np.asarray(weeks), return_inverse=True)
    rng = np.random.default_rng(seed)
    out = np.empty((n_boot, len(w0)))
    for b in range(n_boot):
        cnt = np.bincount(rng.integers(0, len(wk), len(wk)), minlength=len(wk)).astype(float)
        _, wb = fit_clogit(feats, y, k, weights=cnt[inv], w0=th0.copy())
        out[b] = wb
    return w0, out


def pct(a, q=(2.5, 97.5)):
    return tuple(float(np.percentile(a, x)) for x in q)


# ───────────────────────────── bootstrap a blocchi ─────────────────────────────
def block_ratio(num, den, weeks, n_boot=5000, seed=41):
    """Σnum/Σden con IC 95% a blocchi per settimana (num/den per riga; righe NaN escluse)."""
    num, den = np.asarray(num, float), np.asarray(den, float)
    ok = np.isfinite(num) & np.isfinite(den)
    if ok.sum() == 0:
        return float("nan"), float("nan"), float("nan")
    wk, inv = np.unique(np.asarray(weeks)[ok], return_inverse=True)
    sn, sd = np.bincount(inv, num[ok]), np.bincount(inv, den[ok])
    rng = np.random.default_rng(seed)
    b = rng.integers(0, len(wk), size=(n_boot, len(wk)))
    d = sd[b].sum(1)
    with np.errstate(divide="ignore", invalid="ignore"):
        est = np.where(d > 0, sn[b].sum(1) / d, np.nan)
    est = est[np.isfinite(est)]
    lo, hi = (np.percentile(est, 2.5), np.percentile(est, 97.5)) if len(est) else (np.nan, np.nan)
    tot = sd.sum()
    return (float(sn.sum() / tot) if tot > 0 else float("nan")), float(lo), float(hi)


def block_slope(Z, m, weeks, col=1, n_boot=5000, seed=42):
    """Coefficiente `col` della regressione OLS di m su Z con IC 95% a blocchi per settimana."""
    Z, m = np.asarray(Z, float), np.asarray(m, float)
    ok = np.isfinite(Z).all(1) & np.isfinite(m)
    Z, m = Z[ok], m[ok]
    wk, inv = np.unique(np.asarray(weeks)[ok], return_inverse=True)
    q = Z.shape[1]
    S = np.zeros((len(wk), q, q)); T = np.zeros((len(wk), q))
    np.add.at(S, inv, Z[:, :, None] * Z[:, None, :]); np.add.at(T, inv, Z * m[:, None])
    beta = np.linalg.solve(S.sum(0), T.sum(0))
    rng = np.random.default_rng(seed)
    b = rng.integers(0, len(wk), size=(n_boot, len(wk)))
    est = np.linalg.solve(S[b].sum(1), T[b].sum(1)[:, :, None])[:, :, 0][:, col]
    return float(beta[col]), float(np.percentile(est, 2.5)), float(np.percentile(est, 97.5))


def block_corr(d, m, weeks, n_boot=5000, seed=43):
    d, m = np.asarray(d, float), np.asarray(m, float)
    ok = np.isfinite(d) & np.isfinite(m)
    d, m = d[ok], m[ok]
    wk, inv = np.unique(np.asarray(weeks)[ok], return_inverse=True)
    st = np.column_stack([np.ones(len(d)), d, m, d * d, m * m, d * m])
    S = np.zeros((len(wk), 6)); np.add.at(S, inv, st)

    def corr(s):
        n, sd_, sm, sdd, smm, sdm = (s[..., i] for i in range(6))
        cov = sdm / n - sd_ * sm / n ** 2
        return cov / np.sqrt((sdd / n - (sd_ / n) ** 2) * (smm / n - (sm / n) ** 2))

    rng = np.random.default_rng(seed)
    b = rng.integers(0, len(wk), size=(n_boot, len(wk)))
    est = corr(S[b].sum(1))
    return float(corr(S.sum(0))), float(np.percentile(est, 2.5)), float(np.percentile(est, 97.5))
