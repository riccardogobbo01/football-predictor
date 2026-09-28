#!/usr/bin/env python3
"""
Football Predictor — CLI Entry Point
=====================================
Sistema predittivo per statistiche di partite di calcio.
Usa solo fonti gratuite: football-data.org, Understat, ClubElo,
Football-Data.co.uk CSV, Open-Meteo.

Uso:
  python main.py init                           # Inizializza il database
  python main.py update                         # Aggiorna tutti i dati
  python main.py update --source elo            # Solo ELO ratings
  python main.py fixtures                       # Prossime partite
  python main.py fixtures --league serie_a
  python main.py predict "Milan" "Inter" --league serie_a
  python main.py predict --league serie_a --round next
  python main.py fit --league serie_a           # (ri)fitta il modello
  python main.py team "Juventus" --league serie_a
"""
import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone

# ── Logging ──────────────────────────────────────────────────────────────────
from config import LOG_PATH, LEAGUES

import os
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stderr),
    ]
)
log = logging.getLogger("main")


# ── Comandi ───────────────────────────────────────────────────────────────────

def cmd_init(args):
    """Inizializza il database SQLite."""
    from db import init_db
    init_db()


def cmd_update(args):
    """Scarica e aggiorna tutti (o alcuni) dati dalle fonti esterne."""
    source = args.source.lower() if args.source else "all"
    print(f"\n🔄 Aggiornamento dati — source: {source}\n")

    if source in ("all", "fixtures", "results"):
        _update_football_data_org(args)

    if source in ("all", "historical", "csv"):
        _update_csv(args)

    if source in ("all", "xg"):
        _update_understat(args)

    if source in ("all", "elo"):
        _update_elo()

    if source in ("all", "weather"):
        _update_weather()

    if source in ("all", "stats"):
        _rebuild_aggregate_stats()

    if source in ("all", "fbref"):
        _update_fbref(args)

    if source in ("all", "transfermarkt", "injuries"):
        _update_transfermarkt(args)

    print("\n✅ Aggiornamento completato.\n")


def _update_football_data_org(args):
    try:
        from collectors.football_data_org import FootballDataOrgCollector
        c = FootballDataOrgCollector()
        leagues = [args.league] if args.league else list(LEAGUES.keys())
        for l in leagues:
            try:
                c.sync_results(l)
                c.sync_matches(l, days_ahead=getattr(args, "days", 14))
            except Exception as e:
                print(f"  ✗ {l}: {e}")
    except RuntimeError as e:
        print(f"  ⚠ football-data.org: {e}")


def _update_csv(args):
    from collectors.football_data_csv import FootballDataCsvCollector
    c = FootballDataCsvCollector()
    if getattr(args, "source", "") == "historical":
        c.update_all()
    else:
        c.update_current_season()


def _update_understat(args):
    from collectors.understat import UnderstatCollector
    c = UnderstatCollector()
    c.update_current_season()


def _update_elo():
    from collectors.clubelo import ClubEloCollector
    c = ClubEloCollector()
    c.update_all()


def _update_weather():
    from collectors.open_meteo import OpenMeteoCollector
    c = OpenMeteoCollector()
    c.update_all()


def _update_fbref(args):
    try:
        from collectors.fbref import FBrefCollector
        c = FBrefCollector()
        from config import LEAGUES
        leagues = [args.league] if args.league else list(LEAGUES.keys())
        print("  📊 FBref: stats avanzate (xG match, PPDA, progressive passes)...")
        c.update(leagues)
        print("  ✓ FBref aggiornato")
    except Exception as e:
        print(f"  ⚠ FBref non disponibile: {e}")


def _update_transfermarkt(args):
    try:
        from collectors.transfermarkt import TransfermarktCollector
        c = TransfermarktCollector()
        from config import LEAGUES
        leagues = [args.league] if args.league else list(LEAGUES.keys())
        print("  🤕 Transfermarkt: infortuni, squalifiche, valori rosa...")
        c.update(leagues)
        print("  ✓ Transfermarkt aggiornato")
    except Exception as e:
        print(f"  ⚠ Transfermarkt non disponibile: {e}")


def _rebuild_aggregate_stats():
    from collectors.football_data_csv import FootballDataCsvCollector
    c = FootballDataCsvCollector()
    c.rebuild_referee_stats()
    c.rebuild_team_season_stats()


