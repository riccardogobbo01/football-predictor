#!/usr/bin/env python3
"""Riempie a ritroso le quote medie 1X2 pre-partita (odds_avg_h/d/a) di docs/history.csv per le partite dal 11/11/2026 (o dalla data indicata).

Fonti, in quest'ordine, SOLO dove la colonna e' vuota (mai sovrascritta, nessun'altra colonna toccata):
  1. football-data.co.uk/fixtures.csv: quote medie AvgH/AvgD/AvgA delle prossime partite (e di quelle dell'ultimo turno finche' il file le contiene);
  2. il CSV stagionale di football-data.co.uk (quote medie pre-partita AvgH/AvgD/AvgA) per le partite che ha gia'.
Da questa versione le colonne si riempiono da sole all'emissione (predictions/monitor.attach_fixture_market).

Uso:  python scripts/backfill_odds.py [AAAA-MM-GG]"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from backtest import data  # noqa: E402
from predictions import monitor  # noqa: E402


def main(since: str = "2026-11-11"):
    path = os.path.join(REPO_ROOT, "docs", "history.csv")
    history = monitor.load_history(path)
    before = int(history[["odds_avg_h", "odds_avg_d", "odds_avg_a"]].notna().all(axis=1).sum())
    n_fx = monitor.backfill_odds(history, monitor.fixtures_market(), since)
    n_csv = monitor.backfill_odds_csv(history, data.load_matches(verbose=False), since)
    monitor.save_history(history, path)
    h = history[history["match_date"].astype(str) >= since]
    full = h[["odds_avg_h", "odds_avg_d", "odds_avg_a"]].notna().all(axis=1)
    print(f"Quote medie riempite: {n_fx} da fixtures.csv, {n_csv} dal CSV stagionale. Partite dal {since}: {len(h)}, con quote medie: {int(full.sum())} "
          f"(prima: {before} in tutto lo storico).")
    return n_fx + n_csv


if __name__ == "__main__":
    main(*sys.argv[1:2])
