"""
xG partita per partita da Understat (dal 2014/15), abbinati ai CSV di football-data.co.uk.

  GET https://understat.com/getLeagueData/{lega}/{anno}   (header X-Requested-With: XMLHttpRequest)
  lega: "Serie A", "EPL", "Bundesliga", "La liga", "Ligue 1"; anno = anno di inizio stagione.
  Nel JSON, "dates": per ogni partita con isResult=true si usano datetime, h.title, a.title,
  goals.h/a e xG.h/a.

I nomi squadra si abbinano con la tabella ESPLICITA understat_aliases.UNDERSTAT_ALIASES
(niente fuzzy matching). L'abbinamento alla partita football-data è per
(campionato, stagione, casa, trasferta): in un campionato a girone unico quella terna è
univoca, quindi non dipende da fusi orari / date di calendario diverse.

Cache locale in data/cache/understat/: le stagioni concluse si scaricano una sola volta,
quella in corso viene riscaricata se la cache ha più di 12 ore.
"""
import json
import os
import time
import urllib.parse

import numpy as np
import pandas as pd
import requests

from .understat_aliases import UNDERSTAT_ALIASES

FIRST_SEASON = 2014
UNDERSTAT_LEAGUE = {"I1": "Serie A", "E0": "EPL", "D1": "Bundesliga", "SP1": "La liga", "F1": "Ligue 1"}
URL = "https://understat.com/getLeagueData/{league}/{season}"
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "data", "cache", "understat")
CURRENT_CACHE_MAX_AGE_S = 12 * 3600
SLEEP_S = 1.0
MAX_UNMATCHED = 0.01
MAX_DAYS_APART = 5


class UnderstatError(RuntimeError):
    pass


def _season_matches(raw: dict, div: str, season: int) -> list[dict]:
    out = []
    for m in raw.get("dates", []):
        if not m.get("isResult"):
            continue
        out.append({
            "Division": div, "season": season,
            "ut_date": pd.to_datetime(m["datetime"]),
            "ut_home": m["h"]["title"], "ut_away": m["a"]["title"],
            "ut_hg": int(m["goals"]["h"]), "ut_ag": int(m["goals"]["a"]),
            "xg_h": float(m["xG"]["h"]), "xg_a": float(m["xG"]["a"]),
        })
    return out


def _fetch(season: int, div: str, session: requests.Session, current: int) -> dict:
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"{season}_{div}.json")
    if os.path.exists(path):
        age = time.time() - os.path.getmtime(path)
        if season != current or age < CURRENT_CACHE_MAX_AGE_S:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)

    url = URL.format(league=urllib.parse.quote(UNDERSTAT_LEAGUE[div]), season=season)
    try:
        resp = session.get(url, headers={"X-Requested-With": "XMLHttpRequest"}, timeout=30)
        resp.raise_for_status()
        raw = resp.json()
    except (requests.RequestException, ValueError) as e:
        raise UnderstatError(f"Understat {UNDERSTAT_LEAGUE[div]} {season}: {e}") from e
    if "dates" not in raw:
        raise UnderstatError(f"Understat {UNDERSTAT_LEAGUE[div]} {season}: risposta senza 'dates'")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(raw, fh)
    time.sleep(SLEEP_S)
    return raw


def load_xg(first_season: int = FIRST_SEASON, current: int | None = None, verbose=True) -> pd.DataFrame:
    """Tutte le partite giocate con xG, da first_season alla corrente. Solleva UnderstatError."""
    if current is None:
        from .data import current_season
        current = current_season()
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (football-predictor)"
    rows = []
    for season in range(max(first_season, FIRST_SEASON), current + 1):
        for div in UNDERSTAT_LEAGUE:
            rows += _season_matches(_fetch(season, div, session, current), div, season)
    xg = pd.DataFrame(rows)
    if xg.empty:
        raise UnderstatError("Understat: nessuna partita scaricata")
    if verbose:
        print(f"  Understat: {len(xg)} partite con xG ({xg.season.min()}-{xg.season.max()})")
    return xg


def attach_xg(df: pd.DataFrame, xg: pd.DataFrame, strict: bool = True, verbose=True) -> pd.DataFrame:
    """Aggiunge xg_h / xg_a a df (NaN dove non c'è l'xG). Con strict=True si ferma e
    stampa le squadre mancanti se più dell'1% delle partite delle stagioni scaricate
    resta senza xG."""
    xg = xg.copy()
    unknown = sorted((set(xg.ut_home) | set(xg.ut_away)) - set(UNDERSTAT_ALIASES))
    xg["HomeTeam"] = xg.ut_home.map(UNDERSTAT_ALIASES)
    xg["AwayTeam"] = xg.ut_away.map(UNDERSTAT_ALIASES)

    key = ["Division", "season", "HomeTeam", "AwayTeam"]
    dup = xg.duplicated(key, keep=False)
    if dup.any():
        raise UnderstatError("Understat: chiavi duplicate dopo l'abbinamento nomi:\n"
                             + xg[dup][key].head(10).to_string())

    out = df.drop(columns=[c for c in ("xg_h", "xg_a") if c in df.columns]).merge(
        xg[key + ["xg_h", "xg_a", "ut_hg", "ut_ag", "ut_date"]], on=key, how="left")
    out.index = df.index   # merge sinistro con chiavi uniche: stesso ordine di righe

    # La partita Understat deve cadere entro pochi giorni da quella del CSV: altrimenti la
    # stessa coppia di squadre è stata abbinata a un'altra partita (es. andata/ritorno).
    far = ((out.ut_date.dt.normalize() - out.date).dt.days.abs() > MAX_DAYS_APART)
    n_far = int(far.sum())
    out.loc[far, ["xg_h", "xg_a", "ut_hg", "ut_ag", "ut_date"]] = np.nan

    scope = (out.season >= xg.season.min()) & (out.season <= xg.season.max())
    n_scope = int(scope.sum())
    missing = scope & out.xg_h.isna()
    frac = missing.sum() / n_scope

    # controllo di coerenza: i gol di Understat devono coincidere con quelli del CSV
    both = scope & out.xg_h.notna()
    goal_mismatch = int(((out.hg != out.ut_hg) | (out.ag != out.ut_ag))[both].sum())

    if verbose:
        print(f"  xG abbinati: {int((scope & out.xg_h.notna()).sum())}/{n_scope} partite "
              f"({(1 - frac) * 100:.2f}%), scartati per data lontana: {n_far}, gol discordanti: {goal_mismatch}")

    if verbose and unknown:
        print(f"  ⚠ Nomi Understat senza alias: {unknown}")

    if strict and frac > MAX_UNMATCHED:
        by_team = (out[missing].groupby(["Division", "HomeTeam"]).size()
                   .add(out[missing].groupby(["Division", "AwayTeam"]).size(), fill_value=0)
                   .sort_values(ascending=False))
        lines = [f"Abbinamento xG insufficiente: {missing.sum()} partite ({frac * 100:.2f}%) "
                 f"senza xG (soglia {MAX_UNMATCHED * 100:.0f}%)."]
        if unknown:
            lines.append(f"Nomi Understat NON presenti in UNDERSTAT_ALIASES: {unknown}")
        lines.append("Squadre football-data con partite senza xG (campionato, squadra, partite):")
        lines += [f"  {d}/{t}: {int(n)}" for (d, t), n in by_team.items()]
        raise UnderstatError("\n".join(lines))

    return out.drop(columns=["ut_hg", "ut_ag", "ut_date"])
