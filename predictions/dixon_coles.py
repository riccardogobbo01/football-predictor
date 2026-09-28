"""
Modello Dixon-Coles (1997) per la previsione di risultati calcistici.

Ogni squadra ha:
  α_i  — forza d'attacco (log-scale)
  δ_i  — debolezza difensiva (log-scale, valori negativi = difesa forte)

Gol attesi:
  μ = exp(α_home + δ_away + home_advantage)   [gol casa]
  ν = exp(α_away + δ_home)                    [gol trasferta]

Correzione Dixon-Coles τ(ρ) per punteggi bassi (0-0, 1-0, 0-1, 1-1).

Fitting via scipy: weighted log-likelihood con decadimento temporale exp(-ξ·days).
"""
import logging
from datetime import datetime
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize
from scipy.stats import poisson

from config import DC_XI, DC_MAX_GOALS
from db import get_conn
from features.engineer import MatchFeatures

log = logging.getLogger(__name__)


# ── Correzione Dixon-Coles ────────────────────────────────────────────────────

def tau(x: int, y: int, mu: float, nu: float, rho: float) -> float:
    """
    Fattore correttivo Dixon-Coles per punteggi bassi.
    Applicato solo a (0,0), (1,0), (0,1), (1,1).
    """
    if x == 0 and y == 0:
        return 1 - mu * nu * rho
    elif x == 1 and y == 0:
        return 1 + nu * rho
    elif x == 0 and y == 1:
        return 1 + mu * rho
    elif x == 1 and y == 1:
        return 1 - rho
    return 1.0


def dc_prob(x: int, y: int, mu: float, nu: float, rho: float) -> float:
    """P(home_goals=x, away_goals=y) secondo il modello Dixon-Coles."""
    t = tau(x, y, mu, nu, rho)
    return max(t * poisson.pmf(x, mu) * poisson.pmf(y, nu), 1e-10)


# ── Fitting del modello ────────────────────────────────────────────────────────

@dataclass
class DCParams:
    """Parametri fittati del modello per un campionato."""
    teams: list[str]
    attack: dict[str, float]    # α_i per ogni squadra
    defense: dict[str, float]   # δ_i per ogni squadra
    home_adv: float             # λ home advantage
    rho: float                  # ρ correzione basso punteggio
    fitted_at: str = ""
    league_key: str = ""


def _time_weight(match_date: str, ref_date: str, xi: float = DC_XI) -> float:
    """Peso temporale: partite recenti contano di più."""
    try:
        d1 = datetime.strptime(match_date[:10], "%Y-%m-%d")
        d2 = datetime.strptime(ref_date[:10], "%Y-%m-%d")
        days = max((d2 - d1).days, 0)
    except ValueError:
        days = 365
    return np.exp(-xi * days)


