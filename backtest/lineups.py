"""
Round 4 / esperimento E (solo backtest): feature dalla formazione titolare, dal dataset dcaribou/transfermarkt-datasets
(tabelle games, appearances, game_lineups, player_valuations in data/cache/transfermarkt/).

Per ogni partita di campionato e per ciascuna delle due squadre:
  - "11 tipici" = i 11 giocatori con piu' minuti nelle ultime N partite del club (qualsiasi competizione del dataset, con
    righe in appearances) con data STRETTAMENTE precedente;
  - lu_cov = quota dei minuti recenti (di tutta la rosa) coperta dagli 11 considerati;
  - lu_val = log(valore di mercato degli 11 considerati / valore degli 11 tipici), valutazioni piu' recenti con data
    strettamente precedente alla partita, 250.000 EUR se un giocatore non ha valutazioni.
"11 considerati" = gli 11 titolari effettivi della partita (test "a formazione nota": informazione NON disponibile al momento
della previsione, quindi limite massimo) oppure gli 11 titolari dell'ultima partita del club (formazione prevista).
Mancanti: meno di 11 titolari nella tabella, o meno di MIN_HISTORY partite di storico -> miss = True.
"""
import bisect
import os
from collections import defaultdict

import numpy as np
import pandas as pd

from backtest.transfermarkt_aliases import TM_ALIASES

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cache", "transfermarkt")
CACHE = os.path.join(os.path.dirname(DATA_DIR), "round4_lineups.pkl")
COMP_TO_DIV = {"IT1": "I1", "GB1": "E0", "L1": "D1", "ES1": "SP1", "FR1": "F1"}
MIN_HISTORY = 3
MISSING_VALUE = 250_000.0


def _load_raw():
    g = pd.read_csv(os.path.join(DATA_DIR, "games.csv.gz"),
                    usecols=["game_id", "competition_id", "season", "date", "home_club_id", "away_club_id"], parse_dates=["date"])
    a = pd.read_csv(os.path.join(DATA_DIR, "appearances.csv.gz"), usecols=["game_id", "player_id", "player_club_id", "minutes_played"])
    l = pd.read_csv(os.path.join(DATA_DIR, "game_lineups.csv.gz"), usecols=["game_id", "club_id", "player_id", "type"])
    v = pd.read_csv(os.path.join(DATA_DIR, "player_valuations.csv.gz"), usecols=["player_id", "date", "market_value_in_eur"],
                    parse_dates=["date"]).dropna()
    return g, a, l[l.type == "starting_lineup"].drop(columns="type"), v


def build_structures():
    """Strutture di lookup (cache su disco)."""
    if os.path.exists(CACHE):
        return pd.read_pickle(CACHE)
    g, a, l, v = _load_raw()
    date_of = dict(zip(g.game_id, g.date.astype("int64")))
    # minuti per (game_id, club_id) -> {player: minuti}
    minutes = defaultdict(dict)
    for gid, cid, pid, mn in zip(a.game_id.to_numpy(), a.player_club_id.to_numpy(), a.player_id.to_numpy(),
                                 a.minutes_played.fillna(0).to_numpy()):
        minutes[(gid, cid)][pid] = minutes[(gid, cid)].get(pid, 0.0) + float(mn)
    starters = defaultdict(list)
    for gid, cid, pid in zip(l.game_id.to_numpy(), l.club_id.to_numpy(), l.player_id.to_numpy()):
        starters[(gid, cid)].append(pid)
    # storico per club: (date_ns, game_id) con minuti disponibili, ordinato
    hist = defaultdict(list)
    for (gid, cid) in minutes:
        if gid in date_of:
            hist[cid].append((date_of[gid], gid))
    for cid in hist:
        hist[cid].sort()
    # storico dei titolari per club (per la formazione prevista): partite con 11 titolari
    shist = defaultdict(list)
    for (gid, cid), pl in starters.items():
        if gid in date_of and len(pl) == 11:
            shist[cid].append((date_of[gid], gid))
    for cid in shist:
        shist[cid].sort()
    val = {}
    v = v.sort_values(["player_id", "date"])
    for pid, grp in v.groupby("player_id"):
        val[pid] = (grp.date.astype("int64").to_numpy(), grp.market_value_in_eur.to_numpy(float))
    league = g[g.competition_id.isin(COMP_TO_DIV)].copy()
    league["Division"] = league.competition_id.map(COMP_TO_DIV)
    S = dict(minutes=dict(minutes), starters=dict(starters), hist=dict(hist), shist=dict(shist), val=val,
             league=league[["game_id", "Division", "season", "date", "home_club_id", "away_club_id"]], date_of=date_of)
    pd.to_pickle(S, CACHE)
    return S


