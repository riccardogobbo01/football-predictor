#!/usr/bin/env python3
"""
Resoconto settimanale: confronta le previsioni EMESSE PRIMA DEL CALCIO D'INIZIO (righe congelate di docs/history.csv) con i risultati reali e
pubblica docs/resoconto.html (+ docs/resoconto.json). Si rigenera a ogni esecuzione del job giornaliero da tutto lo storico (idempotente), quindi
non dipende dal fatto che il lunedì sia andato in porto: mostra l'ultima settimana completa (lunedì-domenica), la settimana in corso (parziale), le
settimane precedenti e il totale dall'inizio del monitoraggio.

Per ogni insieme di partite di campionato con risultato:
  1X2          log-loss e RPS del modello (probabilità emesse) e del mercato, sulle stesse partite
  gol          media attesa contro reale, rapporto reale/atteso; Over 1,5 / 2,5 / 3,5 e BTTS: probabilità media prevista contro frequenza reale
  statistiche  (tiri, tiri in porta, corner, gialli, falli) copertura degli intervalli (probabilità dichiarata contro frequenza reale, per squadra e totale),
               correlazione e errore medio assoluto del totale; per lega
I risultati vengono da football-data.co.uk e, finché non e' aggiornato, da ESPN (provvisori: `result_source` = espn).

Uso:  python scripts/weekly_report.py [docs/history.csv] [docs/]   (data di riferimento: oggi, UTC)
"""
import html
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
from predictions import monitor  # noqa: E402

LEAGUES = list(monitor.LEAGUE_CODE)
LEAGUE_NAME = {"serie_a": "Serie A", "premier_league": "Premier League", "bundesliga": "Bundesliga", "la_liga": "La Liga", "ligue_1": "Ligue 1"}
STATS = [("tiri", "Tiri"), ("sot", "Tiri in porta"), ("corner", "Corner"), ("gialli", "Gialli"), ("falli", "Falli")]
P3 = ["home", "draw", "away"]
MARKETS = [("p_o15", 2, "Over 1,5"), ("p_o25", 3, "Over 2,5"), ("p_o35", 4, "Over 3,5")]


# ───────────────────────────── calcolo ─────────────────────────────
def _loads(s):
    try:
        return json.loads(s) if isinstance(s, str) and s else None
    except ValueError:
        return None


def _y(res):
    return {"H": 0, "D": 1, "A": 2}.get(res)


def one_x_two(df: pd.DataFrame) -> dict:
    """Log-loss e RPS di modello e mercato sulle stesse partite (probabilità emesse e del mercato entrambe presenti)."""
    d = df.dropna(subset=[f"p_{k}" for k in P3] + [f"mkt_{k}" for k in P3])
    out = {"n": int(len(d)), "ll_model": None, "ll_market": None, "rps_model": None, "rps_market": None}
    if not len(d):
        return out
    y = d["result"].map(_y).to_numpy(int)
    for tag, cols in (("model", [f"p_{k}" for k in P3]), ("market", [f"mkt_{k}" for k in P3])):
        P = np.clip(d[cols].to_numpy(float), 1e-12, 1)
        P = P / P.sum(1, keepdims=True)
        out[f"ll_{tag}"] = float(-np.log(P[np.arange(len(y)), y]).mean())
        Y = np.eye(3)[y]
        out[f"rps_{tag}"] = float((((np.cumsum(P, 1)[:, :2] - np.cumsum(Y, 1)[:, :2]) ** 2).sum(1) / 2).mean())
    return out


def goals(df: pd.DataFrame) -> dict:
    d = df.dropna(subset=["hg", "ag"])
    out = {"n": int(len(d)), "exp": None, "real": None, "ratio": None, "markets": {}}
    tot = (d["hg"] + d["ag"]).to_numpy(float)
    de = d.dropna(subset=["exp_h", "exp_a"])
    if len(de):
        e = (de["exp_h"] + de["exp_a"]).to_numpy(float)
        r = (de["hg"] + de["ag"]).to_numpy(float)
        out.update(n_exp=int(len(de)), exp=float(e.mean()), real=float(r.mean()), ratio=float(r.sum() / e.sum()))
    for col, thr, lab in MARKETS:
        x = d.dropna(subset=[col])
        if len(x):
            o = ((x["hg"] + x["ag"]) >= thr).to_numpy(float)
            out["markets"][lab] = {"n": int(len(x)), "pred": float(x[col].mean()), "real": float(o.mean())}
    x = d.dropna(subset=["p_btts"])
    if len(x):
        o = ((x["hg"] >= 1) & (x["ag"] >= 1)).to_numpy(float)
        out["markets"]["BTTS"] = {"n": int(len(x)), "pred": float(x["p_btts"].mean()), "real": float(o.mean())}
    return out


