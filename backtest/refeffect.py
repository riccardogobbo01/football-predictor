"""
Effetto arbitro sui cartellini gialli (round 5, forma b, k=20), versione di produzione.

Definizione (backtest/round5_parts/prereg.md): per ogni partita, R = (Σ y_j + k·m̄) / (Σ m_j + k·m̄) sulle partite PRECEDENTI dello
stesso arbitro (chiave = campionato + arbitro), con y_j gialli totali osservati, m_j gialli totali attesi dal modello senza arbitro
(walk-forward fuori campione per le stagioni >= 2019/20, in campione per il 2016/17-2018/19), k partite equivalenti di shrinkage
(config.REFEREE_K), m̄ = media dei gialli attesi della lega nel 2016/17-2018/19. Arbitro sconosciuto o senza storico: R = 1,
cioè effetto zero. log R è l'ultima feature (`ref_logR`) delle due regressioni di Poisson dei gialli.

Il training (scripts/train_stack.py) calcola log R per ogni partita storica e le somme finali per arbitro, salvate in
models/stack.json["referees"]; il serving (predictions/stack_predictor.py) le usa per le partite future. Lo storico arbitri
viene da data/referees/matches.csv (Transfermarkt 2016/17-2025/26 + football-data.org fino al backfill) e dalla colonna `referee`
di docs/history.csv per le partite giocate dopo.
"""
import os

import numpy as np
import pandas as pd

from backtest import referees as RF, stats_model as sm
from backtest.referee_aliases import REFEREE_ALIASES
from config import REFEREE_K

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MATCHES_CSV = os.path.join(REPO_ROOT, "data", "referees", "matches.csv")
HISTORY_CSV = os.path.join(REPO_ROOT, "docs", "history.csv")
FIRST_TRAIN = sm.FIRST_TRAIN_SEASON            # 2016
FIRST_TEST = 2019
MBAR_SEASONS = (2016, 2017, 2018)
LEAGUE_CODE = {"serie_a": "I1", "premier_league": "E0", "bundesliga": "D1", "la_liga": "SP1", "ligue_1": "F1"}


class RefereeDataError(RuntimeError):
    pass


def resolve(division: str, name) -> str | None:
    """Chiave canonica di un arbitro: alias esplicito (REFEREE_ALIASES) o, se manca, il nome normalizzato stesso."""
    n = RF.normalize(name)
    if n is None:
        return None
    return REFEREE_ALIASES.get(division, {}).get(n, n)


def season_of(date) -> int:
    d = pd.Timestamp(date)
    return d.year if d.month >= 7 else d.year - 1


# ───────────────────────────── storico arbitri ─────────────────────────────
def load_history_keys(df: pd.DataFrame, matches_csv: str = MATCHES_CSV, history_csv: str = HISTORY_CSV) -> pd.Series:
    """Chiave arbitro per ogni riga di df (None se sconosciuta). Fonti: matches.csv e, per le partite giocate dopo, history.csv."""
    if not os.path.exists(matches_csv):
        raise RefereeDataError(f"{matches_csv} mancante: storico degli arbitri non disponibile")
    m = pd.read_csv(matches_csv, dtype=str)
    key = {}
    for r in m.itertuples(index=False):
        key[(r.Division, int(r.season), r.HomeTeam, r.AwayTeam)] = r.referee_key
    n_csv = len(key)
    if os.path.exists(history_csv):
        h = pd.read_csv(history_csv, dtype=str)
        if "referee" in h.columns:
            h = h[h.referee.notna() & h.result.notna() & h.league.isin(LEAGUE_CODE)]
            for r in h.itertuples(index=False):
                div = LEAGUE_CODE[r.league]
                k = (div, season_of(r.match_date), r.home_dc, r.away_dc)
                if k not in key:
                    rk = resolve(div, r.referee)
                    if rk:
                        key[k] = rk
    out = [key.get((dv, int(s), h, a)) for dv, s, h, a in zip(df.Division, df.season, df.HomeTeam, df.AwayTeam)]
    return pd.Series(out, index=df.index, dtype=object)


