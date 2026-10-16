"""
Round 2 — gol attesi impliciti dalle quote e Elo-Odds.

implied_inputs(): probabilità senza margine 1X2 e Over/Under 2.5 da QUOTE DI CHIUSURA di ogni partita.
solve_lambdas(): per ogni partita (lambda_casa, lambda_ospite) tali che una Poisson (indipendente o con rho
  Dixon-Coles fisso) riproduca al meglio P(1), P(X), P(2), P(Over 2.5) — minimi quadrati sulle probabilità,
  Levenberg-Marquardt vettorizzato. Dove manca l'O/U si usano solo le tre probabilità 1X2 (2 incognite, 2
  equazioni indipendenti: il sistema è esattamente identificato).

Tutte le quote usate sono quelle della partita stessa, destinate ESCLUSIVAMENTE ad alimentare modelli
che le vedono solo per partite già concluse alla data di previsione (vedi round2_models.walk_forward_ext).
"""
import numpy as np
import pandas as pd
from scipy.special import gammaln

from backtest.round2_lib import devig

GRID = 14
_K = np.arange(GRID)
_LGK = gammaln(_K + 1)


def _pmf(lam):
    lam = np.maximum(lam, 1e-6)
    return np.exp(_K[None, :] * np.log(lam)[:, None] - lam[:, None] - _LGK[None, :])


def model_probs(lh, la, rho=0.0):
    """P(1), P(X), P(2), P(Over 2.5) per un batch di coppie di lambda (matrice DC con rho fisso)."""
    ph, pa = _pmf(lh), _pmf(la)
    M = ph[:, :, None] * pa[:, None, :]
    if rho:
        M[:, 0, 0] *= np.maximum(1 - lh * la * rho, 1e-10)
        M[:, 1, 0] *= np.maximum(1 + la * rho, 1e-10)
        M[:, 0, 1] *= np.maximum(1 + lh * rho, 1e-10)
        M[:, 1, 1] *= np.maximum(1 - rho, 1e-10)
    M /= M.sum((1, 2), keepdims=True)
    ii, jj = np.indices((GRID, GRID))
    p1 = (M * (ii > jj)).sum((1, 2))
    px = (M * (ii == jj)).sum((1, 2))
    p2 = (M * (ii < jj)).sum((1, 2))
    po = (M * ((ii + jj) >= 3)).sum((1, 2))
    return np.column_stack([p1, px, p2, po])


def solve_lambdas(T, has_ou, rho=0.0, iters=40):
    """T: (n, 4) probabilità di mercato [P1, PX, P2, POver]; has_ou: (n,) bool.
    Restituisce (lh, la, sse) con sse = somma dei quadrati dei residui alla soluzione."""
    n = len(T)
    w = np.column_stack([np.ones(n), np.ones(n), np.ones(n), has_ou.astype(float)])
    th = np.tile(np.log([1.45, 1.15]), (n, 1))
    damp = np.full(n, 1e-2)

    def resid(th_):
        return (model_probs(np.exp(th_[:, 0]), np.exp(th_[:, 1]), rho) - T) * w

    r = resid(th)
    sse = (r ** 2).sum(1)
    eps = 1e-4
    for _ in range(iters):
        J = np.empty((n, 4, 2))
        for k in range(2):
            t2 = th.copy(); t2[:, k] += eps
            J[:, :, k] = (resid(t2) - r) / eps
        A = np.einsum("nik,nil->nkl", J, J)
        g = np.einsum("nik,ni->nk", J, r)
        A_d = A + damp[:, None, None] * np.eye(2)[None]
        step = np.linalg.solve(A_d, -g[:, :, None])[:, :, 0]
        th_new = np.clip(th + step, np.log(0.05), np.log(8.0))
        r_new = resid(th_new)
        sse_new = (r_new ** 2).sum(1)
        better = sse_new < sse
        th = np.where(better[:, None], th_new, th)
        r = np.where(better[:, None], r_new, r)
        sse = np.where(better, sse_new, sse)
        damp = np.where(better, np.maximum(damp / 3, 1e-8), damp * 4)
    return np.exp(th[:, 0]), np.exp(th[:, 1]), sse


