"""
ClubElo pre-partita per il backtest (feature elo_diff), con alias ESPLICITI tra i nomi
di football-data.co.uk e quelli di ClubElo (stesso approccio di TEAM_ALIASES in
scripts/generate_static.py: niente fuzzy matching).

Per ogni squadra football-data si prova la lista ordinata di nomi ClubElo candidati;
vale il primo che restituisce uno storico non vuoto e con il paese giusto. Se una squadra
non viene risolta il caricamento fallisce (strict) e stampa l'elenco dei nomi mancanti,
così gli alias si correggono a mano invece di perdere copertura in silenzio.

Rating usato: quello valido il giorno PRIMA della partita (nessun dato della partita).
"""
import io
import os
import time

import numpy as np
import pandas as pd
import requests

BASE_URL = "http://api.clubelo.com/{name}"
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "data", "cache", "clubelo")
SLEEP_S = 1.0
COUNTRY = {"I1": "ITA", "E0": "ENG", "D1": "GER", "SP1": "ESP", "F1": "FRA"}

# nome football-data -> candidati ClubElo (nome "con spazi", come nella colonna Club)
CLUBELO_ALIASES = {
    # Serie A
    "Atalanta": ["Atalanta"], "Benevento": ["Benevento"], "Bologna": ["Bologna"],
    "Brescia": ["Brescia"], "Cagliari": ["Cagliari"], "Carpi": ["Carpi"],
    "Catania": ["Catania"], "Cesena": ["Cesena"], "Chievo": ["Chievo"], "Como": ["Como"],
    "Cremonese": ["Cremonese"], "Crotone": ["Crotone"], "Empoli": ["Empoli"],
    "Fiorentina": ["Fiorentina"], "Frosinone": ["Frosinone"], "Genoa": ["Genoa"],
    "Inter": ["Inter"], "Juventus": ["Juventus"], "Lazio": ["Lazio"], "Lecce": ["Lecce"],
    "Livorno": ["Livorno"], "Milan": ["Milan"], "Monza": ["Monza"], "Napoli": ["Napoli"],
    "Palermo": ["Palermo"], "Parma": ["Parma"], "Pescara": ["Pescara"], "Pisa": ["Pisa"],
    "Roma": ["Roma"], "Salernitana": ["Salernitana"], "Sampdoria": ["Sampdoria"],
    "Sassuolo": ["Sassuolo"], "Siena": ["Siena"], "Spal": ["Spal", "SPAL"],
    "Spezia": ["Spezia"], "Torino": ["Torino"], "Udinese": ["Udinese"],
    "Venezia": ["Venezia"], "Verona": ["Verona", "Hellas Verona"],
    # Premier League
    "Arsenal": ["Arsenal"], "Aston Villa": ["Aston Villa"], "Bournemouth": ["Bournemouth"],
    "Brentford": ["Brentford"], "Brighton": ["Brighton"], "Burnley": ["Burnley"],
    "Cardiff": ["Cardiff"], "Chelsea": ["Chelsea"], "Coventry": ["Coventry"],
    "Crystal Palace": ["Crystal Palace"], "Everton": ["Everton"], "Fulham": ["Fulham"],
    "Huddersfield": ["Huddersfield"], "Hull": ["Hull"], "Ipswich": ["Ipswich"],
    "Leeds": ["Leeds"], "Leicester": ["Leicester"], "Liverpool": ["Liverpool"],
    "Luton": ["Luton"], "Man City": ["Man City"], "Man United": ["Man United"],
    "Middlesbrough": ["Middlesbrough"], "Newcastle": ["Newcastle"], "Norwich": ["Norwich"],
    "Nott'm Forest": ["Forest", "Nottingham Forest"], "QPR": ["QPR"], "Reading": ["Reading"],
    "Sheffield United": ["Sheffield United", "Sheffield Utd"], "Southampton": ["Southampton"],
    "Stoke": ["Stoke"], "Sunderland": ["Sunderland"], "Swansea": ["Swansea"],
    "Tottenham": ["Tottenham"], "Watford": ["Watford"], "West Brom": ["West Brom"],
    "West Ham": ["West Ham"], "Wigan": ["Wigan"], "Wolves": ["Wolves"],
    # Bundesliga
    "Augsburg": ["Augsburg"], "Bayern Munich": ["Bayern", "Bayern Munich"],
    "Bielefeld": ["Bielefeld"], "Bochum": ["Bochum"], "Braunschweig": ["Braunschweig"],
    "Darmstadt": ["Darmstadt"], "Dortmund": ["Dortmund"],
    "Ein Frankfurt": ["Frankfurt", "Eintracht Frankfurt"], "Elversberg": ["Elversberg"],
    "FC Koln": ["Koeln", "Koln"], "Fortuna Dusseldorf": ["Duesseldorf", "Dusseldorf"],
    "Freiburg": ["Freiburg"], "Greuther Furth": ["Fuerth", "Furth"], "Hamburg": ["Hamburg"],
    "Hannover": ["Hannover"], "Heidenheim": ["Heidenheim"], "Hertha": ["Hertha"],
    "Hoffenheim": ["Hoffenheim"], "Holstein Kiel": ["Holstein Kiel", "Kiel"],
    "Ingolstadt": ["Ingolstadt"], "Leverkusen": ["Leverkusen"],
    "M'gladbach": ["Gladbach", "Moenchengladbach"], "Mainz": ["Mainz"],
    "Nurnberg": ["Nuernberg", "Nurnberg"], "Paderborn": ["Paderborn"],
    "RB Leipzig": ["RB Leipzig", "Leipzig"], "Schalke 04": ["Schalke 04", "Schalke"],
    "St Pauli": ["St Pauli"], "Stuttgart": ["Stuttgart"], "Union Berlin": ["Union Berlin"],
    "Werder Bremen": ["Werder Bremen", "Bremen"], "Wolfsburg": ["Wolfsburg"],
    # La Liga
    "Alaves": ["Alaves"], "Almeria": ["Almeria"], "Ath Bilbao": ["Bilbao", "Athletic Bilbao"],
    "Ath Madrid": ["Atletico", "Atletico Madrid"], "Barcelona": ["Barcelona"],
    "Betis": ["Betis"], "Cadiz": ["Cadiz"], "Celta": ["Celta"], "Cordoba": ["Cordoba"],
    "Eibar": ["Eibar"], "Elche": ["Elche"], "Espanol": ["Espanyol", "Espanol"],
    "Getafe": ["Getafe"], "Girona": ["Girona"], "Granada": ["Granada"], "Huesca": ["Huesca"],
    "La Coruna": ["La Coruna", "Deportivo"], "Las Palmas": ["Las Palmas"],
    "Leganes": ["Leganes"], "Levante": ["Levante"], "Malaga": ["Malaga"],
    "Mallorca": ["Mallorca"], "Osasuna": ["Osasuna"], "Oviedo": ["Oviedo"],
    "Real Madrid": ["Real Madrid"], "Santander": ["Santander", "Racing Santander"],
    "Sevilla": ["Sevilla"], "Sociedad": ["Sociedad", "Real Sociedad"],
    "Sp Gijon": ["Gijon", "Sporting Gijon"], "Valencia": ["Valencia"],
    "Valladolid": ["Valladolid"], "Vallecano": ["Rayo Vallecano", "Vallecano"],
    "Villarreal": ["Villarreal"], "Zaragoza": ["Zaragoza"],
    # Ligue 1
    "Ajaccio": ["Ajaccio"], "Ajaccio GFCO": ["Gazelec", "Gazelec Ajaccio", "GFC Ajaccio"],
    "Amiens": ["Amiens"], "Angers": ["Angers"], "Auxerre": ["Auxerre"], "Bastia": ["Bastia"],
    "Bordeaux": ["Bordeaux"], "Brest": ["Brest"], "Caen": ["Caen"], "Clermont": ["Clermont"],
    "Dijon": ["Dijon"], "Evian Thonon Gaillard": ["Evian TG", "Evian"],
    "Guingamp": ["Guingamp"], "Le Havre": ["Le Havre"], "Le Mans": ["Le Mans"],
    "Lens": ["Lens"], "Lille": ["Lille"], "Lorient": ["Lorient"], "Lyon": ["Lyon"],
    "Marseille": ["Marseille"], "Metz": ["Metz"], "Monaco": ["Monaco"],
    "Montpellier": ["Montpellier"], "Nancy": ["Nancy"], "Nantes": ["Nantes"], "Nice": ["Nice"],
    "Nimes": ["Nimes"], "Paris FC": ["Paris FC"], "Paris SG": ["Paris SG", "PSG"],
    "Reims": ["Reims"], "Rennes": ["Rennes"], "Sochaux": ["Sochaux"],
    "St Etienne": ["St Etienne", "Saint-Etienne"], "Strasbourg": ["Strasbourg"],
    "Toulouse": ["Toulouse"], "Troyes": ["Troyes"], "Valenciennes": ["Valenciennes"],
}


