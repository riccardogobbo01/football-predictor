#!/usr/bin/env python3
"""
Riempie le colonne «emesse» di docs/history.csv (`p_o25`, `p_o15`, `p_o35`, `p_btts`, `exp_h`, `exp_a`, `stats_json`) nelle righe create prima che le colonne
esistessero, dalle copie di docs/predictions.json nella storia di git: per ogni partita si usa l'ULTIMA copia generata prima del calcio d'inizio che la
contiene. Le righe delle coppe (modello Elo senza mercati dei gol) e quelle senza una copia utile restano vuote. Idempotente (non sovrascrive valori
presenti). `stats_json` solo se la copia ha gli intervalli (dalla versione s4-intervalli).

Uso:  python scripts/backfill_issued.py [docs/history.csv]
"""
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
from predictions import monitor  # noqa: E402

LEAGUES = list(monitor.LEAGUE_CODE)


def git(*args) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", cwd=REPO_ROOT, check=True).stdout


def snapshots():
    """[(generated_at UTC, {(lega, data, casa, ospite): (ora, prob_o25)})] in ordine cronologico, da tutte le copie di predictions.json in git."""
    out = []
    for c in git("log", "--format=%H", "--", "docs/predictions.json").split():
        try:
            j = json.loads(git("show", f"{c}:docs/predictions.json"))
        except Exception:
            continue
        gen = pd.Timestamp(str(j.get("generated_at", "")).replace(" UTC", ""))
        fx = {}
        for lk in LEAGUES:
            for f in (j.get("leagues", {}).get(lk, {}) or {}).get("fixtures", []):
                p = f.get("prediction") or {}
                if p.get("prob_o25") is not None:
                    vals = {"p_o25": p.get("prob_o25"), "p_o15": p.get("prob_o15"), "p_o35": p.get("prob_o35"), "p_btts": p.get("prob_btts"),
                            "exp_h": p.get("exp_goals_home"), "exp_a": p.get("exp_goals_away"), "stats_json": monitor.stats_json_from(f.get("expected_stats"))}
                    vals["kickoff"] = f"{f['date']} {f['time']}" if f.get("time") else None
                    fx[(lk, f["date"], f["home"], f["away"])] = (f.get("time"), vals)
        out.append((gen, fx))
    return sorted(out, key=lambda x: x[0])


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO_ROOT, "docs", "history.csv")
    h = monitor.load_history(path)
    cols = ["p_o25", "p_o15", "p_o35", "p_btts", "exp_h", "exp_a", "stats_json", "kickoff"]
    todo = h[h["league"].isin(LEAGUES) & h[cols].isna().any(axis=1)]
    snaps = snapshots()
    n = 0
    for i, row in todo.iterrows():
        key = (row["league"], str(row["match_date"]), row["home"], row["away"])
        found = None
        for gen, fx in snaps:
            if key in fx:
                t, vals = fx[key]
                ko = pd.Timestamp(row["kickoff"]) if isinstance(row["kickoff"], str) else pd.Timestamp(f"{key[1]} {t or '23:59'}")
                if gen < ko:
                    found = vals                    # l'ultima copia generata prima del calcio d'inizio
        if found is not None:
            for c in cols:
                if pd.isna(h.at[i, c]) and found.get(c) is not None:
                    h.at[i, c] = found[c]
            n += 1
    monitor.save_history(h, path)
    print(f"colonne emesse riempite per {n} partite su {len(todo)} con valori mancanti ({len(snaps)} copie di predictions.json esaminate)")


if __name__ == "__main__":
    main()
