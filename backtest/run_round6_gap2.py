"""Round 6 — Fase 1: estensione della griglia dei GAP ratings (tiri e tiri in porta). Solo backtest.
Da lanciare in modalità isolata:  python -I -X utf8 backtest/run_round6_gap2.py"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import round3_ctx as C3, round6_lib as R6
from backtest.run_round6_IJ import HEAD, md_baseline, md_row

PARTS6 = os.path.join(REPO_ROOT, "backtest", "round6_parts")
TIE = 0.0002
ETAS1, GAMMAS = [0.05, 0.10, 0.15, 0.20], [0.5, 0.75, 1.0]
ETAS2 = [0.30, 0.40]
REF = (0.05, 0.5)


def main():
    feat, keys, c = R6.prepare()
    SP = R6.SPECS
    runs0 = {s: R6.run_model(feat, SP[s], R6.design(feat, SP[s])) for s in ("tiri", "sot")}
    ok = (feat.date >= pd.Timestamp("2019-07-01")) & feat[["HS", "AS", "HST", "AST", "HC", "AC", "HY", "AY", "HF", "AF"]].notna().all(axis=1)
    for r_ in runs0.values():
        ok &= r_.mh.notna()
    rows = feat.index[ok]
    weeks = feat.loc[rows, "date"].dt.strftime("%G-%V").to_numpy()
    is_val = feat.loc[rows, "season"].isin(C3.VALIDATION).to_numpy()

    def gap_run(stat, eta, gam):
        spec = SP[stat]
        g = R6.gap_ratings(c.df, spec["hc"], spec["ac"], eta, gam)
        f2 = feat.copy()
        f2["gap_lh"], f2["gap_la"] = np.log(g.gap_h.reindex(f2.index)), np.log(g.gap_a.reindex(f2.index))
        return R6.run_model(f2, spec, R6.design(f2, spec, own=("gap_lh", "gap_la")))

    L = ["## Fase 1 — Estensione della griglia dei GAP ratings (tiri e tiri in porta)", ""]
    out = {}
    for stat in ("tiri", "sot"):
        spec = SP[stat]
        v0 = R6.evaluate(runs0[stat], rows)
        L += [f"### {'Tiri' if stat == 'tiri' else 'Tiri in porta'}", ""] + md_baseline("Baseline (" + ("modello dei tiri attuale" if stat == "tiri" else "modello I dei tiri in porta, senza GAP") + ")", spec, R6.summarize(v0))
        res, vec = {}, {}

        def do(eta, gam):
            if (eta, gam) in res:
                return
            v = R6.evaluate(gap_run(stat, eta, gam), rows)
            vec[(eta, gam)] = v
            res[(eta, gam)] = R6.compare(v0, v, weeks, is_val)
            print(stat, eta, gam, f"{res[(eta, gam)]['ll_tot']['d']:+.5f}", flush=True)

        def choose(configs):
            best = max(res[k]["ll_tot_val"]["d"] for k in configs)
            cand = [k for k in configs if res[k]["ll_tot_val"]["d"] >= best - TIE]
            return min(cand, key=lambda k: (k[0], k[1]))

        do(*REF)
        grid1 = [(e, g) for e in ETAS1 for g in GAMMAS]
        for k in grid1:
            do(*k)
        ch1 = choose(grid1)
        ext = ch1[0] == max(ETAS1)
        grid_all = list(grid1)
        if ext:
            for e in ETAS2:
                for g in GAMMAS:
                    do(e, g)
                    grid_all.append((e, g))
        chosen = choose(grid_all)
        border_after = (chosen[0] == max(e for e, _ in grid_all)) or (chosen[1] == max(GAMMAS))
        L += [f"**Griglia 1** (η ∈ {ETAS1} × γ ∈ {GAMMAS}): scelta sulle validazione η = {ch1[0]}, γ = {ch1[1]}"
              + (" → sul bordo (η massimo): **estensione** con η ∈ " + str(ETAS2) + " (ultima)." if ext else "; l'ottimo non è al bordo di η (nessuna estensione)."), ""]
        L += ["| η | γ | Δ totale (tutte) [IC a blocchi] | Δ totale validazione | Δ totale held-out [IC a blocchi] | Δ per squadra (tutte) | Δ per squadra held-out | Verdetto |", "|---:|---:|---|---:|---|---:|---:|---|"]
        for k in sorted(res):
            r = res[k]
            L.append(f"| {k[0]} | {k[1]} | {r['ll_tot']['d']:+.5f} [{r['ll_tot']['lob']:+.5f}, {r['ll_tot']['hib']:+.5f}] | {r['ll_tot_val']['d']:+.5f} | "
                     f"{r['ll_tot_held']['d']:+.5f} [{r['ll_tot_held']['lob']:+.5f}, {r['ll_tot_held']['hib']:+.5f}] | {r['ll_team']['d']:+.5f} | {r['ll_team_held']['d']:+.5f} | "
                     f"{R6.verdict(r)}{' ← scelta' if k == chosen else ''}{' (round 6)' if k == REF else ''} |")
        L += ["", f"**Scelta finale sulle sole validazione: η = {chosen[0]}, γ = {chosen[1]}**" +
              (" — γ = 1.0 è il limite naturale del parametro; η al bordo alto della griglia solo se η = 0.20, nel qual caso si è già esteso una volta e si ferma qui." if border_after else " — non sul bordo di η."), ""]
        L += HEAD + [md_row(f"GAP η={chosen[0]}, γ={chosen[1]} vs baseline", res[chosen], R6.verdict(res[chosen]))] + [""]
        # confronto con la configurazione del round 6
        if chosen != REF:
            rr = R6.compare(vec[REF], vec[chosen], weeks, is_val)
            L += [f"Rispetto alla configurazione del round 6 (η=0.05, γ=0.5): Δ totale {rr['ll_tot']['d']:+.5f} [IC a blocchi {rr['ll_tot']['lob']:+.5f}, {rr['ll_tot']['hib']:+.5f}], "
                  f"held-out {rr['ll_tot_held']['d']:+.5f} [{rr['ll_tot_held']['lob']:+.5f}, {rr['ll_tot_held']['hib']:+.5f}]; per squadra {rr['ll_team']['d']:+.5f} [{rr['ll_team']['lob']:+.5f}, {rr['ll_team']['hib']:+.5f}].", ""]
        L += md_baseline(f"Metriche della configurazione scelta (η={chosen[0]}, γ={chosen[1]})", spec, R6.summarize(vec[chosen]))
        out[stat] = dict(chosen=chosen, border=bool(border_after), ext=bool(ext), res={k: {x: y for x, y in v.items()} for k, v in res.items()},
                         verdict=R6.verdict(res[chosen]), summary=R6.summarize(vec[chosen]), base=R6.summarize(v0))
    with open(os.path.join(PARTS6, "GAP2.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    pd.to_pickle(out, os.path.join(C3.R3_DIR, "r6_gap2.pkl"))
    print("\n".join(L))


if __name__ == "__main__":
    main()
