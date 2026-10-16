"""Round 4 — E, analisi aggiuntiva (non nel prereg): Δ sulle sole partite con formazione disponibile (esclude 2026/27)."""
import os, sys
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd
from backtest import round2_ctx as C2, round3_ctx as C3
from backtest.round2_lib import ll_vec

def main():
    c = C3.get_ctx3()
    reg = C2.reg_load()
    P0 = c.base_sp[["pH", "pD", "pA"]].to_numpy()
    cov = (c.ev.season <= 2025).to_numpy()
    held = ~c.is_val
    L = ["### Analisi aggiuntiva (NON prevista dal prereg): solo partite con formazione disponibile, cioè fino al 2025/26", "",
         "La stagione 2026/27 (293 partite) non è nel dataset: in quelle righe lo stack riceve `lu_miss` = 1 e peggiora. Qui si escludono, "
         "per vedere il limite massimo senza quell'artefatto. Le 6 configurazioni sono tutte mostrate (nessuna scelta nuova).", "",
         "| Configurazione | N | Δ tutte (IC a blocchi) | Δ held-out 2022/23-2025/26 (IC a blocchi) |", "|---|---:|---|---|"]
    names = [k for k in reg if k.startswith("R4 E — N=")]
    for k in names:
        P = reg[k]["sp"][["pH", "pD", "pA"]].to_numpy()
        d = ll_vec(P0, c.y) - ll_vec(P, c.y)
        a = C3.ci_block(d[cov], c.weeks[cov]); h = C3.ci_block(d[cov & held], c.weeks[cov & held])
        L.append(f"| {k[5:]} | {int(cov.sum())} | {a[0]:+.5f} [{a[1]:+.5f}, {a[2]:+.5f}] | {h[0]:+.5f} [{h[1]:+.5f}, {h[2]:+.5f}] |")
    L.append("")
    open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "round4_parts", "E2.md"), "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))

if __name__ == "__main__":
    main()
