"""
Collector: football-data.org
Fornisce: calendario, risultati, classifiche per i campionati target.
Fonte: https://www.football-data.org  — GRATUITO (free API key richiesta)
Limite: 10 richieste/minuto (gestite automaticamente con sleep)
"""
import time
import logging
from datetime import datetime, timedelta, timezone

import requests

from config import FOOTBALL_DATA_ORG_KEY, LEAGUES, CURRENT_SEASON, FDO_SLEEP
from db import get_conn

log = logging.getLogger(__name__)

BASE_URL = "https://api.football-data.org/v4"


class FootballDataOrgCollector:
    def __init__(self):
        if not FOOTBALL_DATA_ORG_KEY:
            raise RuntimeError(
                "FOOTBALL_DATA_ORG_KEY non configurata nel file .env\n"
                "Registrati gratis su https://www.football-data.org/client/register"
            )
        self.headers = {"X-Auth-Token": FOOTBALL_DATA_ORG_KEY}
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _get(self, path: str, params: dict = None) -> dict:
        url = f"{BASE_URL}{path}"
        resp = self.session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        time.sleep(FDO_SLEEP)
        return resp.json()

    # ── Fixtures e risultati ────────────────────────────────────────────────

    def fetch_fixtures(self, league_key: str, days_ahead: int = 14) -> list[dict]:
        """Prossime N giorni di partite per un campionato."""
        code = LEAGUES[league_key]["fdo_code"]
        now = datetime.now(timezone.utc)
        date_from = now.strftime("%Y-%m-%d")
        date_to   = (now + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        data = self._get(
            f"/competitions/{code}/matches",
            {"dateFrom": date_from, "dateTo": date_to, "status": "SCHEDULED"}
        )
        return data.get("matches", [])

    def fetch_results(self, league_key: str, season: int = None) -> list[dict]:
        """Risultati già giocati per la stagione corrente."""
        code = LEAGUES[league_key]["fdo_code"]
        s = season or CURRENT_SEASON
        data = self._get(
            f"/competitions/{code}/matches",
            {"season": s, "status": "FINISHED"}
        )
        return data.get("matches", [])

    def fetch_standings(self, league_key: str) -> list[dict]:
        """Classifica attuale."""
        code = LEAGUES[league_key]["fdo_code"]
        data = self._get(f"/competitions/{code}/standings")
        tables = data.get("standings", [])
        if tables:
            return tables[0].get("table", [])
        return []

    # ── Sync al database ─────────────────────────────────────────────────────

    def _upsert_team(self, conn, name: str, short_name: str,
                     fdo_id: int, league_key: str) -> int:
        """Inserisce/aggiorna una squadra e restituisce il suo id locale."""
        now = datetime.utcnow().isoformat()
        cur = conn.execute("""
            INSERT INTO teams (name, short_name, league_key, fdo_id, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name, league_key) DO UPDATE SET
                short_name = excluded.short_name,
                fdo_id     = excluded.fdo_id,
                updated_at = excluded.updated_at
            RETURNING id
        """, (name, short_name, league_key, fdo_id, now))
        row = cur.fetchone()
        return row[0]

    def sync_matches(self, league_key: str, days_ahead: int = 14):
        """Scarica le prossime partite e le salva nel DB."""
        print(f"  → football-data.org: fixtures {LEAGUES[league_key]['name']}...")
        matches = self.fetch_fixtures(league_key, days_ahead)
        conn = get_conn()
        now = datetime.utcnow().isoformat()

        for m in matches:
            ht = m["homeTeam"]
            at = m["awayTeam"]
            home_id = self._upsert_team(conn, ht["name"], ht.get("shortName"), ht["id"], league_key)
            away_id = self._upsert_team(conn, at["name"], at.get("shortName"), at["id"], league_key)

            # Estrai data match
            utc_date = m.get("utcDate", "")

            conn.execute("""
                INSERT INTO matches
                    (fdo_id, league_key, season, home_team_id, away_team_id,
                     match_date, round, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(fdo_id) DO UPDATE SET
                    match_date = excluded.match_date,
                    round      = excluded.round,
                    status     = excluded.status,
                    updated_at = excluded.updated_at
            """, (
                m["id"], league_key, CURRENT_SEASON,
                home_id, away_id, utc_date,
                m.get("matchday"), m.get("status", "SCHEDULED"), now
            ))

        conn.commit()
        conn.close()
        print(f"    ✓ {len(matches)} partite salvate")

    def sync_results(self, league_key: str, season: int = None):
        """Scarica i risultati già giocati e li salva nel DB."""
        print(f"  → football-data.org: risultati {LEAGUES[league_key]['name']}...")
        results = self.fetch_results(league_key, season)
        conn = get_conn()
        now = datetime.utcnow().isoformat()
        updated = 0

        for m in results:
            ht = m["homeTeam"]
            at = m["awayTeam"]
            home_id = self._upsert_team(conn, ht["name"], ht.get("shortName"), ht["id"], league_key)
            away_id = self._upsert_team(conn, at["name"], at.get("shortName"), at["id"], league_key)

            score = m.get("score", {})
            ft = score.get("fullTime", {})
            ht_score = score.get("halfTime", {})

            conn.execute("""
                INSERT INTO matches
                    (fdo_id, league_key, season, home_team_id, away_team_id,
                     match_date, round, status,
                     home_goals, away_goals, home_goals_ht, away_goals_ht, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'FINISHED', ?, ?, ?, ?, ?)
                ON CONFLICT(fdo_id) DO UPDATE SET
                    status       = 'FINISHED',
                    home_goals   = excluded.home_goals,
                    away_goals   = excluded.away_goals,
                    home_goals_ht = excluded.home_goals_ht,
                    away_goals_ht = excluded.away_goals_ht,
                    updated_at   = excluded.updated_at
            """, (
                m["id"], league_key, season or CURRENT_SEASON,
                home_id, away_id, m.get("utcDate", ""),
                m.get("matchday"),
                ft.get("home"), ft.get("away"),
                ht_score.get("home"), ht_score.get("away"), now
            ))
            updated += 1

        conn.commit()
        conn.close()
        print(f"    ✓ {updated} risultati aggiornati")

    def update_all(self, days_ahead: int = 14):
        """Aggiorna tutti i campionati configurati."""
        for key in LEAGUES:
            try:
                self.sync_results(key)
                self.sync_matches(key, days_ahead)
            except requests.HTTPError as e:
                log.warning("Errore %s per %s: %s", e.response.status_code, key, e)
            except Exception as e:
                log.error("Errore inatteso per %s: %s", key, e)