def implied_inputs(df, source="avg", method="power"):
    """Probabilità di mercato senza margine da quote di chiusura.
    source: 'avg' = media di mercato in chiusura (dal 2019/20), Pinnacle chiusura prima;
            'pin' = Pinnacle chiusura (1X2 e O/U) dove disponibile, altrimenti come 'avg'.
    O/U 2.5: chiusura (AvgC>2.5 / PC>2.5) dal 2019/20; per le stagioni 2012-2018 non esiste la chiusura O/U
    e si usa la media pre-chiusura dei bookmaker (BbAv>2.5, BbAv<2.5)."""
    n = len(df)
    c1 = df[["cl_h", "cl_d", "cl_a"]].to_numpy(float)        # AvgC dal 2019/20, Pinnacle chiusura prima
    if source == "pin":
        pin = df[["psc_h", "psc_d", "psc_a"]].to_numpy(float)
        okp = np.isfinite(pin).all(1) & (pin > 1).all(1)
        c1 = np.where(okp[:, None], pin, c1)
    ou_pick = []
    if source == "pin":
        ou_pick.append(df[["ou_psc_o", "ou_psc_u"]].to_numpy(float))
    ou_pick.append(df[["ou_avgc_o", "ou_avgc_u"]].to_numpy(float))
    ou_pick.append(df[["ou_bb_o", "ou_bb_u"]].to_numpy(float))
    ou = np.full((n, 2), np.nan)
    src_ou = np.zeros(n, int)
    for i, cand in enumerate(ou_pick):
        ok = np.isfinite(cand).all(1) & (cand > 1).all(1) & ~np.isfinite(ou).all(1)
        ou[ok] = cand[ok]
        src_ou[ok] = i + 1
    P12 = devig(c1, method)
    POU = devig(ou, method)
    T = np.column_stack([P12, POU[:, 0]])
    has_1x2 = np.isfinite(P12).all(1)
    has_ou = np.isfinite(POU).all(1)
    return T, has_1x2, has_ou, src_ou


def implied_lambdas(df, source="avg", method="power", rho=0.0):
    """DataFrame (indice df) con imp_h, imp_a, flag has_ou e sse; NaN dove mancano le quote 1X2."""
    T, has12, has_ou, src_ou = implied_inputs(df, source, method)
    out = pd.DataFrame(index=df.index, columns=["imp_h", "imp_a", "has_ou", "sse"], dtype=float)
    m = has12
    Tm = T[m].copy()
    ou_m = has_ou[m]
    Tm[~ou_m, 3] = 0.0
    lh, la, sse = solve_lambdas(Tm, ou_m, rho)
    out.loc[m, "imp_h"], out.loc[m, "imp_a"], out.loc[m, "sse"] = lh, la, sse
    out["has_ou"] = has_ou & has12
    return out


# ─────────────────────────────────── Elo-Odds ────────────────────────────────
def elo_odds(df, K=20.0, source="avg", method="power", init_penalty=0.0, season_shrink=0.0):
    """Elo-Odds (Wunderlich & Memmert): rating Elo aggiornato dove il "risultato" è la probabilità implicita
    del mercato (S = P1 + 0.5*PX dalle quote di chiusura senza margine) invece del risultato reale.

    Rating per campionato (5 sistemi separati), pre-partita: usa SOLO le partite precedenti per data
    (le quote della partita da prevedere servono solo DOPO aver letto il rating pre-partita).
    Vantaggio casa HFA (punti Elo): media corrente delle S osservate nel campionato fino a quel momento.
    Squadra mai vista: rating medio delle 3 squadre più deboli del campionato (convenzione del DC);
    alla prima stagione tutti 1500. season_shrink: ritorno parziale alla media di campionato a inizio stagione.
    Restituisce DataFrame con eo_diff (rating casa − ospite pre-partita, senza HFA) e eo_exp (prob. attesa)."""
    T, has12, _, _ = implied_inputs(df, source, method)
    S = np.where(has12, T[:, 0] + 0.5 * T[:, 1], np.nan)
    out = pd.DataFrame(index=df.index, columns=["eo_diff", "eo_exp"], dtype=float)
    for lg, g in df.groupby("Division"):
        g = g.sort_values(["date"], kind="stable")
        R = {}
        s_sum, s_n = 0.58 * 50, 50           # prior: 50 partite al 58% di punteggio atteso casa
        last_season = None
        idx = g.index.to_numpy()
        for pos, i in enumerate(idx):
            row = g.loc[i]
            h, a, season = row.HomeTeam, row.AwayTeam, row.season
            if last_season is not None and season != last_season and season_shrink:
                mean_r = np.mean(list(R.values())) if R else 1500.0
                for t in R:
                    R[t] = mean_r + (1 - season_shrink) * (R[t] - mean_r)
            last_season = season
            if h not in R or a not in R:
                low = np.mean(sorted(R.values())[:3]) - init_penalty if len(R) >= 3 else 1500.0
                R.setdefault(h, low)
                R.setdefault(a, low)
            hfa = 400 * np.log10((s_sum / s_n) / (1 - s_sum / s_n))
            d = R[h] - R[a]
            E = 1 / (1 + 10 ** (-(d + hfa) / 400))
            out.at[i, "eo_diff"], out.at[i, "eo_exp"] = d, E
            s = S[df.index.get_loc(i)]
            if np.isfinite(s):
                R[h] += K * (s - E)
                R[a] -= K * (s - E)
                s_sum += s; s_n += 1
    return out
