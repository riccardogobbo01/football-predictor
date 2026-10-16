"""Round 4 — Esperimento E: limite massimo della formazione titolare (solo backtest).
Da lanciare in modalità isolata:  python -I -X utf8 backtest/run_round4_E.py"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import data, lineups as LU, round2_ctx as C2, round3_ctx as C3, stack
from backtest.round2_lib import run_stack

PARTS4 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "round4_parts")
os.makedirs(PARTS4, exist_ok=True)
TIE = 0.0002
GRID = [("cov", 5), ("val", 5), ("both", 5), ("cov", 10), ("val", 10), ("both", 10)]      # ordine di semplicità
COLS = stack.XG_FEATURES_EO
SETCOLS = {"cov": ["lu_cov_diff"], "val": ["lu_val_diff"], "both": ["lu_cov_diff", "lu_val_diff"]}
SETLAB = {"cov": "quota minuti", "val": "valore", "both": "quota minuti + valore"}


def frame_with(feat, X, fset):
    fr = feat.copy()
    for col in ("lu_cov_diff", "lu_val_diff", "lu_miss"):
        fr[col] = X[col].reindex(fr.index)
    return fr, COLS + SETCOLS[fset] + ["lu_miss"]


def main():
    c = C3.get_ctx3()
    df, feat, ev = c.df, c.feat, c.ev
    S = LU.build_structures()
    L = ["## Esperimento E — Limite massimo della formazione titolare (campionati)", "",
         "> **Questo è un test «a formazione nota».** Le feature usano gli 11 effettivamente schierati nella partita da prevedere, "
         "informazione che si conosce circa un'ora prima del calcio d'inizio: non c'è quando le previsioni si pubblicano. Il guadagno "
         "qui sotto è quindi un **limite massimo** di quanto potrebbe valere conoscere la formazione, non un guadagno ottenibile in "
         "produzione. La versione realistica è la «formazione prevista» (in fondo, solo se la condizione scritta prima è soddisfatta).", ""]

    X = {}
    for N in (5, 10):
        X[N] = LU.build(df, S, N, predicted=False)
    # copertura
    mapped = LU.map_games(df, S)[0].notna()
    L += ["### Copertura", "",
          "Partite di campionato abbinate a una partita del dataset Transfermarkt e con formazione completa per entrambe le squadre "
          "(esattamente 11 titolari) e almeno 3 partite di storico con minuti (N=5 / N=10). Le altre hanno differenze = 0 e "
          "indicatore `lu_miss` = 1 (stesso trattamento in training e in test).", "",
          "| Stagione | Partite di test | Abbinate | Complete (N=5) | Complete (N=10) |", "|---|---:|---:|---:|---:|"]
    for s in sorted(ev.season.unique()):
        m = ev.index[(ev.season == s).to_numpy()]
        L.append(f"| {C2.season_label(s)} | {len(m)} | {mapped.reindex(m).mean():.1%} | {1 - X[5].lu_miss.reindex(m).mean():.1%} | "
                 f"{1 - X[10].lu_miss.reindex(m).mean():.1%} |")
    cov_all = {N: 1 - X[N].lu_miss.reindex(ev.index).mean() for N in (5, 10)}
    L += ["", f"Totale partite di test con formazione completa: N=5 {cov_all[5]:.1%}, N=10 {cov_all[10]:.1%}. Tutta la stagione 2026/27 "
              "manca nel dataset (ultimo aggiornamento 2026-09-05, valutazioni fino al 2026-06-12); anche il training dello stack dal "
              "2016/17 al 2025/26 ha copertura completa (≥ 98% per stagione).", ""]

    res = []
    for fset, N in GRID:
        fr, cols = frame_with(feat, X[N], fset)
        sp = run_stack(fr, cols, ev)
        name = f"E — N={N}, {SETLAB[fset]}"
        C2.reg_save("R4 " + name, sp)
        r = C3.compare3(sp[["pH", "pD", "pA"]].to_numpy(), c, name)
        r["fset"], r["N"] = fset, N
        res.append(r)
        print(name, f"{r['all']['d']:+.5f}", flush=True)

    best_val = max(r["val"]["d"] for r in res)
    chosen = next(r for r in res if r["val"]["d"] >= best_val - TIE)
    L += ["### Griglia di 6 configurazioni (ogni riga da sola vs baseline v6)", ""] + C3.md_table(res) + [""]
    L += [f"Scelta sulle validazione (parità entro {TIE} → la più semplice): **{chosen['name']}** (Δ validazione {chosen['val']['d']:+.5f}). "
          f"Verdetto: **{C3.verdict(chosen)}**.", ""]
    L += C3.md_detail(chosen)

    # guadagno su formazioni complete vs altre (variante scelta)
    miss = X[chosen["N"]].lu_miss.reindex(ev.index).to_numpy() == 1
    d = chosen["d_vec"]
    L += ["**Guadagno su partite con formazione completa e sulle altre (variante scelta)**", "",
          "| Insieme | N | Δ log-loss | IC 95% a blocchi |", "|---|---:|---:|---|"]
    for lab, m in (("formazione completa", ~miss), ("formazione mancante (indicatore = 1)", miss)):
        mm, lo, hi = C3.ci_block(d[m], c.weeks[m]) if m.sum() > 10 else (float("nan"),) * 3
        L.append(f"| {lab} | {int(m.sum())} | {mm:+.5f} | [{lo:+.5f}, {hi:+.5f}] |")
    L.append("")

    # formazione prevista (condizionale)
    h = chosen["held"]
    cond = h["d"] >= 0.002 and h["lob"] > 0
    L += ["### Formazione prevista", "",
          f"Condizione scritta prima: Δ held-out ≥ +0.002 con IC a blocchi che esclude lo zero. Configurazione scelta: Δ held-out "
          f"{h['d']:+.5f}, IC a blocchi [{h['lob']:+.5f}, {h['hib']:+.5f}] → condizione **{'soddisfatta' if cond else 'NON soddisfatta'}**.", ""]
    pred_res = None
    if cond:
        Xp = LU.build(df, S, chosen["N"], predicted=True)
        fr, cols = frame_with(feat, Xp, chosen["fset"])
        sp = run_stack(fr, cols, ev)
        name = f"E — formazione PREVISTA (11 dell'ultima partita), N={chosen['N']}, {SETLAB[chosen['fset']]}"
        C2.reg_save("R4 " + name, sp)
        pred_res = C3.compare3(sp[["pH", "pD", "pA"]].to_numpy(), c, name)
        cmp_ = C3.compare3(sp[["pH", "pD", "pA"]].to_numpy(), c, "prevista vs nota",
                           P_base=C2.reg_load()["R4 " + chosen["name"]]["sp"][["pH", "pD", "pA"]].to_numpy())
        L += C3.md_table([chosen, pred_res]) + [""]
        L += [f"Differenza prevista − nota (Δ = log-loss formazione nota − log-loss formazione prevista; positivo = la prevista è migliore): "
              f"{cmp_['all']['d']:+.5f}, IC a blocchi [{cmp_['all']['lob']:+.5f}, {cmp_['all']['hib']:+.5f}].", ""]
    else:
        L += ["Non si fa la versione «formazione prevista», come stabilito.", ""]
    with open(os.path.join(PARTS4, "E.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    strip = lambda r: {k: v for k, v in r.items() if k not in ("d_vec", "ok")}
    pd.to_pickle(dict(res=[strip(r) for r in res], chosen=chosen["name"], pred=strip(pred_res) if pred_res else None,
                      cond=bool(cond)), os.path.join(C3.R3_DIR, "r4_E.pkl"))
    print("\n".join(L))


if __name__ == "__main__":
    main()
