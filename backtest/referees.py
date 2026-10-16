"""
Round 5 (solo backtest): arbitro di ogni partita di campionato dalla tabella `games` di Transfermarkt
(dataset dcaribou/transfermarkt-datasets, data/cache/transfermarkt/games.csv.gz), abbinata alle partite di football-data
per (campionato, stagione, club casa, club ospite) con i club_id di transfermarkt_aliases.py.
"""
import os
import re
import unicodedata

import numpy as np
import pandas as pd

from backtest.transfermarkt_aliases import TM_ALIASES

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cache", "transfermarkt")
COMP_TO_DIV = {"IT1": "I1", "GB1": "E0", "L1": "D1", "ES1": "SP1", "FR1": "F1"}


def normalize(name) -> str | None:
    """Minuscolo, senza accenti, senza titoli («Dr.», «Prof.») e punteggiatura. None se vuoto."""
    if not isinstance(name, str) or not name.strip():
        return None
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(dr|prof|mr)\b\.?", " ", s)
    s = re.sub(r"[^a-z\s'-]", " ", s)
    s = " ".join(s.split())
    return s or None


def load_games():
    g = pd.read_csv(os.path.join(DATA_DIR, "games.csv.gz"),
                    usecols=["game_id", "competition_id", "season", "date", "home_club_id", "away_club_id", "referee"],
                    parse_dates=["date"])
    g = g[g.competition_id.isin(COMP_TO_DIV)].copy()
    g["Division"] = g.competition_id.map(COMP_TO_DIV)
    g["ref_norm"] = g.referee.map(normalize)
    return g.drop_duplicates(["Division", "season", "home_club_id", "away_club_id"])


def map_referees(df: pd.DataFrame) -> pd.DataFrame:
    """Per ogni riga di df: ref_norm (None se non abbinata o senza arbitro) e flag `matched` (partita trovata in games)."""
    g = load_games()
    hid = np.array([TM_ALIASES[dv][t][0] if t in TM_ALIASES[dv] else -1 for dv, t in zip(df.Division, df.HomeTeam)])
    aid = np.array([TM_ALIASES[dv][t][0] if t in TM_ALIASES[dv] else -1 for dv, t in zip(df.Division, df.AwayTeam)])
    key = pd.DataFrame({"Division": df.Division.to_numpy(), "season": df.season.to_numpy(),
                        "home_club_id": hid, "away_club_id": aid}, index=df.index)
    m = key.reset_index().merge(g[["Division", "season", "home_club_id", "away_club_id", "game_id", "ref_norm"]],
                                on=["Division", "season", "home_club_id", "away_club_id"], how="left").set_index("index")
    out = pd.DataFrame({"ref": m.ref_norm.reindex(df.index), "matched": m.game_id.reindex(df.index).notna()}, index=df.index)
    return out


def fd_referee_e0(df: pd.DataFrame) -> pd.Series:
    """Arbitro da football-data (colonna Referee, solo Premier League), normalizzato, per le righe E0 di df."""
    from backtest import data
    parts = []
    for s in range(data.FIRST_SEASON, data.current_season() + 1):
        p = os.path.join(data.CACHE_DIR, f"{data.season_code(s)}_E0.csv")
        if not os.path.exists(p):
            continue
        d = pd.read_csv(p, encoding="latin-1", on_bad_lines="skip", low_memory=False).dropna(subset=["FTHG"])
        if "Referee" not in d.columns:
            continue
        parts.append(pd.DataFrame({"season": s, "HomeTeam": d.HomeTeam.astype(str).str.strip(),
                                   "AwayTeam": d.AwayTeam.astype(str).str.strip(), "fd_ref": d.Referee.astype(str)}))
    fd = pd.concat(parts).drop_duplicates(["season", "HomeTeam", "AwayTeam"])
    e0 = df[df.Division == "E0"][["season", "HomeTeam", "AwayTeam"]].reset_index().merge(
        fd, on=["season", "HomeTeam", "AwayTeam"], how="left").set_index("index")
    return e0.fd_ref


def same_referee(tm_norm, fd_raw) -> bool:
    """Stesso cognome (ultima parola) e stessa iniziale del nome, dopo la normalizzazione."""
    a, b = normalize(tm_norm), normalize(fd_raw)
    if not a or not b:
        return False
    ta, tb = a.split(), b.split()
    return ta[-1] == tb[-1] and ta[0][0] == tb[0][0]