def cmd_fixtures(args):
    """Mostra le prossime partite programmate."""
    from db import get_conn
    from predictions.output import print_fixtures_table

    conn = get_conn()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    days = args.days if args.days else 7
    end  = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")

    q = """
        SELECT m.match_date,
               ht.name AS home_team, at.name AS away_team,
               m.league_key, m.round
        FROM matches m
        JOIN teams ht ON ht.id = m.home_team_id
        JOIN teams at ON at.id = m.away_team_id
        WHERE m.status = 'SCHEDULED'
          AND m.match_date >= ? AND m.match_date <= ?
    """
    params = [now, end]
    if args.league:
        q += " AND m.league_key = ?"
        params.append(args.league)
    q += " ORDER BY m.match_date"

    rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    conn.close()

    if not rows:
        print(f"\n  Nessuna partita trovata nei prossimi {days} giorni.")
        print("  Prova: python main.py update\n")
        return

    print_fixtures_table(rows)


def cmd_predict(args):
    """Previsione per una o più partite."""
    from db import get_conn
    from features.engineer import FeatureEngineer
    from predictions.dixon_coles import fit, load_params, predict as dc_predict
    from predictions.output import print_prediction

    league_key = args.league or "serie_a"

    # Carica o fitta i parametri del modello
    print(f"\n⚙  Carico parametri modello per {league_key}...")
    dc = load_params(league_key)
    if dc is None:
        print(f"  Nessun modello salvato per {league_key}. Avvio fitting...")
        dc = fit(league_key)

    eng = FeatureEngineer()

    # Determina le partite da prevedere
    if args.home and args.away:
        # Partita singola specificata
        _predict_single(args.home, args.away, league_key, args.date,
                        eng, dc, print_prediction)

    elif args.round == "next":
        # Prossimo turno del campionato
        conn = get_conn()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        end = (datetime.now(timezone.utc) + timedelta(days=10)).strftime("%Y-%m-%d")
        rows = conn.execute("""
            SELECT ht.name AS home, at.name AS away, m.match_date
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.league_key = ? AND m.status = 'SCHEDULED'
              AND m.match_date BETWEEN ? AND ?
            ORDER BY m.match_date LIMIT 20
        """, (league_key, now, end)).fetchall()
        conn.close()

        if not rows:
            print(f"  Nessuna partita trovata per {league_key} nei prossimi 10 giorni.")
            print("  Esegui: python main.py update")
            return

        print(f"\n  Previsioni per il prossimo turno — {LEAGUES.get(league_key, {}).get('name', league_key)}\n")
        for r in rows:
            _predict_single(r["home"], r["away"], league_key,
                            r["match_date"][:10], eng, dc, print_prediction)
    else:
        print("  Specifica --home e --away, oppure --round next")


def _predict_single(home: str, away: str, league_key: str, date: str,
                    eng, dc, print_fn):
    from predictions.dixon_coles import predict as dc_predict
    date = date or datetime.utcnow().strftime("%Y-%m-%d")
    features = eng.build(home, away, league_key, date)
    pred = dc_predict(home, away, features, dc, league_key)
    print_fn(pred)


def cmd_fit(args):
    """Fitta (o re-fitta) il modello Dixon-Coles per un campionato."""
    from predictions.dixon_coles import fit
    league_key = args.league or "serie_a"
    print(f"\n⚙  Fitting Dixon-Coles per {league_key}...")
    dc = fit(league_key)
    if dc:
        print(f"  ✓ Modello fittato su {len(dc.teams)} squadre")
        print(f"  Home advantage: {dc.home_adv:.3f}  |  ρ: {dc.rho:.3f}")
    else:
        print("  ✗ Dati insufficienti per il fitting. Esegui prima: python main.py update")


