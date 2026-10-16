"""Round 6 — verifica di produzione (fase 2): ricalcola i modelli GAP di tiri e tiri in porta con il CODICE DI PRODUZIONE
(backtest/gap.py, backtest/stats_v3.py, parametri di config.GAP_PARAMS) in walk-forward e controlla che riproducano i risultati
della fase 1 (backtest/round6_parts/GAP2.md, pickle r6_gap2.pkl); controlla anche che lo stato GAP del serving (predict dallo stato
finale) coincida con le previsioni pre-partita del backtest.
Da lanciare in modalità isolata:  python -I -X utf8 backtest/run_round6_prod.py"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import gap as G, round3_ctx as C3, round6_lib as R6, stats_v3
from config import GAP_PARAMS

PARTS6 = os.path.join(REPO_ROOT, "backtest", "round6_parts")
TOL = 1e-9


def main():
    feat, keys, c = R6.prepare()
    SP = R6.SPECS
    ref = pd.read_pickle(os.path.join(C3.R3_DIR, "r6_gap2.pkl"))
    runs0 = {s: R6.run_model(feat, SP[s], R6.design(feat, SP[s])) for s in ("tiri", "sot")}
    ok = (feat.date >= pd.Timestamp("2019-07-01")) & feat[["HS", "AS", "HST", "AST", "HC", "AC", "HY", "AY", "HF", "AF"]].notna().all(axis=1)
    for r_ in runs0.values():
        ok &= r_.mh.notna()
    rows = feat.index[ok]
    weeks = feat.loc[rows, "date"].dt.strftime("%G-%V").to_numpy()
    is_val = feat.loc[rows, "season"].isin(C3.VALIDATION).to_numpy()

    pri = stats_v3.gap_priors(c.df)                                   # codice di produzione
    gf = stats_v3.gap_features(c.df, pri)
    f2 = feat.copy()
    for col in gf.columns:
        f2[col] = gf[col].reindex(f2.index)

    L = ["## Fase 2 — Verifica di produzione: il codice messo in produzione riproduce la fase 1", "",
         f"Parametri di produzione (`config.GAP_PARAMS`): tiri η={GAP_PARAMS['tiri'][0]}, γ={GAP_PARAMS['tiri'][1]}; tiri in porta η={GAP_PARAMS['sot'][0]}, γ={GAP_PARAMS['sot'][1]}. "
         "Il walk-forward usa `backtest/gap.py` (rating), `backtest/stats_v3.py` (matrice di progetto) e gli stessi stimatori di `backtest/stats_model.py` del training; "
         "il baseline è lo stesso della fase 1.", "",
         "| Statistica | Δ log-loss totale (produzione) | Δ totale fase 1 | Δ per squadra (produzione) | Δ per squadra fase 1 | Differenza massima | Esito |", "|---|---:|---:|---:|---:|---:|---|"]
    all_ok = True
    for stat in ("tiri", "sot"):
        spec = SP[stat]
        v0 = R6.evaluate(runs0[stat], rows)
        X = stats_v3.design(f2, stat, True)
        run = R6.run_model(f2, spec, X)
        v = R6.evaluate(run, rows)
        r = R6.compare(v0, v, weeks, is_val)
        p1 = ref[stat]["res"][tuple(ref[stat]["chosen"])]
        assert tuple(ref[stat]["chosen"]) == tuple(GAP_PARAMS[stat]), (stat, ref[stat]["chosen"], GAP_PARAMS[stat])
        diffs = [abs(r["ll_tot"]["d"] - p1["ll_tot"]["d"]), abs(r["ll_team"]["d"] - p1["ll_team"]["d"]),
                 abs(r["ll_tot_held"]["d"] - p1["ll_tot_held"]["d"]), abs(r["ll_tot_val"]["d"] - p1["ll_tot_val"]["d"])]
        good = max(diffs) < 1e-6
        all_ok &= good
        L.append(f"| {'Tiri' if stat == 'tiri' else 'Tiri in porta'} | {r['ll_tot']['d']:+.5f} | {p1['ll_tot']['d']:+.5f} | {r['ll_team']['d']:+.5f} | {p1['ll_team']['d']:+.5f} | {max(diffs):.2e} | {'riprodotto' if good else 'NON RIPRODOTTO'} |")
        print(stat, "prod", f"{r['ll_tot']['d']:+.5f}", "fase1", f"{p1['ll_tot']['d']:+.5f}", "maxdiff", f"{max(diffs):.2e}", flush=True)

    # coerenza serving: stato dopo tutte le partite PRECEDENTI all'ultima di ogni lega -> predict == previsione pre-partita del backtest
    L += ["", "**Coerenza del serving** (stato GAP ricostruito dallo storico e `gap.predict`, contro la previsione pre-partita del backtest per l'ultima partita giocata di ogni campionato):", "",
          "| Campionato | Statistica | Scarto massimo (casa, ospite) |", "|---|---|---:|"]
    df = c.df
    for stat, (hc, ac) in stats_v3.GAP_STATS.items():
        eta, gam = GAP_PARAMS[stat]
        bt = G.pre_match(df, hc, ac, eta, gam, pri[stat])
        for lg, g in df.groupby("Division"):
            g = g.sort_values("date", kind="stable")
            last = g.iloc[[-1]]
            _, st = G.run_league(g.iloc[:-1], hc, ac, eta, gam, pri[stat])
            ph, pa = G.predict(st, last.HomeTeam.to_numpy(), last.AwayTeam.to_numpy(), pri[stat])
            d = max(abs(ph[0] - bt.loc[last.index[0], "gap_h"]), abs(pa[0] - bt.loc[last.index[0], "gap_a"]))
            all_ok &= d < TOL
            L.append(f"| {lg} | {stat} | {d:.1e} |")
    L += ["", f"**Esito complessivo: {'tutto riprodotto' if all_ok else 'DIFFERENZE: controllare'}**", ""]
    with open(os.path.join(PARTS6, "prod_check.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print("\n".join(L))
    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
