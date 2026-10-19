"""
Configurazione centrale: chiavi API, league IDs, costanti del modello.
"""
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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

# ─── Risultato consigliato (tutte le competizioni) ────────────────────────────
# Se nessun esito (1, X, 2) supera questa probabilita' si consiglia il pareggio piu' probabile (di solito 1-1);
# altrimenti il punteggio piu' probabile dentro l'esito favorito. Backtest campionati 2019->oggi: pareggi consigliati
# 23% (reali 25%), esito giusto 50.0%, risultato esatto 11.9%.
REC_DRAW_THRESHOLD = 0.42

# ─── Versione del modello (docs/history.csv, riquadro di monitoraggio) ────────
# Da cambiare quando cambia il modello che emette le previsioni (nuove feature, nuovo allenamento strutturale):
# il riquadro di monitoraggio calcola la log-loss solo sulle previsioni della versione corrente.
# LEGACY_MODEL_VERSION = valore assegnato alle righe di history.csv emesse prima che la colonna esistesse.
MODEL_VERSION = "v6-eloodds"
LEGACY_MODEL_VERSION = "v5-pre-eloodds"

# ─── Versione del modello delle statistiche attese (tiri, corner, gialli) ─────
# Separata da MODEL_VERSION (che riguarda solo il modello 1X2: cambiarla farebbe ripartire il monitoraggio 1X2).
# s2-arbitro: modello dei gialli con effetto arbitro (regressore log R, k=20). s3-gap: tiri e tiri in porta con GAP ratings, nuovo
# modello dei falli con arbitro, copula per i mercati «chi ne fa di più», primo tempo. s4-intervalli: intervalli per squadra e totale
# di tutte le statistiche (valori consecutivi più probabili, con la probabilità reale) e dispersione separata per casa e ospite sui tiri. Righe di history.csv precedenti = s1-base / s2-arbitro.
STATS_VERSION = "s5-livello"
LEGACY_STATS_VERSION = "s1-base"
# GAP ratings (Wheatcroft) dei modelli dei tiri e dei tiri in porta: (eta, gamma) scelti sulle sole stagioni di validazione (round 6, fase 1: backtest/round6_parts/GAP2.md)
GAP_PARAMS = {"tiri": (0.10, 1.0), "sot": (0.05, 1.0)}
# Livello stagionale dinamico delle statistiche (s5-livello): (H = emivita in settimane, k = pseudo-partite di shrinkage verso 1) per statistica,
# scelti sulle sole stagioni di validazione dopo un'estensione della griglia (round 7, fase 2: backtest/round7_parts/L3EXT.md).
LEVEL_PARAMS = {"tiri": (12, 80), "sot": (8, 40), "corner": (16, 80), "falli": (3, 15), "gialli": (4, 15)}
REFEREE_K = 20            # partite equivalenti di shrinkage dell'effetto arbitro (scelto in validazione, round 5)

# ─── Aggiustamenti contestuali NON validati (disattivati) ─────────────────────
# Il backtest walk-forward (backtest/results.md) non li ha confermati: il riposo
# sotto i 3 giorni, testato sui soli giorni di riposo di campionato, ha effetto nullo;
# assenze, PPDA e meteo non sono testabili (manca lo storico datato). Fattori fissati a
# mano, mai stimati sui dati: restano nel codice ma spenti finche' non ci sono dati per
# stimarli. NB: il PPDA e' trattato al contrario (PPDA basso = pressing ALTO) —
# se mai riattivato va corretto e poi stimato, non fissato a mano.
USE_REST_ADJUST       = False   # riposo < 3 giorni: -8% gol
USE_CONGESTION_ADJUST = False   # > 3 partite in 14 giorni: -5% gol
USE_ABSENCES_ADJUST   = False   # -5% gol per assente (max -20%)
USE_PRESSING_ADJUST   = False   # pressing/PPDA: -4% gol avversario
USE_WEATHER_ADJUST    = False   # meteo sui gol attesi e sui corner

# ─── Rate limiting ────────────────────────────────────────────────────────────
FDO_SLEEP  = 6.5   # secondi tra chiamate football-data.org (10 req/min → 6s)
API_SLEEP  = 0.5   # secondi tra chiamate API-Football
ELO_SLEEP  = 1.0   # secondi tra chiamate ClubElo
