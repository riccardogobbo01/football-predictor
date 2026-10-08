#!/usr/bin/env python3
"""
Football Predictor — Web Dashboard
Avvia con: python app.py
Poi apri: http://localhost:5000
"""
import json
import threading
import logging
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, render_template_string

app = Flask(__name__)
log = logging.getLogger("app")

# ── Stato aggiornamento ───────────────────────────────────────────────────────

_update_lock = threading.Lock()
_update_status = {"running": False, "step": "", "done": False, "error": ""}


def _run_update(source="all"):
    global _update_status
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(__file__))
        from config import LEAGUES

        steps = {
            "fixtures": ("📅 Calendario (football-data.org)...", _step_fixtures),
            "xg":       ("📊 xG Understat...",                   _step_xg),
            "elo":      ("📈 ELO ratings (ClubElo)...",          _step_elo),
            "weather":  ("🌤 Meteo stadi...",                    _step_weather),
            "stats":    ("📋 Statistiche aggregate...",           _step_stats),
        }
        if source == "all":
            run_steps = list(steps.values())
        elif source in steps:
            run_steps = [steps[source]]
        else:
            run_steps = list(steps.values())

        for label, fn in run_steps:
            with _update_lock:
                _update_status["step"] = label
            fn()

        with _update_lock:
            _update_status.update({"running": False, "done": True,
                                   "step": "✅ Aggiornamento completato!"})
    except Exception as e:
        with _update_lock:
            _update_status.update({"running": False, "done": True,
                                   "step": "", "error": str(e)})


def _step_fixtures():
    try:
        from collectors.football_data_org import FootballDataOrgCollector
        from config import LEAGUES
        c = FootballDataOrgCollector()
        for lk in LEAGUES:
            try:
                c.sync_results(lk)
                c.sync_matches(lk, days_ahead=14)
            except Exception:
                pass
    except RuntimeError:
        pass
    # CSV sempre disponibile
    from collectors.football_data_csv import FootballDataCsvCollector
    FootballDataCsvCollector().update_current_season()


def _step_xg():
    from collectors.understat import UnderstatCollector
    UnderstatCollector().update_current_season()


def _step_elo():
    from collectors.clubelo import ClubEloCollector
    ClubEloCollector().update_all()


def _step_weather():
    from collectors.open_meteo import OpenMeteoCollector
    OpenMeteoCollector().update_all()


def _step_stats():
    from collectors.football_data_csv import FootballDataCsvCollector
    c = FootballDataCsvCollector()
    c.rebuild_referee_stats()
    c.rebuild_team_season_stats()


# ── API ───────────────────────────────────────────────────────────────────────

@app.route("/api/update", methods=["POST"])
def api_update():
    from flask import request
    source = request.json.get("source", "all") if request.is_json else "all"
    with _update_lock:
        if _update_status["running"]:
            return jsonify({"ok": False, "msg": "Aggiornamento già in corso"})
        _update_status.update({"running": True, "done": False,
                               "step": "⏳ Avvio...", "error": ""})
    t = threading.Thread(target=_run_update, args=(source,), daemon=True)
    t.start()
    return jsonify({"ok": True})


@app.route("/api/update/status")
def api_update_status():
    with _update_lock:
        return jsonify(dict(_update_status))


