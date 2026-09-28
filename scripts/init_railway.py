#!/usr/bin/env python3
"""
Inizializzazione DB su Railway (idempotente con --force per re-init).
  python scripts/init_railway.py           # skip se DB già esistente
  python scripts/init_railway.py --force   # riscrive tutto
"""
import sys, os, argparse, logging

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger("init_railway")

from config import DB_PATH, LEAGUES, FOOTBALL_DATA_CSV

TOP5 = [k for k in FOOTBALL_DATA_CSV]  # serie_a, premier_league, ...


def main(force=False):
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    if not force and os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 100_000:
        log.info(f"DB già esistente e popolato ({DB_PATH}) — skip init (usa --force per re-init)")
        return

    log.info(f"Inizializzazione DB: {DB_PATH}")

    # 1. Schema
    log.info("Step 1/5: Schema...")
    from db import init_db
    init_db()
    log.info("Schema OK")

    # 2. Dati storici CSV (Football-Data.co.uk)
    log.info("Step 2/5: Dati storici CSV...")
    try:
        from collectors.football_data_csv import FootballDataCsvCollector
        c = FootballDataCsvCollector()
        c.update_all()   # carica tutte le stagioni definite in HISTORICAL_SEASONS
        log.info("CSV storici OK")
    except Exception as e:
        log.warning(f"CSV storici: {e}")

    # 3. Calendario + risultati correnti (football-data.org)
    log.info("Step 3/5: Calendario football-data.org...")
    try:
        from collectors.football_data_org import FootballDataOrgCollector
        c = FootballDataOrgCollector()
        for lk in TOP5:
            try:
                c.sync_results(lk)
                c.sync_matches(lk, days_ahead=30)
                log.info(f"  {lk}: OK")
            except Exception as e:
                log.warning(f"  {lk}: {e}")
    except Exception as e:
        log.warning(f"football-data.org: {e}")

    # 4. ELO ratings (ClubElo)
    log.info("Step 4/5: ELO ratings...")
    try:
        from collectors.clubelo import ClubEloCollector
        ClubEloCollector().update_all()
        log.info("ELO OK")
    except Exception as e:
        log.warning(f"ELO: {e} — riprova dopo con: python -c \"from collectors.clubelo import ClubEloCollector; ClubEloCollector().update_all()\"")

    # 5. Fit Dixon-Coles per tutte le leghe top-5
    log.info("Step 5/5: Fit modello Dixon-Coles...")
    from predictions.dixon_coles import fit
    for lk in TOP5:
        try:
            dc = fit(lk)
            if dc:
                log.info(f"  {lk}: {len(dc.teams)} squadre, home_adv={dc.home_adv:.3f}")
            else:
                log.warning(f"  {lk}: dati insufficienti")
        except Exception as e:
            log.warning(f"  {lk}: {e}")

    log.info("=== Init completata — app pronta ===")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true", help="Reinizializza anche se DB esiste")
    args = p.parse_args()
    main(force=args.force)
