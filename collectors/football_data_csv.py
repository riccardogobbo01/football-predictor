"""
Collector: Football-Data.co.uk (CSV storici)
Fornisce: risultati storici con gol, tiri, corner, cartellini, arbitri, quote.
Fonte: https://football-data.co.uk — COMPLETAMENTE GRATUITO, nessuna auth
Copertura: stagioni 1993-oggi per i top 5 campionati europei.

Colonne chiave nei CSV:
  Div, Date, HomeTeam, AwayTeam, FTHG, FTAG (gol F.T.)
  HTHG, HTAG (gol H.T.)  HS, AS (tiri totali)  HST, AST (tiri in porta)
  HC, AC (corner)  HF, AF (falli)  HY, AY (gialli)  HR, AR (rossi)
  Referee
  B365H, B365D, B365A (quote Bet365)
"""
import io
import time
import logging
from datetime import datetime

import requests
import pandas as pd

from config import FOOTBALL_DATA_CSV, HISTORICAL_SEASONS
from db import get_conn

log = logging.getLogger(__name__)

BASE_URL = "https://football-data.co.uk/mmz4281"


class FootballDataCsvCollector:

    def _download_csv(self, league_code: str, season_code: str) -> pd.DataFrame | None:
        """Scarica un CSV e lo restituisce come DataFrame. Ritorna None se non trovato."""
        url = f"{BASE_URL}/{season_code}/{league_code}.csv"
        try:
            resp = requests.get(url, timeout=20)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            # Usa latin-1: alcuni CSV contengono caratteri non-ASCII
            df = pd.read_csv(io.StringIO(resp.content.decode("latin-1")), on_bad_lines="skip")
            time.sleep(0.5)
            return df
        except Exception as e:
            log.warning("Impossibile scaricare %s: %s", url, e)
            return None

    def _season_code_to_year(self, season_code: str) -> int:
        """'2526' → 2025"""
        return 2000 + int(season_code[:2])

    def _clean_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalizza i nomi colonne e rimuove righe vuote."""
        df = df.dropna(subset=["HomeTeam", "AwayTeam", "FTHG", "FTAG"])
        df = df.rename(columns=str.strip)
        # Converti gol in int (possono arrivare come float)
        for col in ["FTHG", "FTAG", "HTHG", "HTAG"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        return df

    def _upsert_team(self, conn, name: str, league_key: str) -> int:
        now = datetime.utcnow().isoformat()
        cur = conn.execute("""
            INSERT INTO teams (name, league_key, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(name, league_key) DO UPDATE SET updated_at = excluded.updated_at
            RETURNING id
        """, (name, league_key, now))
        return cur.fetchone()[0]

    def _find_match_id(self, conn, home_id: int, away_id: int,
                       date_str: str, season: int) -> int | None:
        """Trova l'ID di un match già presente nel DB."""
        row = conn.execute("""
            SELECT id FROM matches
            WHERE home_team_id = ? AND away_team_id = ?
              AND season = ? AND date(match_date) = date(?)
            LIMIT 1
        """, (home_id, away_id, season, date_str)).fetchone()
        return row["id"] if row else None

    def _insert_match(self, conn, home_id: int, away_id: int, league_key: str,
                      season: int, date_str: str, row: pd.Series) -> int:
        now = datetime.utcnow().isoformat()
        cur = conn.execute("""
            INSERT OR IGNORE INTO matches
                (league_key, season, home_team_id, away_team_id, match_date,
                 status, home_goals, away_goals, home_goals_ht, away_goals_ht, updated_at)
            VALUES (?, ?, ?, ?, ?, 'FINISHED', ?, ?, ?, ?, ?)
            RETURNING id
        """, (
            league_key, season, home_id, away_id, date_str,
            int(row.get("FTHG", 0)), int(row.get("FTAG", 0)),
            int(row.get("HTHG", 0)) if pd.notna(row.get("HTHG")) else None,
            int(row.get("HTAG", 0)) if pd.notna(row.get("HTAG")) else None,
            now
        ))
        r = cur.fetchone()
        return r[0] if r else None

    def _save_stats(self, conn, match_id: int, row: pd.Series):
        now = datetime.utcnow().isoformat()
        def safe_int(key):
            v = row.get(key)
            return int(v) if pd.notna(v) else None

        conn.execute("""
            INSERT OR REPLACE INTO match_stats
                (match_id, home_shots, away_shots, home_shots_ot, away_shots_ot,
                 home_corners, away_corners, home_fouls, away_fouls,
                 home_yellow, away_yellow, home_red, away_red, referee, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match_id,
            safe_int("HS"), safe_int("AS"),
            safe_int("HST"), safe_int("AST"),
            safe_int("HC"), safe_int("AC"),
            safe_int("HF"), safe_int("AF"),
            safe_int("HY"), safe_int("AY"),
            safe_int("HR"), safe_int("AR"),
            row.get("Referee"), now
        ))

    def _save_odds(self, conn, match_id: int, row: pd.Series):
        h = row.get("B365H"); d = row.get("B365D"); a = row.get("B365A")
        if not all(pd.notna(v) for v in [h, d, a]):
            return
        h, d, a = float(h), float(d), float(a)
        margin = 1/h + 1/d + 1/a
        if margin <= 0:
            return
        conn.execute("""
            INSERT OR REPLACE INTO match_odds
                (match_id, b365_home, b365_draw, b365_away,
                 implied_ph, implied_pd, implied_pa, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match_id, h, d, a,
            (1/h)/margin, (1/d)/margin, (1/a)/margin,
            datetime.utcnow().isoformat()
        ))

    def sync_league_season(self, league_key: str, season_code: str):
        league_code = FOOTBALL_DATA_CSV.get(league_key)
        if not league_code:
            return
        season = self._season_code_to_year(season_code)
        df = self._download_csv(league_code, season_code)
        if df is None or df.empty:
            print(f"    – {league_key} {season_code}: nessun dato disponibile")
            return

        df = self._clean_df(df)
        conn = get_conn()
        saved = 0

        for _, row in df.iterrows():
            home_name = str(row["HomeTeam"]).strip()
            away_name = str(row["AwayTeam"]).strip()
            raw_date  = str(row.get("Date", "")).strip()

            # Normalizza data (può essere DD/MM/YY o DD/MM/YYYY)
            try:
                if "/" in raw_date:
                    parts = raw_date.split("/")
                    if len(parts[2]) == 2:
                        date_str = datetime.strptime(raw_date, "%d/%m/%y").strftime("%Y-%m-%d")
                    else:
                        date_str = datetime.strptime(raw_date, "%d/%m/%Y").strftime("%Y-%m-%d")
                else:
                    date_str = raw_date
            except ValueError:
                continue

            home_id = self._upsert_team(conn, home_name, league_key)
            away_id = self._upsert_team(conn, away_name, league_key)

            match_id = self._find_match_id(conn, home_id, away_id, date_str, season)
            if match_id is None:
                match_id = self._insert_match(conn, home_id, away_id,
                                               league_key, season, date_str, row)
            if match_id:
                self._save_stats(conn, match_id, row)
                self._save_odds(conn, match_id, row)
                saved += 1

        conn.commit()
        conn.close()
        print(f"    ✓ {league_key} {season_code}: {saved} partite")

    def update_all(self, seasons: list[str] = None):
        """Scarica tutti i CSV per tutte le leghe e stagioni configurate."""
        seasons = seasons or HISTORICAL_SEASONS
        for league_key in FOOTBALL_DATA_CSV:
            print(f"  → CSV storico: {league_key}")
            for season_code in seasons:
                self.sync_league_season(league_key, season_code)

    def update_current_season(self):
        """Aggiorna solo la stagione corrente (per update rapidi)."""
        current_code = HISTORICAL_SEASONS[0]  # es. "2526"
        for league_key in FOOTBALL_DATA_CSV:
            self.sync_league_season(league_key, current_code)

    def rebuild_referee_stats(self):
        """Ricalcola le statistiche arbitri da tutti i dati nel DB."""
        print("  → Ricalcolo statistiche arbitri...")
        conn = get_conn()
        rows = conn.execute("""
            SELECT referee,
                   COUNT(*)                    AS matches,
                   AVG(home_yellow + away_yellow) AS yellow_per_game,
                   AVG(home_red    + away_red  )  AS red_per_game,
                   AVG(home_fouls  + away_fouls)  AS foul_per_game
            FROM match_stats
            WHERE referee IS NOT NULL AND referee != ''
            GROUP BY referee
            HAVING matches >= 5
        """).fetchall()

        now = datetime.utcnow().isoformat()
        for r in rows:
            conn.execute("""
                INSERT INTO referee_stats
                    (name, matches, yellow_per_game, red_per_game, foul_per_game, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    matches        = excluded.matches,
                    yellow_per_game = excluded.yellow_per_game,
                    red_per_game   = excluded.red_per_game,
                    foul_per_game  = excluded.foul_per_game,
                    updated_at     = excluded.updated_at
            """, (r["referee"], r["matches"], r["yellow_per_game"],
                  r["red_per_game"], r["foul_per_game"], now))

        conn.commit()
        conn.close()
        print(f"    ✓ {len(rows)} arbitri aggiornati")

    def rebuild_team_season_stats(self):
        """Ricalcola le statistiche aggregate per squadra/stagione dai match."""
        print("  → Ricalcolo statistiche squadre...")
        conn = get_conn()

        conn.execute("DELETE FROM team_season_stats")

        rows = conn.execute("""
            SELECT
                m.home_team_id AS team_id,
                m.league_key, m.season,
                COUNT(*) AS mp,
                SUM(m.home_goals) AS gf, SUM(m.away_goals) AS ga,
                AVG(s.home_shots) AS sf, AVG(s.away_shots) AS sa,
                AVG(s.home_corners) AS cf, AVG(s.away_corners) AS ca,
                AVG(s.home_yellow) AS yc, AVG(s.home_red) AS rc
            FROM matches m
            LEFT JOIN match_stats s ON s.match_id = m.id
            WHERE m.status = 'FINISHED'
            GROUP BY m.home_team_id, m.league_key, m.season
        """).fetchall()

        now = datetime.utcnow().isoformat()
        for r in rows:
            conn.execute("""
                INSERT OR REPLACE INTO team_season_stats
                    (team_id, season, league_key, matches_played,
                     goals_for, goals_against, shots_for, shots_against,
                     corners_for, corners_against, yellow_cards, red_cards,
                     home_matches, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (r["team_id"], r["season"], r["league_key"], r["mp"],
                  r["gf"], r["ga"], r["sf"], r["sa"],
                  r["cf"], r["ca"], r["yc"], r["rc"],
                  r["mp"], now))

        conn.commit()
        conn.close()
        print(f"    ✓ {len(rows)} righe squadra/stagione aggiornate")