@app.route("/api/fixtures")
def api_fixtures():
    from flask import request
    from db import get_conn
    league = request.args.get("league", "")
    days   = int(request.args.get("days", 14))

    conn = get_conn()
    now  = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    end  = (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")

    q = """
        SELECT m.match_date, m.round,
               ht.name AS home_team, at.name AS away_team,
               m.league_key, m.id,
               m.home_goals, m.away_goals, m.status
        FROM matches m
        JOIN teams ht ON ht.id = m.home_team_id
        JOIN teams at ON at.id = m.away_team_id
        WHERE m.match_date >= ? AND m.match_date <= ?
    """
    params = [now, end]
    if league:
        q += " AND m.league_key = ?"
        params.append(league)
    q += " ORDER BY m.match_date, m.league_key"

    rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    conn.close()
    return jsonify(rows)


@app.route("/api/predict")
def api_predict():
    from flask import request
    home       = request.args.get("home", "")
    away       = request.args.get("away", "")
    league_key = request.args.get("league", "serie_a")
    date       = request.args.get("date", datetime.utcnow().strftime("%Y-%m-%d"))

    if not home or not away:
        return jsonify({"error": "home e away richiesti"}), 400

    try:
        from features.engineer import FeatureEngineer
        from predictions.dixon_coles import fit, load_params, predict as dc_predict

        dc = load_params(league_key)
        if dc is None:
            dc = fit(league_key)

        eng      = FeatureEngineer()
        features = eng.build(home, away, league_key, date)
        pred     = dc_predict(home, away, features, dc, league_key)

        # Gol e probabilità: stesso Poisson-stack della pagina statica
        # (predictions/stack_predictor.py). `pred` resta solo per le statistiche
        # secondarie (tiri, corner, cartellini) e il contesto.
        from predictions import stack_predictor
        sp = stack_predictor.predict_single(league_key, home, away)

        f = features
        return jsonify({
            "home_team":   pred.home_team,
            "away_team":   pred.away_team,
            "home_xg":     sp["exp_goals_home"],   # chiave storica: sono gol attesi, non xG
            "away_xg":     sp["exp_goals_away"],
            "prob_home":   round(sp["prob_home"], 3),
            "prob_draw":   round(sp["prob_draw"], 3),
            "prob_away":   round(sp["prob_away"], 3),
            "prob_o05":    round(sp["prob_o05"], 3),
            "prob_o15":    round(sp["prob_o15"], 3),
            "prob_o25":    round(sp["prob_o25"], 3),
            "prob_o35":    round(sp["prob_o35"], 3),
            "prob_btts":   round(sp["prob_btts"], 3),
            "prob_cs_home": round(sp["prob_cs_home"], 3),
            "prob_cs_away": round(sp["prob_cs_away"], 3),
            "top_scores":  [[x, y, p / 100] for x, y, p in sp["top_scores"][:5]],
            "stack_model": sp["model"],             # with_xg, oppure without_xg se xG non disponibili
            "stack_fallback_reason": sp["fallback_reason"],
            "exp_shots":   pred.exp_shots,
            "exp_corners": pred.exp_corners,
            "exp_yellow":  pred.exp_yellow,
            "context": {
                "home_elo":       f.home_elo,
                "away_elo":       f.away_elo,
                "elo_diff":       f.elo_diff,
                "home_form":      round(f.home_form_5, 2),
                "away_form":      round(f.away_form_5, 2),
                "home_rest":      f.home_rest_days,
                "away_rest":      f.away_rest_days,
                "weather_impact": round(f.weather_impact, 2),
                "h2h_advantage":  round(f.h2h_advantage, 2),
                "market_ph":      round(f.market_ph, 3),
                "market_pd":      round(f.market_pd, 3),
                "market_pa":      round(f.market_pa, 3),
            }
        })
    except Exception as e:
        log.exception("Errore previsione")
        return jsonify({"error": str(e)}), 500


# ── Dashboard HTML ────────────────────────────────────────────────────────────

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Football Predictor</title>
<style>
  :root {
    --bg: #0f1117;
    --surface: #1a1d27;
    --card: #21253a;
    --card-hover: #272b42;
    --border: #2e3350;
    --accent: #4f8ef7;
    --accent2: #22c55e;
    --text: #e8eaf0;
    --muted: #8892aa;
    --red: #f87171;
    --yellow: #fbbf24;
    --green: #4ade80;
    --radius: 12px;
    --shadow: 0 4px 24px rgba(0,0,0,.45);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: system-ui,sans-serif; min-height: 100vh; }

  /* ── Header ── */
  header { display: flex; align-items: center; gap: 16px; padding: 18px 24px;
    background: var(--surface); border-bottom: 1px solid var(--border); flex-wrap: wrap; }
  header h1 { font-size: 1.35rem; font-weight: 700; letter-spacing: -.3px; }
  header h1 span { color: var(--accent); }
  .header-right { display: flex; gap: 10px; align-items: center; margin-left: auto; }

  /* ── Buttons ── */
  .btn { padding: 9px 20px; border-radius: 8px; border: none; cursor: pointer;
    font-size: .9rem; font-weight: 600; display: flex; align-items: center; gap: 7px;
    transition: opacity .15s, transform .1s; }
  .btn:active { transform: scale(.97); }
  .btn-primary { background: var(--accent); color: #fff; }
  .btn-primary:hover { opacity: .88; }
  .btn-ghost { background: transparent; color: var(--muted); border: 1px solid var(--border); }
  .btn-ghost:hover { color: var(--text); border-color: var(--accent); }
  .btn:disabled { opacity: .45; cursor: default; }

  /* ── Spinner ── */
  .spinner { width: 16px; height: 16px; border: 2px solid rgba(255,255,255,.3);
    border-top-color: #fff; border-radius: 50%; animation: spin .7s linear infinite; display: none; }
  .spinner.active { display: block; }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Update status bar ── */
  #status-bar { background: var(--surface); border-bottom: 1px solid var(--border);
    padding: 8px 24px; font-size: .82rem; color: var(--muted); display: none;
    align-items: center; gap: 10px; }
  #status-bar.visible { display: flex; }
  #status-bar .status-icon { font-size: 1rem; }

  /* ── League tabs ── */
  .tabs { display: flex; gap: 4px; padding: 16px 24px 0; flex-wrap: wrap; }
  .tab { padding: 8px 16px; border-radius: 8px 8px 0 0; border: 1px solid transparent;
    cursor: pointer; font-size: .85rem; color: var(--muted); transition: all .15s; }
  .tab:hover { color: var(--text); }
  .tab.active { color: var(--accent); border-color: var(--border); border-bottom-color: var(--bg);
    background: var(--bg); font-weight: 600; }

  /* ── Fixtures grid ── */
  main { padding: 0 24px 40px; }
  .league-divider { font-size: .78rem; color: var(--muted); padding: 16px 0 8px;
    text-transform: uppercase; letter-spacing: .06em; border-bottom: 1px solid var(--border); margin-bottom: 12px; }
  .fixtures-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; margin-bottom: 24px; }

  .match-card { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius);
    padding: 16px; cursor: pointer; transition: all .18s; position: relative; overflow: hidden; }
  .match-card:hover { background: var(--card-hover); border-color: var(--accent); box-shadow: var(--shadow); transform: translateY(-1px); }
  .match-card.selected { border-color: var(--accent); box-shadow: 0 0 0 2px rgba(79,142,247,.25); }

  .match-date { font-size: .75rem; color: var(--muted); margin-bottom: 10px; display: flex; justify-content: space-between; }
  .match-teams { display: flex; align-items: center; gap: 10px; }
  .team-name { font-weight: 700; font-size: .95rem; flex: 1; }
  .team-name.away { text-align: right; }
  .vs { color: var(--muted); font-size: .8rem; font-weight: 500; flex-shrink: 0; }
  .match-round { font-size: .72rem; color: var(--muted); margin-top: 8px; }

  /* ── Empty state ── */
  .empty { padding: 60px 0; text-align: center; color: var(--muted); }
  .empty-icon { font-size: 2.5rem; margin-bottom: 12px; }

  /* ── Prediction panel (slide-in from right) ── */
  #pred-panel { position: fixed; top: 0; right: -520px; width: 520px; max-width: 100vw;
    height: 100vh; background: var(--surface); border-left: 1px solid var(--border);
    z-index: 100; overflow-y: auto; transition: right .28s cubic-bezier(.4,0,.2,1);
    box-shadow: -8px 0 40px rgba(0,0,0,.6); }
  #pred-panel.open { right: 0; }
  .panel-header { position: sticky; top: 0; background: var(--surface);
    padding: 16px 20px; border-bottom: 1px solid var(--border); z-index: 1;
    display: flex; align-items: center; gap: 10px; }
  .panel-close { background: none; border: none; color: var(--muted); cursor: pointer;
    font-size: 1.3rem; padding: 4px; margin-left: auto; line-height: 1; }
  .panel-close:hover { color: var(--text); }
  .panel-body { padding: 20px; }

  /* ── Prediction content ── */
  .pred-matchup { text-align: center; margin-bottom: 20px; }
  .pred-matchup .teams { font-size: 1.15rem; font-weight: 700; margin-bottom: 4px; }
  .pred-matchup .league-date { font-size: .8rem; color: var(--muted); }

  .pred-xg { display: flex; justify-content: center; gap: 40px; margin: 16px 0;
    padding: 14px; background: var(--card); border-radius: var(--radius); }
  .xg-side { text-align: center; }
  .xg-value { font-size: 2rem; font-weight: 800; color: var(--accent); }
  .xg-label { font-size: .72rem; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; }
  .xg-team { font-size: .82rem; font-weight: 600; margin-top: 4px; }

  .section-title { font-size: .78rem; color: var(--muted); text-transform: uppercase;
    letter-spacing: .07em; margin: 18px 0 10px; }

  /* ── Probability bars ── */
  .prob-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
  .prob-label { font-size: .82rem; width: 130px; flex-shrink: 0; }
  .prob-bar-wrap { flex: 1; background: var(--card); border-radius: 4px; height: 8px; overflow: hidden; }
  .prob-bar { height: 100%; border-radius: 4px; transition: width .4s ease; }
  .prob-pct { font-size: .82rem; font-weight: 700; width: 46px; text-align: right; flex-shrink: 0; }

  /* ── Top scores ── */
  .scores-grid { display: flex; flex-wrap: wrap; gap: 8px; }
  .score-chip { background: var(--card); border: 1px solid var(--border); border-radius: 8px;
    padding: 8px 14px; text-align: center; min-width: 72px; }
  .score-chip.top { border-color: var(--accent); background: rgba(79,142,247,.1); }
  .score-chip .score { font-size: 1.1rem; font-weight: 700; }
  .score-chip .pct { font-size: .72rem; color: var(--muted); }

  /* ── Stats tiles ── */
  .stats-tiles { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
  .stat-tile { background: var(--card); border-radius: var(--radius); padding: 12px;
    text-align: center; }
  .stat-tile .val { font-size: 1.5rem; font-weight: 800; }
  .stat-tile .lbl { font-size: .72rem; color: var(--muted); margin-top: 2px; }

  /* ── Context ── */
  .context-row { display: flex; justify-content: space-between; align-items: center;
    padding: 7px 0; border-bottom: 1px solid var(--border); font-size: .82rem; }
  .context-row:last-child { border: none; }
  .context-label { color: var(--muted); }
  .context-val { font-weight: 600; }

  /* ── Overlay ── */
  #overlay { position: fixed; inset: 0; background: rgba(0,0,0,.45); z-index: 99;
    display: none; backdrop-filter: blur(2px); }
  #overlay.visible { display: block; }

  /* ── Loading skeleton ── */
  .skeleton { background: linear-gradient(90deg, var(--card) 25%, var(--card-hover) 50%, var(--card) 75%);
    background-size: 200% 100%; animation: shimmer 1.4s infinite; border-radius: 6px; height: 14px; }
  @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

  @media (max-width: 600px) {
    header { padding: 14px 16px; }
    main { padding: 0 16px 40px; }
    .tabs { padding: 12px 16px 0; }
    #pred-panel { width: 100vw; }
    .stats-tiles { grid-template-columns: 1fr 1fr; }
  }
