"""
Previsioni con il Poisson-stack (senza Elo): UNICA logica usata sia dalla pagina statica
(scripts/generate_static.py) sia dall'app Flask (/api/predict), così i numeri coincidono.

Per ogni lega, alla data di oggi:
  1. Dixon-Coles sui gol (xi=0.0018, finestra 5 anni, con tau)      -> dc_lmu, dc_lnu
  2. Dixon-Coles sui tiri in porta HST/AST (senza tau)               -> sot_lmu, sot_lnu
  3. pi-ratings correnti (stato dopo l'ultima partita giocata)       -> pi_gd, pi_diff
  4. models/stack.json (coefficienti, scaler, rho)                   -> gol attesi (mu, nu)
  5. matrice dei punteggi con correzione tau -> 1X2, O/U, BTTS, clean sheet, risultati esatti

Le feature sono calcolate con le STESSE funzioni (backtest/models.py, backtest/features.py)
usate per allenare lo stack: nessuna divergenza tra training e serving.
Solo numpy/scipy/pandas: lo stack si applica da JSON, senza scikit-learn.
"""
import json
import os
import sys
import threading
import time
import unicodedata
from difflib import SequenceMatcher

import numpy as np
import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backtest import data, features, models, stack  # noqa: E402

STACK_PATH = os.path.join(REPO_ROOT, "models", "stack.json")
XI = features.XI
YEARS_WINDOW = 5
HISTORY_TTL_S = 6 * 3600

CSV_CODE = {"serie_a": "I1", "premier_league": "E0", "bundesliga": "D1",
            "la_liga": "SP1", "ligue_1": "F1"}

