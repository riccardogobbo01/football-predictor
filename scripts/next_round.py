#!/usr/bin/env python3
"""
Stampa le predizioni per il prossimo turno di campionato.

Uso:
  python scripts/next_round.py              # finestre 7 giorni
  python scripts/next_round.py --days 18    # pausa internazionale
  python scripts/next_round.py --league serie_a
  python scripts/next_round.py --save       # salva in predictions/
"""
import sys
import os
import argparse
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from config import LEAGUES, DB_PATH


def get_fixtures(days: int, league_filter: str | None):
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc)
    cutoff = (now + timedelta(days=days)).isoformat()

    q = """
        SELECT f.id, f.league, f.home_team, f.away_team,
               f.match_date, f.home_goals, f.away_goals,
               f.status
          FROM fixtures f
         WHERE f.match_date BETWEEN ? AND ?
           AND f.status IN ('SCHEDULED', 'TIMED')
         ORDER BY f.league, f.match_date
    """
    rows = conn.execute(q, (now.isoformat(), cutoff)).fetchall()
    conn.close()
    if league_filter:
        rows = [r for r in rows if r["league"] == league_filter]
    return rows


def predict_fixture(home: str, away: str, league: str):
    from predictions.dixon_coles import load_params, predict as dc_predict
    try:
        params = load_params(league)
        result = dc_predict(home, away, params)
        return result
    except Exception:
        return None


def format_table(fixtures, league_key: str):
    league_name = LEAGUES.get(league_key, {}).get("name", league_key.upper())
    lines = [f"\n{'─'*60}", f"  {league_name}", f"{'─'*60}"]
    lines.append(f"  {'Casa':<20} {'Ospite':<20} {'1':>5} {'X':>5} {'2':>5}")
    lines.append(f"  {'─'*58}")
    for f in fixtures:
        pred = predict_fixture(f["home_team"], f["away_team"], league_key)
        date_str = f["match_date"][:10] if f["match_date"] else "?"
        if pred:
            p1 = f"{pred.get('home_win', 0)*100:.0f}%"
            px = f"{pred.get('draw', 0)*100:.0f}%"
            p2 = f"{pred.get('away_win', 0)*100:.0f}%"
        else:
            p1 = px = p2 = "  ?"
        lines.append(
            f"  {f['home_team']:<20} {f['away_team']:<20} {p1:>5} {px:>5} {p2:>5}  {date_str}"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Predizioni prossimo turno")
    parser.add_argument("--days", type=int, default=7,
                        help="Finestra giorni da oggi (default 7)")
    parser.add_argument("--league", default=None,
                        help="Filtra per lega (es. serie_a)")
    parser.add_argument("--save", action="store_true",
                        help="Salva output in predictions/")
    args = parser.parse_args()

    fixtures = get_fixtures(args.days, args.league)
    if not fixtures:
        print(f"Nessuna partita nei prossimi {args.days} giorni.")
        return

    # Raggruppa per lega
    by_league: dict = {}
    for f in fixtures:
        by_league.setdefault(f["league"], []).append(f)

    output_lines = [
        f"⚽ Predizioni prossimo turno — {datetime.now():%Y-%m-%d %H:%M}",
        f"Finestra: {args.days} giorni | {len(fixtures)} partite",
    ]
    for lk, matches in by_league.items():
        output_lines.append(format_table(matches, lk))

    output = "\n".join(output_lines)
    print(output)

    if args.save:
        os.makedirs(os.path.join(ROOT, "predictions"), exist_ok=True)
        fname = os.path.join(ROOT, "predictions",
                             f"next_round_{datetime.now():%Y%m%d}.txt")
        with open(fname, "w", encoding="utf-8") as fh:
            fh.write(output)
        print(f"\nSalvato in: {fname}")


if __name__ == "__main__":
    main()
