#!/usr/bin/env python3
"""
generate_static.py — Genera docs/index.html con le previsioni delle prossime partite.

Completamente standalone: scarica i CSV da football-data.co.uk, fitta Dixon-Coles
in memoria (nessun DB), scarica le fixture da football-data.org, genera HTML statico.

Usato da GitHub Actions per aggiornare GitHub Pages ogni giorno.
Funziona anche in locale: python scripts/generate_static.py
"""
import io
import json
import logging
import os
import time
from datetime import datetime, timedelta
from difflib import SequenceMatcher

import numpy as np
import pandas as pd
import requests
from scipy.optimize import minimize
from scipy.stats import poisson

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Configurazione ─────────────────────────────────────────────────────────────

FOOTBALL_DATA_ORG_KEY = os.getenv("FOOTBALL_DATA_ORG_KEY", "")

LEAGUES = {
    "serie_a":        {"code": "SA",  "csv": "I1",  "name": "Serie A",        "flag": "🇮🇹"},
    "premier_league": {"code": "PL",  "csv": "E0",  "name": "Premier League", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    "bundesliga":     {"code": "BL1", "csv": "D1",  "name": "Bundesliga",      "flag": "🇩🇪"},
    "la_liga":        {"code": "PD",  "csv": "SP1", "name": "La Liga",         "flag": "🇪🇸"},
    "ligue_1":        {"code": "FL1", "csv": "F1",  "name": "Ligue 1",         "flag": "🇫🇷"},
}

CSV_SEASONS = ["2526", "2425", "2324", "2223", "2122"]  # ~5 stagioni
DC_XI       = 0.0018   # tasso decadimento temporale
DC_MAX_GOALS = 7
DAYS_AHEAD  = 14

# ── Download CSV ───────────────────────────────────────────────────────────────

def download_csv_data(league_key: str) -> pd.DataFrame:
    """Scarica i CSV storici da football-data.co.uk e restituisce un DataFrame pulito."""
    csv_code = LEAGUES[league_key]["csv"]
    dfs = []

    for season in CSV_SEASONS:
        url = f"https://www.football-data.co.uk/mmz4281/{season}/{csv_code}.csv"
        try:
            resp = requests.get(url, timeout=25)
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            df = pd.read_csv(
                io.StringIO(resp.content.decode("latin-1")),
                on_bad_lines="skip"
            )
            needed = ["HomeTeam", "AwayTeam", "FTHG", "FTAG", "Date"]
            if not all(c in df.columns for c in needed):
                continue

            df = df[needed + [c for c in ["HS", "AS", "HC", "AC", "HY", "AY"]
                              if c in df.columns]].copy()
            df = df.dropna(subset=["HomeTeam", "AwayTeam", "FTHG", "FTAG"])
            df["FTHG"] = pd.to_numeric(df["FTHG"], errors="coerce")
            df["FTAG"] = pd.to_numeric(df["FTAG"], errors="coerce")
            df = df.dropna(subset=["FTHG", "FTAG"])
            df["FTHG"] = df["FTHG"].astype(int)
            df["FTAG"] = df["FTAG"].astype(int)

            # Parse date — football-data usa DD/MM/YY o DD/MM/YYYY
            for fmt in ["%d/%m/%Y", "%d/%m/%y"]:
                try:
                    df["date_parsed"] = pd.to_datetime(df["Date"], format=fmt)
                    break
                except Exception:
                    pass
            else:
                df["date_parsed"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")

            df = df.dropna(subset=["date_parsed"])
            df["season"] = season
            dfs.append(df)
            log.info("  %s/%s: %d partite", league_key, season, len(df))
            time.sleep(0.4)
        except Exception as e:
            log.warning("  Errore download %s: %s", url, e)

    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True).sort_values("date_parsed").reset_index(drop=True)


# ── Dixon-Coles ────────────────────────────────────────────────────────────────

def fit_dixon_coles(df: pd.DataFrame) -> dict | None:
    """
    Fitta il modello Dixon-Coles su df con ottimizzazione vettorizzata.
    Restituisce un dict con attack/defense/home_adv/rho per ogni squadra.
    """
    if len(df) < 60:
        log.warning("  Dati insufficienti (%d partite)", len(df))
        return None

    ref_date = df["date_parsed"].max()
    days_ago = (ref_date - df["date_parsed"]).dt.days.values.astype(float)
    weights  = np.exp(-DC_XI * days_ago)

    teams = sorted(set(df["HomeTeam"].tolist()) | set(df["AwayTeam"].tolist()))
    t_idx = {t: i for i, t in enumerate(teams)}
    n     = len(teams)

    hi_arr = np.array([t_idx[t] for t in df["HomeTeam"]])
    ai_arr = np.array([t_idx[t] for t in df["AwayTeam"]])
    hg_arr = df["FTHG"].values
    ag_arr = df["FTAG"].values

    def neg_log_lik(params):
        home_adv = params[0]
        rho      = params[1]
        alphas   = params[2:2 + n]
        deltas   = params[2 + n:]

        mu = np.exp(alphas[hi_arr] + deltas[ai_arr] + home_adv)
        nu = np.exp(alphas[ai_arr] + deltas[hi_arr])

        # Poisson PMF vettorizzato
        log_p = (poisson.logpmf(hg_arr, mu) + poisson.logpmf(ag_arr, nu))

        # Correzione Dixon-Coles per punteggi bassi
        tau_vec = np.ones(len(df))
        m00 = (hg_arr == 0) & (ag_arr == 0)
        m10 = (hg_arr == 1) & (ag_arr == 0)
        m01 = (hg_arr == 0) & (ag_arr == 1)
        m11 = (hg_arr == 1) & (ag_arr == 1)
        tau_vec[m00] = np.maximum(1 - mu[m00] * nu[m00] * rho, 1e-10)
        tau_vec[m10] = np.maximum(1 + nu[m10] * rho,           1e-10)
        tau_vec[m01] = np.maximum(1 + mu[m01] * rho,           1e-10)
        tau_vec[m11] = np.maximum(1 - rho,                      1e-10)

        ll = np.sum(weights * (log_p + np.log(tau_vec)))
        return -ll

    x0 = np.zeros(2 + 2 * n)
    x0[0] = 0.2    # home advantage
    x0[1] = -0.08  # rho

    bounds = [(-0.5, 1.0), (-0.5, 0.5)] + [(-2.5, 2.5)] * (2 * n)

    result = minimize(
        neg_log_lik, x0,
        method="SLSQP",
        bounds=bounds,
        constraints={"type": "eq", "fun": lambda p: p[2:2 + n].sum()},
        options={"maxiter": 400, "ftol": 1e-7},
    )

    if not result.success:
        log.warning("  Dixon-Coles non convergita: %s", result.message)

    p = result.x
    return {
        "teams":      teams,
        "attack":     {t: float(p[2 + t_idx[t]])          for t in teams},
        "defense":    {t: float(p[2 + n + t_idx[t]])      for t in teams},
        "home_adv":   float(p[0]),
        "rho":        float(p[1]),
        "fitted_at":  ref_date.strftime("%Y-%m-%d"),
        "n_matches":  int(len(df)),
    }


# ── Previsione ─────────────────────────────────────────────────────────────────

def predict_match(home: str, away: str, dc: dict) -> dict | None:
    """Genera una previsione completa per home vs away."""
    if home not in dc["attack"] or away not in dc["attack"]:
        return None

    mu  = np.exp(dc["attack"][home] + dc["defense"][away] + dc["home_adv"])
    nu  = np.exp(dc["attack"][away] + dc["defense"][home])
    rho = dc["rho"]
    mu  = max(float(mu), 0.1)
    nu  = max(float(nu), 0.1)

    G = DC_MAX_GOALS
    score_matrix = np.zeros((G + 1, G + 1))
    for x in range(G + 1):
        for y in range(G + 1):
            t = 1.0
            if   x == 0 and y == 0: t = max(1 - mu * nu * rho, 1e-10)
            elif x == 1 and y == 0: t = max(1 + nu * rho,       1e-10)
            elif x == 0 and y == 1: t = max(1 + mu * rho,       1e-10)
            elif x == 1 and y == 1: t = max(1 - rho,             1e-10)
            score_matrix[x, y] = t * poisson.pmf(x, mu) * poisson.pmf(y, nu)
    score_matrix = np.maximum(score_matrix, 1e-10)
    score_matrix /= score_matrix.sum()

    prob_home = float(np.tril(score_matrix, -1).sum())
    prob_draw = float(np.trace(score_matrix))
    prob_away = float(np.triu(score_matrix, 1).sum())

    prob_o15 = float(sum(score_matrix[i, j] for i in range(G+1) for j in range(G+1) if i+j > 1))
    prob_o25 = float(sum(score_matrix[i, j] for i in range(G+1) for j in range(G+1) if i+j > 2))
    prob_o35 = float(sum(score_matrix[i, j] for i in range(G+1) for j in range(G+1) if i+j > 3))
    prob_btts = float(score_matrix[1:, 1:].sum())
    prob_cs_home = float(score_matrix[:, 0].sum())

    scores_flat = [
        (int(x), int(y), float(score_matrix[x, y]))
        for x in range(G + 1) for y in range(G + 1)
    ]
    top_scores = sorted(scores_flat, key=lambda s: s[2], reverse=True)[:6]

    return {
        "home_xg":     round(mu, 2),
        "away_xg":     round(nu, 2),
        "prob_home":   round(prob_home, 3),
        "prob_draw":   round(prob_draw, 3),
        "prob_away":   round(prob_away, 3),
        "prob_o15":    round(prob_o15, 3),
        "prob_o25":    round(prob_o25, 3),
        "prob_o35":    round(prob_o35, 3),
        "prob_btts":   round(prob_btts, 3),
        "prob_cs_home":round(prob_cs_home, 3),
        "top_scores":  [[s[0], s[1], round(s[2]*100, 1)] for s in top_scores],
    }


# ── Fixture da football-data.org ──────────────────────────────────────────────

def get_fixtures(league_code: str) -> list[dict]:
    """Scarica le prossime partite da football-data.org (free tier)."""
    if not FOOTBALL_DATA_ORG_KEY:
        return []

    today = datetime.utcnow().strftime("%Y-%m-%d")
    end   = (datetime.utcnow() + timedelta(days=DAYS_AHEAD)).strftime("%Y-%m-%d")
    url   = f"https://api.football-data.org/v4/competitions/{league_code}/matches"

    try:
        resp = requests.get(
            url,
            headers={"X-Auth-Token": FOOTBALL_DATA_ORG_KEY},
            params={"dateFrom": today, "dateTo": end, "status": "SCHEDULED,TIMED"},
            timeout=20,
        )
        resp.raise_for_status()
        matches = []
        for m in resp.json().get("matches", []):
            home = m["homeTeam"].get("shortName") or m["homeTeam"]["name"]
            away = m["awayTeam"].get("shortName") or m["awayTeam"]["name"]
            matches.append({
                "date":      m["utcDate"][:10],
                "time":      m["utcDate"][11:16],
                "home":      home,
                "away":      away,
                "home_full": m["homeTeam"]["name"],
                "away_full": m["awayTeam"]["name"],
                "matchday":  m.get("matchday", "?"),
            })
        return matches
    except Exception as e:
        log.warning("  Errore fixture %s: %s", league_code, e)
        return []


# ── Name matching ──────────────────────────────────────────────────────────────

def best_match(name: str, candidates: list[str]) -> str | None:
    """Trova il miglior match fuzzy per un nome squadra nella lista DC."""
    name_l = name.lower().strip()

    # 1. Exact
    for c in candidates:
        if c.lower() == name_l:
            return c

    # 2. Containment
    for c in candidates:
        c_l = c.lower()
        if name_l in c_l or c_l in name_l:
            return c

    # 3. Sequenza (SequenceMatcher)
    scored = [(SequenceMatcher(None, name_l, c.lower()).ratio(), c) for c in candidates]
    best_score, best = max(scored, key=lambda x: x[0])
    return best if best_score > 0.55 else None


# ── Generazione HTML ───────────────────────────────────────────────────────────

def _prob_color(p: float) -> str:
    if p >= 0.50: return "#4ade80"
    if p >= 0.35: return "#fbbf24"
    return "#f87171"

def _bar(p: float, color: str) -> str:
    return (f'<div class="bar-wrap"><div class="bar" '
            f'style="width:{p*100:.1f}%;background:{color}"></div></div>')


def generate_html(leagues_data: dict, generated_at: str) -> str:
    # Conta totale previsioni
    total_preds = sum(
        sum(1 for f in ld["fixtures"] if f.get("prediction"))
        for ld in leagues_data.values()
    )

    # Costruisci i tab buttons
    tabs_html = '<button class="tab active" onclick="switchTab(\'all\',this)">🌍 Tutte</button>\n'
    for lk, ld in leagues_data.items():
        count = sum(1 for f in ld["fixtures"] if f.get("prediction"))
        tabs_html += (f'<button class="tab" onclick="switchTab(\'{lk}\',this)">'
                      f'{ld["flag"]} {ld["name"]} <span class="badge">{count}</span></button>\n')

    # Costruisci le card per ogni lega
    cards_html = ""
    for lk, ld in leagues_data.items():
        has_preds = [f for f in ld["fixtures"] if f.get("prediction")]
        if not has_preds:
            continue

        cards_html += f'<div class="league-section" data-league="{lk}">\n'
        cards_html += (f'<div class="league-header">'
                       f'<span class="league-flag">{ld["flag"]}</span>'
                       f'<span class="league-name">{ld["name"]}</span>'
                       f'<span class="league-meta">Modello fittato su {ld["dc_n_matches"]} partite · {ld["dc_fitted_at"]}</span>'
                       f'</div>\n')
        cards_html += '<div class="matches-grid">\n'

        for fix in ld["fixtures"]:
            pred = fix.get("prediction")
            if not pred:
                continue

            ph = pred["prob_home"]
            pd_ = pred["prob_draw"]
            pa = pred["prob_away"]

            # Determina esito più probabile
            max_p = max(ph, pd_, pa)
            if max_p == ph:
                outcome_label, outcome_color = "1 Casa", "#4ade80" if ph > 0.5 else "#fbbf24"
            elif max_p == pd_:
                outcome_label, outcome_color = "X Pareggio", "#fbbf24"
            else:
                outcome_label, outcome_color = "2 Ospite", "#f87171" if pa > 0.5 else "#fbbf24"

            top_score = pred["top_scores"][0]
            ts_str = f"{top_score[0]}–{top_score[1]} ({top_score[2]:.1f}%)"

            c = _prob_color
            cards_html += f"""
<div class="match-card">
  <div class="match-meta">
    <span>Giornata {fix['matchday']}</span>
    <span>{fix['date']} {fix['time']} UTC</span>
  </div>
  <div class="teams-row">
    <div class="team home-team">{fix['home']}</div>
    <div class="xg-display">
      <span class="xg home-xg">{pred['home_xg']}</span>
      <span class="xg-sep">xG</span>
      <span class="xg away-xg">{pred['away_xg']}</span>
    </div>
    <div class="team away-team">{fix['away']}</div>
  </div>
  <div class="outcome-badge" style="color:{outcome_color}">{outcome_label} — {max_p*100:.1f}%</div>
  <div class="probs-section">
    <div class="prob-row">
      <span class="prob-lbl">1</span>
      {_bar(ph, c(ph))}
      <span class="prob-pct" style="color:{c(ph)}">{ph*100:.1f}%</span>
    </div>
    <div class="prob-row">
      <span class="prob-lbl">X</span>
      {_bar(pd_, c(pd_))}
      <span class="prob-pct" style="color:{c(pd_)}">{pd_*100:.1f}%</span>
    </div>
    <div class="prob-row">
      <span class="prob-lbl">2</span>
      {_bar(pa, c(pa))}
      <span class="prob-pct" style="color:{c(pa)}">{pa*100:.1f}%</span>
    </div>
  </div>
  <div class="secondaries">
    <div class="sec-item">
      <span class="sec-lbl">Over 2.5</span>
      <span class="sec-val" style="color:{c(pred['prob_o25'])}">{pred['prob_o25']*100:.1f}%</span>
    </div>
    <div class="sec-item">
      <span class="sec-lbl">BTTS</span>
      <span class="sec-val" style="color:{c(pred['prob_btts'])}">{pred['prob_btts']*100:.1f}%</span>
    </div>
    <div class="sec-item">
      <span class="sec-lbl">Score tip</span>
      <span class="sec-val score-tip">{ts_str}</span>
    </div>
  </div>
</div>
"""
        cards_html += "</div>\n</div>\n"

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Football Predictor</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
:root {{
  --bg: #0d1117;
  --surface: #161b22;
  --card: #1c2128;
  --card-hover: #22272e;
  --border: #30363d;
  --accent: #4f8ef7;
  --text: #e6edf3;
  --muted: #8b949e;
  --green: #4ade80;
  --yellow: #fbbf24;
  --red: #f87171;
  --radius: 12px;
}}
@media (prefers-color-scheme: light) {{
  :root:not([data-theme="dark"]) {{
    --bg: #f6f8fa;
    --surface: #ffffff;
    --card: #ffffff;
    --card-hover: #f0f4f9;
    --border: #d0d7de;
    --text: #1f2328;
    --muted: #656d76;
  }}
}}
:root[data-theme="light"] {{
  --bg: #f6f8fa;
  --surface: #ffffff;
  --card: #ffffff;
  --card-hover: #f0f4f9;
  --border: #d0d7de;
  --text: #1f2328;
  --muted: #656d76;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background: var(--bg);
  color: var(--text);
  font-family: 'Inter', system-ui, sans-serif;
  min-height: 100vh;
}}
/* Header */
header {{
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 16px 24px;
  display: flex;
  align-items: center;
  gap: 14px;
  position: sticky;
  top: 0;
  z-index: 50;
}}
.logo {{ font-size: 1.6rem; }}
.site-title {{ font-size: 1.2rem; font-weight: 800; letter-spacing: -.4px; }}
.site-title em {{ color: var(--accent); font-style: normal; }}
.header-meta {{ margin-left: auto; font-size: .78rem; color: var(--muted); text-align: right; }}
.header-meta strong {{ color: var(--text); }}
.theme-btn {{
  background: none; border: 1px solid var(--border); border-radius: 8px;
  padding: 6px 10px; cursor: pointer; color: var(--muted); font-size: .85rem;
  transition: color .15s, border-color .15s;
}}
.theme-btn:hover {{ color: var(--text); border-color: var(--accent); }}

/* Tabs */
.tabs-wrap {{
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 0 20px;
  display: flex;
  gap: 2px;
  overflow-x: auto;
  scrollbar-width: none;
}}
.tabs-wrap::-webkit-scrollbar {{ display: none; }}
.tab {{
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 12px 14px;
  cursor: pointer;
  font-size: .84rem;
  font-weight: 500;
  color: var(--muted);
  white-space: nowrap;
  transition: color .15s, border-color .15s;
  display: flex;
  align-items: center;
  gap: 6px;
}}
.tab:hover {{ color: var(--text); }}
.tab.active {{ color: var(--accent); border-bottom-color: var(--accent); font-weight: 700; }}
.badge {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1px 7px;
  font-size: .72rem;
  font-variant-numeric: tabular-nums;
}}