def stat_rows(df: pd.DataFrame, stat: str):
    """Elenco di (casa/ospite/totale, previsto, intervallo, reale) per una statistica: righe con stats_json e stats_real_json."""
    out = []
    for _, r in df.iterrows():
        sj, rj = _loads(r.get("stats_json")), _loads(r.get("stats_real_json"))
        if not sj or not rj or stat not in sj or stat not in rj:
            continue
        s, (yh, ya) = sj[stat], rj[stat]
        out.append({"league": r["league"], "ph": s["h"], "pa": s["a"], "pt": s["t"], "ih": s["ih"], "ia": s["ia"], "it": s["it"], "yh": yh, "ya": ya, "yt": yh + ya})
    return out


def stats_metrics(df: pd.DataFrame) -> dict:
    """Per statistica: n, copertura (dichiarata contro reale) per squadra e totale, correlazione e MAE del totale."""
    res = {}
    for stat, _ in STATS:
        rows = stat_rows(df, stat)
        m = {"n": len(rows)}
        if rows:
            hit_t = np.array([r["it"][0] <= r["yt"] <= r["it"][1] for r in rows], float)
            m["total"] = {"declared": float(np.mean([r["it"][2] for r in rows])), "real": float(hit_t.mean())}
            hit_s = np.array([r["ih"][0] <= r["yh"] <= r["ih"][1] for r in rows] + [r["ia"][0] <= r["ya"] <= r["ia"][1] for r in rows], float)
            dec_s = np.array([r["ih"][2] for r in rows] + [r["ia"][2] for r in rows], float)
            m["team"] = {"declared": float(dec_s.mean()), "real": float(hit_s.mean())}
            pt = np.array([r["pt"] for r in rows], float)
            yt = np.array([r["yt"] for r in rows], float)
            m["mae"] = float(np.abs(pt - yt).mean())
            m["bias"] = float((yt - pt).mean())                     # reale - previsto
            m["corr"] = float(np.corrcoef(pt, yt)[0, 1]) if len(rows) >= 8 and pt.std() > 0 and yt.std() > 0 else None
        res[stat] = m
    return res


def summarize(df: pd.DataFrame) -> dict:
    return {"n": int(len(df)), "x12": one_x_two(df), "goals": goals(df), "stats": stats_metrics(df),
            "by_league": {lg: {"x12": one_x_two(g), "goals": goals(g), "stats": stats_metrics(g)} for lg, g in df.groupby("league")}}


def played_rows(history: pd.DataFrame) -> pd.DataFrame:
    """Partite di campionato giocate con la previsione emessa dalla versione corrente del modello 1X2 (prima del calcio d'inizio: righe congelate)."""
    h = history[history["league"].isin(LEAGUES) & history["result"].isin(["H", "D", "A"])].copy()
    h["_d"] = pd.to_datetime(h["match_date"])
    return h


def week_bounds(day: pd.Timestamp):
    """(lunedì, domenica) della settimana che contiene `day`."""
    mon = (day - pd.Timedelta(days=day.weekday())).normalize()
    return mon, mon + pd.Timedelta(days=6)


def build(history: pd.DataFrame, today) -> dict:
    today = pd.Timestamp(today).normalize()
    h = played_rows(history)
    cur_mon, _ = week_bounds(today)
    last_mon = cur_mon - pd.Timedelta(days=7)
    weeks = {}
    for mon, g in h.groupby(h["_d"].map(lambda d: week_bounds(d)[0])):
        weeks[mon] = summarize(g)
    return {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "today": str(today.date()),
            "last_week": {"start": str(last_mon.date()), "end": str((last_mon + pd.Timedelta(days=6)).date()), **(weeks.get(last_mon) or summarize(h.iloc[0:0]))},
            "current_week": {"start": str(cur_mon.date()), **(weeks.get(cur_mon) or summarize(h.iloc[0:0]))},
            "weeks": {str(k.date()): {"n": v["n"], "x12": v["x12"], "goals": {kk: vv for kk, vv in v["goals"].items() if kk != "markets"}} for k, v in sorted(weeks.items())},
            "total": summarize(h), "since": str(h["_d"].min().date()) if len(h) else None,
            "provisional": int((h["result_source"] == "espn").sum())}


