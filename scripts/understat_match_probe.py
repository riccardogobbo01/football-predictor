#!/usr/bin/env python3
"""Sonda di Understat per il dettaglio partita (round 13, passo 1). NON e' il download storico: al massimo 3 partite di prova piu' fino a 12 richieste per trovare un rigore.

Scarica  https://understat.com/getMatchData/{match_id}  (header X-Requested-With: XMLHttpRequest, come getLeagueData) per:
  1. una partita di Serie A 2025/26, 2. una di Premier League 2025/26 (id da data/cache/understat/*.json: `dates[].id`),
  3. una partita con un rigore (si prova, in ordine, le partite di Serie A e Premier 2025/26 successive alle prime due, al massimo 12 richieste).
Stampa: campi dei tiri e dei roster, valori di situation/result/shotType, i giocatori con gialli/rossi/sostituzioni, coerenza dei gol con il punteggio (due convenzioni per
gli autogol) e dell'xG con quello di getLeagueData. Salva le risposte grezze in data/cache/understat/probe/ (cartella ignorata da git).
Pausa di 1 secondo tra le richieste. Se Understat risponde con la pagina di manutenzione («We will come back soon») o con qualcosa che non e' JSON, si ferma con un messaggio chiaro.

Uso:  python scripts/understat_match_probe.py"""
import glob
import json
import os
import re
import sys
import time
from collections import Counter

import requests

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(REPO_ROOT, "data", "cache", "understat")
OUT = os.path.join(CACHE, "probe")
BASE = "https://understat.com"
HEAD = {"X-Requested-With": "XMLHttpRequest", "User-Agent": "Mozilla/5.0 (football-predictor research; 1 req/s)"}
PAUSE_S = 1.0
MAX_EXTRA = 12


class UnderstatDown(RuntimeError):
    pass


def visible_text(html: str) -> str:
    t = re.sub(r"<(svg|style|script).*?</\1>", "", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)).strip()[:160]


def get_match(match_id: str, session: requests.Session) -> dict:
    r = session.get(f"{BASE}/getMatchData/{match_id}", headers=HEAD, timeout=30)
    try:
        d = r.json()
    except ValueError:
        raise UnderstatDown(f"HTTP {r.status_code}, content-type {r.headers.get('content-type')}: risposta non JSON, testo visibile: «{visible_text(r.text)}»")
    if not isinstance(d, dict) or "shots" not in d or "rosters" not in d:
        raise UnderstatDown(f"JSON senza shots/rosters: chiavi {list(d)[:8] if isinstance(d, dict) else type(d).__name__}")
    return d


def finished(season: int, div: str) -> list:
    p = os.path.join(CACHE, f"{season}_{div}.json")
    if not os.path.exists(p):
        return []
    return [m for m in json.load(open(p, encoding="utf-8"))["dates"] if m.get("isResult")]


