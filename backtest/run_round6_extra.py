"""Round 6 — analisi aggiuntive (NON previste dal prereg), per completare il quadro: baseline dei gialli (con arbitro) con tutte le
metriche per squadra e totale, e confronto del modello GAP dei tiri in porta (scelto in validazione) con il baseline semplice di I.
Da lanciare in modalità isolata:  python -I -X utf8 backtest/run_round6_extra.py"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import round3_ctx as C3, round6_lib as R6
from backtest.run_round6_IJ import HEAD, md_baseline, md_row, share_series

PARTS6 = os.path.join(REPO_ROOT, "backtest", "round6_parts")


def main():
    feat, keys, c = R6.prepare()
    SP = R6.SPECS
    run_g = R6.run_model(feat, SP["gialli"], R6.design(feat, SP["gialli"], extra=["ref_logR"]))
    run_t = R6.run_model(feat, SP["tiri"], R6.design(feat, SP["tiri"]))
    g = R6.gap_ratings(c.df, "HST", "AST", 0.05, 0.5)
    f2 = feat.copy()
    f2["gap_lh"], f2["gap_la"] = np.log(g.gap_h.reindex(f2.index)), np.log(g.gap_a.reindex(f2.index))
    run_sg = R6.run_model(f2, SP["sot"], R6.design(f2, SP["sot"], own=("gap_lh", "gap_la")))
    sh, sa = share_series(feat)
    simple_folds = {s: dict(idx=fd["idx"], mh=fd["mh"] * sh.loc[fd["idx"]].to_numpy(), ma=fd["ma"] * sa.loc[fd["idx"]].to_numpy()) for s, fd in run_t.folds.items()}
    run_simple = R6.Run(feat, SP["sot"], run_t.mh * sh, run_t.ma * sa, simple_folds)
    complete = feat[["HS", "AS", "HST", "AST", "HC", "AC", "HY", "AY", "HF", "AF"]].notna().all(axis=1)
    ok = (feat.date >= pd.Timestamp("2019-07-01")) & complete
    for r_ in (run_g, run_t, run_sg, run_simple):
        ok &= r_.mh.notna()
    rows = feat.index[ok]
    weeks = feat.loc[rows, "date"].dt.strftime("%G-%V").to_numpy()
    is_val = feat.loc[rows, "season"].isin(C3.VALIDATION).to_numpy()
    L = ["### Analisi aggiuntive (NON previste dal prereg)", "",
         f"Stesso insieme di valutazione dei campionati ({len(rows)} partite).", ""]
    vg = R6.evaluate(run_g, rows)
    L += md_baseline("Baseline dei gialli (modello attuale con effetto arbitro): metriche per squadra e totale", SP["gialli"], R6.summarize(vg))
    vs, vsg = R6.evaluate(run_simple, rows), R6.evaluate(run_sg, rows)
    cmp_ = R6.compare(vs, vsg, weeks, is_val)
    L += md_baseline("Tiri in porta: modello con GAP ratings (η=0.05, γ=0.5, scelto in validazione per J4)", SP["sot"], R6.summarize(vsg))
    L += ["Tiri in porta, GAP vs baseline semplice «tiri previsti × quota in porta» (Δ positivo = GAP migliore):", ""] + HEAD + \
         [md_row("Tiri in porta — J4 GAP vs baseline semplice", cmp_, R6.verdict(cmp_))] + [""]
    with open(os.path.join(PARTS6, "extra.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    pd.to_pickle(dict(gialli=R6.summarize(vg), sot_gap=R6.summarize(vsg), cmp=cmp_), os.path.join(C3.R3_DIR, "r6_extra.pkl"))
    print("\n".join(L))


if __name__ == "__main__":
    main()