def cmd_team(args):
    """Mostra il profilo di una squadra."""
    from db import get_conn
    from collectors.clubelo import ClubEloCollector
    from features.engineer import FeatureEngineer
    from predictions.output import print_team_info

    team = args.team
    league_key = args.league or "serie_a"

    conn = get_conn()
    today = datetime.utcnow().strftime("%Y-%m-%d")

    # ELO
    elo_row = conn.execute("""
        SELECT elo FROM elo_ratings
        WHERE lower(team_name) LIKE lower(?)
          AND date_from <= ?
        ORDER BY date_from DESC LIMIT 1
    """, (f"%{team[:6]}%", today)).fetchone()

    # Statistiche aggregate
    team_row = conn.execute("""
        SELECT ts.*, t.name FROM team_season_stats ts
        JOIN teams t ON t.id = ts.team_id
        WHERE lower(t.name) LIKE lower(?) AND ts.league_key = ?
        ORDER BY ts.season DESC LIMIT 1
    """, (f"%{team[:6]}%", league_key)).fetchone()

    conn.close()

    eng = FeatureEngineer()
    team_id_conn = get_conn()
    t_row = team_id_conn.execute("""
        SELECT id FROM teams WHERE lower(name) LIKE lower(?) LIMIT 1
    """, (f"%{team[:6]}%",)).fetchone()

    form = 0.5
    if t_row:
        from features.engineer import FeatureEngineer
        eng2 = FeatureEngineer()
        matches = eng2._recent_matches(team_id_conn, t_row["id"], today)
        form = eng2._form_score(matches, t_row["id"]) if matches else 0.5

    team_id_conn.close()

    stats = {
        "elo":           float(elo_row["elo"]) if elo_row else None,
        "form":          form,
        "matches":       team_row["matches_played"] if team_row else None,
        "goals_for":     (team_row["goals_for"] / max(team_row["matches_played"], 1))
                         if team_row else None,
        "goals_against": (team_row["goals_against"] / max(team_row["matches_played"], 1))
                         if team_row else None,
        "xg_for":        team_row["xg_for"] if team_row else None,
        "xg_against":    team_row["xg_against"] if team_row else None,
    }

    print_team_info(team, stats)


# ── Parser ────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="football-predictor",
        description="Sistema predittivo statistiche calcio — solo fonti gratuite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    sub.add_parser("init", help="Inizializza il database SQLite")

    # update
    p_upd = sub.add_parser("update", help="Aggiorna dati dalle fonti esterne")
    p_upd.add_argument("--source", default="all",
        choices=["all", "fixtures", "results", "historical", "csv",
                 "xg", "elo", "weather", "stats", "fbref", "transfermarkt", "injuries"],
        help="Quale fonte aggiornare (default: all)")
    p_upd.add_argument("--league",
        choices=list(LEAGUES.keys()),
        help="Limita l'aggiornamento a un campionato")
    p_upd.add_argument("--days", type=int, default=14,
        help="Giorni in avanti per i fixtures (default: 14)")

    # fixtures
    p_fix = sub.add_parser("fixtures", help="Mostra prossime partite")
    p_fix.add_argument("--league", choices=list(LEAGUES.keys()))
    p_fix.add_argument("--days", type=int, default=7)

    # predict
    p_pred = sub.add_parser("predict", help="Previsione statistiche partita")
    p_pred.add_argument("home", nargs="?", help="Squadra di casa")
    p_pred.add_argument("away", nargs="?", help="Squadra ospite")
    p_pred.add_argument("--league", choices=list(LEAGUES.keys()), default="serie_a")
    p_pred.add_argument("--date", help="Data partita YYYY-MM-DD (default: oggi)")
    p_pred.add_argument("--round", choices=["next"], help="next = prossimo turno")

    # fit
    p_fit = sub.add_parser("fit", help="Fitta il modello Dixon-Coles")
    p_fit.add_argument("--league", choices=list(LEAGUES.keys()), default="serie_a")

    # team
    p_team = sub.add_parser("team", help="Profilo squadra")
    p_team.add_argument("team", help="Nome squadra")
    p_team.add_argument("--league", choices=list(LEAGUES.keys()), default="serie_a")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "init":     cmd_init,
        "update":   cmd_update,
        "fixtures": cmd_fixtures,
        "predict":  cmd_predict,
        "fit":      cmd_fit,
        "team":     cmd_team,
    }

    fn = dispatch.get(args.command)
    if fn:
        try:
            fn(args)
        except KeyboardInterrupt:
            print("\n  Interrotto.")
            sys.exit(0)
        except Exception as e:
            log.exception("Errore non gestito")
            print(f"\n  ✗ Errore: {e}")
            print("  Controlla il log: data/football.log")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