/* Main */
main {{ padding: 24px 20px 60px; max-width: 1400px; margin: 0 auto; }}

/* League section */
.league-section {{ margin-bottom: 32px; }}
.league-header {{
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}}
.league-flag {{ font-size: 1.4rem; }}
.league-name {{ font-size: 1.05rem; font-weight: 700; }}
.league-meta {{ margin-left: auto; font-size: .75rem; color: var(--muted); }}

/* Match grid */
.matches-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}}

/* Match card */
.match-card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  transition: border-color .2s, background .2s, transform .15s;
}}
.match-card:hover {{
  background: var(--card-hover);
  border-color: var(--accent);
  transform: translateY(-2px);
}}
.match-meta {{
  display: flex;
  justify-content: space-between;
  font-size: .72rem;
  color: var(--muted);
  margin-bottom: 12px;
}}
.teams-row {{
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}}
.team {{
  flex: 1;
  font-weight: 700;
  font-size: .9rem;
}}
.away-team {{ text-align: right; }}
.xg-display {{
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  flex-shrink: 0;
}}
.xg {{
  font-size: 1.05rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}}
.home-xg {{ color: var(--accent); }}
.away-xg {{ color: var(--green); }}
.xg-sep {{ font-size: .6rem; color: var(--muted); }}
.outcome-badge {{
  font-size: .78rem;
  font-weight: 700;
  text-align: center;
  margin-bottom: 12px;
  letter-spacing: .02em;
}}

