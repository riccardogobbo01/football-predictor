"""
FBref collector — statistiche avanzate gratuite
Fonte: https://fbref.com (scraping, no auth, no rate limit dichiarato)
Dati: xG per match, PPDA, progressive passes, possession, pressioni difensive

Rate limit consigliato: 1 req ogni 4-6 secondi
"""
import time
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from db.schema import get_conn

log = logging.getLogger(__name__)

FBREF_LEAGUES = {
    "serie_a":          {"id": "11",  "slug": "Serie-A"},
    "premier_league":   {"id": "9",   "slug": "Premier-League"},
    "bundesliga":       {"id": "20",  "slug": "Bundesliga"},
    "la_liga":          {"id": "12",  "slug": "La-Liga"},
    "ligue_1":          {"id": "13",  "slug": "Ligue-1"},
    "champions_league": {"id": "8",   "slug": "Champions-League"},
    "europa_league":    {"id": "19",  "slug": "Europa-League"},
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://fbref.com/",
}


class FBrefCollector:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _get(self, url: str, delay: float = 5.0) -> BeautifulSoup | None:
        try:
            time.sleep(delay)
            r = self.session.get(url, timeout=30)
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            log.warning("FBref GET error %s: %s", url, e)
            return None

    # ── Calendario con xG ────────────────────────────────────────────────────

    def fetch_schedule_xg(self, league: str) -> list[dict]:
        """Scarica calendario stagione corrente con xG home/away per ogni match."""
        if league not in FBREF_LEAGUES:
            return []

        lid  = FBREF_LEAGUES[league]["id"]
        slug = FBREF_LEAGUES[league]["slug"]
        url  = f"https://fbref.com/en/comps/{lid}/schedule/{slug}-Scores-and-Fixtures"

        soup = self._get(url)
        if not soup:
            return []

        table = soup.find("table", {"id": "sched_all"})
        if not table:
            # prova con nome alternativo
            table = soup.find("table", class_="stats_table")
        if not table:
            log.warning("FBref: tabella calendario non trovata per %s", league)
            return []

        rows = []
        for tr in table.find("tbody").find_all("tr"):
            cls = tr.get("class", [])
            if "spacer" in cls or "thead" in cls:
                continue
            cells = {td.get("data-stat"): td.get_text(strip=True)
                     for td in tr.find_all(["td", "th"])}
            if not cells.get("home_team") or not cells.get("away_team"):
                continue

            score_raw = cells.get("score", "")
            # Partite completate hanno score tipo "2–1" o "2-1"
            sep = "–" if "–" in score_raw else ("-" if "-" in score_raw else None)
            if sep and score_raw.replace(sep, "").replace(" ", "").isdigit() is False:
                pass  # accetta anche "2–1"

            home_goals = away_goals = None
            if sep and score_raw:
                parts = score_raw.split(sep)
                if len(parts) == 2:
                    try:
                        home_goals = int(parts[0].strip())
                        away_goals = int(parts[1].strip())
                    except ValueError:
                        pass

            xg_home = xg_away = None
            try:
                xg_home = float(cells["xg_a"]) if cells.get("xg_a") else None
                xg_away = float(cells["xg_b"]) if cells.get("xg_b") else None
            except (ValueError, TypeError):
                pass

            rows.append({
                "date":        cells.get("date", ""),
                "home_team":   cells.get("home_team", ""),
                "away_team":   cells.get("away_team", ""),
                "home_goals":  home_goals,
                "away_goals":  away_goals,
                "xg_home":     xg_home,
                "xg_away":     xg_away,
                "league":      league,
            })

        return rows

    # ── Stats avanzate per squadra ────────────────────────────────────────────

    def fetch_team_stats(self, league: str) -> list[dict]:
        """Scarica PPDA (proxy), progressive passes/carries, possession."""
        if league not in FBREF_LEAGUES:
            return []

        lid  = FBREF_LEAGUES[league]["id"]
        slug = FBREF_LEAGUES[league]["slug"]
        results: dict[str, dict] = {}

        # 1) Possession: progressive passes, carries, possession %
        url = f"https://fbref.com/en/comps/{lid}/possession/{slug}-Possession-Stats"
        soup = self._get(url, delay=5.0)
        if soup:
            table = soup.find("table", id=lambda x: x and "possession" in str(x).lower())
            if table:
                for tr in table.find("tbody").find_all("tr"):
                    cls = tr.get("class", [])
                    if "spacer" in cls or "thead" in cls:
                        continue
                    c = {td.get("data-stat"): td.get_text(strip=True)
                         for td in tr.find_all(["td", "th"])}
                    team = c.get("team")
                    if not team:
                        continue
                    results.setdefault(team, {})
                    results[team]["progressive_passes"]  = _safe_float(c.get("progressive_passes"))
                    results[team]["progressive_carries"] = _safe_float(c.get("progressive_carries"))
                    results[team]["possession"]          = _safe_float(c.get("possession"))

        time.sleep(4)

        # 2) Defensive: pressures (proxy PPDA)
        url = f"https://fbref.com/en/comps/{lid}/defense/{slug}-Defense-Stats"
        soup = self._get(url, delay=5.0)
        if soup:
            table = soup.find("table", id=lambda x: x and "defense" in str(x).lower())
            if table:
                for tr in table.find("tbody").find_all("tr"):
                    cls = tr.get("class", [])
                    if "spacer" in cls or "thead" in cls:
                        continue
                    c = {td.get("data-stat"): td.get_text(strip=True)
                         for td in tr.find_all(["td", "th"])}
                    team = c.get("team")
                    if not team:
                        continue
                    results.setdefault(team, {})
                    results[team]["pressures"]             = _safe_float(c.get("pressures"))
                    results[team]["pressure_success_pct"]  = _safe_float(c.get("pressure_success_rate") or c.get("pressure_regain_pct"))

        return [{"team": k, "league": league, **v} for k, v in results.items()]

    # ── Salvataggio ───────────────────────────────────────────────────────────

    def save_schedule_xg(self, rows: list[dict]):
        if not rows:
            return
        conn = get_conn()
        cur = conn.cursor()
        for r in rows:
            cur.execute("""
                INSERT OR REPLACE INTO fbref_match_xg
                (date, home_team, away_team, xg_home, xg_away,
                 home_goals, away_goals, league, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (r["date"], r["home_team"], r["away_team"],
                  r.get("xg_home"), r.get("xg_away"),
                  r.get("home_goals"), r.get("away_goals"),
                  r["league"], datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        log.info("FBref: salvati %d match xG", len(rows))

    def save_team_stats(self, stats: list[dict]):
        if not stats:
            return
        conn = get_conn()
        cur = conn.cursor()
        now = datetime.utcnow().isoformat()
        for s in stats:
            cur.execute("""
                INSERT OR REPLACE INTO fbref_team_stats
                (team, league, progressive_passes, progressive_carries,
                 possession, pressures, pressure_success_pct, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (s["team"], s["league"],
                  s.get("progressive_passes"), s.get("progressive_carries"),
                  s.get("possession"), s.get("pressures"),
                  s.get("pressure_success_pct"), now))
        conn.commit()
        conn.close()
        log.info("FBref: salvate stats per %d squadre", len(stats))

    def update(self, leagues: list[str] = None):
        if leagues is None:
            leagues = list(FBREF_LEAGUES.keys())
        for league in leagues:
            log.info("FBref: aggiornamento %s ...", league)
            rows = self.fetch_schedule_xg(league)
            if rows:
                self.save_schedule_xg(rows)
                log.info("  → %d partite con xG", len(rows))
            time.sleep(4)
            stats = self.fetch_team_stats(league)
            if stats:
                self.save_team_stats(stats)
                log.info("  → %d squadre con stats avanzate", len(stats))
            time.sleep(6)


def _safe_float(val) -> float | None:
    try:
        return float(str(val).replace(",", ".").replace("%", "").strip()) if val else None
    except (ValueError, TypeError):
        return None
