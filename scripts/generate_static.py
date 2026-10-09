#!/usr/bin/env python3
"""
generate_static.py — Genera docs/index.html e docs/predictions.json con le previsioni
delle prossime partite dei 5 campionati.

Usa il Poisson-stack di models/stack.json: per ogni lega calcola le feature (Dixon-Coles
sui gol, sui tiri in porta e sugli xG Understat, pi-ratings) con i dati fino a oggi, applica
lo stack e ricava tutti i mercati (1X2, O/U, BTTS, clean sheet, risultati esatti) da una
sola matrice dei punteggi. In produzione si usa il modello "with_xg"; se Understat non
risponde o mancano gli xG di una squadra si passa automaticamente a "without_xg" (partita per
partita), e lo si scrive nel log e in predictions.json. La logica è in
predictions/stack_predictor.py, la stessa usata dall'app Flask.

Mercato (Step 6): se football-data.co.uk/fixtures.csv ha la partita, la card mostra anche le
probabilità dei bookmaker senza margine (metodo power) e la differenza modello - mercato per
1, X e 2, evidenziando gli scarti sopra i 5 punti percentuali. È solo un confronto: il modello
non usa le quote. Se la partita non c'è la card mostra solo il modello.

Monitoraggio (predictions/monitor.py): a ogni esecuzione le previsioni emesse vengono
aggiunte a docs/history.csv (insieme alle probabilità di mercato) e, per le partite giocate,
si aggiungono i risultati; la log-loss mobile di with_xg, without_xg e mercato compare in un
riquadro della pagina.

Scarica i CSV da football-data.co.uk e le fixture da football-data.org (serve
FOOTBALL_DATA_ORG_KEY nell'ambiente). Usato da GitHub Actions ogni giorno; in locale:
  python scripts/generate_static.py
"""
import html as _html
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import pandas as pd
import requests

from backtest import data
from predictions import monitor
from predictions import stack_predictor as sp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Configurazione ─────────────────────────────────────────────────────────────

FOOTBALL_DATA_ORG_KEY = os.getenv("FOOTBALL_DATA_ORG_KEY", "")

