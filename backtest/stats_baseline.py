"""
Metodo "a medie" delle statistiche attese (quello che il modello vero sostituisce): serve come
termine di confronto nel backtest (backtest/run_stats_backtest.py).

Per ogni statistica: media con decadimento temporale (xi=0.0018, stagione in corso + precedente)
di quanto ogni squadra produce e concede in casa/trasferta (colonne HS/AS, HC/AC, HY/AY); la
produzione attesa di una squadra è la media tra quello che fa di solito e quello che l'avversario
concede. Squadra senza dati = media di lega.
"""
import numpy as np
import pandas as pd

STATS_XI = 0.0018
STATS_SEASONS = 2
STAT_COLS = {"tiri": ("HS", "AS"), "corner": ("HC", "AC"), "gialli": ("HY", "AY")}


def _wmean(frame, col, by):
    w = frame["_w"]
    return (frame[col] * w).groupby(frame[by]).sum() / w.groupby(frame[by]).sum()


def build_tables(g: pd.DataFrame, today: pd.Timestamp, cur: int) -> dict:
    win = g[(g.season >= cur - STATS_SEASONS + 1) & (g.date < today)].copy()
    if win.empty:
        return {}
    win["_w"] = np.exp(-STATS_XI * (today - win.date).dt.days.to_numpy(float))
    tables = {}
    for name, (hc, ac) in STAT_COLS.items():
        sub = win.dropna(subset=[hc, ac])
        if sub.empty:
            continue
        w = sub["_w"]
        tables[name] = {
            "home_for": _wmean(sub, hc, "HomeTeam"), "home_against": _wmean(sub, ac, "HomeTeam"),
            "away_for": _wmean(sub, ac, "AwayTeam"), "away_against": _wmean(sub, hc, "AwayTeam"),
            "lg_home": float((sub[hc] * w).sum() / w.sum()), "lg_away": float((sub[ac] * w).sum() / w.sum()),
        }
    return tables


def expected(tables: dict, home, away) -> dict:
    """{stat: (atteso casa, atteso ospite)} per una partita."""
    out = {}
    for name, t in tables.items():
        h = (t["home_for"].get(home, t["lg_home"]) + t["away_against"].get(away, t["lg_home"])) / 2
        a = (t["away_for"].get(away, t["lg_away"]) + t["home_against"].get(home, t["lg_away"])) / 2
        out[name] = (float(h), float(a))
    return out


def walk_forward(df: pd.DataFrame, start="2019-07-01", step_days=7) -> pd.DataFrame:
    """Previsioni a medie out-of-sample (tabelle rifatte ogni settimana con le sole partite
    precedenti). Colonne {stat}_bh, {stat}_ba, indicizzate come df, dalle partite da `start`."""
    rows = []
    for lg, g in df.groupby("Division"):
        g = g.sort_values("date")
        cuts = pd.date_range(pd.Timestamp(start), g.date.max() + pd.Timedelta(days=1), freq=f"{step_days}D")
        cuts = cuts.append(cuts[-1:] + pd.Timedelta(days=step_days))      # copre anche l'ultima settimana
        for c0, c1 in zip(cuts[:-1], cuts[1:]):
            test = g[(g.date >= c0) & (g.date < c1)]
            if test.empty:
                continue
            tables = build_tables(g, c0, int(test.season.max()))
            for idx, h, a in zip(test.index, test.HomeTeam.values, test.AwayTeam.values):
                e = expected(tables, h, a)
                rows.append({"_idx": idx, **{f"{k}_bh": v[0] for k, v in e.items()},
                             **{f"{k}_ba": v[1] for k, v in e.items()}})
    out = pd.DataFrame(rows).set_index("_idx").sort_index()
    out.index.name = None
    return out
