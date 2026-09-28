"""
Collector: Understat
Fornisce: xG, npxG, shot-level data per i top 5 campionati europei (2014-oggi).
Fonte: https://understat.com — COMPLETAMENTE GRATUITO, nessuna auth
Tecnica: scraping HTML — Understat incorpora i dati come JSON nelle pagine JavaScript.
"""
import re
import json
import time
import logging
from datetime import datetime

import requests

from config import UNDERSTAT_LEAGUES, CURRENT_SEASON
from db import get_conn

log = logging.getLogger(__name__)

BASE_URL = "https://understat.com"

# Regex per estrarre il JSON incorporato nelle pagine Understat
JSON_RE = re.compile(r"JSON\.parse\('(.+?)'\)", re.DOTALL)


def _extract_json(html: str, var_name: str):
    """Estrae una variabile JS contenente JSON.parse('...')."""
    pattern = re.compile(rf"var {var_name}\s*=\s*JSON\.parse\('(.+?)'\);", re.DOTALL)
    m = pattern.search(html)
    if not m:
        return None
    # Understat usa escaped unicode e backslash — decode correttamente
    raw = m.group(1).encode("utf-8").decode("unicode_escape")
    return json.loads(raw)


class UnderstatCollector:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; football-predictor-bot/1.0)"
        })

    def _get(self, url: str) -> str:
        resp = self.session.get(url, timeout=20)
        resp.raise_for_status()
        time.sleep(2.0)   # cortesia verso understat.com
        return resp.text

    def fetch_league_season(self, understat_key: str, season: int) -> list[dict]:
        """
        Restituisce lista di match con xG per una lega e stagione.
        Ogni elemento: {id, h, a, goals_h, goals_a, xG_h, xG_a, date, ...}
        """
        url = f"{BASE_URL}/league/{understat_key}/{season}"
        html = self._get(url)
        data = _extract_json(html, "datesData")
        if not data:
            log.warning("Nessun dato xG trovato per %s/%s", understat_key, season)
            return []
        return data

    def _find_match(self, conn, home_name: str, away_name: str,
                    date_str: str, league_key: str) -> int | None:
        """Cerca il match nel DB con fuzzy match sul nome squadra."""
        # Prima prova exact match sulla data
        row = conn.execute("""
            SELECT m.id FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            JOIN teams at ON at.id = m.away_team_id
            WHERE m.league_key = ?
              AND date(m.match_date) = date(?)
              AND (
                  ht.name LIKE ? OR ht.short_name LIKE ?
                  OR lower(ht.name) LIKE lower(?)
              )
            LIMIT 1
        """, (league_key, date_str,
              f"%{home_name[:6]}%", f"%{home_name[:6]}%",
              f"%{home_name[:6]}%")).fetchone()
        return row["id"] if row else None

    def sync_league_season(self, league_key: str, understat_key: str, season: int):
        print(f"  → Understat xG: {league_key} {season}/{season+1}...")
        matches = self.fetch_league_season(understat_key, season)
        conn = get_conn()
        saved = 0
        now = datetime.utcnow().isoformat()

        for m in matches:
            # Solo partite già giocate
            if not m.get("isResult"):
                continue

            # Data partita
            dt_str = m.get("datetime", "")
            try:
                dt = datetime.strptime(dt_str[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
            except ValueError:
                continue

            home_name = m.get("h", {}).get("title", "")
            away_name = m.get("a", {}).get("title", "")

            match_id = self._find_match(conn, home_name, away_name, dt, league_key)
            if not match_id:
                continue

            try:
                home_xg  = float(m["xG"]["h"])
                away_xg  = float(m["xG"]["a"])
                home_npxg = float(m.get("npxG", {}).get("h", home_xg))
                away_npxg = float(m.get("npxG", {}).get("a", away_xg))
            except (KeyError, TypeError, ValueError):
                continue

            conn.execute("""
                INSERT OR REPLACE INTO match_xg
                    (match_id, home_xg, away_xg, home_npxg, away_npxg, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (match_id, home_xg, away_xg, home_npxg, away_npxg, now))
            saved += 1

        conn.commit()
        conn.close()
        print(f"    ✓ {saved} record xG salvati")

    def update_all(self, seasons: list[int] = None):
        """Aggiorna xG per tutti i campionati Understat."""
        seasons = seasons or [CURRENT_SEASON, CURRENT_SEASON - 1, CURRENT_SEASON - 2]
        for league_key, understat_key in UNDERSTAT_LEAGUES.items():
            for season in seasons:
                try:
                    self.sync_league_season(league_key, understat_key, season)
                except Exception as e:
                    log.error("Errore Understat %s/%s: %s", league_key, season, e)

    def update_current_season(self):
        """Aggiorna solo la stagione corrente."""
        for league_key, understat_key in UNDERSTAT_LEAGUES.items():
            try:
                self.sync_league_season(league_key, understat_key, CURRENT_SEASON)
            except Exception as e:
                log.error("Errore Understat %s: %s", league_key, e)
