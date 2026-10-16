"""
Valore della rosa Transfermarkt (dataset dcaribou/transfermarkt-datasets, tabella player_valuations; solo backtest).

Valore di un club a una data di riferimento D = somma, sui giocatori con almeno una valutazione nella finestra
(D - window, D], dell'ULTIMA valutazione <= D, assegnata al club indicato in quella riga (current_club_id = club al momento
della valutazione). Le squadre con meno di MIN_VALUED giocatori valutati sono "non affidabili" (tipico delle neopromosse:
la seconda divisione non è nel dataset): il loro valore è imputato col minimo tra i club affidabili della stessa lega e
stagione. Abbinamento dei nomi: tabella ESPLICITA backtest/transfermarkt_aliases.py, controllata per copertura.

Niente di tutto ciò usa dati posteriori alla data D, che precede la prima partita della stagione.
"""
import os

import numpy as np
import pandas as pd

from backtest.transfermarkt_aliases import TM_ALIASES

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cache", "transfermarkt")
MIN_VALUED = 12
FIRST_SEASON = 2013


class TransfermarktError(RuntimeError):
    pass


def load_valuations():
    pv = pd.read_csv(os.path.join(DATA_DIR, "player_valuations.csv.gz"),
                     usecols=["player_id", "date", "market_value_in_eur", "current_club_id"], parse_dates=["date"])
    return pv.dropna(subset=["market_value_in_eur", "current_club_id"]).astype({"current_club_id": int})


def club_values(pv, ref_date, window_days):
    """DataFrame club_id -> (value, n) alla data di riferimento."""
    ref = pd.Timestamp(ref_date)
    w = pv[(pv.date <= ref) & (pv.date > ref - pd.Timedelta(days=window_days))]
    last = w.sort_values("date").groupby("player_id").tail(1)
    g = last.groupby("current_club_id").agg(value=("market_value_in_eur", "sum"), n=("player_id", "size"))
    return g


def check_aliases(df):
    """Ogni squadra di ogni (campionato, stagione) >= FIRST_SEASON deve avere un alias: altrimenti errore."""
    missing = set()
    for (lg, s), g in df[df.season >= FIRST_SEASON].groupby(["Division", "season"]):
        for t in set(g.HomeTeam) | set(g.AwayTeam):
            if t not in TM_ALIASES[lg]:
                missing.add((lg, t))
    if missing:
        raise TransfermarktError(f"squadre senza alias Transfermarkt: {sorted(missing)}")
    ids = [v[0] for lg in TM_ALIASES.values() for v in lg.values()]
    # un club_id non deve essere assegnato a due squadre dello stesso campionato
    for lg, d in TM_ALIASES.items():
        v = [x[0] for x in d.values()]
        if len(set(v)) != len(v):
            raise TransfermarktError(f"club_id duplicati in {lg}")


def team_table(df, pv, month_day=(8, 1), window_days=365):
    """Una riga per (campionato, stagione, squadra): value, n, reliable, value_imp, tm_rel (log del valore relativo alla
    media della lega, con imputazione per le non affidabili) e tm_chg (variazione rispetto alla stagione precedente, 0 se
    una delle due stagioni è non affidabile)."""
    check_aliases(df)
    cache = {}
    rows = []
    for (lg, s), g in df[df.season >= FIRST_SEASON].groupby(["Division", "season"]):
        ref = pd.Timestamp(year=int(s), month=month_day[0], day=month_day[1])
        if ref not in cache:
            cache[ref] = club_values(pv, ref, window_days)
        cv = cache[ref]
        for t in sorted(set(g.HomeTeam) | set(g.AwayTeam)):
            cid = TM_ALIASES[lg][t][0]
            v, n = (cv.value.get(cid, 0.0), int(cv.n.get(cid, 0)))
            rows.append(dict(Division=lg, season=int(s), team=t, club_id=cid, value=float(v), n=n))
    T = pd.DataFrame(rows)
    T["reliable"] = T.n >= MIN_VALUED
    out = []
    for (lg, s), g in T.groupby(["Division", "season"]):
        g = g.copy()
        mn = g.value[g.reliable].min()
        g["value_imp"] = np.where(g.reliable, g.value, mn)
        g["tm_rel"] = np.log(g.value_imp / g.value_imp.mean())
        out.append(g)
    T = pd.concat(out)
    prev = T.set_index(["Division", "team", "season"])[["tm_rel", "reliable"]]
    chg = []
    for r in T.itertuples():
        k = (r.Division, r.team, r.season - 1)
        if k in prev.index and r.reliable and prev.at[k, "reliable"]:
            chg.append(r.tm_rel - prev.at[k, "tm_rel"])
        else:
            chg.append(0.0)
    T["tm_chg"] = chg
    return T


def match_features(df, T, chg=False):
    """tm_diff (e opzionalmente tm_chg_diff) per ogni partita di df: casa - ospite. NaN prima di FIRST_SEASON."""
    idx = T.set_index(["Division", "season", "team"])
    out = pd.DataFrame(index=df.index, columns=["tm_diff", "tm_chg_diff"], dtype=float)
    ok = (df.season >= FIRST_SEASON).to_numpy()
    kh = list(zip(df.Division[ok], df.season[ok], df.HomeTeam[ok]))
    ka = list(zip(df.Division[ok], df.season[ok], df.AwayTeam[ok]))
    h, a = idx.loc[kh], idx.loc[ka]
    out.loc[ok, "tm_diff"] = h.tm_rel.to_numpy() - a.tm_rel.to_numpy()
    out.loc[ok, "tm_chg_diff"] = h.tm_chg.to_numpy() - a.tm_chg.to_numpy()
    return out if chg else out[["tm_diff"]]
