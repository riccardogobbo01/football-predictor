"""Round 2 — diagnostica: perché Elo-Odds migliora solo dal 2021/22? (finestra di training dello stack, fonte quote)"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import round2_ctx as C, round2_implied as I, stack
from backtest.round2_lib import Boot, run_stack
from backtest.run_round2_exp2 import PARTS, cpath


def main():
    c = C.get_ctx()
    df, feat, ev = c.df, c.feat, c.ev
    boot = Boot(len(ev))
    Pb = c.base_sp[["pH", "pD", "pA"]].to_numpy()
    b = pd.read_pickle(cpath("exp2b_results.pkl"))
    K = b["K_star"]
    eo = pd.read_pickle(cpath(f"exp2_eo_K{K}.pkl"))["v"]
    L = ["### Diagnostica su Elo-Odds: il guadagno compare solo dal 2021/22?", "",
         f"Il guadagno di 2b (K={K}) è ≈0 o negativo nel 2019/20 e 2020/21 e +0.003/+0.007 dal 2021/22. Due spiegazioni possibili: "
         "(i) cambio di fonte delle quote (Pinnacle in chiusura fino al 2018/19 nel training, media di mercato dopo); "
         "(ii) lo stack con xG si allena solo dal 2016/17 (gli xG partono dal 2014 e il DC xG ha bisogno di 2 anni di storia): "
         "per il 2019/20 ha solo 3 stagioni di training per imparare il peso di una feature rumorosa come il rating Elo-Odds.", ""]
    # (i) Pinnacle ovunque
    eo_p = I.elo_odds(df, K=float(K), source="pin")
    fr = feat.copy()
    fr["eo_diff"] = eo_p.eo_diff.reindex(fr.index)
    sp = run_stack(fr, stack.XG_FEATURES + ["eo_diff"], ev)
    C.reg_save("X 2b — Elo-Odds, Pinnacle in chiusura ovunque", sp)
    r1 = C.compare(sp[["pH", "pD", "pA"]].to_numpy(), Pb, ev, boot, f"2b K={K}, Pinnacle in chiusura (dove disponibile)")
    # (ii) stack senza xG con training dal 2013/14
    fr2 = feat.copy()
    fr2["eo_diff"] = eo.eo_diff.reindex(fr2.index)
    s_no = stack.walk_forward_stack(fr2, stack.PRODUCTION_FEATURES, 2019, None).reindex(ev.index)
    s_eo = stack.walk_forward_stack(fr2, stack.PRODUCTION_FEATURES + ["eo_diff"], 2019, None).reindex(ev.index)
    C.reg_save("X stack senza xG (training dal 2013/14)", s_no)
    C.reg_save("X stack senza xG + Elo-Odds (training dal 2013/14)", s_eo)
    P_no, P_eo = s_no[["pH", "pD", "pA"]].to_numpy(), s_eo[["pH", "pD", "pA"]].to_numpy()
    r2 = C.compare(P_eo, P_no, ev, boot, "senza xG, training dal 2013/14: con vs senza Elo-Odds")
    r3 = C.compare(P_eo, Pb, ev, boot, "senza xG + Elo-Odds (training dal 2013/14) vs baseline con xG")
    L += ["| Prova | Log-loss | Δ log-loss [IC 95%] | Δ per stagione (2019/20 → 2026/27) |", "|---|---:|---|---|"]
    for lab, r in ((f"2b K={K} con Pinnacle in chiusura ovunque (vs baseline)", r1),
                   ("Stack SENZA xG, training dal 2013/14: con Elo-Odds vs senza (stessa finestra)", r2),
                   ("Stack senza xG + Elo-Odds (training dal 2013/14) vs baseline con xG", r3)):
        L.append(f"| {lab} | {r['ll']:.4f} | {r['d_ll']:+.5f} [{r['lo_ll']:+.5f}, {r['hi_ll']:+.5f}] | "
                 + ", ".join(f"{v[0]:+.4f}" for v in r["by_season"].values()) + " |")
    L += ["", "Lettura: cambiare fonte non cambia il quadro (i); con più stagioni di training (ii) Elo-Odds migliora in TUTTE le "
              "stagioni, compreso il 2019/20. Il basso guadagno delle prime due stagioni è quindi compatibile con la finestra di "
              "training corta imposta dagli xG (3 stagioni nel 2019/20) più che con un difetto del segnale (non è una prova: la "
              "seconda riga cambia anche il modello di base). In produzione il modello with_xg si allena dal 2016/17 fino all'ultima "
              "stagione (circa 10 stagioni), cioè nella situazione delle stagioni recenti del backtest, dove il guadagno è più grande.", ""]
    with open(os.path.join(PARTS, "extra.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