</style>
</head>
<body>

<header>
  <div style="font-size:1.5rem">⚽</div>
  <h1>Football <span>Predictor</span></h1>
  <div class="header-right">
    <select id="days-select" class="btn btn-ghost" style="padding:8px 12px">
      <option value="7">7 giorni</option>
      <option value="14" selected>14 giorni</option>
      <option value="30">30 giorni</option>
    </select>
    <button class="btn btn-primary" id="update-btn" onclick="startUpdate()">
      <div class="spinner" id="update-spinner"></div>
      <span id="update-label">🔄 Aggiorna Dati</span>
    </button>
  </div>
</header>

<div id="status-bar">
  <span class="status-icon">⏳</span>
  <span id="status-text">Aggiornamento in corso...</span>
</div>

<div class="tabs" id="tabs"></div>
<main id="main-content">
  <div class="empty"><div class="empty-icon">📅</div><p>Carico le partite...</p></div>
</main>

<!-- Prediction panel -->
<div id="overlay" onclick="closePanel()"></div>
<div id="pred-panel">
  <div class="panel-header">
    <span style="font-size:1.1rem">🔮</span>
    <strong>Previsione partita</strong>
    <button class="panel-close" onclick="closePanel()">✕</button>
  </div>
  <div class="panel-body" id="panel-body">
    <div class="skeleton" style="height:60px;margin-bottom:12px"></div>
    <div class="skeleton" style="height:100px;margin-bottom:12px"></div>
    <div class="skeleton" style="height:200px"></div>
  </div>