def fit(league_key: str, season: int = None,
        min_matches: int = 5, xi: float = DC_XI) -> DCParams | None:
    """
    Fitta il modello Dixon-Coles per un campionato.
    Restituisce DCParams o None se dati insufficienti.
    """
    conn = get_conn()
    ref_date = datetime.utcnow().strftime("%Y-%m-%d")

    # Carica le partite con risultati
    q = """
        SELECT m.match_date,
               ht.name AS home_team, at.name AS away_team,
               m.home_goals, m.away_goals
        FROM matches m
        JOIN teams ht ON ht.id = m.home_team_id
        JOIN teams at ON at.id = m.away_team_id
        WHERE m.league_key = ?
          AND m.status = 'FINISHED'
          AND m.home_goals IS NOT NULL
    """
    params = [league_key]
    if season:
        q += " AND m.season = ?"
        params.append(season)
    q += " ORDER BY m.match_date"

    rows = conn.execute(q, params).fetchall()
    conn.close()

    if len(rows) < min_matches:
        log.warning("Dati insufficienti per %s: %d partite", league_key, len(rows))
        return None

    # Raccoglie tutte le squadre
    teams = sorted(set(
        [r["home_team"] for r in rows] + [r["away_team"] for r in rows]
    ))
    n_teams = len(teams)
    t_idx = {t: i for i, t in enumerate(teams)}

    # Calcola i pesi temporali
    weights = np.array([_time_weight(r["match_date"], ref_date, xi) for r in rows])

    # ── Funzione di log-verosimiglianza negativa ──────────────────────────────
    def neg_log_lik(params_vec):
        home_adv = params_vec[0]
        rho      = params_vec[1]
        alphas   = params_vec[2:2 + n_teams]        # attacchi
        deltas   = params_vec[2 + n_teams:]          # difese (vincolo: sum=0)

        ll = 0.0
        for i, r in enumerate(rows):
            hi = t_idx[r["home_team"]]
            ai = t_idx[r["away_team"]]
            mu = np.exp(alphas[hi] + deltas[ai] + home_adv)
            nu = np.exp(alphas[ai] + deltas[hi])
            p  = dc_prob(r["home_goals"], r["away_goals"], mu, nu, rho)
            ll += weights[i] * np.log(p)

        return -ll

    # Inizializzazione
    x0 = np.zeros(2 + 2 * n_teams)
    x0[0] = 0.2   # home advantage
    x0[1] = -0.1  # rho

    # Bounds
    bounds = [(-0.5, 1.0), (-0.5, 0.5)]   # home_adv, rho
    bounds += [(-2.0, 2.0)] * n_teams      # alphas
    bounds += [(-2.0, 2.0)] * n_teams      # deltas

    # Vincolo: media attacchi = 0 (identificabilità)
    from scipy.optimize import LinearConstraint
    A = np.zeros((1, len(x0)))
    A[0, 2:2 + n_teams] = 1.0
    constraint = LinearConstraint(A, lb=0.0, ub=0.0)

    result = minimize(
        neg_log_lik, x0,
        method="SLSQP",
        bounds=bounds,
        constraints={"type": "eq", "fun": lambda p: p[2:2+n_teams].sum()},
        options={"maxiter": 500, "ftol": 1e-8}
    )

    if not result.success:
        log.warning("Ottimizzazione Dixon-Coles non convergita: %s", result.message)

    p = result.x
    home_adv = p[0]
    rho      = p[1]
    alphas   = p[2:2 + n_teams]
    deltas   = p[2 + n_teams:]

    dc = DCParams(
        teams=teams,
        attack={t: float(alphas[t_idx[t]])  for t in teams},
        defense={t: float(deltas[t_idx[t]]) for t in teams},
        home_adv=float(home_adv),
        rho=float(rho),
        fitted_at=ref_date,
        league_key=league_key,
    )

    _save_params(dc)
    return dc


def _save_params(dc: DCParams):
    """Salva i parametri nel database per riuso successivo."""
    conn = get_conn()
    now = dc.fitted_at
    for t in dc.teams:
        conn.execute("""
            INSERT OR REPLACE INTO dc_params (league_key, team_name, attack, defense, fitted_at)
            VALUES (?, ?, ?, ?, ?)
        """, (dc.league_key, t, dc.attack[t], dc.defense[t], now))
    conn.execute("""
        INSERT OR REPLACE INTO dc_globals (league_key, home_adv, rho, fitted_at)
        VALUES (?, ?, ?, ?)
    """, (dc.league_key, dc.home_adv, dc.rho, now))
    conn.commit()
    conn.close()


def load_params(league_key: str) -> DCParams | None:
    """Carica gli ultimi parametri fittati dal DB."""
    conn = get_conn()
    g = conn.execute("""
        SELECT home_adv, rho, fitted_at FROM dc_globals
        WHERE league_key = ?
    """, (league_key,)).fetchone()

    if not g:
        conn.close()
        return None

    fitted_at = g["fitted_at"]
    rows = conn.execute("""
        SELECT team_name, attack, defense FROM dc_params
        WHERE league_key = ? AND fitted_at = ?
    """, (league_key, fitted_at)).fetchall()
    conn.close()

    if not rows:
        return None

    teams = [r["team_name"] for r in rows]
    return DCParams(
        teams=teams,
        attack={r["team_name"]: r["attack"] for r in rows},
        defense={r["team_name"]: r["defense"] for r in rows},
        home_adv=g["home_adv"],
        rho=g["rho"],
        fitted_at=fitted_at,
        league_key=league_key,
    )


# ── Previsione ─────────────────────────────────────────────────────────────────