def map_games(df, S):
    """game_id per ogni riga di df (campionati), abbinando (Division, season, id club casa, id club ospite). NaN se assente."""
    hid = np.array([TM_ALIASES[dv][t][0] if t in TM_ALIASES[dv] else -1 for dv, t in zip(df.Division, df.HomeTeam)])
    aid = np.array([TM_ALIASES[dv][t][0] if t in TM_ALIASES[dv] else -1 for dv, t in zip(df.Division, df.AwayTeam)])
    key = pd.DataFrame({"Division": df.Division.to_numpy(), "season": df.season.to_numpy(), "home_club_id": hid, "away_club_id": aid},
                       index=df.index)
    lg = S["league"].drop_duplicates(["Division", "season", "home_club_id", "away_club_id"])
    m = key.reset_index().merge(lg, on=["Division", "season", "home_club_id", "away_club_id"], how="left").set_index("index")
    return m.game_id.reindex(df.index), hid, aid


def _value(S, pid, t_ns):
    arr = S["val"].get(pid)
    if arr is None:
        return MISSING_VALUE
    i = bisect.bisect_left(arr[0], t_ns) - 1          # ultima valutazione con data < t
    return float(arr[1][i]) if i >= 0 else MISSING_VALUE


def team_features(S, club_id, game_id, t_ns, N, predicted):
    """(cov, val, ok) per un club in una partita."""
    h = S["hist"].get(club_id, [])
    k = bisect.bisect_left(h, (t_ns, -1))               # partite con data < t
    prev = h[max(0, k - N):k]
    if len(prev) < MIN_HISTORY:
        return 0.0, 0.0, False
    mins = defaultdict(float)
    for _, gid in prev:
        for pid, mn in S["minutes"][(gid, club_id)].items():
            mins[pid] += mn
    tot = sum(mins.values())
    if tot <= 0:
        return 0.0, 0.0, False
    if predicted:
        sh = S["shist"].get(club_id, [])
        j = bisect.bisect_left(sh, (t_ns, -1))
        if j == 0:
            return 0.0, 0.0, False
        xi = S["starters"][(sh[j - 1][1], club_id)]
    else:
        xi = S["starters"].get((game_id, club_id))
        if xi is None or len(xi) != 11:
            return 0.0, 0.0, False
    typical = [p for p, _ in sorted(mins.items(), key=lambda x: (-x[1], x[0]))[:11]]
    cov = sum(mins.get(p, 0.0) for p in xi) / tot
    v_x = sum(_value(S, p, t_ns) for p in xi)
    v_t = sum(_value(S, p, t_ns) for p in typical)
    return cov, float(np.log(v_x / v_t)), True


def build(df, S, N, predicted=False):
    """DataFrame (indice df) con lu_cov_diff, lu_val_diff (casa - ospite) e lu_miss; differenze 0 dove manca qualcosa."""
    gid, hid, aid = map_games(df, S)
    t_ns = df.date.astype("int64").to_numpy()
    out = np.zeros((len(df), 3))
    for i in range(len(df)):
        g_ = gid.iloc[i]
        if hid[i] < 0 or aid[i] < 0 or (not predicted and pd.isna(g_)):
            out[i, 2] = 1
            continue
        ch, vh, okh = team_features(S, hid[i], g_, t_ns[i], N, predicted)
        ca, va, oka = team_features(S, aid[i], g_, t_ns[i], N, predicted)
        if okh and oka:
            out[i] = (ch - ca, vh - va, 0)
        else:
            out[i, 2] = 1
    return pd.DataFrame(out, index=df.index, columns=["lu_cov_diff", "lu_val_diff", "lu_miss"])