/* Prob bars */
.probs-section {{ margin-bottom: 12px; }}
.prob-row {{
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
}}
.prob-lbl {{
  font-size: .75rem;
  font-weight: 700;
  width: 14px;
  flex-shrink: 0;
  color: var(--muted);
}}
.bar-wrap {{
  flex: 1;
  background: var(--bg);
  border-radius: 4px;
  height: 7px;
  overflow: hidden;
}}
.bar {{
  height: 100%;
  border-radius: 4px;
  transition: width .5s ease;
}}
.prob-pct {{
  font-size: .75rem;
  font-weight: 700;
  width: 38px;
  text-align: right;
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}}

/* Secondaries */
.secondaries {{
  display: flex;
  gap: 0;
  border-top: 1px solid var(--border);
  padding-top: 10px;
  flex-wrap: wrap;
  gap: 6px;
}}
.sec-item {{
  display: flex;
  flex-direction: column;
  align-items: center;
  background: var(--bg);
  border-radius: 8px;
  padding: 5px 8px;
  min-width: 72px;
  flex: 1;
}}
.sec-lbl {{ font-size: .65rem; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; }}
.sec-val {{ font-size: .82rem; font-weight: 700; margin-top: 2px; font-variant-numeric: tabular-nums; }}
.score-tip {{ font-size: .76rem; }}

