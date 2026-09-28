#!/usr/bin/env python3
"""
Inizializzazione DB su Railway (idempotente).
Lancia SOLO al primo deploy o se il volume è vuoto.

  python scripts/init_railway.py
"""
import sys
import os
import logging

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("init_railway")

from config import DB_PATH, LEAGUES


def main():
    # Crea directory del DB se non esiste
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0:
        log.info(f"DB già esistente ({DB_PATH}) — skip init")
        return

    log.info(f"DB non trovato — inizio inizializzazione ({DB_PATH})")

    # 1. Schema
    log.info("Step 1/4: Creazione schema...")
    from db import init_db
    init_db()
    log.info("Schema creato")

    # 2. Dati storici CSV
    log.info("Step 2/4: Download dati storici CSV...")
    try:
        from collectors.football_data_csv import FootballDataCsvCollector
        c = FootballDataCsvCollector()
        c.update_all_seasons()
        log.info("CSV storici caricati")
    except Exception as e:
        log.warning(f"CSV storici: {e}")

    # 3. Calendario e risultati correnti
    log.info("Step 3/4: Calendario corrente football-data.org...")
    try:
        from collectors.football_data_org import FootballDataOrgCollector
        c = FootballDataOrgCollector()
        for lk in LEAGUES:
            try:
                c.sync_results(lk)
                c.sync_matches(lk, days_ahead=30)
                log.info(f"  {lk}: OK")
            except Exception as e:
                log.warning(f"  {lk}: {e}")
    except Exception as e:
        log.warning(f"football-data.org: {e}")

    # 4. ELO ratings
    log.info("Step 4/4: ELO ratings...")
    try:
        from collectors.clubelo import ClubEloCollector
        ClubEloCollector().update_all()
        log.info("ELO caricati")
    except Exception as e:
        log.warning(f"ELO: {e}")

    log.info("=== Inizializzazione completata ===")
    log.info("Avvia ora: python scripts/next_round.py --days 14")


if __name__ == "__main__":
    main()