def _fetch(club_name: str) -> pd.DataFrame | None:
    """Storico ClubElo di un club (cache su disco). None se non esiste o API non raggiungibile."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe = club_name.replace(" ", "")
    path = os.path.join(CACHE_DIR, f"{safe}.csv")
    if os.path.exists(path):
        text = open(path, encoding="utf-8").read()
    else:
        text = None
        for attempt in range(3):
            try:
                resp = requests.get(BASE_URL.format(name=safe), timeout=30)
            except requests.RequestException:
                resp = None
            time.sleep(SLEEP_S)
            if resp is not None and resp.status_code == 200:
                text = resp.text
                break
            if resp is not None and resp.status_code == 404:
                break
            time.sleep(2 * (attempt + 1))
        if text is None:
            return None
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    if not text.strip():
        return None
    try:
        h = pd.read_csv(io.StringIO(text), parse_dates=["From", "To"])
    except Exception:
        return None
    return h if len(h) else None


def api_available() -> bool:
    try:
        r = requests.get(BASE_URL.format(name="ManCity"), timeout=20)
        return r.status_code == 200 and len(r.text) > 100
    except requests.RequestException:
        return False


def load_histories(feat, verbose=True, strict=True):
    """Storici ClubElo per tutte le squadre presenti in feat. Ritorna {(div, team): DataFrame}."""
    pairs = sorted(set(zip(feat.Division, feat.HomeTeam)) | set(zip(feat.Division, feat.AwayTeam)))
    out, missing = {}, []
    for div, team in pairs:
        cands = CLUBELO_ALIASES.get(team)
        hist = None
        for c in cands or []:
            h = _fetch(c)
            if h is not None and (h["Country"] == COUNTRY[div]).mean() > 0.5:
                hist = h.sort_values("From").reset_index(drop=True)
                break
        if hist is None:
            missing.append((div, team, cands))
        else:
            out[(div, team)] = hist
    if verbose:
        print(f"  Elo: {len(out)}/{len(pairs)} squadre risolte")
    if missing and strict:
        lines = "\n".join(f"    {d}/{t}: candidati {c}" for d, t, c in missing)
        raise RuntimeError(f"Squadre senza storico ClubElo (correggere CLUBELO_ALIASES):\n{lines}")
    return out


def _rating_on(hist, dates):
    """Rating valido alla data indicata (NaN prima del primo rating)."""
    from_ = hist["From"].values
    to = hist["To"].values
    idx = np.searchsorted(from_, dates, side="right") - 1
    ok = (idx >= 0)
    idx = np.clip(idx, 0, len(hist) - 1)
    ok &= dates <= to[idx]
    return np.where(ok, hist["Elo"].values[idx], np.nan)


def add_elo(feat, strict=True, verbose=True):
    """Aggiunge elo_home, elo_away, elo_diff (pre-partita: rating del giorno prima)."""
    hists = load_histories(feat, verbose=verbose, strict=strict)
    feat = feat.copy()
    feat["elo_home"] = np.nan
    feat["elo_away"] = np.nan
    before = (feat.date - pd.Timedelta(days=1)).values.astype("datetime64[ns]")
    for (div, team), h in hists.items():
        for col, side in (("elo_home", "HomeTeam"), ("elo_away", "AwayTeam")):
            m = ((feat.Division == div) & (feat[side] == team)).values
            if m.any():
                feat.loc[m, col] = _rating_on(h, before[m])
    feat["elo_diff"] = feat.elo_home - feat.elo_away
    if verbose:
        print(f"  Elo: copertura {feat.elo_diff.notna().mean() * 100:.1f}% delle partite")
    return feat
