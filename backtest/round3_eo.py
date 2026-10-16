"""
Round 3 — varianti di Elo-Odds (solo backtest). Le regole di base sono quelle di backtest/eloodds.py (produzione):
Elo per campionato, "risultato" = S = P(1) + 0.5 P(X) dalle quote senza margine (power), squadra nuova = media dei 3
rating piu' bassi, HFA = media corrente di S nel campionato.

  scores(df, source)        S per partita: source 'avg' = chiusura media poi quote pre-partita (produzione);
                            'pin' = Pinnacle in chiusura, poi chiusura media, poi quote pre-partita
  build_std(df, S, K)       eo_diff standard con K uniforme o per campionato ({Division: K})
  build_ha(df, S, K, gamma) rating separati casa / trasferta: feature = R_casa[squadra di casa] - R_trasf[ospite];
                            ogni partita aggiorna R_casa[casa] e R_trasf[ospite] con K*(S-E) e, con frazione gamma,
                            R_trasf[casa] e R_casa[ospite] (con segno opposto per l'ospite).
"""
import numpy as np
import pandas as pd

from backtest import eloodds as E


def scores(df, source="avg"):
    chain = []
    if source == "pin":
        chain.append(df[["psc_h", "psc_d", "psc_a"]].to_numpy(float))
    chain.append(df[["cl_h", "cl_d", "cl_a"]].to_numpy(float))
    chain.append(df[["odds_h", "odds_d", "odds_a"]].to_numpy(float))
    n = len(df)
    P = np.full((n, 3), np.nan)
    src = np.zeros(n, int)
    for i, o in enumerate(chain):
        p = E.power_devig(o)
        ok = np.isfinite(p).all(1) & ~np.isfinite(P).all(1)
        P[ok], src[ok] = p[ok], i + 1
    S = np.where(np.isfinite(P).all(1), P[:, 0] + 0.5 * P[:, 1], np.nan)
    return S, src


def _groups(df):
    for lg, g in df.groupby("Division"):
        yield lg, g.sort_values("date", kind="stable")


def build_std(df, S_all, K):
    s_ser = pd.Series(S_all, index=df.index)
    out = pd.Series(np.nan, index=df.index, name="eo_diff")
    for lg, g in _groups(df):
        k = K[lg] if isinstance(K, dict) else K
        diff, _ = E._run_league(g.HomeTeam.to_numpy(), g.AwayTeam.to_numpy(), s_ser.loc[g.index].to_numpy(), k)
        out.loc[g.index] = diff
    return out


def _run_league_ha(home, away, S, K, gamma):
    RH, RA = {}, {}
    s_sum, s_n = E.HFA_PRIOR_S * E.HFA_PRIOR_N, E.HFA_PRIOR_N
    diff = np.empty(len(home))
    for i, (h, a) in enumerate(zip(home, away)):
        if h not in RH or a not in RH:                    # come in produzione: entrambe le nuove squadre ricevono lo stesso valore
            low_h, low_a = E._initial_rating(RH), E._initial_rating(RA)
            for t in (h, a):
                RH.setdefault(t, low_h)
                RA.setdefault(t, low_a)
        m = s_sum / s_n
        hfa = 400 * np.log10(m / (1 - m))
        d = RH[h] - RA[a]
        diff[i] = d
        s = S[i]
        if np.isfinite(s):
            err = K * (s - 1 / (1 + 10 ** (-(d + hfa) / 400)))
            RH[h] += err
            RA[a] -= err
            RA[h] += gamma * err
            RH[a] -= gamma * err
            s_sum += s
            s_n += 1
    return diff


def build_ha(df, S_all, K, gamma):
    s_ser = pd.Series(S_all, index=df.index)
    out = pd.Series(np.nan, index=df.index, name="eo_ha")
    for lg, g in _groups(df):
        out.loc[g.index] = _run_league_ha(g.HomeTeam.to_numpy(), g.AwayTeam.to_numpy(), s_ser.loc[g.index].to_numpy(), K, gamma)
    return out
