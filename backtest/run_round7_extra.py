"""Round 7 — parti accessorie: (a) weekend 16-18/10 (partite non ancora nei CSV di football-data.co.uk: risultati da theScore, previsioni
emesse prima del weekend dal sito, in git); (b) moltiplicatori correnti L3 per statistica e lega; (c) confronto delle definizioni con theScore.
Da lanciare:  python -I -X utf8 backtest/run_round7_extra.py"""
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import round7_lib as L7
from backtest.run_round7 import LG_NAME, prepare, SPEC

P7 = L7.P7
LG_KEY = {"serie_a": "I1", "premier_league": "E0", "bundesliga": "D1", "la_liga": "SP1", "ligue_1": "F1"}


def weekend():
    w = json.load(open(os.path.join(P7, "weekend_scores.json"), encoding="utf-8"))
    out = subprocess.run(["git", "show", f"{w['pred_commit']}:docs/predictions.json"], capture_output=True, text=True, encoding="utf-8", cwd=REPO_ROOT).stdout
    p = json.loads(out)
    L = ["### Weekend 16-18/10 (partite non ancora nei CSV di football-data.co.uk)", "",
         f"Risultati finali da theScore; previsioni = quelle pubblicate dal sito prima del weekend (commit `{w['pred_commit']}`, modello di produzione con i dati fino al 12/10). Stesse partite per lega (le partite del 19/10 non sono incluse).", "",
         "| Lega | N | Gol previsti (media) | Gol reali (media) | Rapporto | Over 2,5 previsto | Over 2,5 reale |", "|---|---:|---:|---:|---:|---:|---:|"]
    tp = ta = n = o25p = o25a = 0
    for lk, sc in w["scores"].items():
        fx = [f for f in p["leagues"][lk]["fixtures"] if f["date"] <= "2026-10-18"]
        assert len(fx) == len(sc), (lk, len(fx), len(sc))
        pr = sum(f["prediction"]["exp_goals_home"] + f["prediction"]["exp_goals_away"] for f in fx)
        ac = sum(a + b for _, _, a, b in sc)
        op, oa = sum(f["prediction"]["prob_o25"] for f in fx), sum((a + b) >= 3 for _, _, a, b in sc)
        L.append(f"| {LG_NAME[LG_KEY[lk]]} | {len(sc)} | {pr / len(sc):.2f} | {ac / len(sc):.2f} | {ac / pr:.2f} | {op / len(sc):.2f} | {oa / len(sc):.2f} |")
        tp, ta, n, o25p, o25a = tp + pr, ta + ac, n + len(sc), o25p + op, o25a + oa
    L.append(f"| **Tutte** | {n} | {tp / n:.2f} | {ta / n:.2f} | {ta / tp:.2f} | {o25p / n:.2f} | {o25a / n:.2f} |")
    L += ["", "Con 44 partite l'errore standard della media dei gol è circa 0,25 per partita: lo scarto complessivo (+0,15) è dentro il rumore; le differenze per lega (8-9 partite ciascuna, errore standard circa 0,6) non sono interpretabili.", ""]
    return L


def levels_L3(feat, st, cfgs):
    last = feat.date.max() + pd.Timedelta(days=1)
    L = ["### Moltiplicatori correnti L3 (configurazioni scelte in validazione) dopo l'ultima partita giocata", "", "Rapporto di livello per lega e lato (casa / ospite) applicato alle medie previste.", "",
         "| Statistica | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |", "|---|---|---|---|---|---|"]
    for s in L7.STATS:
        run, spec = st[s]["run"], SPEC[s]
        cfg = cfgs[s]
        cells = []
        for lg in L7.LEAGUES:
            m = (feat.Division == lg) & run.mh.notna() & feat[spec["hc"]].notna()
            d = pd.concat([feat.date[m], pd.Series([last])], ignore_index=True)
            lab = np.r_[feat.Division[m].to_numpy(), [lg]]
            rh = L7.dynamic_level(d, lab, np.r_[run.mh[m].to_numpy(), [np.nan]], np.r_[feat[spec["hc"]][m].to_numpy(float), [np.nan]], *cfg)[-1]
            ra = L7.dynamic_level(d, lab, np.r_[run.ma[m].to_numpy(), [np.nan]], np.r_[feat[spec["ac"]][m].to_numpy(float), [np.nan]], *cfg)[-1]
            cells.append(f"{rh:.2f} / {ra:.2f}")
        L.append(f"| {L7.KEYS[s]} (H={cfg[0]}, k={cfg[1]}) | " + " | ".join(cells) + " |")
    L.append("")
    return L


def main():
    res = pd.read_pickle(os.path.join(os.path.dirname(L7.CTX7), "round7_results.pkl"))
    cfgs = {s: res["stats"][s]["chosen"] for s in L7.STATS}
    feat, gw, weeks, st = prepare()
    L = weekend() + levels_L3(feat, st, cfgs)
    open(os.path.join(P7, "EXTRA.md"), "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