</div>

<script>
const LEAGUES = {
  all:                  '🌍 Tutte',
  serie_a:              '🇮🇹 Serie A',
  premier_league:       '🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League',
  bundesliga:           '🇩🇪 Bundesliga',
  la_liga:              '🇪🇸 La Liga',
  ligue_1:              '🇫🇷 Ligue 1',
  champions_league:     '⭐ Champions League',
  europa_league:        '🟠 Europa League',
  conference_league:    '🔵 Conference League',
};

let currentLeague = 'all';
let currentDays   = 14;
let allFixtures   = [];
let updateTimer   = null;

// ── Tabs ──────────────────────────────────────────────────────────────────────
function renderTabs() {
  const tabs = document.getElementById('tabs');
  tabs.innerHTML = Object.entries(LEAGUES).map(([k,v]) =>
    `<div class="tab ${k===currentLeague?'active':''}" onclick="selectLeague('${k}')">${v}</div>`
  ).join('');
}

function selectLeague(lk) {
  currentLeague = lk;
  renderTabs();
  renderFixtures();
}

// ── Fixtures ──────────────────────────────────────────────────────────────────
async function loadFixtures() {
  const days = document.getElementById('days-select').value;
  const url  = currentLeague === 'all'
    ? `/api/fixtures?days=${days}`
    : `/api/fixtures?league=${currentLeague}&days=${days}`;
  const res  = await fetch(url);
  allFixtures = await res.json();
  renderFixtures();
}

