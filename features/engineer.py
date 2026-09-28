"""
Feature Engineering
Calcola le 12 variabili derivate usate dal modello predittivo.
Tutte le variabili sono estratte dal database locale.
"""
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from db import get_conn

log = logging.getLogger(__name__)


@dataclass
class MatchFeatures:
    """Tutte le feature per una partita home vs away."""

    # Squadre
    home_team: str = ""
    away_team: str = ""
    league_key: str = ""
    match_date: str = ""

    # 1. Forza d'attacco (media gol/xG segnati ultimi 10 match)
    home_attack:  float = 1.0
    away_attack:  float = 1.0

    # 2. Debolezza difensiva (media gol/xG subiti ultimi 10 match)
    home_defense: float = 1.0
    away_defense: float = 1.0

    # 3. Forma recente EMA-5 (ultimi 5 match: vittorie pesano 3, pareggio 1, sconfitta 0)
    home_form_5:  float = 0.5
    away_form_5:  float = 0.5

    # 4. ELO attuale (da ClubElo)
    home_elo:     float = 1500.0
    away_elo:     float = 1500.0
    elo_diff:     float = 0.0    # home_elo - away_elo

    # 5. xG differenziale stagionale (home - away per ogni squadra)
    home_xg_diff: float = 0.0
    away_xg_diff: float = 0.0

    # 6. Stanchezza (giorni dall'ultima partita — minore = più stancato)
    home_rest_days: int = 7
    away_rest_days: int = 7

    # 7. H2H (storico scontri diretti — last 5, valore tra -1 e 1)
    h2h_advantage: float = 0.0

    # 8. Media corner stagionale (per modello corner separato)
    home_corners_avg: float = 5.0
    away_corners_avg: float = 4.5

    # 9. Media cartellini stagionale
    home_yellow_avg: float = 2.0
    away_yellow_avg: float = 2.0

    # 10. Statistiche arbitro atteso (se noto)
    referee_yellow_avg: float = 4.0

    # 11. Meteo (impatto sulla partita: 0 = nessuno, 1 = molto)
    weather_impact: float = 0.0   # pioggia intensa / vento forte aumentano questo

    # 12. Quote implicite (se disponibili — probabilità normalizzate)
    market_ph: float = 0.0   # probabilità implicita vittoria casa
    market_pd: float = 0.0   # probabilità implicita pareggio
    market_pa: float = 0.0   # probabilità implicita vittoria trasferta

    # 13. Assenze chiave (infortuni + squalifiche da Transfermarkt)
    home_absences: int = 0   # numero giocatori assenti casa
    away_absences: int = 0   # numero giocatori assenti trasferta

    # 14. Congestionamento calendario (partite negli ultimi 14 giorni)
    home_congestion: int = 0
    away_congestion: int = 0

    # 15. Stats avanzate FBref
    home_possession:    float = 50.0  # % possesso medio stagionale
    away_possession:    float = 50.0
    home_ppda:          float = 10.0  # pressioni/possesso avversario (pressing)
    away_ppda:          float = 10.0
    home_prog_passes:   float = 0.0   # passaggi progressivi per partita
    away_prog_passes:   float = 0.0


