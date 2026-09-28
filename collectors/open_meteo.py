"""
Collector: Open-Meteo
Fornisce: previsioni meteo orarie per le coordinate GPS degli stadi.
Fonte: https://api.open-meteo.com — COMPLETAMENTE GRATUITO, 10.000 req/giorno, nessuna auth
"""
import time
import logging
from datetime import datetime, timedelta, timezone

import requests

from db import get_conn
from data.stadiums import STADIUMS

log = logging.getLogger(__name__)

BASE_URL = "https://api.open-meteo.com/v1/forecast"


def _get_weather(lat: float, lon: float, date: str, hour: int = 15) -> dict | None:
    """
    Recupera meteo orario per coordinate e data.
    Restituisce i valori all'ora più vicina al kickoff.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation,wind_speed_10m,cloud_cover",
        "forecast_days": 14,
        "timezone": "auto",
    }
    try:
        resp = requests.get(BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        time.sleep(0.3)
    except Exception as e:
        log.warning("Open-Meteo errore: %s", e)
        return None

    hourly = data.get("hourly", {})
    times  = hourly.get("time", [])
    target = f"{date}T{hour:02d}:00"

    if target not in times:
        # Cerca l'ora più vicina nella stessa giornata
        day_times = [t for t in times if t.startswith(date)]
        if not day_times:
            return None
        target = day_times[min(range(len(day_times)),
                               key=lambda i: abs(int(day_times[i][11:13]) - hour))]

    idx = times.index(target)
    return {
        "temp_c":    hourly["temperature_2m"][idx],
        "precip_mm": hourly["precipitation"][idx],
        "wind_kmh":  hourly["wind_speed_10m"][idx],
        "cloud_pct": hourly["cloud_cover"][idx],
    }


class OpenMeteoCollector:

    def _find_stadium(self, team_name: str) -> dict | None:
        """Cerca le coordinate dello stadio per una squadra."""
        name_lower = team_name.lower()
        for key, info in STADIUMS.items():
            if key.lower() in name_lower or name_lower in key.lower():
                return info
        return None

    def sync_upcoming_matches(self, days_ahead: int = 14):
        """Aggiorna il meteo per tutte le partite programmate nei prossimi N giorni."""
        print("  → Open-Meteo: previsioni meteo...")
        conn = get_conn()
        now = datetime.now(timezone.utc)
        cutoff = (now + timedelta(days=days_ahead)).isoformat()
        today_str = now.strftime("%Y-%m-%d")

        upcoming = conn.execute("""
            SELECT m.id, m.match_date,
                   ht.name AS home_team
            FROM matches m
            JOIN teams ht ON ht.id = m.home_team_id
            WHERE m.status = 'SCHEDULED'
              AND m.match_date >= ?
              AND m.match_date <= ?
              AND m.id NOT IN (SELECT match_id FROM weather_forecasts)
        """, (today_str, cutoff)).fetchall()

        updated = 0
        for match in upcoming:
            stadium = self._find_stadium(match["home_team"])
            if not stadium:
                continue

            date_part = match["match_date"][:10]
            hour = 15  # default kickoff hour (può essere migliorato con dati reali)

            weather = _get_weather(stadium["lat"], stadium["lon"], date_part, hour)
            if not weather:
                continue

            conn.execute("""
                INSERT OR REPLACE INTO weather_forecasts
                    (match_id, kickoff_utc, temp_c, precip_mm, wind_kmh, cloud_pct, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                match["id"], match["match_date"],
                weather["temp_c"], weather["precip_mm"],
                weather["wind_kmh"], weather["cloud_pct"],
                datetime.utcnow().isoformat()
            ))
            updated += 1

        conn.commit()
        conn.close()
        print(f"    ✓ {updated} previsioni meteo salvate")

    def update_all(self):
        self.sync_upcoming_matches()