function renderFixtures() {
  const main = document.getElementById('main-content');
  const filtered = currentLeague === 'all'
    ? allFixtures
    : allFixtures.filter(m => m.league_key === currentLeague);

  if (!filtered.length) {
    main.innerHTML = `<div class="empty">
      <div class="empty-icon">📅</div>
      <p>Nessuna partita trovata nei prossimi ${document.getElementById('days-select').value} giorni.</p>
      <p style="margin-top:8px;font-size:.85rem">Clicca <strong>Aggiorna Dati</strong> per scaricare il calendario.</p>
    </div>`;
    return;
  }

  // Raggruppa per lega
  const byLeague = {};
  for (const m of filtered) {
    if (!byLeague[m.league_key]) byLeague[m.league_key] = [];
    byLeague[m.league_key].push(m);
  }

  let html = '';
  for (const [lk, matches] of Object.entries(byLeague)) {
    const leagueName = LEAGUES[lk] || lk.replace(/_/g,' ');
    if (currentLeague === 'all') {
      html += `<div class="league-divider">${leagueName} — ${matches.length} partite</div>`;
    }
    html += '<div class="fixtures-grid">';
    for (const m of matches) {
      const dt   = m.match_date ? m.match_date.slice(0,16) : '?';
      const day  = dt.slice(0,10);
      const hour = dt.length > 10 ? dt.slice(11,16) : '';
      const rnd  = m.round ? `<div class="match-round">${m.round}</div>` : '';
      html += `<div class="match-card" onclick="openPredict('${esc(m.home_team)}','${esc(m.away_team)}','${m.league_key}','${day}')">
        <div class="match-date"><span>${day}</span><span>${hour}</span></div>
        <div class="match-teams">
          <div class="team-name">${m.home_team}</div>
          <div class="vs">vs</div>
          <div class="team-name away">${m.away_team}</div>
        </div>
        ${rnd}
      </div>`;
    }
    html += '</div>';
  }
  main.innerHTML = html;
}

