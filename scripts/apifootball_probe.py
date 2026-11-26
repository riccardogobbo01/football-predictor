#!/usr/bin/env python3
"""Sonda di API-Football (api-sports.io), piano gratuito. SOLO sonda: tetto rigido di 10 richieste in tutto (contatore persistente in
data/cache/apifootball_probe/count.json), nessuna raccolta, nessun collegamento con la produzione.
La chiave si legge dalla variabile d'ambiente API_FOOTBALL_KEY o dal file .env (ignorato da git); non viene mai stampata ne' salvata.
Le risposte grezze vanno in data/cache/apifootball_probe/ (ignorata da git); l'intestazione della chiave non e' salvata.

Uso:  python scripts/apifootball_probe.py <percorso> [chiave=valore ...]
      es.  python scripts/apifootball_probe.py status
           python scripts/apifootball_probe.py fixtures league=135 season=2022 from=2022-09-01 to=2022-09-04"""
import json
import os
import sys
import time

import requests

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO_ROOT, "data", "cache", "apifootball_probe")
CAP = 10
BASE = "https://v3.football.api-sports.io"


def key():
    k = os.environ.get("API_FOOTBALL_KEY", "")
    if not k:
        try:
            from dotenv import dotenv_values
            k = dotenv_values(os.path.join(REPO_ROOT, ".env")).get("API_FOOTBALL_KEY", "")
        except Exception:
            k = ""
    return k


def main():
    path = sys.argv[1]
    params = dict(a.split("=", 1) for a in sys.argv[2:])
    os.makedirs(OUT, exist_ok=True)
    cf = os.path.join(OUT, "count.json")
    st = json.load(open(cf)) if os.path.exists(cf) else {"n": 0, "log": []}
    if st["n"] >= CAP:
        print(f"TETTO RAGGIUNTO: {st['n']}/{CAP} richieste gia' usate. Nessuna richiesta fatta.")
        return 2
    k = key()
    if not k:
        print("API_FOOTBALL_KEY non trovata (ambiente o .env)")
        return 2
    st["n"] += 1
    st["log"].append({"n": st["n"], "path": path, "params": params, "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    json.dump(st, open(cf, "w"), indent=1)                                           # il contatore si aggiorna PRIMA della richiesta
    r = requests.get(f"{BASE}/{path}", params=params, headers={"x-apisports-key": k}, timeout=40)
    hd = {h: r.headers.get(h) for h in ("x-ratelimit-requests-limit", "x-ratelimit-requests-remaining", "X-RateLimit-Limit", "X-RateLimit-Remaining") if r.headers.get(h) is not None}
    try:
        d = r.json()
    except ValueError:
        d = {"non_json": r.text[:300]}
    name = f"{st['n']:02d}_{path.replace('/', '_')}_{'_'.join(f'{a}-{b}' for a, b in params.items())[:80]}.json"
    json.dump({"http": r.status_code, "headers": hd, "response": d}, open(os.path.join(OUT, name), "w", encoding="utf-8"), ensure_ascii=False)
    print(f"[richiesta {st['n']}/{CAP}] {path} {params} -> HTTP {r.status_code}, {len(r.content)} byte; {hd}")
    print(f"errors: {d.get('errors')} | results: {d.get('results')} | paging: {d.get('paging')}")
    print("file:", name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
