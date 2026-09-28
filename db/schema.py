"""
Inizializzazione e accesso al database SQLite.
Tutte le tabelle del sistema predittivo.
"""
import sqlite3
import os
import logging
from config import DB_PATH

log = logging.getLogger(__name__)


def get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Crea tutte le tabelle se non esistono già."""
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
    -- Squadre
    CREATE TABLE IF NOT EXISTS teams (
        id          INTEGER PRIMARY KEY,
        name        TEXT NOT NULL,
        short_name  TEXT,
        league_key  TEXT NOT NULL,
        fdo_id      INTEGER,          -- football-data.org team ID
        updated_at  TEXT
    );
    CREATE UNIQUE INDEX IF NOT EXISTS idx_teams_name_league ON teams(name, league_key);

    -- Partite (fixture + risultati)
    CREATE TABLE IF NOT EXISTS matches (
        id            INTEGER PRIMARY KEY,
        fdo_id        INTEGER UNIQUE,          -- football-data.org match ID
        league_key    TEXT NOT NULL,
        season        INTEGER NOT NULL,
        home_team_id  INTEGER REFERENCES teams(id),
        away_team_id  INTEGER REFERENCES teams(id),
        match_date    TEXT NOT NULL,           -- ISO8601 UTC
        round         TEXT,
        status        TEXT DEFAULT 'SCHEDULED', -- SCHEDULED, FINISHED, LIVE, ...
        home_goals    INTEGER,
        away_goals    INTEGER,
        home_goals_ht INTEGER,
        away_goals_ht INTEGER,
        updated_at    TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date);
    CREATE INDEX IF NOT EXISTS idx_matches_teams ON matches(home_team_id, away_team_id);

    -- Statistiche partita (da Football-Data.co.uk CSV)
    CREATE TABLE IF NOT EXISTS match_stats (
        match_id     INTEGER PRIMARY KEY REFERENCES matches(id),
        home_shots   INTEGER,
        away_shots   INTEGER,
        home_shots_ot INTEGER,
        away_shots_ot INTEGER,
        home_corners INTEGER,
        away_corners INTEGER,
        home_fouls   INTEGER,
        away_fouls   INTEGER,
        home_yellow  INTEGER,
        away_yellow  INTEGER,
        home_red     INTEGER,
        away_red     INTEGER,
        referee      TEXT,
        updated_at   TEXT
    );

    -- xG per partita (da Understat)
    CREATE TABLE IF NOT EXISTS match_xg (
        match_id  INTEGER PRIMARY KEY REFERENCES matches(id),
        home_xg   REAL,
        away_xg   REAL,
        home_npxg REAL,
        away_npxg REAL,
        updated_at TEXT
    );

    -- ELO ratings storici (da ClubElo)
    CREATE TABLE IF NOT EXISTS elo_ratings (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        team_name TEXT NOT NULL,
        date_from TEXT NOT NULL,
        date_to   TEXT,
        elo       REAL NOT NULL,
        league    TEXT,
        UNIQUE(team_name, date_from)
    );
    CREATE INDEX IF NOT EXISTS idx_elo_team ON elo_ratings(team_name);

    -- Previsioni meteo per stadio (da Open-Meteo)
    CREATE TABLE IF NOT EXISTS weather_forecasts (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        match_id    INTEGER REFERENCES matches(id),
        kickoff_utc TEXT,
        temp_c      REAL,
        precip_mm   REAL,
        wind_kmh    REAL,
        cloud_pct   INTEGER,
        updated_at  TEXT,
        UNIQUE(match_id)
    );

    -- Statistiche aggregate per squadra per stagione (calcolate dai CSV)
    CREATE TABLE IF NOT EXISTS team_season_stats (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        team_id         INTEGER REFERENCES teams(id),
        season          INTEGER NOT NULL,
        league_key      TEXT NOT NULL,
        matches_played  INTEGER DEFAULT 0,
        goals_for       REAL DEFAULT 0,
        goals_against   REAL DEFAULT 0,
        xg_for          REAL DEFAULT 0,
        xg_against      REAL DEFAULT 0,
        shots_for       REAL DEFAULT 0,
        shots_against   REAL DEFAULT 0,
        corners_for     REAL DEFAULT 0,
        corners_against REAL DEFAULT 0,
        yellow_cards    REAL DEFAULT 0,
        red_cards       REAL DEFAULT 0,
        home_matches    INTEGER DEFAULT 0,
        away_matches    INTEGER DEFAULT 0,
        updated_at      TEXT,
        UNIQUE(team_id, season, league_key)
    );

    -- Statistiche per arbitro (aggregate dai CSV)
    CREATE TABLE IF NOT EXISTS referee_stats (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT UNIQUE NOT NULL,
        matches         INTEGER DEFAULT 0,
        yellow_per_game REAL DEFAULT 0,
        red_per_game    REAL DEFAULT 0,
        foul_per_game   REAL DEFAULT 0,
        league_key      TEXT,
        updated_at      TEXT
    );

    -- Cache ultime quote pre-partita (da Football-Data.co.uk CSV — colonne B365)
    CREATE TABLE IF NOT EXISTS match_odds (
        match_id    INTEGER PRIMARY KEY REFERENCES matches(id),
        b365_home   REAL,
        b365_draw   REAL,
        b365_away   REAL,
        implied_ph  REAL,   -- probabilità implicita home (tolto margine)
        implied_pd  REAL,
        implied_pa  REAL,
        updated_at  TEXT
    );

    -- Infortuni e squalifiche (da Transfermarkt)
    CREATE TABLE IF NOT EXISTS player_absences (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        player       TEXT NOT NULL,
        team         TEXT NOT NULL,
        league       TEXT NOT NULL,
        status       TEXT NOT NULL,   -- 'injured' | 'suspended'
        injury_type  TEXT,
        return_date  TEXT,
        market_value TEXT,            -- valore giocatore (proxy importanza)
        scraped_at   TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_absences_team ON player_absences(team, league);

    -- Valori di mercato per squadra (da Transfermarkt)
    CREATE TABLE IF NOT EXISTS squad_values (
        team              TEXT NOT NULL,
        league            TEXT NOT NULL,
        market_value_str  TEXT,       -- es. "412,10 Mio. €"
        updated_at        TEXT,
        PRIMARY KEY (team, league)
    );

    -- xG per match da FBref (alternativa a Understat per coppe europee)
    CREATE TABLE IF NOT EXISTS fbref_match_xg (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        date        TEXT NOT NULL,
        home_team   TEXT NOT NULL,
        away_team   TEXT NOT NULL,
        xg_home     REAL,
        xg_away     REAL,
        home_goals  INTEGER,
        away_goals  INTEGER,
        league      TEXT NOT NULL,
        updated_at  TEXT,
        UNIQUE(date, home_team, away_team)
    );

    -- Stats avanzate per squadra da FBref (PPDA, progressive passes, possession)
    CREATE TABLE IF NOT EXISTS fbref_team_stats (
        team                 TEXT NOT NULL,
        league               TEXT NOT NULL,
        progressive_passes   REAL,
        progressive_carries  REAL,
        possession           REAL,    -- % possesso medio
        pressures            REAL,    -- numero pressioni difensive (proxy PPDA)
        pressure_success_pct REAL,    -- % pressioni riuscite
        updated_at           TEXT,
        PRIMARY KEY (team, league)
    );

    -- Parametri modello Dixon-Coles (salvati dopo ogni fit)
    CREATE TABLE IF NOT EXISTS dc_params (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        league_key  TEXT NOT NULL,
        team_name   TEXT NOT NULL,
        attack      REAL NOT NULL,
        defense     REAL NOT NULL,
        fitted_at   TEXT NOT NULL,
        UNIQUE(league_key, team_name, fitted_at)
    );

    CREATE TABLE IF NOT EXISTS dc_globals (
        league_key  TEXT PRIMARY KEY,
        home_adv    REAL NOT NULL,
        rho         REAL NOT NULL,
        fitted_at   TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()
    log.info("Database inizializzato: %s", DB_PATH)
    print(f"✓ Database pronto: {DB_PATH}")