@dataclass
class Prediction:
    """Risultato della previsione per una partita."""
    home_team: str
    away_team: str

    # Gol attesi
    home_xg: float = 0.0
    away_xg: float = 0.0

    # Probabilità 1X2
    prob_home: float = 0.0
    prob_draw: float = 0.0
    prob_away: float = 0.0

    # Over/Under
    prob_o05: float = 0.0
    prob_o15: float = 0.0
    prob_o25: float = 0.0
    prob_o35: float = 0.0
    prob_o45: float = 0.0

    # BTTS
    prob_btts: float = 0.0

    # Clean sheet
    prob_cs_home: float = 0.0   # away non segna
    prob_cs_away: float = 0.0   # home non segna

    # Punteggi più probabili (lista di (home_gol, away_gol, prob))
    top_scores: list = None

    # Statistiche secondarie (Poisson semplice)
    exp_corners: float = 0.0
    exp_yellow:  float = 0.0
    exp_shots:   float = 0.0

    # Features usate (per trasparenza)
    features: MatchFeatures = None

    def __post_init__(self):
        if self.top_scores is None:
            self.top_scores = []


def _contextual_adjustment(mu: float, nu: float,
                            features: "MatchFeatures") -> tuple[float, float]:
    """
    Aggiusta μ (gol attesi casa) e ν (gol attesi trasferta) in base a
    fattori contestuali non catturati dal modello Dixon-Coles puro.

    Logica:
    - Stanchezza (< 3 giorni di riposo) → -8% gol
    - Congestionamento (> 3 partite in 14 gg) → -5% gol
    - Assenze chiave → -5% per ogni assente (max -20%)
    - Pressing alto (PPDA avversario alto) → +4% gol subiti
    """
    # 1. Stanchezza
    if getattr(features, "home_rest_days", 7) < 3:
        mu *= 0.92
    if getattr(features, "away_rest_days", 7) < 3:
        nu *= 0.92

    # 2. Congestionamento calendario
    home_cong = getattr(features, "home_congestion", 0)
    away_cong = getattr(features, "away_congestion", 0)
    if home_cong > 3:
        mu *= 0.95
    if away_cong > 3:
        nu *= 0.95

    # 3. Assenze chiave (infortuni/squalifiche)
    home_abs = min(getattr(features, "home_absences", 0), 4)
    away_abs = min(getattr(features, "away_absences", 0), 4)
    if home_abs > 0:
        mu *= max(1.0 - home_abs * 0.05, 0.80)
    if away_abs > 0:
        nu *= max(1.0 - away_abs * 0.05, 0.80)

    # 4. Pressing aggressivo: squadra con molte pressioni difensive tende
    #    a concedere meno → riduzione leggera dei gol attesi avversario
    home_ppda = getattr(features, "home_ppda", 10.0)
    away_ppda = getattr(features, "away_ppda", 10.0)
    # Normalizzazione: media ~10, alto pressing = valore alto
    if home_ppda > 0 and away_ppda > 0:
        press_ratio = home_ppda / max(away_ppda, 1.0)
        # Se home preme molto più dell'avversario → riduce attacco away
        if press_ratio > 1.3:
            nu *= 0.96
        elif press_ratio < 0.77:
            mu *= 0.96

    return mu, nu


