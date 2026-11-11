"""Chiamata di prova di The Odds API per i mercati secondari (cartellini e corner). NON fa parte della generazione del sito e non scrive nulla nel repository.

Legge la chiave da ODDS_API_KEY (variabile d'ambiente oppure file .env nella radice del repository, ignorato da git). La chiave non viene mai stampata né salvata.
Usa pochi crediti: per ogni campionato elenca le partite (/events) e chiede le quote solo della prossima partita (/events/{id}/odds) per i due mercati;
poi una seconda richiesta su una partita con due regioni per vedere quanti bookmaker in più compaiono. Stampa i crediti consumati letti dalle intestazioni
della risposta (x-requests-used / -remaining / -last).

Uso:  python scripts/odds_probe.py [file_json_di_uscita]
L'uscita JSON (senza chiave) serve a scrivere/controllare il parser reale."""
import json
import os
import sys
from datetime import datetime, timezone

import requests

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://api.the-odds-api.com/v4"
SPORTS = {"Serie A": "soccer_italy_serie_a", "Premier League": "soccer_epl", "Bundesliga": "soccer_germany_bundesliga",
          "La Liga": "soccer_spain_la_liga", "Ligue 1": "soccer_france_ligue_one"}
MARKETS = "alternate_totals_cards,alternate_totals_corners"


def load_key():
    k = os.environ.get("ODDS_API_KEY", "").strip()
    if k:
        return k
    path = os.path.join(REPO_ROOT, ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line.startswith("ODDS_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def call(path, key, **params):
    """GET con la chiave; restituisce (json | None, intestazioni dei crediti, errore | None). La chiave non compare mai in messaggi o log."""
    try:
        r = requests.get(f"{BASE}{path}", params={"apiKey": key, **params}, timeout=30)
    except requests.RequestException as e:
        return None, {}, f"{type(e).__name__} (dettaglio omesso: puo' contenere l'URL con la chiave)"
    hdr = {k: r.headers.get(k) for k in ("x-requests-used", "x-requests-remaining", "x-requests-last")}
    if r.status_code != 200:
        try:
            msg = r.json().get("message")
        except Exception:
            msg = r.text[:120]
        return None, hdr, f"HTTP {r.status_code}: {str(msg).replace(key, '***')}"
    return r.json(), hdr, None


def main():
    key = load_key()
    if not key:
        print("ODDS_API_KEY non impostata (variabile d'ambiente o .env): nessuna chiamata fatta.")
        return 2
    out = {"at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "leagues": {}, "credits": []}
    sports, h, err = call("/sports/", key)
    out["credits"].append(["/sports", h])
    if err:
        print("Errore /sports:", err)
        return 1
    have = {s["key"]: s.get("active") for s in sports}
    print("Campionati attivi:", {n: have.get(k) for n, k in SPORTS.items()})
    for name, sk in SPORTS.items():
        ev, h, err = call(f"/sports/{sk}/events", key)
        out["credits"].append([f"/events {name}", h])
        if err or not ev:
            print(f"{name}: partite non disponibili ({err})")
            out["leagues"][name] = {"error": err, "events": 0}
            continue
        ev = sorted(ev, key=lambda e: e["commence_time"])
        nxt = ev[0]
        odds, h2, err2 = call(f"/sports/{sk}/events/{nxt['id']}/odds", key, regions="eu", markets=MARKETS, oddsFormat="decimal")
        out["credits"].append([f"/events/odds {name} eu", h2])
        entry = {"events": len(ev), "next": {"id": nxt["id"], "home": nxt["home_team"], "away": nxt["away_team"], "commence": nxt["commence_time"]}, "odds_error": err2}
        if odds:
            entry["bookmakers"] = {b["key"]: {m["key"]: sorted({o.get("point") for o in m["outcomes"] if o.get("point") is not None}) for m in b["markets"]} for b in odds.get("bookmakers", [])}
            entry["raw"] = odds
        out["leagues"][name] = entry
        nb = len(entry.get("bookmakers", {}))
        print(f"{name}: {len(ev)} partite; prossima {nxt['home_team']} - {nxt['away_team']} ({nxt['commence_time']}); bookmaker con quote (eu): {nb}; "
              f"crediti: usati {h2.get('x-requests-used')}, rimasti {h2.get('x-requests-remaining')}, ultima richiesta {h2.get('x-requests-last')}" + (f"; errore {err2}" if err2 else ""))
    # una partita con due regioni per confronto
    first = next((n for n, e in out["leagues"].items() if e.get("next")), None)
    if first:
        e = out["leagues"][first]["next"]
        odds, h3, err3 = call(f"/sports/{SPORTS[first]}/events/{e['id']}/odds", key, regions="eu,uk", markets=MARKETS, oddsFormat="decimal")
        out["credits"].append([f"/events/odds {first} eu+uk", h3])
        if odds:
            out["two_regions"] = {first: {b["key"]: [m["key"] for m in b["markets"]] for b in odds.get("bookmakers", [])}}
            print(f"{first} con regioni eu+uk: {len(odds.get('bookmakers', []))} bookmaker; crediti ultima richiesta {h3.get('x-requests-last')}, rimasti {h3.get('x-requests-remaining')}")
        else:
            print("eu+uk:", err3)
    if len(sys.argv) > 1:
        json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("Dettaglio salvato in", sys.argv[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
