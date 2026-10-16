"""Round 3 — Esperimento C: ordered logit di ricalibrazione sopra il baseline v6 (solo backtest)."""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import models, round2_ctx as C2, round2_recal as RC, round3_ctx as C3
from config import REC_DRAW_THRESHOLD

KINDS = [("ol", "Ordered logit semplice (4 parametri)"),
         ("olflex", "Ordered logit flessibile (banda del pareggio dipende da gol attesi)")]
TIE = 0.0002


def rec_scores(M, P, thr):
    G = M.shape[1]
    ii, jj = np.indices((G, G))
    cls = np.where(ii > jj, 0, np.where(ii == jj, 1, 2))
    k = np.where(P.max(1) > thr, P.argmax(1), 1)
    masked = np.where(cls[None] == k[:, None, None], M, -1.0).reshape(len(M), -1)
    f = masked.argmax(1)
    return k, f // G, f % G


def main():
    c = C3.get_ctx3()
    ev, y = c.ev, c.y
    sp = c.base_sp
    P0 = sp[["pH", "pD", "pA"]].to_numpy()
    res, burn, hist = RC.walk_forward_recal(ev.date, sp.mu.to_numpy(), sp.nu.to_numpy(), P0, y, [k for k, _ in KINDS])
    L = ["## Esperimento C — Ordered logit di ricalibrazione sopra il baseline v6", "",
         f"Rifit settimanale sul passato (finestra espansiva), burn-in di {RC.N_MIN} partite con identità ({burn} partite di test). "
         "Input: x1 = log(λ casa/λ ospite), x2 = λ casa + λ ospite del modello baseline; output: 1X2.", ""]
    rows = []
    for k, desc in KINDS:
        r = C3.compare3(res[k], c, desc)
        rows.append((k, r))
        C2.reg_save("R3 C " + desc, sp.assign(pH=res[k][:, 0], pD=res[k][:, 1], pA=res[k][:, 2]))
    best_val = max(r["val"]["d"] for _, r in rows)
    chosen_k, chosen = next((k, r) for k, r in rows if r["val"]["d"] >= best_val - TIE)
    L += C3.md_table([r for _, r in rows]) + [""]
    L += [f"Scelta sulle validazione (parità entro {TIE} → il semplice): **{chosen['name']}** (Δ validazione {chosen['val']['d']:+.5f}). "
          f"Verdetto: **{C3.verdict(chosen)}**.", ""]
    L += C3.md_detail(chosen)
    zD = (y == 1).astype(float)
    L += [f"Pareggio: previsto medio {P0[:, 1].mean():.4f} → {res[chosen_k][:, 1].mean():.4f} dopo la ricalibrazione "
          f"(reale {zD.mean():.4f}). Parametri dell'ultimo rifit: " + ", ".join(f"{v:.3f}" for v in hist[chosen_k][-1][1]) + ".", ""]

    if C3.verdict(chosen) == "migliora":
        Pn = res[chosen_k]
        M = models.score_matrix(sp.mu.to_numpy(), sp.nu.to_numpy(), sp.rho.to_numpy())
        Mt = RC.tilt_matrix(M, P0, Pn)
        Mt /= Mt.sum((1, 2), keepdims=True)
        G = M.shape[1]
        ii, jj = np.indices((G, G))
        hg, ag = ev.hg.to_numpy(), ev.ag.to_numpy()
        res_out = ev.res.to_numpy()
        def binm(Mx, mask, z):
            p = np.clip((Mx * mask[None]).sum((1, 2)), 1e-9, 1 - 1e-9)
            return -(z * np.log(p) + (1 - z) * np.log(1 - p)), p
        z_over, z_btts = (hg + ag >= 3).astype(float), ((hg >= 1) & (ag >= 1)).astype(float)
        lo_, po_ = binm(M, ii + jj >= 3, z_over); ln_, pn_ = binm(Mt, ii + jj >= 3, z_over)
        lb_, pb_ = binm(M, (ii >= 1) & (jj >= 1), z_btts); lbn_, pbn_ = binm(Mt, (ii >= 1) & (jj >= 1), z_btts)
        d1, d2 = C3.ci_block(lo_ - ln_, c.weeks), C3.ci_block(lb_ - lbn_, c.weeks)
        k0, i0, j0 = rec_scores(M, P0, REC_DRAW_THRESHOLD)
        k1, i1, j1 = rec_scores(Mt, Pn, REC_DRAW_THRESHOLD)
        err = np.abs(models.probs_1x2(Mt) - Pn / Pn.sum(1, keepdims=True)).max()
        L += ["### Applicazione alla matrice dei punteggi (riscalando ogni cella per P_nuova/P_vecchia del suo esito)", "",
              f"- 1X2 della matrice riponderata = 1X2 ricalibrato (errore massimo {err:.1e}).",
              f"- Over 2.5, log-loss: {lo_.mean():.4f} → {ln_.mean():.4f}; Δ (prima − dopo) {d1[0]:+.5f}, IC a blocchi [{d1[1]:+.5f}, {d1[2]:+.5f}]; "
              f"probabilità media {po_.mean():.4f} → {pn_.mean():.4f} (reale {z_over.mean():.4f}).",
              f"- BTTS, log-loss: {lb_.mean():.4f} → {lbn_.mean():.4f}; Δ {d2[0]:+.5f}, IC a blocchi [{d2[1]:+.5f}, {d2[2]:+.5f}]; "
              f"probabilità media {pb_.mean():.4f} → {pbn_.mean():.4f} (reale {z_btts.mean():.4f}).",
              f"- Esito consigliato (soglia pareggio {REC_DRAW_THRESHOLD}): cambia in {(k0 != k1).mean() * 100:.1f}% delle partite; pareggi consigliati "
              f"{np.mean(k0 == 1) * 100:.1f}% → {np.mean(k1 == 1) * 100:.1f}% (reali {np.mean(res_out == 1) * 100:.1f}%); esito giusto "
              f"{np.mean(k0 == res_out) * 100:.1f}% → {np.mean(k1 == res_out) * 100:.1f}%; risultato esatto "
              f"{np.mean((i0 == hg) & (j0 == ag)) * 100:.2f}% → {np.mean((i1 == hg) & (j1 == ag)) * 100:.2f}%.", ""]
    else:
        L += ["La ricalibrazione non «migliora» secondo la regola scritta prima: non è stata applicata alla matrice dei punteggi "
              "(come richiesto, solo se migliora).", ""]
    with open(os.path.join(C3.PARTS, "C.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    pd.to_pickle(dict(res=[{k: v for k, v in r.items() if k not in ("d_vec", "ok")} for _, r in rows], chosen=chosen_k),
                 os.path.join(C3.R3_DIR, "r3_C.pkl"))
    print("\n".join(L))


if __name__ == "__main__":
    main()
