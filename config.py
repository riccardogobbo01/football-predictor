"""
Configurazione centrale: chiavi API, league IDs, costanti del modello.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── API Keys ─────────────────────────────────────────────────────────────────
FOOTBALL_DATA_ORG_KEY = os.getenv("FOOTBALL_DATA_ORG_KEY", "")
API_FOOTBALL_KEY      = os.getenv("API_FOOTBALL_KEY", "")

# ─── Stagione corrente ────────────────────────────────────────────────────────
CURRENT_SEASON = 2026  # 2026 = stagione 2026/27

# ─── Database ─────────────────────────────────────────────────────────────────
DB_PATH  = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "data", "football.db"))
LOG_PATH = os.path.join(os.path.dirname(__file__), "data", "football.log")

# ─── Campionati (football-data.org competition codes) ─────────────────────────
# https://www.football-data.org/coverage
LEAGUES = {
    "serie_a":          {"fdo_code": "SA",  "name": "Serie A",          "country": "Italy"},
    "premier_league":   {"fdo_code": "PL",  "name": "Premier League",   "country": "England"},
    "bundesliga":       {"fdo_code": "BL1", "name": "Bundesliga",        "country": "Germany"},
    "la_liga":          {"fdo_code": "PD",  "name": "La Liga",           "country": "Spain"},
    "ligue_1":          {"fdo_code": "FL1", "name": "Ligue 1",           "country": "France"},
    "champions_league": {"fdo_code": "CL",  "name": "Champions League",  "country": "World"},
    "europa_league":    {"fdo_code": "EL",  "name": "Europa League",     "country": "World"},
    "conference_league":{"fdo_code": "ECL", "name": "Conference League", "country": "World"},
}

# ─── Codici CSV Football-Data.co.uk per dati storici ──────────────────────────
# https://football-data.co.uk/data.php
FOOTBALL_DATA_CSV = {
    "serie_a":        "I1",   # Italia Serie A
    "premier_league": "E0",   # Inghilterra Premier
    "bundesliga":     "D1",   # Germania Bundesliga
    "la_liga":        "SP1",  # Spagna Primera
    "ligue_1":        "F1",   # Francia Ligue 1
}

# Stagioni disponibili su football-data.co.uk (formato "XXYY")
# es. 2526 = 2025/26, 2425 = 2024/25 ...
HISTORICAL_SEASONS = ["2526", "2425", "2324", "2223", "2122", "2021", "1920", "1819"]

# ─── Understat league codes ───────────────────────────────────────────────────
UNDERSTAT_LEAGUES = {
    "serie_a":        "Serie_A",
    "premier_league": "EPL",
    "bundesliga":     "Bundesliga",
    "la_liga":        "La_liga",
    "ligue_1":        "Ligue_1",
}

# ─── Parametri modello Dixon-Coles ────────────────────────────────────────────
DC_XI   = 0.0018   # tasso di decadimento temporale (≈ 1/556 giorni)
DC_MAX_GOALS = 8   # massimo gol per lato nella matrice punteggi

# ─── Rate limiting ────────────────────────────────────────────────────────────
FDO_SLEEP  = 6.5   # secondi tra chiamate football-data.org (10 req/min → 6s)
API_SLEEP  = 0.5   # secondi tra chiamate API-Football
ELO_SLEEP  = 1.0   # secondi tra chiamate ClubElo