# ───────────────────────────── pagina ─────────────────────────────
def _pct(x, d=1):
    return "–" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{100 * x:.{d}f}%"


def _num(x, d=3):
    return "–" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{d}f}".replace(".", ",")


def _gap(decl, real):
    return "–" if decl is None else f"{100 * (real - decl):+.1f}".replace(".", ",") + " pp"


def _table(head, rows, cls=""):
    th = "".join(f"<th>{html.escape(h)}</th>" for h in head)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def block_html(title: str, s: dict, sub: str = "") -> str:
    if not s["n"]:
        return f'<section><h2>{html.escape(title)}</h2><p class="note">{html.escape(sub)} Nessuna partita giocata.</p></section>'
    x, g = s["x12"], s["goals"]
    out = [f'<section><h2>{html.escape(title)}</h2><p class="note">{html.escape(sub)} {s["n"]} partite di campionato giocate.</p>']
    # 1X2
    rows = [["Tutte", x["n"], _num(x["ll_model"], 4), _num(x["ll_market"], 4), _num(x["rps_model"], 4), _num(x["rps_market"], 4)]]
    for lg in LEAGUES:
        b = s["by_league"].get(lg)
        if b and b["x12"]["n"]:
            y = b["x12"]
            rows.append([LEAGUE_NAME[lg], y["n"], _num(y["ll_model"], 4), _num(y["ll_market"], 4), _num(y["rps_model"], 4), _num(y["rps_market"], 4)])
    out.append("<h3>1X2: modello contro mercato</h3>" + _table(["Insieme", "Partite", "Log-loss modello", "Log-loss mercato", "RPS modello", "RPS mercato"], rows)
               + '<p class="note">Più basso = meglio. Il mercato è la probabilità senza margine delle quote.</p>')
    # gol e mercati
    rows = [["Tutte", g.get("n_exp", 0), _num(g["exp"], 2), _num(g["real"], 2), _num(g["ratio"], 2)]]
    for lg in LEAGUES:
        b = s["by_league"].get(lg)
        if b and b["goals"].get("n_exp"):
            q = b["goals"]
            rows.append([LEAGUE_NAME[lg], q["n_exp"], _num(q["exp"], 2), _num(q["real"], 2), _num(q["ratio"], 2)])
    out.append("<h3>Gol</h3>" + _table(["Insieme", "Partite", "Gol attesi a partita", "Gol reali a partita", "Reali / attesi"], rows))
    rows = []
    for lab in ("Over 1,5", "Over 2,5", "Over 3,5", "BTTS"):
        m = g["markets"].get(lab)
        if m:
            rows.append([lab, m["n"], _pct(m["pred"]), _pct(m["real"]), f"{100 * (m['pred'] - m['real']):+.1f}".replace(".", ",") + " pp"])
    if rows:
        out.append("<h3>Over/Under e BTTS</h3>" + _table(["Mercato", "Partite", "Previsto", "Reale", "Previsto − reale"], rows))
    # statistiche
    rows = []
    for stat, lab in STATS:
        m = s["stats"].get(stat) or {"n": 0}
        if not m["n"]:
            rows.append([lab, 0, "–", "–", "–", "–", "–", "–"])
            continue
        rows.append([lab, m["n"], f'{_pct(m["team"]["declared"])} → {_pct(m["team"]["real"])}', _gap(m["team"]["declared"], m["team"]["real"]),
                     f'{_pct(m["total"]["declared"])} → {_pct(m["total"]["real"])}', _gap(m["total"]["declared"], m["total"]["real"]),
                     _num(m["corr"], 2), _num(m["mae"], 2)])
    out.append("<h3>Statistiche: intervalli, correlazione, errore</h3>" + _table(
        ["Statistica", "Partite", "Intervallo per squadra (dichiarata → reale)", "Scarto", "Intervallo del totale (dichiarata → reale)", "Scarto", "Correlazione del totale", "Errore medio assoluto del totale"], rows)
        + '<p class="note">La probabilità dichiarata è quella stampata accanto a ogni intervallo nel pannello; la frequenza reale è quante volte il valore cade dentro. '
          'Con poche partite i numeri sono rumorosi (correlazione solo da 8 partite).</p>')
    # per lega: copertura del totale e per squadra
    rows = []
    for stat, lab in STATS:
        cells = []
        for lg in LEAGUES:
            m = ((s["by_league"].get(lg) or {}).get("stats") or {}).get(stat) or {"n": 0}
            cells.append("–" if not m["n"] else f'{_pct(m["team"]["real"], 0)} / {_pct(m["total"]["real"], 0)} <span class="n">({m["n"]})</span>')
        rows.append([lab] + cells)
    out.append("<h3>Copertura reale degli intervalli per lega (squadra / totale, tra parentesi le partite)</h3>" + _table(["Statistica"] + [LEAGUE_NAME[lg] for lg in LEAGUES], rows))
    out.append("</section>")
    return "".join(out)


