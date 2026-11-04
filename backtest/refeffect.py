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
def base_predictions(feat: pd.DataFrame, stat: str = "gialli", with_xg: bool = True):
    """Medie attese (mh, ma) del modello SENZA arbitro (variante with_xg, o without_xg): walk-forward per stagione dal 2019/20, in campione
    per il 2016/17-2018/19 (previsioni del primo fold). Serie con NaN dove le feature non ci sono."""
    hc, ac = sm.STATS[stat][:2]
    X = sm.design(feat, stat, with_xg)
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


EPOCH = pd.Timestamp("2000-01-01")


def referee_ratio(feat, y, m, keys, k, mbar, half_life_days=None):
    """(R per riga, somme finali {"Div|chiave": [Σy, Σm, n, ultimo giorno]}). Le partite si leggono in ordine di data; R usa solo le precedenti.
    half_life_days (round 10, s6-arbitro-decay): peso 0,5^(giorni/emivita) sulle partite passate dell'arbitro (None = peso uniforme, come prima).
    Le somme finali sono quelle DECADUTE fino all'ultimo giorno in cui l'arbitro ha arbitrato (campo 4, giorni dall'epoca 2000-01-01)."""
    order = np.argsort(feat.date.to_numpy(), kind="stable")
    sums = {}
    out = np.ones(len(feat))
    div = feat.Division.to_numpy()
    days = (feat.date - EPOCH).dt.days.to_numpy(float)
    yv, mv = y.to_numpy(float), m.to_numpy(float)
    kv = keys.to_numpy(dtype=object)
    default = float(np.mean(list(mbar.values())))
    for i in order:
        key = kv[i]
        if key is None or (isinstance(key, float) and np.isnan(key)):
            continue
        kk = f"{div[i]}|{key}"
        s = sums.setdefault(kk, [0.0, 0.0, 0, days[i]])
        if half_life_days:
            f = 0.5 ** ((days[i] - s[3]) / half_life_days)
            s[0] *= f
            s[1] *= f
        s[3] = days[i]
        mb = mbar.get(div[i], default)
        out[i] = (s[0] + k * mb) / (s[1] + k * mb)
        if np.isfinite(yv[i]) and np.isfinite(mv[i]):
            s[0] += yv[i]
            s[1] += mv[i]
            s[2] += 1
    return pd.Series(out, index=feat.index), sums


def compute_stat(feat: pd.DataFrame, keys: pd.Series, mh0, ma0, y, k: float = REFEREE_K, half_life_days=None):
    """Effetto arbitro per una statistica generica: mh0/ma0 = medie attese del modello SENZA arbitro (come base_predictions), y = totale
    osservato. Restituisce (log R per riga, stato per il serving). Con half_life_days lo stato ha anche "half_life_days" ed "epoch" e le somme
    per arbitro sono decadute fino all'ultima partita [Σy, Σm, n, giorno]; senza, il formato e' quello originale [Σy, Σm, n]."""
    m_tot = mh0 + ma0
    mbar = mbar_by_league(feat, m_tot)
    R, sums = referee_ratio(feat, y, m_tot, keys, k, mbar, half_life_days)
    if half_life_days:
        eff = {kk: [round(v[0], 4), round(v[1], 4), int(v[2]), int(v[3])] for kk, v in sums.items() if v[2] > 0}
    else:
        eff = {kk: [round(v[0], 3), round(v[1], 3), int(v[2])] for kk, v in sums.items() if v[2] > 0}
    state = {"k": float(k), "mbar": mbar, "effects": eff,
             "asof": str(feat.date.max().date()), "n_matches_with_referee": int(keys.notna().sum()),
             "n_referees": int(len(sums))}
    if half_life_days:
        state.update(half_life_days=float(half_life_days), epoch=str(EPOCH.date()))
    return np.log(R), state


def compute(feat: pd.DataFrame, keys: pd.Series, k: float = REFEREE_K, half_life_days=None, with_xg: bool = True):
    """feat: feature del training con anche le feature delle statistiche (build_stat_features); keys: chiave arbitro per riga.
    Restituisce (ref_logR per riga, stato per il serving) per i GIALLI. with_xg=False: medie di base senza xG (training senza xG)."""
    mh, ma = base_predictions(feat, "gialli", with_xg)
    return compute_stat(feat, keys, mh, ma, feat["HY"] + feat["AY"], k, half_life_days)


# ───────────────────────────── serving ─────────────────────────────
def ratio(state: dict, division: str, name, asof=None) -> tuple:
    """(R, chiave, storico_noto) per un arbitro indicato da football-data.org. Sconosciuto o senza storico -> R = 1.
    Con uno stato a decadimento (half_life_days) le somme dell'arbitro decadono dall'ultima sua partita alla data `asof` (data ISO della partita da
    prevedere; default: oggi) prima del calcolo, come nel walk-forward (`referee_ratio`); uno stato senza decadimento ignora `asof`."""
    if not state or not name:
        return 1.0, None, False
    key = resolve(division, name)
    e = state["effects"].get(f"{division}|{key}")
    if key is None or e is None:
        return 1.0, key, False
    mb = state["mbar"].get(division, float(np.mean(list(state["mbar"].values()))))
    k = state["k"]
    sy, sm = e[0], e[1]
    hl = state.get("half_life_days")
    if hl and len(e) > 3:
        day = (pd.Timestamp(asof) if asof is not None else pd.Timestamp.now().normalize()) - pd.Timestamp(state.get("epoch", "2000-01-01"))
        f = 0.5 ** (max(day.days - e[3], 0) / hl)
        sy, sm = sy * f, sm * f
    return (sy + k * mb) / (sm + k * mb), key, True


def check_premier_league(df: pd.DataFrame, keys: pd.Series) -> dict:
    """Controllo di coerenza con la colonna Referee di football-data.co.uk (solo Premier League): stesso cognome."""
    fd = RF.fd_referee_e0(df).reindex(df.index)
    e0 = df.Division == "E0"
    both = e0 & keys.notna() & fd.notna()
    if not both.any():
        return {"n": 0, "agree": None}
    same = [RF.normalize(a).split()[-1] == RF.normalize(b).split()[-1] for a, b in zip(keys[both], fd[both])]
    return {"n": int(both.sum()), "agree": float(np.mean(same))}