def predict(home_team: str, away_team: str,
            features: MatchFeatures,
            dc: DCParams | None = None,
            league_key: str = None,
            max_goals: int = DC_MAX_GOALS) -> Prediction:
    """
    Genera una previsione completa per home_team vs away_team.
    Se dc è None, carica i parametri dal DB o usa i parametri di default.
    """
    pred = Prediction(home_team=home_team, away_team=away_team, features=features)

    # ── Calcola μ e ν ─────────────────────────────────────────────────────────
    if dc and home_team in dc.attack and away_team in dc.attack:
        # Usa parametri Dixon-Coles
        alpha_h = dc.attack.get(home_team, 0.0)
        delta_h = dc.defense.get(home_team, 0.0)
        alpha_a = dc.attack.get(away_team, 0.0)
        delta_a = dc.defense.get(away_team, 0.0)
        mu = np.exp(alpha_h + delta_a + dc.home_adv)
        nu = np.exp(alpha_a + delta_h)
        rho = dc.rho
    else:
        # Fallback: stima diretta dalle feature
        # Liga-media gol per partita ≈ 1.5 (casa) / 1.2 (trasferta)
        LEAGUE_AVG_HOME = 1.50
        LEAGUE_AVG_AWAY = 1.15
        mu = features.home_attack / features.away_defense * LEAGUE_AVG_HOME
        nu = features.away_attack / features.home_defense * LEAGUE_AVG_AWAY

        # Aggiustamento ELO (ogni 100 punti ELO ≈ 5% variazione gol attesi)
        elo_factor = 1 + features.elo_diff / 2000.0
        mu *= elo_factor
        nu /= max(elo_factor, 0.1)

        # Aggiustamento meteo (pioggia riduce gol del ~8% per punto di impatto)
        mu *= (1 - features.weather_impact * 0.08)
        nu *= (1 - features.weather_impact * 0.08)

        rho = -0.08   # default

    mu = max(mu, 0.1)
    nu = max(nu, 0.1)

    # ── Aggiustamenti contestuali ─────────────────────────────────────────────
    mu, nu = _contextual_adjustment(mu, nu, features)

    mu = max(mu, 0.1)
    nu = max(nu, 0.1)

    pred.home_xg = round(float(mu), 2)
    pred.away_xg = round(float(nu), 2)

    # ── Matrice dei punteggi ──────────────────────────────────────────────────
    score_matrix = np.zeros((max_goals + 1, max_goals + 1))
    for x in range(max_goals + 1):
        for y in range(max_goals + 1):
            score_matrix[x, y] = dc_prob(x, y, mu, nu, rho)

    # Normalizza (somma ≈ 1 ma non esatta per via del troncamento)
    score_matrix /= score_matrix.sum()

    # ── Probabilità 1X2 ───────────────────────────────────────────────────────
    pred.prob_home = float(np.tril(score_matrix, -1).sum())   # home > away
    pred.prob_draw = float(np.trace(score_matrix))             # pareggio
    pred.prob_away = float(np.triu(score_matrix, 1).sum())    # away > home

    # ── Over/Under ────────────────────────────────────────────────────────────
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            total = i + j
            p = score_matrix[i, j]
            if total > 0.5: pred.prob_o05 += p
            if total > 1.5: pred.prob_o15 += p
            if total > 2.5: pred.prob_o25 += p
            if total > 3.5: pred.prob_o35 += p
            if total > 4.5: pred.prob_o45 += p

    # ── BTTS ──────────────────────────────────────────────────────────────────
    pred.prob_btts = float(score_matrix[1:, 1:].sum())

    # ── Clean sheet ───────────────────────────────────────────────────────────
    pred.prob_cs_home = float(score_matrix[:, 0].sum())   # away segna 0
    pred.prob_cs_away = float(score_matrix[0, :].sum())   # home segna 0

    # ── Top punteggi ──────────────────────────────────────────────────────────
    scores_flat = [
        (int(x), int(y), float(score_matrix[x, y]))
        for x in range(max_goals + 1)
        for y in range(max_goals + 1)
    ]
    pred.top_scores = sorted(scores_flat, key=lambda s: s[2], reverse=True)[:8]

    # ── Statistiche secondarie ────────────────────────────────────────────────
    # Corner: media squadra × aggiustamento meteo (pioggia riduce corner del ~4%)
    pred.exp_corners = round(
        (features.home_corners_avg + features.away_corners_avg)
        * (1 - features.weather_impact * 0.04), 1
    )

    # Cartellini gialli: media referee + media squadre × fattore derby (H2H)
    derby_factor = 1 + abs(features.h2h_advantage) * 0.15
    pred.exp_yellow = round(
        (features.referee_yellow_avg +
         features.home_yellow_avg + features.away_yellow_avg) / 3.0
        * derby_factor, 1
    )

    # Tiri: xG / conversion rate medio (0.105 tiri xG nei top 5 campionati)
    SHOT_XG_RATE = 0.105
    pred.exp_shots = round((mu + nu) / SHOT_XG_RATE, 1)

    # Blend con quote di mercato (se disponibili) — peso 20% mercato
    if features.market_ph > 0:
        w = 0.20
        pred.prob_home = pred.prob_home * (1-w) + features.market_ph * w
        pred.prob_draw = pred.prob_draw * (1-w) + features.market_pd * w
        pred.prob_away = pred.prob_away * (1-w) + features.market_pa * w
        total = pred.prob_home + pred.prob_draw + pred.prob_away
        pred.prob_home /= total
        pred.prob_draw /= total
        pred.prob_away /= total

    return pred