class FeatureEngineer:
    """Calcola MatchFeatures per una partita specificata."""

    def __init__(self, n_recent: int = 10):
        self.n_recent = n_recent   # numero match recenti per medie

    def _get_team_id(self, conn, team_name: str, league_key: str) -> int | None:
        row = conn.execute("""
            SELECT id FROM teams
            WHERE (lower(name) = lower(?) OR lower(short_name) = lower(?))
              AND league_key = ?
            LIMIT 1
        """, (team_name, team_name, league_key)).fetchone()
        if row:
            return row["id"]
        # Prova senza vincolo di lega (per partite UEFA)
        row = conn.execute("""
            SELECT id FROM teams
            WHERE lower(name) LIKE lower(?)
            ORDER BY id DESC LIMIT 1
        """, (f"%{team_name[:6]}%",)).fetchone()
        return row["id"] if row else None

    def _recent_matches(self, conn, team_id: int, before_date: str,
                        n: int = 10, home_only: bool = False,
                        away_only: bool = False) -> list:
        """Ultimi N match per una squadra prima di una certa data."""
        if home_only:
            cond = "m.home_team_id = ?"
        elif away_only:
            cond = "m.away_team_id = ?"
        else:
            cond = "(m.home_team_id = ? OR m.away_team_id = ?)"
            team_id = (team_id, team_id)

        q = f"""
            SELECT m.*, s.home_shots, s.away_shots, s.home_corners, s.away_corners,
                   s.home_yellow, s.away_yellow, x.home_xg, x.away_xg
            FROM matches m
            LEFT JOIN match_stats s ON s.match_id = m.id
            LEFT JOIN match_xg    x ON x.match_id = m.id
            WHERE {cond}
              AND m.status = 'FINISHED'
              AND date(m.match_date) < date(?)
            ORDER BY m.match_date DESC
            LIMIT ?
        """
        if isinstance(team_id, tuple):
            return conn.execute(q, (*team_id, before_date, n)).fetchall()
        return conn.execute(q, (team_id, before_date, n)).fetchall()

    def _form_score(self, matches: list, team_id: int) -> float:
        """
        Forma EMA-5: punti medi pesati esponenzialmente.
        Valore normalizzato 0-1 (0 = solo sconfitte, 1 = solo vittorie).
        """
        if not matches:
            return 0.5

        alpha = 0.35
        weighted_sum = 0.0
        weight_total = 0.0
        weight = 1.0

        for m in reversed(matches[:5]):
            is_home = m["home_team_id"] == team_id
            gf = m["home_goals"] if is_home else m["away_goals"]
            ga = m["away_goals"] if is_home else m["home_goals"]
            pts = 1.0 if gf > ga else (0.5 if gf == ga else 0.0)
            weighted_sum += pts * weight
            weight_total += weight
            weight *= (1 - alpha)

        return weighted_sum / weight_total if weight_total > 0 else 0.5

    def _attack_strength(self, matches: list, team_id: int) -> float:
        """Media gol segnati per partita (con fallback a xG se disponibile)."""
        if not matches:
            return 1.0
        vals = []
        for m in matches:
            is_home = m["home_team_id"] == team_id
            xg = m["home_xg"] if is_home else m["away_xg"]
            gf = m["home_goals"] if is_home else m["away_goals"]
            vals.append(float(xg) if xg is not None else float(gf or 0))
        return max(sum(vals) / len(vals), 0.1)

    def _defense_strength(self, matches: list, team_id: int) -> float:
        """Media gol/xG concessi per partita (normalizzata: più basso = meglio)."""
        if not matches:
            return 1.0
        vals = []
        for m in matches:
            is_home = m["home_team_id"] == team_id
            xg_a = m["away_xg"] if is_home else m["home_xg"]
            ga   = m["away_goals"] if is_home else m["home_goals"]
            vals.append(float(xg_a) if xg_a is not None else float(ga or 0))
        return max(sum(vals) / len(vals), 0.1)

    def _corners_avg(self, matches: list, team_id: int) -> float:
        if not matches:
            return 5.0
        vals = []
        for m in matches:
            is_home = m["home_team_id"] == team_id
            c = m["home_corners"] if is_home else m["away_corners"]
            if c is not None:
                vals.append(float(c))
        return sum(vals) / len(vals) if vals else 5.0

    def _yellow_avg(self, matches: list, team_id: int) -> float:
        if not matches:
            return 2.0
        vals = []
        for m in matches:
            is_home = m["home_team_id"] == team_id
            y = m["home_yellow"] if is_home else m["away_yellow"]
            if y is not None:
                vals.append(float(y))
        return sum(vals) / len(vals) if vals else 2.0

    def _h2h_advantage(self, conn, home_id: int, away_id: int,
                        before_date: str, n: int = 5) -> float:
        """
        Vantaggio storico H2H tra -1 (away domina) e +1 (home domina).
        """
        rows = conn.execute("""
            SELECT home_team_id, home_goals, away_goals
            FROM matches
            WHERE ((home_team_id = ? AND away_team_id = ?)
                OR (home_team_id = ? AND away_team_id = ?))
              AND status = 'FINISHED'
              AND date(match_date) < date(?)
            ORDER BY match_date DESC
            LIMIT ?
        """, (home_id, away_id, away_id, home_id, before_date, n)).fetchall()

        if not rows:
            return 0.0

        score = 0.0
        for r in rows:
            if r["home_team_id"] == home_id:
                # partita in casa per home_team
                score += 1.0 if r["home_goals"] > r["away_goals"] else \
                        (-1.0 if r["home_goals"] < r["away_goals"] else 0.0)
            else:
                # partita in trasferta per home_team (era away)
                score += -1.0 if r["home_goals"] > r["away_goals"] else \
                          (1.0 if r["home_goals"] < r["away_goals"] else 0.0)

        return score / len(rows)

    def _rest_days(self, conn, team_id: int, before_date: str) -> int:
        """Giorni dall'ultima partita giocata."""
        row = conn.execute("""
            SELECT match_date FROM matches
            WHERE (home_team_id = ? OR away_team_id = ?)
              AND status = 'FINISHED'
              AND date(match_date) < date(?)
            ORDER BY match_date DESC LIMIT 1
        """, (team_id, team_id, before_date)).fetchone()

        if not row:
            return 7  # default
        last = datetime.strptime(row["match_date"][:10], "%Y-%m-%d")
        target = datetime.strptime(before_date[:10], "%Y-%m-%d")
        return (target - last).days

    def _elo(self, conn, team_name: str) -> float:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        row = conn.execute("""
            SELECT elo FROM elo_ratings
            WHERE lower(team_name) LIKE lower(?)
              AND date_from <= ?
            ORDER BY date_from DESC LIMIT 1
        """, (f"%{team_name[:6]}%", today)).fetchone()
        return row["elo"] if row else 1500.0

    def _weather_impact(self, conn, home_team_name: str, match_date: str) -> float:
        """
        Impatto meteo sulla partita (0-1).
        Pioggia >5mm/h o vento >50km/h = impatto significativo.
        """
        row = conn.execute("""
            SELECT w.precip_mm, w.wind_kmh FROM weather_forecasts w
            JOIN matches m ON m.id = w.match_id
            JOIN teams t ON t.id = m.home_team_id
            WHERE lower(t.name) LIKE lower(?)
              AND date(m.match_date) = date(?)
            ORDER BY w.updated_at DESC LIMIT 1
        """, (f"%{home_team_name[:6]}%", match_date)).fetchone()

        if not row:
            return 0.0
        rain = float(row["precip_mm"] or 0)
        wind = float(row["wind_kmh"] or 0)
        return min(rain / 20.0 + wind / 100.0, 1.0)

    def _market_odds(self, conn, home_id: int, away_id: int) -> tuple[float, float, float]:
        """Probabilità implicite dalle quote (se disponibili)."""
        row = conn.execute("""
            SELECT implied_ph, implied_pd, implied_pa FROM match_odds o
            JOIN matches m ON m.id = o.match_id
            WHERE m.home_team_id = ? AND m.away_team_id = ?
              AND m.status = 'SCHEDULED'
            ORDER BY m.match_date ASC LIMIT 1
        """, (home_id, away_id)).fetchone()
        if row:
            return row["implied_ph"], row["implied_pd"], row["implied_pa"]
        return 0.0, 0.0, 0.0

    def _absences(self, conn, team_name: str, league_key: str) -> int:
        """Conta giocatori assenti (infortuni + squalifiche) per una squadra."""
        row = conn.execute("""
            SELECT COUNT(*) as cnt FROM player_absences
            WHERE lower(team) LIKE lower(?)
              AND league = ?
        """, (f"%{team_name[:8]}%", league_key)).fetchone()
        return int(row["cnt"]) if row else 0

    def _congestion(self, conn, team_id: int, before_date: str, days: int = 14) -> int:
        """Numero di partite giocate negli ultimi N giorni (stanchezza)."""
        from datetime import datetime, timedelta
        start = (datetime.strptime(before_date[:10], "%Y-%m-%d")
                 - timedelta(days=days)).strftime("%Y-%m-%d")
        row = conn.execute("""
            SELECT COUNT(*) as cnt FROM matches
            WHERE (home_team_id = ? OR away_team_id = ?)
              AND status = 'FINISHED'
              AND date(match_date) >= date(?)
              AND date(match_date) < date(?)
        """, (team_id, team_id, start, before_date)).fetchone()
        return int(row["cnt"]) if row else 0

    def _fbref_stats(self, conn, team_name: str, league_key: str) -> dict:
        """Recupera stats avanzate FBref per una squadra."""
        row = conn.execute("""
            SELECT possession, pressures, progressive_passes
            FROM fbref_team_stats
            WHERE lower(team) LIKE lower(?)
              AND league = ?
            ORDER BY updated_at DESC LIMIT 1
        """, (f"%{team_name[:8]}%", league_key)).fetchone()
        if row:
            return {
                "possession":   float(row["possession"] or 50.0),
                "pressures":    float(row["pressures"]  or 10.0),
                "prog_passes":  float(row["progressive_passes"] or 0.0),
            }
        return {"possession": 50.0, "pressures": 10.0, "prog_passes": 0.0}

    def _referee_stats(self, conn, match_id: int | None) -> float:
        """Media cartellini per partita dell'arbitro assegnato."""
        if not match_id:
            return 4.0
        row = conn.execute("""
            SELECT r.yellow_per_game FROM referee_stats r
            JOIN match_stats s ON lower(s.referee) = lower(r.name)
            WHERE s.match_id = ?
        """, (match_id,)).fetchone()
        return row["yellow_per_game"] if row else 4.0

    # ── API pubblica ─────────────────────────────────────────────────────────

    def build(self, home_team: str, away_team: str,
              league_key: str, match_date: str = None) -> MatchFeatures:
        """
        Calcola tutte le feature per una partita.
        match_date: formato YYYY-MM-DD (default: oggi)
        """
        if match_date is None:
            match_date = datetime.utcnow().strftime("%Y-%m-%d")

        f = MatchFeatures(
            home_team=home_team,
            away_team=away_team,
            league_key=league_key,
            match_date=match_date,
        )

        conn = get_conn()

        home_id = self._get_team_id(conn, home_team, league_key)
        away_id = self._get_team_id(conn, away_team, league_key)

        if not home_id or not away_id:
            log.warning("Squadra non trovata: %s o %s (league=%s)",
                        home_team, away_team, league_key)
            conn.close()
            return f

        n = self.n_recent
        home_matches = self._recent_matches(conn, home_id, match_date, n)
        away_matches = self._recent_matches(conn, away_id, match_date, n)

        f.home_attack  = self._attack_strength(home_matches, home_id)
        f.away_attack  = self._attack_strength(away_matches, away_id)
        f.home_defense = self._defense_strength(home_matches, home_id)
        f.away_defense = self._defense_strength(away_matches, away_id)

        f.home_form_5  = self._form_score(home_matches, home_id)
        f.away_form_5  = self._form_score(away_matches, away_id)

        f.home_elo     = self._elo(conn, home_team)
        f.away_elo     = self._elo(conn, away_team)
        f.elo_diff     = f.home_elo - f.away_elo

        f.h2h_advantage = self._h2h_advantage(conn, home_id, away_id, match_date)

        f.home_corners_avg = self._corners_avg(home_matches, home_id)
        f.away_corners_avg = self._corners_avg(away_matches, away_id)

        f.home_yellow_avg = self._yellow_avg(home_matches, home_id)
        f.away_yellow_avg = self._yellow_avg(away_matches, away_id)

        f.home_rest_days = self._rest_days(conn, home_id, match_date)
        f.away_rest_days = self._rest_days(conn, away_id, match_date)

        f.weather_impact = self._weather_impact(conn, home_team, match_date)

        ph, pd, pa = self._market_odds(conn, home_id, away_id)
        f.market_ph = ph
        f.market_pd = pd
        f.market_pa = pa

        # Nuove feature
        f.home_absences   = self._absences(conn, home_team, league_key)
        f.away_absences   = self._absences(conn, away_team, league_key)
        f.home_congestion = self._congestion(conn, home_id, match_date)
        f.away_congestion = self._congestion(conn, away_id, match_date)

        home_fbref = self._fbref_stats(conn, home_team, league_key)
        away_fbref = self._fbref_stats(conn, away_team, league_key)
        f.home_possession  = home_fbref["possession"]
        f.away_possession  = away_fbref["possession"]
        f.home_ppda        = home_fbref["pressures"]
        f.away_ppda        = away_fbref["pressures"]
        f.home_prog_passes = home_fbref["prog_passes"]
        f.away_prog_passes = away_fbref["prog_passes"]

        conn.close()
        return f
