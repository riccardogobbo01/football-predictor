"""
Collector: ClubElo
Fornisce: ELO ratings storici e correnti per squadre europee.
Fonte: http://api.clubelo.com — COMPLETAMENTE GRATUITO, nessuna auth
API: REST semplice che restituisce CSV.
  GET /today            → tutti i rating correnti
  GET /2026-09-17       → rating in una data specifica
  GET /Barcelona        → storico completo di una squadra
"""
import io
import time
import logging
from datetime import datetime

import requests
import pandas as pd

from config import ELO_SLEEP
from db import get_conn

log = logging.getLogger(__name__)

BASE_URL = "http://api.clubelo.com"

# Mappatura nomi ClubElo → nomi nel DB (dove differiscono)
NAME_MAP = {
    "Man United":   "Manchester United",
    "Man City":     "Manchester City",
    "Wolves":       "Wolverhampton Wanderers",
    "Sp Lisbon":    "Sporting CP",
    "B Munich":     "Bayern München",
    "Dortmund":     "Borussia Dortmund",
    "Leverkusen":   "Bayer 04 Leverkusen",
    "M'gladbach":   "Borussia Mönchengladbach",
    "Atletico":     "Atlético de Madrid",
    "Sociedad":     "Real Sociedad",
    "Valladolid":   "Real Valladolid",
    "P.S.G.":       "Paris Saint-Germain",
    "Saint-Etienne": "Saint-Étienne",
}


class ClubEloCollector:

    def _fetch_csv(self, path: str) -> pd.DataFrame | None:
        url = f"{BASE_URL}/{path}"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            time.sleep(ELO_SLEEP)
            df = pd.read_csv(io.StringIO(resp.text))
            return df
        except Exception as e:
            log.error("Errore ClubElo %s: %s", url, e)
            return None

    def fetch_today(self) -> pd.DataFrame | None:
        """Rating ELO attuali per tutte le squadre tracciate."""
        return self._fetch_csv("today")

    def fetch_by_date(self, date: str) -> pd.DataFrame | None:
        """Rating ELO per una data specifica (formato YYYY-MM-DD)."""
        return self._fetch_csv(date)

    def fetch_team_history(self, team_name: str) -> pd.DataFrame | None:
        """Storico ELO completo per una squadra."""
        # ClubElo usa nomi senza spazi o con naming proprio
        clubelo_name = team_name.replace(" ", "_").replace("ü", "u").replace("ö", "o")
        return self._fetch_csv(clubelo_name)

    def _normalize_name(self, name: str) -> str:
        return NAME_MAP.get(name, name)

    def sync_current_ratings(self):
        """Scarica i rating ELO odierni e li salva nel DB."""
        print("  → ClubElo: rating correnti...")
        df = self.fetch_today()
        if df is None or df.empty:
            print("    ✗ Nessun dato ricevuto")
            return

        today = datetime.utcnow().strftime("%Y-%m-%d")
        conn = get_conn()
        saved = 0

        for _, row in df.iterrows():
            name = self._normalize_name(str(row.get("Club", "")).strip())
            elo  = row.get("Elo")
            if not name or pd.isna(elo):
                continue

            conn.execute("""
                INSERT INTO elo_ratings (team_name, date_from, elo, league)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(team_name, date_from) DO UPDATE SET
                    elo    = excluded.elo,
                    league = excluded.league
            """, (name, today, float(elo), row.get("Country", "")))
            saved += 1

        conn.commit()
        conn.close()
        print(f"    ✓ {saved} rating ELO aggiornati")

    def get_team_elo(self, team_name: str, date: str = None) -> float | None:
        """
        Restituisce l'ELO di una squadra per una data (o oggi).
        Prima cerca nel DB, poi scarica se necessario.
        """
        date = date or datetime.utcnow().strftime("%Y-%m-%d")
        conn = get_conn()

        # Cerca il rating più recente <= data richiesta
        row = conn.execute("""
            SELECT elo FROM elo_ratings
            WHERE lower(team_name) = lower(?)
              AND date_from <= ?
            ORDER BY date_from DESC
            LIMIT 1
        """, (team_name, date)).fetchone()
        conn.close()

        if row:
            return row["elo"]

        # Non trovato: prova a scaricare
        df = self.fetch_team_history(team_name)
        if df is None or df.empty:
            return None

        # Filtra per la data più vicina
        df["From"] = pd.to_datetime(df["From"], errors="coerce")
        df = df[df["From"] <= pd.Timestamp(date)]
        if df.empty:
            return None

        elo = df.sort_values("From").iloc[-1]["Elo"]
        return float(elo)

    def update_all(self):
        self.sync_current_ratings()