/* Empty state */
.empty-state {{
  text-align: center;
  padding: 60px 20px;
  color: var(--muted);
}}
.empty-state .icon {{ font-size: 3rem; margin-bottom: 14px; }}
.empty-state h2 {{ font-size: 1.1rem; font-weight: 700; margin-bottom: 8px; color: var(--text); }}

/* Footer */
footer {{
  text-align: center;
  padding: 24px;
  font-size: .75rem;
  color: var(--muted);
  border-top: 1px solid var(--border);
}}
footer a {{ color: var(--accent); text-decoration: none; }}

@media (max-width: 600px) {{
  header {{ padding: 12px 16px; }}
  main {{ padding: 16px 14px 40px; }}
  .league-meta {{ display: none; }}
  .matches-grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>

<header>
  <div class="logo">⚽</div>
  <h1 class="site-title">Football <em>Predictor</em></h1>
  <div class="header-meta">
    <strong>{total_preds} previsioni</strong> · aggiornato {generated_at}<br>
    Dixon-Coles + dati football-data.co.uk
  </div>
  <button class="theme-btn" onclick="toggleTheme()" title="Cambia tema">☀️/🌙</button>
</header>

<div class="tabs-wrap">
  {tabs_html}
</div>

<main id="main-content">
  <div id="leagues-container">
    {cards_html if cards_html else '<div class="empty-state"><div class="icon">🔍</div><h2>Nessuna partita trovata nei prossimi 14 giorni</h2><p>Le previsioni vengono aggiornate automaticamente ogni mattina.</p></div>'}
  </div>
</main>

<footer>
  Dati: <a href="https://football-data.co.uk" target="_blank">football-data.co.uk</a> ·
  <a href="https://football-data.org" target="_blank">football-data.org</a> ·
  Modello: Dixon-Coles (1997) ·
  <a href="predictions.json" target="_blank">JSON grezzo</a>
</footer>

<script>
function switchTab(league, btn) {{
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');

  document.querySelectorAll('.league-section').forEach(sec => {{
    if (league === 'all') {{
      sec.style.display = '';
    }} else {{
      sec.style.display = sec.dataset.league === league ? '' : 'none';
    }}
  }});
}}

function toggleTheme() {{
  const root = document.documentElement;
  const current = root.getAttribute('data-theme');
  root.setAttribute('data-theme', current === 'light' ? 'dark' : 'light');
  try {{ localStorage.setItem('fp-theme', root.getAttribute('data-theme')); }} catch(e) {{}}
}}

// Ripristina tema salvato
try {{
  const saved = localStorage.getItem('fp-theme');
  if (saved) document.documentElement.setAttribute('data-theme', saved);
}} catch(e) {{}}
</script>
</body>
</html>"""


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    os.makedirs("docs", exist_ok=True)
    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    log.info("🚀 Football Predictor — Generazione statica")
    log.info("=" * 55)

    all_data = {}

    for league_key, league_info in LEAGUES.items():
        log.info("\n⚽ %s", league_info["name"])

        # 1. CSV storici
        log.info("  ↓ Download CSV...")
        df = download_csv_data(league_key)
        if df.empty:
            log.warning("  Nessun CSV scaricato — salto")
            continue
        log.info("  Totale storico: %d partite", len(df))

        # 2. Fit Dixon-Coles
        log.info("  📐 Fitting Dixon-Coles...")
        t0 = time.time()
        dc = fit_dixon_coles(df)
        log.info("  Fit in %.1fs — home_adv=%.3f rho=%.3f squadre=%d",
                 time.time() - t0, dc["home_adv"], dc["rho"], len(dc["teams"]))

        # 3. Fixture prossime
        log.info("  📅 Fixture da football-data.org...")
        time.sleep(7)  # rate limit: 10 req/min
        fixtures = get_fixtures(league_info["code"])
        log.info("  %d partite nei prossimi %d giorni", len(fixtures), DAYS_AHEAD)

        # 4. Previsioni
        preds_list = []
        for fix in fixtures:
            # Prova short name e full name
            home_dc = (best_match(fix["home"],      dc["teams"]) or
                       best_match(fix["home_full"], dc["teams"]))
            away_dc = (best_match(fix["away"],      dc["teams"]) or
                       best_match(fix["away_full"], dc["teams"]))

            pred = predict_match(home_dc, away_dc, dc) if (home_dc and away_dc) else None
            if not pred:
                log.warning("  ⚠ Non trovato: %s / %s", fix["home"], fix["away"])

            preds_list.append({
                **fix,
                "home_dc":    home_dc,
                "away_dc":    away_dc,
                "prediction": pred,
            })

        all_data[league_key] = {
            "name":         league_info["name"],
            "flag":         league_info["flag"],
            "dc_fitted_at": dc["fitted_at"],
            "dc_n_matches": dc["n_matches"],
            "dc_teams":     dc["teams"],
            "fixtures":     preds_list,
        }

    # ── Output ──
    log.info("\n💾 Scrittura output...")

    # JSON (per API / debug)
    with open("docs/predictions.json", "w", encoding="utf-8") as f:
        json.dump({"generated_at": generated_at, "leagues": all_data},
                  f, ensure_ascii=False, indent=2)

    # HTML statico
    html = generate_html(all_data, generated_at)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)

    total = sum(
        sum(1 for fix in ld["fixtures"] if fix.get("prediction"))
        for ld in all_data.values()
    )
    log.info("✅ Generati docs/index.html e docs/predictions.json")
    log.info("   %d previsioni totali in %d campionati", total, len(all_data))


if __name__ == "__main__":
    main()
