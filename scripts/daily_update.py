#!/usr/bin/env python3
"""
Aggiornamento giornaliero — da lanciare ogni mattina (cron Railway 0 6 * * *).
Aggiorna: calendario, risultati, ELO ratings, xG, meteo, statistiche.
"""
import sys
import os
import logging
from datetime import datetime

# Assicura che la root del progetto sia nel PYTHONPATH
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("daily_update")


def step_fixtures():
    """Calendario e risultati da football-data.org + CSV Football-Data.co.uk."""
    try:
        from collectors.football_data_org import FootballDataOrgCollector
        from config import LEAGUES
        c = FootballDataOrgCollector()
        for lk in LEAGUES:
            try:
                c.sync_results(lk)
                c.sync_matches(lk, days_ahead=14)
            except Exception as e:
                log.warning(f"  {lk}: {e}")
        log.info("Calendario football-data.org aggiornato")
    except Exception as e:
        log.warning(f"football-data.org non disponibile: {e}")

    try:
        from collectors.football_data_csv import FootballDataCsvCollector
        FootballDataCsvCollector().update_current_season()
        log.info("CSV Football-Data.co.uk aggiornato")
    except Exception as e:
        log.warning(f"CSV update fallito: {e}")


def step_elo():
    """Ratings ClubElo."""
    try:
        from collectors.clubelo import ClubEloCollector
        ClubEloCollector().update_all()
        log.info("ELO aggiornato")
    except Exception as e:
        log.warning(f"ELO update fallito: {e}")


def step_xg():
    """xG da Understat (solo top-5 leghe europee)."""
    try:
        from collectors.understat import UnderstatCollector
        UnderstatCollector().update_current_season()
        log.info("xG Understat aggiornato")
    except Exception as e:
        log.warning(f"xG update fallito: {e}")


def step_weather():
    """Previsioni meteo stadi."""
    try:
        from collectors.open_meteo import OpenMeteoCollector
        OpenMeteoCollector().update_all()
        log.info("Meteo aggiornato")
    except Exception as e:
        log.warning(f"Meteo update fallito: {e}")


def step_stats():
    """Statistiche aggregate referee e team-season."""
    try:
        from collectors.football_data_csv import FootballDataCsvCollector
        c = FootballDataCsvCollector()
        c.rebuild_referee_stats()
        c.rebuild_team_season_stats()
        log.info("Statistiche aggregate aggiornate")
    except Exception as e:
        log.warning(f"Stats update fallito: {e}")


if __name__ == "__main__":
    log.info(f"=== Daily update avviato: {datetime.now():%Y-%m-%d %H:%M} ===")

    step_fixtures()
    step_elo()
    step_xg()
    step_weather()
    step_stats()

    log.info("=== Daily update completato ===")
