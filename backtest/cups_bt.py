"""
Round 4 / esperimento F (solo backtest): coppe europee, gare di ritorno.

  build_elo(games)         Elo ricostruito (metodo ClubElo / World Football Elo) su TUTTE le partite della tabella games
  cup_table(games, elo, minutes_max)   tabella delle partite di CL/EL/UCOL (fasi principali, senza finali) con Elo pre-partita,
                           classe 1X2 ai 90', flag supplementari, coppia andata/ritorno e differenza reti dell'andata
  fit_predict(...)         modello Elo -> gol (Poisson pesate) -> matrice Dixon-Coles, walk-forward per stagione
"""
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy.special import gammaln

from backtest import models

K_ELO, HFA, START = 20.0, 100.0, 1500.0
CUPS = ("CL", "EL", "UCOL")
HALF_LIFE_SEASONS = 3.0


def build_elo(games: pd.DataFrame) -> pd.DataFrame:
    """Elo PRIMA di ogni partita (elo_h, elo_a), per game_id. games: colonne game_id, date, round, home_club_id,
    away_club_id, home_club_goals, away_club_goals."""
    g = games.dropna(subset=["home_club_id", "away_club_id", "home_club_goals", "away_club_goals"]).sort_values(["date", "game_id"], kind="stable")
    R = {}
    n = len(g)
    eh, ea = np.empty(n), np.empty(n)
    final = g["round"].astype(str).str.lower().eq("final").to_numpy()
    for i, (h, a, hg, ag) in enumerate(zip(g.home_club_id.to_numpy(), g.away_club_id.to_numpy(),
                                           g.home_club_goals.to_numpy(), g.away_club_goals.to_numpy())):
        rh, ra = R.get(h, START), R.get(a, START)
        eh[i], ea[i] = rh, ra
        hfa = 0.0 if final[i] else HFA
        E = 1 / (1 + 10 ** (-(rh - ra + hfa) / 400))
        d = abs(hg - ag)
        G = 1.0 if d <= 1 else (1.5 if d == 2 else (11 + d) / 8)
        S = 1.0 if hg > ag else (0.5 if hg == ag else 0.0)
        delta = K_ELO * G * (S - E)
        R[h], R[a] = rh + delta, ra - delta
    out = pd.DataFrame({"game_id": g.game_id.to_numpy(), "elo_h": eh, "elo_a": ea})
    out.attrs["final_ratings"] = R
    return out


def cup_table(games: pd.DataFrame, elo: pd.DataFrame, minutes_max: pd.Series) -> pd.DataFrame:
    c = games[games.competition_id.isin(CUPS)].copy()
    c = c.dropna(subset=["home_club_goals", "away_club_goals"])
    c = c.merge(elo, on="game_id", how="inner")
    c["round_l"] = c["round"].astype(str).str.lower()
    c["is_final"] = c.round_l.eq("final")
    c["is_group"] = c.round_l.str.startswith("group")
    c["mx"] = c.game_id.map(minutes_max)
    c["has_minutes"] = c.mx.notna()
    c["is_et"] = c.mx > 95
    c = c[~c.is_final].copy()
    # coppie andata / ritorno tra le partite a eliminazione diretta
    ko = c[~c.is_group]
    first_of = {}
    for r in ko.itertuples():
        first_of.setdefault((r.competition_id, r.season, r.home_club_id, r.away_club_id), []).append((r.date, r.game_id, r.home_club_goals, r.away_club_goals))
    g_val = np.full(len(c), np.nan)
    idx = {gid: i for i, gid in enumerate(c.game_id)}
    for r in ko.itertuples():
        cand = [x for x in first_of.get((r.competition_id, r.season, r.away_club_id, r.home_club_id), [])
                if 0 < (r.date - x[0]).days <= 30]
        if cand:
            d0, gid0, hg0, ag0 = max(cand)                    # l'andata piu' recente prima del ritorno
            g_val[idx[r.game_id]] = float(ag0 - hg0)          # reti dell'andata dal punto di vista di chi gioca in casa il ritorno
    c["g"] = g_val
    c["is_return"] = ~np.isnan(g_val)
    # partite di andata: quelle che compaiono come partner di un ritorno
    c["is_first_leg"] = False
    partner = {}
    for r in c[c.is_return].itertuples():
        cand = [x for x in first_of[(r.competition_id, r.season, r.away_club_id, r.home_club_id)] if 0 < (r.date - x[0]).days <= 30]
        partner[max(cand)[1]] = True
    c.loc[c.game_id.isin(partner), "is_first_leg"] = True
    c["is_single_ko"] = ~c.is_group & ~c.is_return & ~c.is_first_leg
    hg, ag = c.home_club_goals.to_numpy(), c.away_club_goals.to_numpy()
    y = np.where(hg > ag, 0, np.where(hg == ag, 1, 2))
    # classe ai 90' per le partite ai supplementari (regola esatta, vedi prereg)
    et = c.is_et.to_numpy()
    y90 = y.copy()
    ret = c.is_return.to_numpy()
    gv = np.nan_to_num(c.g.to_numpy())
    y90[et & ret] = np.where(gv[et & ret] > 0, 2, np.where(gv[et & ret] < 0, 0, 1))
    y90[et & c.is_single_ko.to_numpy()] = 1
    # ET su una gara di andata o di girone: impossibile, il flag è spurio -> si tiene il punteggio registrato
    c["et_ok"] = et & (ret | c.is_single_ko.to_numpy())
    c["y"] = y90
    c["elo_diff"] = (c.elo_h - c.elo_a) / 100.0
    c["usable_goals"] = ~c.et_ok                               # per il training dei gol: fuori le partite ai supplementari
    return c.reset_index(drop=True)