# ───────────────────────────── calcolo dell'effetto ─────────────────────────────
def base_predictions(feat: pd.DataFrame, stat: str = "gialli"):
    """Medie attese (mh, ma) del modello SENZA arbitro (variante with_xg): walk-forward per stagione dal 2019/20, in campione
    per il 2016/17-2018/19 (previsioni del primo fold). Serie con NaN dove le feature non ci sono."""
    hc, ac = sm.STATS[stat][:2]
    X = sm.design(feat, stat, True)
    has_x = X.notna().all(axis=1)
    ok = has_x & feat[hc].notna() & feat[ac].notna()
    mh = pd.Series(np.nan, index=feat.index)
    ma = pd.Series(np.nan, index=feat.index)
    for s in sorted(feat.season.unique()):
        if s < FIRST_TEST:
            continue
        tr = ok & (feat.season >= FIRST_TRAIN) & (feat.season < s)
        te = has_x & (feat.season == s)
        if not te.any() or tr.sum() < 100:
            continue
        m = sm.fit_stat_model(X[tr], feat[hc][tr], feat[ac][tr])
        mh[te], ma[te] = sm.predict_means(m, X[te])
        if s == FIRST_TEST:
            mh[tr], ma[tr] = sm.predict_means(m, X[tr])
    return mh, ma


def mbar_by_league(feat, m_tot) -> dict:
    sel = feat.season.isin(MBAR_SEASONS) & m_tot.notna()
    return {k: float(v) for k, v in m_tot[sel].groupby(feat.Division[sel]).mean().items()}


def referee_ratio(feat, y, m, keys, k, mbar):
    """(R per riga, somme finali {"Div|chiave": [Σy, Σm, n]}). Le partite si leggono in ordine di data; R usa solo le precedenti."""
    order = np.argsort(feat.date.to_numpy(), kind="stable")
    sums = {}
    out = np.ones(len(feat))
    div = feat.Division.to_numpy()
    yv, mv = y.to_numpy(float), m.to_numpy(float)
    kv = keys.to_numpy(dtype=object)
    default = float(np.mean(list(mbar.values())))
    for i in order:
        key = kv[i]
        if key is None or (isinstance(key, float) and np.isnan(key)):
            continue
        kk = f"{div[i]}|{key}"
        s = sums.setdefault(kk, [0.0, 0.0, 0])
        mb = mbar.get(div[i], default)
        out[i] = (s[0] + k * mb) / (s[1] + k * mb)
        if np.isfinite(yv[i]) and np.isfinite(mv[i]):
            s[0] += yv[i]
            s[1] += mv[i]
            s[2] += 1
    return pd.Series(out, index=feat.index), sums


def compute(feat: pd.DataFrame, keys: pd.Series, k: float = REFEREE_K):
    """feat: feature del training con anche le feature delle statistiche (build_stat_features); keys: chiave arbitro per riga.
    Restituisce (ref_logR per riga, stato per il serving)."""
    mh, ma = base_predictions(feat)
    m_tot = mh + ma
    y = feat["HY"] + feat["AY"]
    mbar = mbar_by_league(feat, m_tot)
    R, sums = referee_ratio(feat, y, m_tot, keys, k, mbar)
    state = {"k": float(k), "mbar": mbar, "effects": {kk: [round(v[0], 3), round(v[1], 3), int(v[2])] for kk, v in sums.items() if v[2] > 0},
             "asof": str(feat.date.max().date()), "n_matches_with_referee": int(keys.notna().sum()),
             "n_referees": int(len(sums))}
    return np.log(R), state


# ───────────────────────────── serving ─────────────────────────────
def ratio(state: dict, division: str, name) -> tuple:
    """(R, chiave, storico_noto) per un arbitro indicato da football-data.org. Sconosciuto o senza storico -> R = 1."""
    if not state or not name:
        return 1.0, None, False
    key = resolve(division, name)
    e = state["effects"].get(f"{division}|{key}")
    if key is None or e is None:
        return 1.0, key, False
    mb = state["mbar"].get(division, float(np.mean(list(state["mbar"].values()))))
    k = state["k"]
    return (e[0] + k * mb) / (e[1] + k * mb), key, True


def check_premier_league(df: pd.DataFrame, keys: pd.Series) -> dict:
    """Controllo di coerenza con la colonna Referee di football-data.co.uk (solo Premier League): stesso cognome."""
    fd = RF.fd_referee_e0(df).reindex(df.index)
    e0 = df.Division == "E0"
    both = e0 & keys.notna() & fd.notna()
    if not both.any():
        return {"n": 0, "agree": None}
    same = [RF.normalize(a).split()[-1] == RF.normalize(b).split()[-1] for a, b in zip(keys[both], fd[both])]
    return {"n": int(both.sum()), "agree": float(np.mean(same))}
