#!/usr/bin/env python3
"""
Costruisce data/referees/matches.csv: arbitro di ogni partita di campionato giocata, con i nomi squadra di football-data.co.uk.
Fonti:
  - Transfermarkt (dataset dcaribou/transfermarkt-datasets, tabella games; cache locale in data/cache/transfermarkt/): stagioni
    2016/17-2025/26 (chiave = nome normalizzato Transfermarkt);
  - football-data.org (campo `referees`): partite giocate della stagione corrente (chiave = alias di REFEREE_ALIASES o nome normalizzato).
Da lanciare a mano (richiede la cache Transfermarkt e FOOTBALL_DATA_ORG_KEY). Dopo il backfill, lo storico si aggiorna da solo:
l'arbitro delle partite giocate resta in docs/history.csv (colonna `referee`) e il training lo legge da lì.

Uso:  python scripts/build_referee_history.py [--fdo-json file.json]   (il json è il dump {codice: [match...]} dell'API, per non rifare le chiamate)
"""
import argparse
import json
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import numpy as np
import pandas as pd
import requests

from backtest import data, refeffect, referees as RF
from predictions import stack_predictor as sp

CODES = {"SA": "I1", "PL": "E0", "BL1": "D1", "PD": "SP1", "FL1": "F1"}
OUT = refeffect.MATCHES_CSV


def fetch_fdo(key):
    out = {}
    for code in CODES:
        r = requests.get(f"https://api.football-data.org/v4/competitions/{code}/matches", params={"status": "FINISHED"},
                         headers={"X-Auth-Token": key}, timeout=30)
        r.raise_for_status()
        out[code] = r.json()["matches"]
        time.sleep(7)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fdo-json")
    args = ap.parse_args()
    df = data.load_matches(verbose=False)
    cur = data.current_season()

    # 1) Transfermarkt: stagioni 2016/17 -> precedente alla corrente
    tm = RF.map_referees(df)
    sel = (df.season >= refeffect.FIRST_TRAIN) & (df.season < cur) & tm.ref.notna()
    rows = [dict(Division=dv, season=int(s), date=str(d.date()), HomeTeam=h, AwayTeam=a, referee_key=k, source="tm")
            for dv, s, d, h, a, k in zip(df.Division[sel], df.season[sel], df.date[sel], df.HomeTeam[sel], df.AwayTeam[sel], tm.ref[sel])]
    n_tm = len(rows)

    # 2) football-data.org: partite giocate della stagione corrente
    if args.fdo_json:
        with open(args.fdo_json, encoding="utf-8") as fh:
            fdo = json.load(fh)
    else:
        key = os.getenv("FOOTBALL_DATA_ORG_KEY", "")
        if not key:
            sys.exit("FOOTBALL_DATA_ORG_KEY mancante")
        fdo = fetch_fdo(key)
    played = df[df.season == cur]
    n_fdo = n_missing = n_noref = 0
    unmatched_teams, unknown_names = set(), set()
    for code, ms in fdo.items():
        div = CODES[code]
        g = played[played.Division == div]
        teams = sorted(set(g.HomeTeam) | set(g.AwayTeam))
        have = {(r.HomeTeam, r.AwayTeam): r for r in g.itertuples()}
        for m in ms:
            if m.get("status") != "FINISHED":
                continue
            ref = next((r["name"] for r in m.get("referees", []) if r.get("type") == "REFEREE"), None)
            if not ref:
                n_noref += 1
                continue
            ht, at = m.get("homeTeam") or m.get("home"), m.get("awayTeam") or m.get("away")     # il dump puo' usare home/away
            h = sp.best_match(ht.get("shortName") or ht["name"], teams) or sp.best_match(ht["name"], teams)
            a = sp.best_match(at.get("shortName") or at["name"], teams) or sp.best_match(at["name"], teams)
            if (h, a) not in have:
                n_missing += 1
                unmatched_teams.add((ht["name"], at["name"]))
                continue
            key_ = refeffect.resolve(div, ref)
            from backtest.referee_aliases import REFEREE_ALIASES
            if RF.normalize(ref) not in REFEREE_ALIASES.get(div, {}):
                unknown_names.add((div, ref))
            rows.append(dict(Division=div, season=int(cur), date=str(have[(h, a)].date.date()), HomeTeam=h, AwayTeam=a,
                             referee_key=key_, source="fdo"))
            n_fdo += 1
    out = pd.DataFrame(rows).drop_duplicates(["Division", "season", "HomeTeam", "AwayTeam"])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Scritto {OUT}: {len(out)} partite (Transfermarkt {n_tm}, football-data.org {n_fdo}); "
          f"football-data.org: {n_noref} partite giocate senza arbitro, {n_missing} non abbinate alle partite del CSV")
    if unmatched_teams:
        print("  coppie di squadre non abbinate:", sorted(unmatched_teams)[:5])
    if unknown_names:
        print("  nomi arbitro non presenti in REFEREE_ALIASES:", sorted(unknown_names))


if __name__ == "__main__":
    main()