# ───────────────────────────── modello ─────────────────────────────
def design(c: pd.DataFrame, form: str) -> np.ndarray:
    ed = c.elo_diff.to_numpy()[:, None]
    g = np.nan_to_num(c.g.to_numpy())
    if form == "base":
        return ed
    gc = np.clip(g, -3, 3)
    if form == "F1":
        return np.column_stack([ed, gc])
    if form == "F2":
        return np.column_stack([ed, np.sign(g)])
    if form == "F3":
        return np.column_stack([ed, np.clip(np.maximum(g, 0), 0, 3), np.clip(np.minimum(g, 0), -3, 0)])
    raise ValueError(form)


def _fit(X, hg, ag, w):
    from sklearn.linear_model import PoissonRegressor
    mh = PoissonRegressor(alpha=1e-9, max_iter=2000).fit(X, hg, sample_weight=w)
    ma = PoissonRegressor(alpha=1e-9, max_iter=2000).fit(X, ag, sample_weight=w)
    mu, nu = mh.predict(X), ma.predict(X)

    def nll(r):
        t = np.ones(len(hg))
        m00 = (hg == 0) & (ag == 0); m10 = (hg == 1) & (ag == 0)
        m01 = (hg == 0) & (ag == 1); m11 = (hg == 1) & (ag == 1)
        t[m00] = 1 - mu[m00] * nu[m00] * r; t[m10] = 1 + nu[m10] * r
        t[m01] = 1 + mu[m01] * r; t[m11] = 1 - r
        return -(w * np.log(np.maximum(t, 1e-10))).sum()
    rho = minimize_scalar(nll, bounds=(-0.3, 0.3), method="bounded").x
    return mh, ma, rho


def walk_forward(c: pd.DataFrame, form: str, first_test=2016, last_test=2025):
    """Probabilità 1X2 (n,3) per le partite con season in [first_test, last_test]; NaN altrove."""
    X_all = design(c, form)
    P = np.full((len(c), 3), np.nan)
    for s in range(first_test, last_test + 1):
        tr = (c.season < s).to_numpy() & c.usable_goals.to_numpy()
        te = (c.season == s).to_numpy()
        if not te.any() or tr.sum() < 50:
            continue
        w = 0.5 ** ((s - 1 - c.season.to_numpy()[tr]) / HALF_LIFE_SEASONS)
        mh, ma, rho = _fit(X_all[tr], c.home_club_goals.to_numpy()[tr], c.away_club_goals.to_numpy()[tr], w)
        mu, nu = mh.predict(X_all[te]), ma.predict(X_all[te])
        M = models.score_matrix(mu, nu, np.full(len(mu), rho))
        P[te] = models.probs_1x2(M)
    return P