CSS = """
:root{--bg:#f6f7f9;--card:#fff;--text:#1a1d21;--muted:#5d6672;--border:#dde1e6;--accent:#2f6fed;--green:#1f9d55;--red:#d64545}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#0d1117;--card:#161b22;--text:#e6edf3;--muted:#8b949e;--border:#2b323b;--accent:#58a6ff;--green:#4ade80;--red:#f87171}}
:root[data-theme="dark"]{--bg:#0d1117;--card:#161b22;--text:#e6edf3;--muted:#8b949e;--border:#2b323b;--accent:#58a6ff;--green:#4ade80;--red:#f87171}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;padding:16px}
main{max-width:980px;margin:0 auto}a{color:var(--accent)}h1{font-size:1.4rem;margin:.2rem 0 .4rem}h2{font-size:1.1rem;margin:0 0 .3rem}h3{font-size:.85rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin:1rem 0 .4rem}
section{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;margin:14px 0}
.note{color:var(--muted);font-size:.8rem;margin:.3rem 0}.tw{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.82rem;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:5px 8px;border-bottom:1px solid var(--border);white-space:nowrap}th{color:var(--muted);font-weight:600}.n{color:var(--muted);font-size:.72rem}
.warn{border-left:4px solid var(--red);padding:8px 12px;background:var(--card);border-radius:8px;margin:12px 0;font-size:.85rem}
"""


def render(rep: dict) -> str:
    lw, cw, tot = rep["last_week"], rep["current_week"], rep["total"]
    prov = (f'<div class="warn">{rep["provisional"]} partite hanno risultato e statistiche provvisori da ESPN (football-data.co.uk non è ancora aggiornato): '
            f'verranno sostituiti dal CSV.</div>') if rep["provisional"] else ""
    rows = []
    for wk, v in rep["weeks"].items():
        x, g = v["x12"], v["goals"]
        rows.append([wk, v["n"], _num(x["ll_model"], 4), _num(x["ll_market"], 4), _num(g.get("exp"), 2), _num(g.get("real"), 2), _num(g.get("ratio"), 2)])
    body = [f'<h1>Resoconto settimanale</h1><p class="note">Previsioni emesse prima del calcio d’inizio contro i risultati reali, campionati. '
            f'Dal {rep["since"]} · aggiornato il {rep["generated_at"]} · <a href="index.html">← Previsioni</a></p>', prov,
            block_html(f'Ultima settimana completa ({lw["start"]} → {lw["end"]})', lw),
            block_html(f'Settimana in corso dal {cw["start"]} (parziale)', cw),
            '<section><h2>Settimane</h2>' + _table(["Settimana dal", "Partite", "Log-loss modello", "Log-loss mercato", "Gol attesi", "Gol reali", "Reali / attesi"], rows) + "</section>",
            block_html("Totale dall'inizio del monitoraggio", tot)]
    return ('<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Resoconto settimanale</title><style>' + CSS + '</style></head><body><main>' + "".join(body) + "</main></body></html>")


def main(history_path=None, out_dir=None, today=None):
    history_path = history_path or os.path.join(REPO_ROOT, "docs", "history.csv")
    out_dir = out_dir or os.path.dirname(history_path)
    history = monitor.load_history(history_path)
    rep = build(history, today or datetime.now(timezone.utc).date())
    with open(os.path.join(out_dir, "resoconto.html"), "w", encoding="utf-8") as fh:
        fh.write(render(rep))
    with open(os.path.join(out_dir, "resoconto.json"), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=1, default=lambda o: None if o is None else float(o))
    return rep


if __name__ == "__main__":
    r = main(*sys.argv[1:3])
    print(f"Resoconto: {r['total']['n']} partite, ultima settimana {r['last_week']['n']}, in corso {r['current_week']['n']}")
