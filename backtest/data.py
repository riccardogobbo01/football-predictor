"""
Download e normalizzazione dei CSV di football-data.co.uk per il backtest.

Stagioni dalla 2012/13 alla corrente, top-5 campionati (I1, E0, D1, SP1, F1).
Cache locale in data/cache/ (nel .gitignore): le stagioni concluse si scaricano
una sola volta, quella in corso viene riscaricata se la cache ha più di 12 ore.

Il DataFrame restituito usa lo stesso schema atteso da backtest/models.py:
  Division, date, HomeTeam, AwayTeam, hg, ag, res (0=1, 1=X, 2=2), season,
  HST, AST, odds_h/odds_d/odds_a (quote medie), cl_h/cl_d/cl_a (chiusura).
"""
import io
import os
import time
from datetime import datetime

import numpy as np
import pandas as pd
import requests

LEAGUES = ["I1", "E0", "D1", "SP1", "F1"]
LEAGUE_NAMES = {"I1": "Serie A", "E0": "Premier League", "D1": "Bundesliga",
                "SP1": "La Liga", "F1": "Ligue 1"}

FIRST_SEASON = 2012
BASE_URL = "https://www.football-data.co.uk/mmz4281/{code}/{league}.csv"
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "data", "cache")
CURRENT_CACHE_MAX_AGE_S = 12 * 3600

# Colonne quote: (casa, X, trasferta) in ordine di preferenza
AVG_ODDS = [("AvgH", "AvgD", "AvgA"), ("BbAvH", "BbAvD", "BbAvA"), ("B365H", "B365D", "B365A")]
CLOSING_ODDS = [("AvgCH", "AvgCD", "AvgCA"), ("PSCH", "PSCD", "PSCA")]


def current_season() -> int:
    today = datetime.utcnow()
    return today.year if today.month >= 7 else today.year - 1


def season_code(season: int) -> str:
    return f"{season % 100:02d}{(season + 1) % 100:02d}"


def _download(season: int, league: str, session: requests.Session) -> bytes | None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"{season_code(season)}_{league}.csv")
    is_current = season == current_season()

    if os.path.exists(path):
        age = time.time() - os.path.getmtime(path)
        if not is_current or age < CURRENT_CACHE_MAX_AGE_S:
            with open(path, "rb") as fh:
                return fh.read()

    url = BASE_URL.format(code=season_code(season), league=league)
    resp = session.get(url, timeout=30)
    if resp.status_code != 200 or len(resp.content) < 200:
        return None
    with open(path, "wb") as fh:
        fh.write(resp.content)
    return resp.content


def _first_available(df: pd.DataFrame, candidates: list[tuple[str, str, str]]):
    """Prima terna di colonne quote presente nel file, con valori numerici."""
    for cols in candidates:
        if all(c in df.columns for c in cols):
            out = df[list(cols)].apply(pd.to_numeric, errors="coerce")
            if out.notna().all(axis=1).any():
                return out.to_numpy(dtype=float)
    return np.full((len(df), 3), np.nan)


def _parse_one(raw: bytes, season: int, league: str) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(raw), encoding="latin-1", on_bad_lines="skip", low_memory=False)
    df = df.dropna(subset=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]).copy()
    if df.empty:
        return df

    out = pd.DataFrame(index=df.index)
    out["Division"] = league
    out["date"] = pd.to_datetime(df["Date"], dayfirst=True, format="mixed", errors="coerce")
    out["HomeTeam"] = df["HomeTeam"].astype(str).str.strip()
    out["AwayTeam"] = df["AwayTeam"].astype(str).str.strip()
    out["hg"] = pd.to_numeric(df["FTHG"], errors="coerce")
    out["ag"] = pd.to_numeric(df["FTAG"], errors="coerce")
    for col in ("HST", "AST"):
        out[col] = pd.to_numeric(df[col], errors="coerce") if col in df.columns else np.nan

    odds = _first_available(df, AVG_ODDS)
    out["odds_h"], out["odds_d"], out["odds_a"] = odds.T
    closing = _first_available(df, CLOSING_ODDS)
    out["cl_h"], out["cl_d"], out["cl_a"] = closing.T

    out = out.dropna(subset=["date", "hg", "ag"])
    out["hg"] = out["hg"].astype(int)
    out["ag"] = out["ag"].astype(int)
    # stagione = quella del file CSV (non dedotta dal mese: la coda del 2019/20 è stata giocata
    # a luglio-agosto 2020 e va nella 2019/20)
    out["season"] = season
    out["res"] = np.select([out.hg > out.ag, out.hg == out.ag], [0, 1], 2)
    return out


def load_matches(first_season: int = FIRST_SEASON, verbose: bool = True) -> pd.DataFrame:
    frames = []
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (football-predictor backtest)"

    for season in range(first_season, current_season() + 1):
        for league in LEAGUES:
            raw = _download(season, league, session)
            if raw is None:
                if verbose:
                    print(f"  ⚠ {season_code(season)}/{league}: non disponibile")
                continue
            part = _parse_one(raw, season, league)
            if not part.empty:
                frames.append(part)

    df = pd.concat(frames, ignore_index=True)
    df = df.sort_values(["Division", "date"]).reset_index(drop=True)
    if verbose:
        print(f"  {len(df)} partite caricate, "
              f"{df.date.min().date()} → {df.date.max().date()}")
    return df