LEAGUES = {
    "serie_a":        {"code": "SA",  "name": "Serie A",        "flag": "🇮🇹"},
    "premier_league": {"code": "PL",  "name": "Premier League", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
    "bundesliga":     {"code": "BL1", "name": "Bundesliga",      "flag": "🇩🇪"},
    "la_liga":        {"code": "PD",  "name": "La Liga",         "flag": "🇪🇸"},
    "ligue_1":        {"code": "FL1", "name": "Ligue 1",         "flag": "🇫🇷"},
}

DAYS_AHEAD = 14
PROB_TOL = 1e-4   # tolleranza sulla somma delle probabilità 1X2 (arrotondamento a 5 decimali)


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


# ── Generazione HTML ───────────────────────────────────────────────────────────

def _prob_color(p: float) -> str:
    if p >= 0.50: return "#4ade80"
    if p >= 0.35: return "#fbbf24"
    return "#f87171"

def _bar(p: float, color: str) -> str:
    return (f'<div class="bar-wrap"><div class="bar" '
            f'style="width:{p*100:.1f}%;background:{color}"></div></div>')


MARKET_DIFF_PP = 5.0   # scarto modello - mercato oltre il quale la cella viene evidenziata


def _market_html(pred: dict, market) -> str:
    """Blocco "Mercato" della card: probabilità senza margine e differenza modello - mercato
    per 1, X e 2 (in punti percentuali). Vuoto se la partita non è in fixtures.csv."""
    if not market:
        return ""
    cells, flagged = [], False
    for lbl, key in (("1", "home"), ("X", "draw"), ("2", "away")):
        m = market[key]
        diff = (pred[f"prob_{key}"] - m) * 100
        hi = abs(round(diff, 1)) > MARKET_DIFF_PP
        flagged = flagged or hi
        cells.append(f'<div class="mkt-cell{" hi" if hi else ""}"><span class="mkt-lbl">{lbl}</span>'
                     f'<span class="mkt-val">{m * 100:.1f}%</span>'
                     f'<span class="mkt-diff">{diff:+.1f} pp</span></div>')
    flag = f'<span class="mkt-flag">scarto &gt; {MARKET_DIFF_PP:g} pp</span>' if flagged else ""
    return ('<div class="mkt-section"><div class="mkt-title"><span>Mercato (Δ = modello − mercato)</span>'
            f'{flag}</div><div class="mkt-grid">{"".join(cells)}</div></div>')


def _row_market(row: dict):
    """Probabilità di mercato all'emissione (solo fixtures.csv), oppure None."""
    if row.get("mkt_source") != "fixtures":
        return None
    return {"home": round(float(row["mkt_home"]), 5), "draw": round(float(row["mkt_draw"]), 5),
            "away": round(float(row["mkt_away"]), 5), "source": "fixtures"}


def _monitor_html(mon: dict) -> str:
    if mon["status"] != "ok":
        return (f'<section class="monitor"><h2>📈 Monitoraggio</h2>'
                f'<p class="mon-note">Dati in raccolta: {mon["tracked"]} previsioni registrate, '
                f'{mon["with_result"]} giocate con risultato ({mon["n"]} con with_xg, without_xg e '
                f'mercato disponibili). Il riquadro con la log-loss mobile (ultime {mon["window"]} partite) '
                f'compare da {mon["min_n"]} partite in poi.</p></section>')

    def cell(label, key, delta_key=None):
        delta = (f'<span class="mon-delta">{mon[delta_key]:+.4f} vs mercato</span>' if delta_key
                 else '<span class="mon-delta">riferimento</span>')
        return (f'<div class="mon-cell"><span class="mon-lbl">{label}</span>'
                f'<span class="mon-val">{mon[key]:.4f}</span>{delta}</div>')

    return (f'<section class="monitor"><h2>📈 Monitoraggio — log-loss mobile</h2>'
            f'<p class="mon-sub">Ultime {mon["n"]} partite giocate ({mon["since"]} → {mon["until"]}) con '
            f'with_xg, without_xg e mercato disponibili · più basso = meglio</p>'
            f'<div class="mon-grid">'
            f'{cell("with_xg", "with_xg", "delta_with_xg_vs_market")}'
            f'{cell("without_xg", "without_xg", "delta_without_xg_vs_market")}'
            f'{cell("Mercato", "market")}</div>'
            f'<p class="mon-note">Il mercato storicamente è più preciso del modello. '
            f'{mon["tracked"]} previsioni registrate, {mon["with_result"]} giocate con risultato.</p></section>')


def generate_html(leagues_data: dict, generated_at: str, mon: dict) -> str:
    # Conta totale previsioni
    total_preds = sum(
        sum(1 for f in ld["fixtures"] if f.get("prediction"))
        for ld in leagues_data.values()
    )

    monitor_html = _monitor_html(mon)

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
                       f'<span class="league-meta">Stack su {ld["dc_n_matches"]} partite recenti · {ld["dc_fitted_at"]}</span>'
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

            no_xg_tag = ("" if pred["model"] == "with_xg" else
                         ' · <span title="' + _html.escape(pred["fallback_reason"] or "") + '">senza xG</span>')
            top_score = pred["top_scores"][0]
            ts_str = f"{top_score[0]}–{top_score[1]} ({top_score[2]:.1f}%)"

            mkt_html = _market_html(pred, fix.get("market"))

            c = _prob_color
            cards_html += f"""
<div class="match-card">
  <div class="match-meta">
    <span>Giornata {fix['matchday']}</span>
    <span>{fix['date']} {fix['time']} UTC{no_xg_tag}</span>
  </div>
  <div class="teams-row">
    <div class="team home-team">{fix['home']}</div>
    <div class="xg-display">
      <span class="xg home-xg">{pred['exp_goals_home']}</span>
      <span class="xg-sep">gol attesi</span>
      <span class="xg away-xg">{pred['exp_goals_away']}</span>
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
  {mkt_html}
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
      <span class="sec-lbl">Risultato più probabile</span>
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

/* Mercato */
.mkt-section {{ border-top: 1px solid var(--border); padding-top: 10px; margin-bottom: 12px; }}
.mkt-title {{
  display: flex; justify-content: space-between; align-items: center; gap: 8px;
  font-size: .7rem; color: var(--muted); margin-bottom: 6px;
}}
.mkt-flag {{ color: var(--yellow); font-weight: 700; white-space: nowrap; }}
.mkt-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }}
.mkt-cell {{
  background: var(--bg); border: 1px solid transparent; border-radius: 8px;
  padding: 5px 8px; display: flex; flex-direction: column; align-items: center;
}}
.mkt-cell.hi {{ border-color: var(--yellow); background: rgba(251,191,36,.14); }}
.mkt-lbl {{ font-size: .65rem; color: var(--muted); font-weight: 700; }}
.mkt-val {{ font-size: .82rem; font-weight: 700; font-variant-numeric: tabular-nums; }}
.mkt-diff {{ font-size: .72rem; color: var(--muted); font-variant-numeric: tabular-nums; }}
.mkt-cell.hi .mkt-diff {{ color: var(--text); font-weight: 700; }}
.disclaimer {{
  font-size: .78rem; color: var(--muted); border-left: 3px solid var(--border);
  padding: 6px 12px; margin-top: 20px;
}}

/* Monitoraggio */
.monitor {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 18px;
  margin-bottom: 28px;
}}
.monitor h2 {{ font-size: 1rem; font-weight: 700; margin-bottom: 4px; }}
.mon-sub, .mon-note {{ font-size: .75rem; color: var(--muted); margin: 4px 0 10px; }}
.mon-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }}
.mon-cell {{ background: var(--bg); border-radius: 8px; padding: 10px 12px; display: flex; flex-direction: column; }}
.mon-lbl {{ font-size: .68rem; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; }}
.mon-val {{ font-size: 1.25rem; font-weight: 800; font-variant-numeric: tabular-nums; }}
.mon-delta {{ font-size: .72rem; color: var(--muted); font-variant-numeric: tabular-nums; }}

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
    Poisson-stack (Dixon-Coles + tiri in porta + pi-ratings + xG Understat)
  </div>
  <button class="theme-btn" onclick="toggleTheme()" title="Cambia tema">☀️/🌙</button>
</header>

<div class="tabs-wrap">
  {tabs_html}
</div>

<main id="main-content">
  {monitor_html}
  <div id="leagues-container">
    {cards_html if cards_html else '<div class="empty-state"><div class="icon">🔍</div><h2>Nessuna partita trovata nei prossimi 14 giorni</h2><p>Le previsioni vengono aggiornate automaticamente ogni mattina.</p></div>'}
  </div>
  <p class="disclaimer">Storicamente il mercato è più preciso del modello (log-loss 0,973 contro 0,983): le differenze indicano dove il modello e i bookmaker non sono d'accordo, non scommesse sicure</p>
</main>

<footer>
  Dati: <a href="https://football-data.co.uk" target="_blank">football-data.co.uk</a> ·
  <a href="https://football-data.org" target="_blank">football-data.org</a> ·
  xG: <a href="https://understat.com" target="_blank">understat.com</a> · Modello: Poisson-stack su Dixon-Coles (1997) ·
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


# ── Verifica dell'output ───────────────────────────────────────────────────────

def validate_output(all_data: dict) -> list:
    """Controlli di coerenza sull'output: ritorna l'elenco dei problemi trovati."""
    problems = []
    for lk, ld in all_data.items():
        for fix in ld["fixtures"]:
            tag = f"{lk}: {fix['home']} - {fix['away']}"
            p = fix.get("prediction")
            if not p:
                problems.append(f"{tag}: nessuna previsione")
                continue
            if p.get("model") not in ("with_xg", "without_xg"):
                problems.append(f"{tag}: modello non indicato")
            if p.get("model") == "without_xg" and not p.get("fallback_reason"):
                problems.append(f"{tag}: without_xg senza motivo del ripiego")
            total = p["prob_home"] + p["prob_draw"] + p["prob_away"]
            if abs(total - 1) > PROB_TOL:
                problems.append(f"{tag}: 1X2 non somma a 1 ({total:.5f})")
            vals = [v for k, v in p.items() if k.startswith(("prob_", "exp_goals"))]
            if any(v != v or v < 0 for v in vals):
                problems.append(f"{tag}: valori non validi")
            if not (p["prob_o15"] >= p["prob_o25"] >= p["prob_o35"]):
                problems.append(f"{tag}: Over non monotoni")
            if any(v > 1 for k, v in p.items() if k.startswith("prob_")):
                problems.append(f"{tag}: probabilità > 1")
            mk = fix.get("market")
            if mk and (abs(mk["home"] + mk["draw"] + mk["away"] - 1) > PROB_TOL
                       or min(mk["home"], mk["draw"], mk["away"]) <= 0):
                problems.append(f"{tag}: probabilità di mercato non valide")
    return problems


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    os.makedirs("docs", exist_ok=True)
    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    today = pd.Timestamp(datetime.utcnow().date())

    log.info("Football Predictor — Generazione statica (Poisson-stack)")
    log.info("=" * 55)

    model = sp.load_stack()
    log.info("Stack allenato %s - with_xg: %s partite (rho=%.4f), without_xg: %s partite (rho=%.4f)",
             model["meta"].get("trained_at"),
             model["models"]["with_xg"]["meta"]["n_train"], model["models"]["with_xg"]["rho"],
             model["models"]["without_xg"]["meta"]["n_train"], model["models"]["without_xg"]["rho"])

    log.info("Storico football-data.co.uk (2012/13 -> oggi)...")
    df = data.load_matches(verbose=False)
    log.info("  %d partite", len(df))

    log.info("xG Understat (ultime stagioni)...")
    df, xg_error = sp.attach_recent_xg(df)
    if xg_error:
        log.warning("  RIPIEGO: %s -> modello without_xg per tutte le partite", xg_error)
    else:
        log.info("  xG caricati per %d partite", int(df.xg_h.notna().sum()))

    history_path = os.path.join("docs", "history.csv")
    history = monitor.load_history(history_path)
    fx_market = monitor.fixtures_market()
    log.info("Quote di mercato da fixtures.csv: %d partite dei 5 campionati", len(fx_market))
    new_rows = []

    all_data = {}

    for league_key, league_info in LEAGUES.items():
        log.info("\n%s", league_info["name"])

        g = df[df.Division == sp.CSV_CODE[league_key]]
        t0 = time.time()
        state = sp.LeagueState(g, today, xg_error=xg_error)
        log.info("  Feature calcolate in %.1fs - %d partite nella finestra, %d squadre",
                 time.time() - t0, state.n_matches, len(state.teams))

        log.info("  Fixture da football-data.org...")
        time.sleep(7)  # rate limit: 10 req/min
        fixtures = get_fixtures(league_info["code"])
        log.info("  %d partite nei prossimi %d giorni", len(fixtures), DAYS_AHEAD)

        pairs, names = [], []
        for fix in fixtures:
            h = state.resolve(fix["home"], fix["home_full"])
            a = state.resolve(fix["away"], fix["away_full"])
            for n, r in ((fix["home"], h), (fix["away"], a)):
                if r is None:
                    log.warning("  Squadra sconosciuta '%s': trattata come neopromossa", n)
            pairs.append((h or fix["home"], a or fix["away"]))
            names.append((h, a))

        preds = sp.predict_pairs(state, model, pairs)
        probs = sp.probs_by_model(state, model, pairs)
        n0 = len(new_rows)
        for fix, (h, a), pred, pr in zip(fixtures, names, preds, probs):
            new_rows.append(monitor.make_row(league_key, {**fix, "home_dc": h, "away_dc": a}, pred, pr,
                                             today.strftime("%Y-%m-%d")))
        league_rows = new_rows[n0:]
        monitor.attach_fixture_market(league_rows, fx_market)
        preds_list = [{**fix, "home_dc": h, "away_dc": a, "new_team": h is None or a is None,
                       "prediction": pred, "market": _row_market(row)}
                      for fix, (h, a), pred, row in zip(fixtures, names, preds, league_rows)]

        all_data[league_key] = {
            "name":         league_info["name"],
            "flag":         league_info["flag"],
            "dc_fitted_at": state.fitted_at,
            "dc_n_matches": state.n_matches,
            "dc_teams":     state.teams,
            "fixtures":     preds_list,
        }

    # ── Storico e monitoraggio ──
    history = monitor.upsert(history, new_rows, today)
    history = monitor.fill_results(history, df, today)
    monitor.save_history(history, history_path)
    mon = monitor.rolling_logloss(history)
    log.info("Storico: %d partite registrate, %d con risultato, %d con quote di mercato",
             len(history), int(history.result.notna().sum()), int(history.mkt_home.notna().sum()))
    if mon["status"] == "ok":
        log.info("Log-loss mobile (ultime %d): with_xg=%.4f without_xg=%.4f mercato=%.4f",
                 mon["n"], mon["with_xg"], mon["without_xg"], mon["market"])
    else:
        log.info("Monitoraggio in raccolta: %d partite con tutti i modelli e il mercato (servono %d)",
                 mon["n"], mon["min_n"])

    # ── Output ──
    log.info("\nScrittura output...")

    counts = {"with_xg": 0, "without_xg": 0}
    for ld in all_data.values():
        for fix in ld["fixtures"]:
            counts[fix["prediction"]["model"]] += 1
    log.info("   Modello usato: with_xg=%d, without_xg=%d", counts["with_xg"], counts["without_xg"])
    if counts["without_xg"]:
        reasons = sorted({fix["prediction"]["fallback_reason"] for ld in all_data.values()
                          for fix in ld["fixtures"] if fix["prediction"]["fallback_reason"]})
        log.warning("   %d partite su %d con ripiego without_xg (dettaglio per partita in "
                    "docs/predictions.json). Motivi: %s",
                    counts["without_xg"], sum(counts.values()), " | ".join(reasons))

    with open("docs/predictions.json", "w", encoding="utf-8") as f:
        json.dump({"generated_at": generated_at,
                   "model": {"name": "Poisson-stack (with_xg, ripiego without_xg)",
                             "trained_at": model["meta"].get("trained_at"),
                             "n_train": {k: v["meta"]["n_train"] for k, v in model["models"].items()}},
                   "xg_status": {"available": xg_error is None, "error": xg_error},
                   "model_counts": counts,
                   "monitor": mon,
                   "leagues": all_data},
                  f, ensure_ascii=False, indent=2)

    html = generate_html(all_data, generated_at, mon)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)

    total = sum(len(ld["fixtures"]) for ld in all_data.values())
    log.info("Generati docs/index.html e docs/predictions.json")
    log.info("   %d previsioni totali in %d campionati", total, len(all_data))

    problems = validate_output(all_data)
    if problems:
        for pr in problems:
            log.error("  X %s", pr)
        sys.exit(1)
    log.info("   Verifica OK: tutte le partite hanno una previsione e le probabilità sommano a 1")


if __name__ == "__main__":
    main()
