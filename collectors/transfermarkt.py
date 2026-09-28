"""
Transfermarkt collector — infortuni, squalifiche, valore di mercato rosa
Fonte: https://www.transfermarkt.com (scraping, no auth)

Dati raccolti:
- Giocatori infortunati per squadra / lega
- Giocatori squalificati per squadra / lega
- Valore di mercato totale della rosa (proxy forza economica squadra)

Rate limit consigliato: 1 req ogni 3-5 secondi + User-Agent rotante
"""
import time
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from db.schema import get_conn

log = logging.getLogger(__name__)

# Mappa lega → (slug URL, codice wettbewerb)
LEAGUE_MAP = {
    "serie_a":          ("serie-a",        "IT1"),
    "premier_league":   ("premier-league", "GB1"),
    "bundesliga":       ("bundesliga",     "L1"),
    "la_liga":          ("laliga",         "ES1"),
    "ligue_1":          ("ligue-1",        "FR1"),
    "champions_league": ("champions-league","CL"),
    "europa_league":    ("europa-league",  "EL"),
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) "
        "Gecko/20100101 Firefox/124.0"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection":      "keep-alive",
}


class TransfermarktCollector:

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def _get(self, url: str, delay: float = 4.0) -> BeautifulSoup | None:
        try:
            time.sleep(delay)
            r = self.session.get(url, timeout=30)
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            log.warning("Transfermarkt GET error %s: %s", url, e)
            return None

    # ── Infortuni ─────────────────────────────────────────────────────────────

    def fetch_injuries(self, league: str) -> list[dict]:
        """
        Scarica lista giocatori infortunati per un campionato.
        URL: /serie-a/verletzte/wettbewerb/IT1
        """
        if league not in LEAGUE_MAP:
            return []
        slug, code = LEAGUE_MAP[league]
        url = f"https://www.transfermarkt.com/{slug}/verletzte/wettbewerb/{code}"
        return self._parse_absence_table(url, league, "injured")

    # ── Squalifiche ───────────────────────────────────────────────────────────

    def fetch_suspensions(self, league: str) -> list[dict]:
        """
        Scarica lista giocatori squalificati.
        URL: /serie-a/gesperrte/wettbewerb/IT1
        """
        if league not in LEAGUE_MAP:
            return []
        slug, code = LEAGUE_MAP[league]
        url = f"https://www.transfermarkt.com/{slug}/gesperrte/wettbewerb/{code}"
        return self._parse_absence_table(url, league, "suspended")

    def _parse_absence_table(self, url: str, league: str, status: str) -> list[dict]:
        soup = self._get(url)
        if not soup:
            return []

        table = soup.find("table", class_="items")
        if not table:
            return []

        records = []
        now = datetime.utcnow().isoformat()

        for row in table.find("tbody").find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 4:
                continue
            try:
                # La struttura varia; troviamo i link con nome giocatore e squadra
                player_link = row.find("a", attrs={"data-id": True}) or row.find("td", class_=lambda x: x and "hauptlink" in str(x))
                player_name = player_link.get_text(strip=True) if player_link else cells[1].get_text(strip=True)

                # Squadra (colonna variabile)
                team_name = ""
                for td in cells:
                    img = td.find("img", title=True)
                    if img and "club" in str(img.get("class", "")):
                        team_name = img["title"]
                        break
                if not team_name:
                    team_name = cells[3].get_text(strip=True) if len(cells) > 3 else ""

                # Tipo infortunio / data ritorno
                injury_type = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                return_date = cells[5].get_text(strip=True) if len(cells) > 5 else ""

                # Valore di mercato del giocatore (importanza)
                market_val = ""
                for td in cells:
                    txt = td.get_text(strip=True)
                    if "€" in txt and ("Mio" in txt or "Tsd" in txt or "." in txt):
                        market_val = txt
                        break

                if player_name:
                    records.append({
                        "player":      player_name,
                        "team":        team_name,
                        "league":      league,
                        "status":      status,
                        "injury_type": injury_type,
                        "return_date": return_date,
                        "market_value": market_val,
                        "scraped_at":  now,
                    })
            except Exception as ex:
                log.debug("Riga non parsabile: %s", ex)
                continue

        return records

    # ── Valori rosa ───────────────────────────────────────────────────────────

    def fetch_squad_values(self, league: str) -> list[dict]:
        """
        Valore di mercato totale per ogni squadra in un campionato.
        URL: /wettbewerb/IT1
        """
        if league not in LEAGUE_MAP:
            return []
        _, code = LEAGUE_MAP[league]
        url = f"https://www.transfermarkt.com/wettbewerb/{code}"
        soup = self._get(url)
        if not soup:
            return []

        table = soup.find("table", class_="items")
        if not table:
            return []

        values = []
        now = datetime.utcnow().isoformat()

        for row in table.find("tbody").find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 3:
                continue
            try:
                # Nome squadra
                team_link = row.find("a", class_=lambda x: x and "hauptlink" in str(x))
                team_name = team_link.get_text(strip=True) if team_link else cells[1].get_text(strip=True)
                if not team_name:
                    continue

                # Valore totale rosa (ultima colonna significativa)
                val_str = ""
                for td in reversed(cells):
                    txt = td.get_text(strip=True)
                    if "€" in txt or "Mio" in txt:
                        val_str = txt
                        break

                if team_name:
                    values.append({
                        "team":              team_name,
                        "league":            league,
                        "market_value_str":  val_str,
                        "updated_at":        now,
                    })
            except Exception as ex:
                log.debug("Riga valore non parsabile: %s", ex)
                continue

        return values

    # ── Salvataggio ───────────────────────────────────────────────────────────

    def save_absences(self, records: list[dict]):
        if not records:
            return
        conn = get_conn()
        cur = conn.cursor()
        # Prima pulisci i vecchi dati per questa lega
        leagues = set(r["league"] for r in records)
        for league in leagues:
            cur.execute(
                "DELETE FROM player_absences WHERE league = ?", (league,)
            )
        for r in records:
            cur.execute("""
                INSERT INTO player_absences
                (player, team, league, status, injury_type,
                 return_date, market_value, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (r["player"], r["team"], r["league"], r["status"],
                  r.get("injury_type", ""), r.get("return_date", ""),
                  r.get("market_value", ""), r.get("scraped_at", "")))
        conn.commit()
        conn.close()
        log.info("Transfermarkt: salvati %d assenti", len(records))

    def save_squad_values(self, values: list[dict]):
        if not values:
            return
        conn = get_conn()
        cur = conn.cursor()
        for v in values:
            cur.execute("""
                INSERT OR REPLACE INTO squad_values
                (team, league, market_value_str, updated_at)
                VALUES (?, ?, ?, ?)
            """, (v["team"], v["league"],
                  v.get("market_value_str", ""), v.get("updated_at", "")))
        conn.commit()
        conn.close()
        log.info("Transfermarkt: salvati valori per %d squadre", len(values))

    # ── Aggiornamento completo ────────────────────────────────────────────────

    def update(self, leagues: list[str] = None):
        if leagues is None:
            leagues = list(LEAGUE_MAP.keys())

        for league in leagues:
            log.info("Transfermarkt: %s ...", league)
            all_absences = []

            injuries = self.fetch_injuries(league)
            all_absences.extend(injuries)
            log.info("  → %d infortuni", len(injuries))
            time.sleep(3)

            suspensions = self.fetch_suspensions(league)
            all_absences.extend(suspensions)
            log.info("  → %d squalifiche", len(suspensions))
            time.sleep(3)

            if all_absences:
                self.save_absences(all_absences)

            values = self.fetch_squad_values(league)
            if values:
                self.save_squad_values(values)
                log.info("  → %d valori rosa", len(values))
            time.sleep(5)