function esc(s) { return s.replace(/'/g,"\\'"); }

// ── Update ────────────────────────────────────────────────────────────────────
async function startUpdate() {
  const btn     = document.getElementById('update-btn');
  const spinner = document.getElementById('update-spinner');
  const label   = document.getElementById('update-label');
  const bar     = document.getElementById('status-bar');
  btn.disabled  = true;
  spinner.classList.add('active');
  label.textContent = 'Aggiornamento...';
  bar.classList.add('visible');

  await fetch('/api/update', { method:'POST', headers:{'Content-Type':'application/json'}, body:'{}' });
  updateTimer = setInterval(pollStatus, 1800);
}

async function pollStatus() {
  const res    = await fetch('/api/update/status');
  const data   = await res.json();
  const text   = document.getElementById('status-text');
  const bar    = document.getElementById('status-bar');
  const btn    = document.getElementById('update-btn');
  const spinner= document.getElementById('update-spinner');
  const label  = document.getElementById('update-label');

  text.textContent = data.step || (data.error ? '✗ ' + data.error : '');

  if (!data.running && data.done) {
    clearInterval(updateTimer);
    btn.disabled = false;
    spinner.classList.remove('active');
    label.textContent = '🔄 Aggiorna Dati';
    setTimeout(() => bar.classList.remove('visible'), 4000);
    loadFixtures();
  }
}

// ── Prediction panel ──────────────────────────────────────────────────────────
async function openPredict(home, away, league, date) {
  document.getElementById('pred-panel').classList.add('open');
  document.getElementById('overlay').classList.add('visible');
  document.getElementById('panel-body').innerHTML = `
    <div style="text-align:center;padding:30px;color:var(--muted)">
      <div style="font-size:2rem;margin-bottom:10px">⏳</div>
      Calcolo previsione...
    </div>`;

  const url = `/api/predict?home=${encodeURIComponent(home)}&away=${encodeURIComponent(away)}&league=${league}&date=${date}`;
  const res = await fetch(url);
  const p   = await res.json();

  if (p.error) {
    document.getElementById('panel-body').innerHTML =
      `<div style="color:var(--red);padding:20px">✗ ${p.error}</div>`;
    return;
  }

  const leagueName = LEAGUES[league] || league;
  const bar = (v, color) => `<div class="prob-bar" style="width:${(v*100).toFixed(1)}%;background:${color}"></div>`;
  const pct = v => (v*100).toFixed(1) + '%';

  const c1x2Color = v => v > .5 ? 'var(--green)' : v > .33 ? 'var(--yellow)' : 'var(--red)';
  const overColor = v => v > .6 ? 'var(--green)' : v > .4 ? 'var(--yellow)' : 'var(--red)';

  const topScores = (p.top_scores || []).map((s,i) =>
    `<div class="score-chip ${i===0?'top':''}">
      <div class="score">${s[0]}–${s[1]}</div>
      <div class="pct">${pct(s[2])}</div>
    </div>`
  ).join('');

  const ctx = p.context || {};
  const ctxRows = [
    ctx.home_elo && ctx.away_elo ? ['ELO', `${ctx.home_elo.toFixed(0)} · ${ctx.away_elo.toFixed(0)} (diff ${ctx.elo_diff > 0 ? '+' : ''}${ctx.elo_diff.toFixed(0)})`] : null,
    ['Forma [0-1]', `${ctx.home_form?.toFixed(2)} · ${ctx.away_form?.toFixed(2)}`],
    ['Riposo (giorni)', `${ctx.home_rest} · ${ctx.away_rest}`],
    ctx.weather_impact > 0.05 ? ['☁ Meteo', `Impatto ${(ctx.weather_impact*100).toFixed(0)}%`] : null,
    ctx.h2h_advantage !== 0 ? ['H2H', ctx.h2h_advantage > 0 ? `Vantaggio casa (${Math.abs(ctx.h2h_advantage).toFixed(2)})` : `Vantaggio ospite (${Math.abs(ctx.h2h_advantage).toFixed(2)})`] : null,
    ctx.market_ph > 0 ? ['Quote mercato', `${pct(ctx.market_ph)} · ${pct(ctx.market_pd)} · ${pct(ctx.market_pa)}`] : null,
  ].filter(Boolean);

  document.getElementById('panel-body').innerHTML = `
    <div class="pred-matchup">
      <div class="teams">${p.home_team} vs ${p.away_team}</div>
      <div class="league-date">${leagueName} · ${date}</div>
    </div>

    <div class="pred-xg">
      <div class="xg-side">
        <div class="xg-value">${p.home_xg.toFixed(2)}</div>
        <div class="xg-label">Gol attesi</div>
        <div class="xg-team">${p.home_team}</div>
      </div>
      <div style="color:var(--muted);font-weight:700;font-size:1.1rem;align-self:center">—</div>
      <div class="xg-side">
        <div class="xg-value" style="color:var(--accent2)">${p.away_xg.toFixed(2)}</div>
        <div class="xg-label">Gol attesi</div>
        <div class="xg-team">${p.away_team}</div>
      </div>
    </div>

    <div class="section-title">📊 Risultato</div>
    <div class="prob-row">
      <div class="prob-label">1 – ${p.home_team.slice(0,16)}</div>
      <div class="prob-bar-wrap">${bar(p.prob_home, c1x2Color(p.prob_home))}</div>
      <div class="prob-pct" style="color:${c1x2Color(p.prob_home)}">${pct(p.prob_home)}</div>
    </div>
    <div class="prob-row">
      <div class="prob-label">X – Pareggio</div>
      <div class="prob-bar-wrap">${bar(p.prob_draw, c1x2Color(p.prob_draw))}</div>
      <div class="prob-pct" style="color:${c1x2Color(p.prob_draw)}">${pct(p.prob_draw)}</div>
    </div>
    <div class="prob-row">
      <div class="prob-label">2 – ${p.away_team.slice(0,16)}</div>
      <div class="prob-bar-wrap">${bar(p.prob_away, c1x2Color(p.prob_away))}</div>
      <div class="prob-pct" style="color:${c1x2Color(p.prob_away)}">${pct(p.prob_away)}</div>
    </div>

    <div class="section-title">📈 Over / Under</div>
    ${['Over 0.5','Over 1.5','Over 2.5','Over 3.5'].map((l,i) => {
      const v = [p.prob_o05,p.prob_o15,p.prob_o25,p.prob_o35][i];
      return `<div class="prob-row">
        <div class="prob-label">${l}</div>
        <div class="prob-bar-wrap">${bar(v, overColor(v))}</div>
        <div class="prob-pct" style="color:${overColor(v)}">${pct(v)}</div>
      </div>`;
    }).join('')}

    <div class="section-title">🎯 Speciali</div>
    <div class="prob-row">
      <div class="prob-label">BTTS (entrambi segnano)</div>
      <div class="prob-bar-wrap">${bar(p.prob_btts, overColor(p.prob_btts))}</div>
      <div class="prob-pct" style="color:${overColor(p.prob_btts)}">${pct(p.prob_btts)}</div>
    </div>
    <div class="prob-row">
      <div class="prob-label">Clean sheet casa</div>
      <div class="prob-bar-wrap">${bar(p.prob_cs_home, 'var(--accent)')}</div>
      <div class="prob-pct" style="color:var(--accent)">${pct(p.prob_cs_home)}</div>
    </div>
    <div class="prob-row">
      <div class="prob-label">Clean sheet ospite</div>
      <div class="prob-bar-wrap">${bar(p.prob_cs_away, 'var(--accent)')}</div>
      <div class="prob-pct" style="color:var(--accent)">${pct(p.prob_cs_away)}</div>
    </div>

    <div class="section-title">🏆 Punteggi più probabili</div>
    <div class="scores-grid">${topScores}</div>

    <div class="section-title">📋 Statistiche attese</div>
    <div class="stats-tiles">
      <div class="stat-tile">
        <div class="val">${p.exp_shots}</div>
        <div class="lbl">Tiri totali</div>
      </div>
      <div class="stat-tile">
        <div class="val">${p.exp_corners}</div>
        <div class="lbl">Corner totali</div>
      </div>
      <div class="stat-tile">
        <div class="val">${p.exp_yellow}</div>
        <div class="lbl">Cartellini gialli</div>
      </div>
    </div>

    ${ctxRows.length ? `
    <div class="section-title">🔍 Contesto</div>
    <div>${ctxRows.map(([l,v]) => `
      <div class="context-row">
        <span class="context-label">${l}</span>
        <span class="context-val">${v}</span>
      </div>`).join('')}
    </div>` : ''}
  `;
}

function closePanel() {
  document.getElementById('pred-panel').classList.remove('open');
  document.getElementById('overlay').classList.remove('visible');
}

// ── Days change ────────────────────────────────────────────────────────────────
document.getElementById('days-select').addEventListener('change', loadFixtures);

// ── Init ──────────────────────────────────────────────────────────────────────
renderTabs();
loadFixtures();
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)


# ── Avvio ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import os
    from db import init_db
    init_db()   # crea il DB se non esiste
    print("\n  ⚽ Football Predictor Dashboard")
    print("  ─────────────────────────────")
    print("  Apri nel browser: http://localhost:5000\n")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