# ── Nomi squadra: football-data.org -> football-data.co.uk ─────────────────────
# Alias espliciti, consultati prima del fuzzy matching (che altrimenti sbaglia,
# es. "Atleti" -> Almeria, "Nottingham" -> Tottenham).
TEAM_ALIASES = {
    # Premier League
    "nottingham": "Nott'm Forest", "nottingham forest": "Nott'm Forest",
    "wolverhampton": "Wolves", "wolverhampton wanderers": "Wolves", "wolves": "Wolves",
    "brighton hove": "Brighton", "brighton & hove albion": "Brighton",
    "man city": "Man City", "manchester city": "Man City",
    "man united": "Man United", "manchester united": "Man United",
    "newcastle": "Newcastle", "newcastle united": "Newcastle",
    "west ham": "West Ham", "west ham united": "West Ham",
    "tottenham": "Tottenham", "tottenham hotspur": "Tottenham",
    "sheffield united": "Sheffield United", "west brom": "West Brom",
    "west bromwich albion": "West Brom",
    # La Liga
    "atleti": "Ath Madrid", "atletico madrid": "Ath Madrid", "club atletico de madrid": "Ath Madrid",
    "athletic": "Ath Bilbao", "athletic club": "Ath Bilbao", "athletic bilbao": "Ath Bilbao",
    "deportivo": "La Coruna", "rc deportivo la coruna": "La Coruna", "deportivo la coruna": "La Coruna",
    "barca": "Barcelona", "espanyol": "Espanol", "rcd espanyol de barcelona": "Espanol",
    "rayo vallecano": "Vallecano", "real sociedad": "Sociedad", "real betis": "Betis",
    "real oviedo": "Oviedo", "racing santander": "Santander",
    "real racing club de santander": "Santander", "ud almeria": "Almeria",
    # Bundesliga
    "bayern": "Bayern Munich", "fc bayern munchen": "Bayern Munich",
    "frankfurt": "Ein Frankfurt", "eintracht frankfurt": "Ein Frankfurt",
    "m'gladbach": "M'gladbach", "borussia monchengladbach": "M'gladbach",
    "hsv": "Hamburg", "hamburger sv": "Hamburg", "1. fc koln": "FC Koln",
    "st. pauli": "St Pauli", "fc st. pauli 1910": "St Pauli",
    "bremen": "Werder Bremen", "sv werder bremen": "Werder Bremen",
    "1. fc heidenheim 1846": "Heidenheim", "holstein kiel": "Holstein Kiel",
    # Ligue 1
    "psg": "Paris SG", "paris saint-germain": "Paris SG", "paris saint-germain fc": "Paris SG",
    "stade rennais": "Rennes", "stade rennais fc 1901": "Rennes",
    "olympique lyon": "Lyon", "olympique lyonnais": "Lyon",
    "olympique de marseille": "Marseille", "rc lens": "Lens", "racing club de lens": "Lens",
    "saint-etienne": "St Etienne", "as saint-etienne": "St Etienne",
    "stade brestois 29": "Brest", "stade de reims": "Reims",
    # Serie A
    "hellas verona": "Verona", "hellas verona fc": "Verona",
    "fc internazionale milano": "Inter", "internazionale": "Inter",
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return " ".join(s.lower().strip().split())


def best_match(name: str, candidates) -> str | None:
    """Abbina un nome squadra di football-data.org al nome usato nei CSV storici."""
    name_l = _norm(name)
    cand = {_norm(c): c for c in candidates}

    alias = TEAM_ALIASES.get(name_l)
    if alias and _norm(alias) in cand:
        return cand[_norm(alias)]
    if name_l in cand:
        return cand[name_l]
    hits = [c for n, c in cand.items() if n in name_l or name_l in n]
    if len(hits) == 1:
        return hits[0]
    scored = [(SequenceMatcher(None, name_l, n).ratio(), c) for n, c in cand.items()]
    best_score, best = max(scored, key=lambda x: x[0])
    return best if best_score > 0.75 else None


# ── Modello salvato ────────────────────────────────────────────────────────────

def load_stack(path: str = STACK_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    if d["features"] != stack.PRODUCTION_FEATURES:
        raise ValueError(f"models/stack.json usa feature {d['features']}, "
                         f"attese {stack.PRODUCTION_FEATURES}")
    return d


# ── Stato della lega (fit di oggi) ─────────────────────────────────────────────

class LeagueState:
    """DC gol + DC tiri in porta + pi-ratings, calcolati con i dati precedenti a `today`."""

    def __init__(self, g: pd.DataFrame, today: pd.Timestamp):
        c0 = pd.Timestamp(today).normalize()
        g = g.sort_values("date")
        tr = g[(g.date < c0) & (g.date >= c0 - pd.Timedelta(days=365 * YEARS_WINDOW))]
        tr = tr.dropna(subset=["hg", "ag"])
        teams = sorted(set(tr.HomeTeam) | set(tr.AwayTeam))
        days = (c0 - tr.date).dt.days.values
        self.goals = models.fit_dc(tr.HomeTeam.values, tr.AwayTeam.values, tr.hg.values,
                                   tr.ag.values, days, XI, use_tau=True, teams=teams)

        trs = tr.dropna(subset=["HST", "AST"])
        teams_s = sorted(set(trs.HomeTeam) | set(trs.AwayTeam))
        days_s = (c0 - trs.date).dt.days.values
        self.shots = models.fit_dc(trs.HomeTeam.values, trs.AwayTeam.values, trs.HST.values,
                                   trs.AST.values, days_s, XI, use_tau=False, teams=teams_s)

        _, self.pi_state = models.pi_ratings(g[g.date < c0], return_state=True)
        self.teams = teams
        self.n_matches = int(len(tr))
        self.fitted_at = c0.strftime("%Y-%m-%d")

    def resolve(self, *names: str) -> str | None:
        """Nome CSV per una squadra (prova nome breve e completo); None se sconosciuta."""
        for n in names:
            if n:
                m = best_match(n, self.teams)
                if m:
                    return m
        return None

    def features(self, homes, aways) -> pd.DataFrame:
        homes, aways = list(homes), list(aways)
        mu_g, nu_g = models.dc_lambdas(self.goals, homes, aways)
        mu_s, nu_s = models.dc_lambdas(self.shots, homes, aways)
        rh = [self.pi_state.get(h, [0.0, 0.0]) for h in homes]
        ra = [self.pi_state.get(a, [0.0, 0.0]) for a in aways]
        pi = features.pi_features(pd.DataFrame({
            "pi_hh": [r[0] for r in rh], "pi_ha": [r[1] for r in rh],
            "pi_ah": [r[0] for r in ra], "pi_aa": [r[1] for r in ra]}))
        return pd.DataFrame({"dc_lmu": np.log(mu_g), "dc_lnu": np.log(nu_g),
                             "sot_lmu": np.log(mu_s), "sot_lnu": np.log(nu_s),
                             "pi_gd": pi.pi_gd.values, "pi_diff": pi.pi_diff.values})[stack.PRODUCTION_FEATURES]


# ── Mercati dalla matrice dei punteggi ─────────────────────────────────────────

def markets(M: np.ndarray, mu: float, nu: float) -> dict:
    """Tutti i mercati da UNA matrice (G+1)x(G+1): sono coerenti tra loro per costruzione."""
    G = M.shape[0]
    tot = np.add.outer(np.arange(G), np.arange(G))
    P = models.probs_1x2(M[None])[0]
    flat = sorted(((int(i), int(j), float(M[i, j])) for i in range(G) for j in range(G)),
                  key=lambda s: s[2], reverse=True)[:6]
    return {
        "exp_goals_home": round(float(mu), 2),
        "exp_goals_away": round(float(nu), 2),
        "prob_home": round(float(P[0]), 5),
        "prob_draw": round(float(P[1]), 5),
        "prob_away": round(float(P[2]), 5),
        "prob_o05": round(float(M[tot > 0].sum()), 5),
        "prob_o15": round(float(M[tot > 1].sum()), 5),
        "prob_o25": round(float(M[tot > 2].sum()), 5),
        "prob_o35": round(float(M[tot > 3].sum()), 5),
        "prob_btts": round(float(M[1:, 1:].sum()), 5),
        "prob_cs_home": round(float(M[:, 0].sum()), 5),
        "prob_cs_away": round(float(M[0, :].sum()), 5),
        "top_scores": [[s[0], s[1], round(s[2] * 100, 1)] for s in flat],
    }


def predict_pairs(state: LeagueState, model: dict, pairs) -> list[dict]:
    """pairs = [(home_csv_name, away_csv_name)]; nomi non presenti nel fit = squadra nuova."""
    if not pairs:
        return []
    homes, aways = zip(*pairs)
    X = state.features(homes, aways)
    mu, nu, rho = stack.predict_from_dict(model, X.to_numpy())
    M = models.score_matrix(mu, nu, np.full(len(mu), rho))
    return [markets(M[i], mu[i], nu[i]) for i in range(len(pairs))]


# ── Storico e stato in cache (usato dall'app Flask) ────────────────────────────

_lock = threading.Lock()
_cache = {"df": None, "loaded": 0.0, "states": {}, "model": None}


def _history() -> pd.DataFrame:
    if _cache["df"] is None or time.time() - _cache["loaded"] > HISTORY_TTL_S:
        _cache.update(df=data.load_matches(verbose=False), loaded=time.time(), states={})
    return _cache["df"]


def league_state(league_key: str, today=None) -> LeagueState:
    today = pd.Timestamp(today or pd.Timestamp.utcnow().tz_localize(None)).normalize()
    with _lock:
        df = _history()
        key = (league_key, str(today.date()))
        if key not in _cache["states"]:
            g = df[df.Division == CSV_CODE[league_key]]
            _cache["states"][key] = LeagueState(g, today)
        if _cache["model"] is None:
            _cache["model"] = load_stack()
        return _cache["states"][key]


def predict_single(league_key: str, home: str, away: str, home_full=None, away_full=None) -> dict:
    """Previsione per una partita, con gli stessi numeri della pagina statica."""
    state = league_state(league_key)
    h = state.resolve(home, home_full)
    a = state.resolve(away, away_full)
    pred = predict_pairs(state, _cache["model"], [(h or home, a or away)])[0]
    pred.update(home_dc=h, away_dc=a, new_team=bool(h is None or a is None))
    return pred
