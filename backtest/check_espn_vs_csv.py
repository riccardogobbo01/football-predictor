"""Confronto partita per partita tra ESPN (predictions/espn.py) e football-data.co.uk per tutte le partite di campionato della stagione in corso.
Da lanciare:  python -I -X utf8 backtest/check_espn_vs_csv.py   (scrive backtest/round8_parts/ESPN.md)"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd
import requests

from backtest import data
from predictions import espn

DIV = {"I1": "ita.1", "E0": "eng.1", "D1": "ger.1", "SP1": "esp.1", "F1": "fra.1"}
COLS = [("hg", "hg", "Gol casa"), ("ag", "ag", "Gol ospite"), ("HTHG+HTAG", "ht_goals", "Gol del primo tempo (totale)"), ("HST", "sot_h", "Tiri in porta casa"),
        ("AST", "sot_a", "Tiri in porta ospite"), ("HS", "shots_h", "Tiri casa"), ("AS", "shots_a", "Tiri ospite"), ("HC", "corners_h", "Corner casa"),
        ("AC", "corners_a", "Corner ospite"), ("HF", "fouls_h", "Falli casa"), ("AF", "fouls_a", "Falli ospite"), ("HY", "yellow_h", "Gialli casa"), ("AY", "yellow_a", "Gialli ospite")]


def main():
    df = data.load_matches(verbose=False)
    c = df[df.season == data.current_season()]
    sess = requests.Session()
    ev = []
    for dv, code in DIV.items():
        for d in sorted(c[c.Division == dv].date.dt.strftime("%Y-%m-%d").unique()):
            ev += [dict(div=dv, **m) for m in espn.fetch_day(code, d, sess)]
    seen = {e["espn_id"]: e for e in ev}
    recs = list(seen.values())
    n_ok, diffs, unmatched = 0, [], []
    for _, r in c.iterrows():
        row = dict(match_date=str(r.date.date()), home=r.HomeTeam, away=r.AwayTeam, home_dc=r.HomeTeam, away_dc=r.AwayTeam)
        best = espn.match_event(row, [e for e in recs if e["div"] == r.Division], threshold=0.7)
        if best is None:
            unmatched.append((r.Division, str(r.date.date()), r.HomeTeam, r.AwayTeam))
            continue
        n_ok += 1
        d = {}
        for a, b, _ in COLS:
            va = (r["HTHG"] + r["HTAG"]) if a == "HTHG+HTAG" else r[a]
            vb = best[b]
            d[a] = None if pd.isna(va) or vb is None or pd.isna(vb) else int(va != vb)
        diffs.append(d)
    D = pd.DataFrame(diffs)
    L = ["# ESPN contro football-data.co.uk (stagione in corso)", "", f"{len(c)} partite di campionato nel CSV, {n_ok} abbinate a un evento ESPN (data ±1 giorno, nomi simili), {len(unmatched)} senza abbinamento"
         + (f" ({', '.join(f'{a} {b} {x}-{y}' for a, b, x, y in unmatched[:6])}{'…' if len(unmatched) > 6 else ''})." if unmatched else "."), "",
         "| Campo | Confrontate | Uguali | % uguali |", "|---|---:|---:|---:|"]
    for a, b, lab in COLS:
        n = int(D[a].notna().sum())
        k = int((D[a] == 0).sum())
        L.append(f"| {lab} | {n} | {k} | {100 * k / n:.1f}% |" if n else f"| {lab} | 0 | – | – |")
    L.append("")
    out = "\n".join(L)
    open(os.path.join(REPO_ROOT, "backtest", "round8_parts", "ESPN.md"), "w", encoding="utf-8").write(out)
    print(out)


if __name__ == "__main__":
    main()