def report(label: str, m: dict, d: dict):
    shots = {s: d["shots"][s] for s in ("h", "a")}
    ros = {s: d["rosters"][s] for s in ("h", "a")}
    allshots = shots["h"] + shots["a"]
    print(f"\n=== {label}: {m['h']['title']} - {m['a']['title']} {m['goals']['h']}-{m['goals']['a']} ({m['datetime'][:10]}), match_id {m['id']} ===")
    print(f"chiavi della risposta: {list(d)}; tiri casa/ospite: {len(shots['h'])}/{len(shots['a'])}; giocatori nei roster: {len(ros['h'])}/{len(ros['a'])}")
    if allshots:
        print("campi dei tiri:", list(allshots[0]))
        print("esempio di tiro:", json.dumps(allshots[0], ensure_ascii=False))
    print("situation:", dict(Counter(s["situation"] for s in allshots)), "| result:", dict(Counter(s["result"] for s in allshots)),
          "| shotType:", dict(Counter(s["shotType"] for s in allshots)))
    pens = [s for s in allshots if s["situation"] == "Penalty"]
    og = [s for s in allshots if s["result"] == "OwnGoal"]
    print(f"rigori: {len(pens)} {[(s['minute'], s['player'], s['h_a'], s['result'], round(float(s['xG']), 3)) for s in pens]}; autogol: {len(og)} {[(s['minute'], s['player'], s['h_a']) for s in og]}")
    goals = {s: sum(1 for x in shots[s] if x["result"] == "Goal") for s in ("h", "a")}
    ogs = {s: sum(1 for x in shots[s] if x["result"] == "OwnGoal") for s in ("h", "a")}
    off = (int(m["goals"]["h"]), int(m["goals"]["a"]))
    c1 = (goals["h"] + ogs["a"], goals["a"] + ogs["h"])          # C1: l'autogol elencato tra i tiri di X vale per l'avversario
    c2 = (goals["h"] + ogs["h"], goals["a"] + ogs["a"])          # C2: l'autogol elencato tra i tiri di X vale per X
    print(f"gol dai tiri: C1 (autogol all'avversario) {c1}, C2 (autogol alla stessa squadra) {c2}; punteggio ufficiale {off}; coerenza C1: {c1 == off}, C2: {c2 == off}")
    xg = {s: sum(float(x["xG"]) for x in shots[s]) for s in ("h", "a")}
    print(f"xG dalla somma dei tiri: {xg['h']:.3f} / {xg['a']:.3f}; xG di getLeagueData: {m['xG']['h']} / {m['xG']['a']}")
    allp = [dict(p, side=s) for s in ("h", "a") for p in ros[s].values()]
    print("campi dei roster:", list(allp[0]))
    print("esempio di giocatore:", json.dumps(allp[0], ensure_ascii=False))
    print("posizioni:", dict(Counter(p["position"] for p in allp)))
    print("minuti totali per squadra (casa/ospite):", [sum(int(p["time"]) for p in ros[s].values()) for s in ("h", "a")],
          "| gialli:", [(p["player"], p["side"]) for p in allp if p["yellow_card"] != "0"], "| rossi:", [(p["player"], p["side"]) for p in allp if p["red_card"] != "0"])
    print("sostituzioni (roster_in/roster_out = id della riga di roster sostituita/sostituente; `time` = minuti giocati):",
          [(p["player"], p["side"], p["time"], p["roster_in"], p["roster_out"]) for p in allp if p["roster_in"] != "0" or p["roster_out"] != "0"][:6])
    print("gol/assist/xG/xA dei roster (somma casa, ospite):", [(sum(int(p["goals"]) for p in ros[s].values()), sum(int(p["assists"]) for p in ros[s].values()),
                                                                round(sum(float(p["xG"]) for p in ros[s].values()), 3), round(sum(float(p["xA"]) for p in ros[s].values()), 3)) for s in ("h", "a")])
    print("tmpl/informazioni partita:", json.dumps(d.get("tmpl"), ensure_ascii=False)[:420] if d.get("tmpl") else "assenti")


def main():
    os.makedirs(OUT, exist_ok=True)
    it, pl = finished(2025, "I1"), finished(2025, "E0")
    if not it or not pl:
        print("Cache di getLeagueData 2025 mancante: servono data/cache/understat/2025_I1.json e 2025_E0.json")
        return 2
    s = requests.Session()
    picks = [("Serie A", it[0]), ("Premier League", pl[0])]
    got, pen = [], None
    try:
        for label, m in picks:
            d = get_match(m["id"], s)
            json.dump(d, open(os.path.join(OUT, f"{m['id']}.json"), "w", encoding="utf-8"), ensure_ascii=False)
            got.append((label, m, d))
            if any(x["situation"] == "Penalty" for sd in d["shots"].values() for x in sd) and pen is None:
                pen = (label + " (con rigore)", m, d)
            time.sleep(PAUSE_S)
        pool = [("Serie A", m) for m in it[1:]] + [("Premier League", m) for m in pl[1:]]
        pool = [x for pair in zip([p for p in pool if p[0] == "Serie A"], [p for p in pool if p[0] == "Premier League"]) for x in pair]       # alternate le due leghe
        for label, m in pool[:MAX_EXTRA]:
            if pen is not None:
                break
            d = get_match(m["id"], s)
            json.dump(d, open(os.path.join(OUT, f"{m['id']}.json"), "w", encoding="utf-8"), ensure_ascii=False)
            if any(x["situation"] == "Penalty" for sd in d["shots"].values() for x in sd):
                pen = (label + " (con rigore)", m, d)
            time.sleep(PAUSE_S)
    except UnderstatDown as e:
        print("UNDERSTAT NON DISPONIBILE:", e)
        print("Nessun dato scaricato. Rilanciare quando il sito risponde (la sonda e' sicura da ripetere).")
        return 3
    for label, m, d in got:
        report(label, m, d)
    if pen is not None:
        report(pen[0], pen[1], pen[2])
    else:
        print(f"\nNessun rigore nelle prime {len(got) + MAX_EXTRA} partite provate: indicare un match_id a mano.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
