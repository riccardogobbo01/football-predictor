#!/usr/bin/env python3
"""
Controllo puntuale di una partita nel CSV di football-data.co.uk (che si aggiorna con ritardo): stampa le statistiche della partita se c'è.

Uso:  python scripts/check_match_stats.py I1 2026-10-18 Milan Atalanta
Esempio (round 7): theScore dava per Milan-Atalanta (18/10/2026) 3 falli del Milan e 10 dell'Atalanta, 6-4 tiri in porta, 2-2 corner.
Stampa «NON ANCORA» (codice di uscita 3) se la partita non è ancora nel CSV.
"""
import io
import sys

import pandas as pd
import requests


def main():
    div, date, home, away = sys.argv[1:5]
    season = "2627"
    url = f"https://www.football-data.co.uk/mmz4281/{season}/{div}.csv"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=60, allow_redirects=True)
    r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.content.decode("latin-1")))
    d["_d"] = pd.to_datetime(d["Date"], dayfirst=True, errors="coerce")
    print(f"CSV {div}: {len(d)} partite, ultima data {d['_d'].max().date()}")
    m = d[(d["_d"] == pd.Timestamp(date)) & d["HomeTeam"].str.contains(home, case=False) & d["AwayTeam"].str.contains(away, case=False)]
    if m.empty:
        print("NON ANCORA: la partita non è nel CSV")
        sys.exit(3)
    cols = [c for c in ("Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "HS", "AS", "HST", "AST", "HF", "AF", "HC", "AC", "HY", "AY", "HR", "AR") if c in m.columns]
    print(m[cols].to_string(index=False))


if __name__ == "__main__":
    main()
