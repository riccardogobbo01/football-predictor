"""Round 3 — Esperimento B: varianti di Elo-Odds (Pinnacle, K per lega, rating casa/trasferta). Solo backtest."""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import data, round2_ctx as C2, round3_ctx as C3, round3_eo as EO, stack
from backtest.round2_lib import ll_vec, run_stack

K_GRID = [100, 150, 200, 300, 400]
HA_GRID = [(200, 0.0), (300, 0.0), (400, 0.0), (200, 0.5), (300, 0.5), (400, 0.5)]    # ordine di semplicità
TIE = 0.0002
COLS = stack.XG_FEATURES_EO


def run(c, fr, cols, name):
    sp = run_stack(fr, cols, c.ev)
    C2.reg_save("R3 " + name, sp)
    return sp, C3.compare3(sp[["pH", "pD", "pA"]].to_numpy(), c, name)


def main():
    c = C3.get_ctx3()
    df, feat, ev = c.df, c.feat, c.ev
    S_avg, src_avg = EO.scores(df, "avg")
    L = ["## Esperimento B — Varianti di Elo-Odds", ""]

    # controllo: la ricostruzione standard coincide con la produzione
    chk = EO.build_std(df, S_avg, 200.0)
    assert np.allclose(chk.reindex(c.feat.index).to_numpy(), c.feat.eo_diff.to_numpy(), atol=1e-9), "eo_diff standard != produzione"
    L += ["Controllo: la ricostruzione con le funzioni del round 3 (K=200, chiusura media) coincide con `eo_diff` di produzione "
          "(differenza massima < 1e-9).", ""]

    # ── B1: Pinnacle ──────────────────────────────────────────────────────────
    S_pin, src_pin = EO.scores(df, "pin")
    fr = feat.copy()
    fr["eo_diff"] = EO.build_std(df, S_pin, 200.0).reindex(fr.index)
    used_pin = float((src_pin[df.index.isin(ev.index)] == 1).mean())
    _, r_b1 = run(c, fr, COLS, "B1 — Elo-Odds su quote Pinnacle di chiusura")
    L += [f"### B1 — Pinnacle di chiusura al posto della media", "",
          f"Nelle partite di test Pinnacle (PSCH/PSCD/PSCA) è disponibile per il {used_pin:.1%}; il resto ricade sulla chiusura media "
          f"(per 2025/26 metà e 2026/27 tutto). Nessun parametro libero.", ""] + C3.md_detail(r_b1)

    # ── B2: K per lega ────────────────────────────────────────────────────────
    val_ll = {}
    uni = {}
    for K in K_GRID:
        fr = feat.copy()
        fr["eo_diff"] = EO.build_std(df, S_avg, float(K)).reindex(fr.index)
        sp, r = run(c, fr, COLS, f"B2 — K uniforme {K} (griglia)")
        uni[K] = r
        P = sp[["pH", "pD", "pA"]].to_numpy()
        ll = ll_vec(P, c.y)
        for lg in data.LEAGUES:
            m = c.is_val & (ev.Division == lg).to_numpy()
            val_ll[(lg, K)] = float(ll[m].mean())
    K_lg = {}
    for lg in data.LEAGUES:
        best = min(val_ll[(lg, K)] for K in K_GRID)
        near = [K for K in K_GRID if val_ll[(lg, K)] <= best + TIE]
        K_lg[lg] = min(near, key=lambda k: abs(k - 200))
    L += ["### B2 — K separato per lega", "",
          "Log-loss sulle sole stagioni di validazione, per lega e K uniforme (stack completo ogni volta):", "",
          "| Lega | " + " | ".join(f"K={k}" for k in K_GRID) + " | K scelto |", "|---|" + "---:|" * (len(K_GRID) + 1)]
    for lg in data.LEAGUES:
        L.append(f"| {data.LEAGUE_NAMES[lg]} | " + " | ".join(f"{val_ll[(lg, k)]:.4f}" for k in K_GRID) + f" | **{K_lg[lg]}** |")
    L += ["", f"Regola: per ogni lega il K con la log-loss di validazione più bassa; parità entro {TIE} → il più vicino a 200.", ""]
    fr = feat.copy()
    fr["eo_diff"] = EO.build_std(df, S_avg, {lg: float(k) for lg, k in K_lg.items()}).reindex(fr.index)
    _, r_b2 = run(c, fr, COLS, "B2 — K per lega " + str(K_lg))
    L += C3.md_detail(r_b2, title="B2 — K per lega (" + ", ".join(f"{data.LEAGUE_NAMES[l]} {k}" for l, k in K_lg.items()) + ")")

    # ── B3: rating casa/trasferta ─────────────────────────────────────────────
    ha_res = []
    for K, g in HA_GRID:
        fr = feat.copy()
        fr["eo_ha"] = EO.build_ha(df, S_avg, float(K), g).reindex(fr.index)
        cols = [x for x in COLS if x != "eo_diff"] + ["eo_ha"]
        _, r = run(c, fr, cols, f"B3a — rating casa/trasferta K={K}, γ={g}")
        ha_res.append(r)
    best_val = max(r["val"]["d"] for r in ha_res)
    ci = next(i for i, r in enumerate(ha_res) if r["val"]["d"] >= best_val - TIE)
    Kb, gb = HA_GRID[ci]
    L += ["### B3 — Rating separati casa / trasferta", "",
          "B3a: la feature `eo_ha` = R_casa(squadra di casa) − R_trasf(ospite) sostituisce `eo_diff`. Griglia (6 configurazioni), "
          "scelta sulle validazione (parità entro 0.0002 → la più semplice, nell'ordine in tabella).", ""] + C3.md_table(ha_res) + [""]
    L += [f"Scelta: **K={Kb}, γ={gb}** (Δ validazione {ha_res[ci]['val']['d']:+.5f}).", ""]
    L += C3.md_detail(ha_res[ci], title=f"B3a — rating casa/trasferta (K={Kb}, γ={gb}) al posto di eo_diff")
    fr = feat.copy()
    fr["eo_ha"] = EO.build_ha(df, S_avg, float(Kb), gb).reindex(fr.index)
    _, r_b3b = run(c, fr, COLS + ["eo_ha"], f"B3b — eo_diff + rating casa/trasferta (K={Kb}, γ={gb})")
    L += C3.md_detail(r_b3b, title=f"B3b — eo_ha AGGIUNTO a eo_diff (stessi parametri di B3a)")

    allr = [r_b1, r_b2, ha_res[ci], r_b3b]
    L += ["### Riepilogo B (ogni variante da sola vs baseline)", ""] + C3.md_table(allr) + [""]
    L += ["Verdetti (regola: Δ held-out > 0 con IC a blocchi che esclude lo zero): " +
          "; ".join(f"{r['name'].split(' — ')[0]}: **{C3.verdict(r)}**" for r in allr) + ".", ""]
    with open(os.path.join(C3.PARTS, "B.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    pd.to_pickle(dict(res=[{k: v for k, v in r.items() if k not in ("d_vec", "ok")} for r in allr],
                      K_lg=K_lg, ha=(Kb, gb)), os.path.join(C3.R3_DIR, "r3_B.pkl"))
    print("\n".join(L))


if __name__ == "__main__":
    main()
