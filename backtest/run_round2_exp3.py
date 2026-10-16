"""Round 2 — Esperimento 3: ricalibrazione 1X2 walk-forward (solo backtest)."""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import data, models, round2_ctx as C, round2_recal as RC
from backtest.round2_lib import Boot, ll_vec, metric_vecs
from config import REC_DRAW_THRESHOLD

PARTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "round2_parts")
KINDS = [("ol", "Ordered logit (4 parametri)"), ("olflex", "Ordered logit flessibile (banda del pareggio dipende da gol attesi)"),
         ("ts", "Temperature scaling globale"), ("ts_d", "Temperature scaling con T separata per il pareggio"),
         ("ts_b", "Temperature scaling + bias sul pareggio")]
BEST_NAME = "E2 2b — Elo-Odds, K=200"


def rec_outcome(P, thr):
    """Esito consigliato: argmax se supera la soglia, altrimenti pareggio (come in produzione)."""
    k = P.argmax(1)
    return np.where(P.max(1) > thr, k, 1)


def rec_scores(M, P, thr):
    """Punteggio consigliato (i, j) dalla matrice M e dalle probabilità P: prima l'esito, poi la cella migliore."""
    G = M.shape[1]
    ii, jj = np.indices((G, G))
    cls = np.where(ii > jj, 0, np.where(ii == jj, 1, 2))
    k = rec_outcome(P, thr)
    masked = np.where(cls[None] == k[:, None, None], M, -1.0).reshape(len(M), -1)
    f = masked.argmax(1)
    return k, f // G, f % G


def main():
    c = C.get_ctx()
    ev, y = c.ev, c.y
    boot = Boot(len(ev))
    reg = C.reg_load()
    inputs = [("baseline", c.base_sp), ("migliore tra 1 e 2 (Elo-Odds K=200)", reg[BEST_NAME]["sp"])]
    P0_base = c.base_sp[["pH", "pD", "pA"]].to_numpy()
    L = ["## Esperimento 3 — Ricalibrazione 1X2", "",
         f"Ricalibratore rifittato ogni 7 giorni su TUTTE le previsioni out-of-sample del modello di partenza per partite già "
         f"concluse (finestra espansiva, dalla prima partita di test); finché le partite concluse sono meno di {RC.N_MIN} si usa "
         f"l'identità (burn-in: le prime settimane del 2019/20). Input: x1 = log(λ casa/λ ospite), x2 = λ casa + λ ospite; output: "
         f"1X2. Δ = log-loss(modello di partenza) − log-loss(ricalibrato): positivo = la ricalibrazione migliora; IC 95% bootstrap "
         f"appaiato per partita.", ""]
    store = {}
    for label, sp in inputs:
        P0 = sp[["pH", "pD", "pA"]].to_numpy()
        mu, nu = sp.mu.to_numpy(), sp.nu.to_numpy()
        res, burn, hist = RC.walk_forward_recal(ev.date, mu, nu, P0, y, [k for k, _ in KINDS])
        rows = []
        for k, desc in KINDS:
            r_in = C.compare(res[k], P0, ev, boot, desc)               # vs il modello di partenza
            r_base = C.compare(res[k], P0_base, ev, boot, desc)        # vs baseline
            rows.append((k, desc, r_in, r_base))
        store[label] = dict(res=res, rows=rows, burn=burn, hist=hist, P0=P0, sp=sp)
        L += [f"### Ricalibrazione di: {label}", "",
              f"Partite in burn-in (identità): {burn} su {len(ev)}.", "",
              "| Ricalibratore | Log-loss | RPS | Brier | Δ log-loss vs modello di partenza [IC 95%] | Δ vs baseline [IC 95%] | Stagioni migliorate (vs partenza) |",
              "|---|---:|---:|---:|---|---|---:|"]
        for k, desc, ri, rb in rows:
            L.append(f"| {desc} | {ri['ll']:.4f} | {ri['rps']:.4f} | {ri['brier']:.4f} | {ri['d_ll']:+.5f} "
                     f"[{ri['lo_ll']:+.5f}, {ri['hi_ll']:+.5f}] | {rb['d_ll']:+.5f} [{rb['lo_ll']:+.5f}, {rb['hi_ll']:+.5f}] | "
                     f"{ri['seasons_better'][0]}/{ri['seasons_better'][1]} |")
        L.append("")
        bestk = max(rows, key=lambda r: r[2]["d_ll"])
        L += C.md_variant(bestk[2], title=f"Dettaglio del migliore ({bestk[1]}) vs {label}")
        # stato del pareggio dopo la ricalibrazione
        zD = (y == 1).astype(float)
        Pn = res[bestk[0]]
        L += [f"Pareggio dopo la ricalibrazione ({bestk[1]}): previsto medio {Pn[:, 1].mean():.4f} contro reale {zD.mean():.4f} "
              f"(prima {P0[:, 1].mean():.4f}).", ""]
        # ultimi parametri
        last = hist[bestk[0]][-1][1]
        L += [f"Parametri dell'ultimo rifit ({bestk[0]}): " + ", ".join(f"{v:.3f}" for v in last) + ".", ""]
        store[label]["best"] = bestk[0]

    # ── coerenza con punteggio consigliato e mercati derivati ─────────────────
    L += ["### Coerenza di punteggio consigliato e mercati derivati", ""]
    for label, st in store.items():
        k = st["best"]
        sp = st["sp"]
        Pn, Po = st["res"][k], st["P0"]
        M = models.score_matrix(sp.mu.to_numpy(), sp.nu.to_numpy(), sp.rho.to_numpy())
        Mt = RC.tilt_matrix(M, Po, Pn)
        Mt /= Mt.sum((1, 2), keepdims=True)
        G = M.shape[1]
        ii, jj = np.indices((G, G))
        # 1X2 dalla matrice riponderata
        P_chk = models.probs_1x2(Mt)
        err = np.abs(P_chk - Pn / Pn.sum(1, keepdims=True)).max()
        over = (ii + jj >= 3)
        btts = (ii >= 1) & (jj >= 1)
        hg, ag = ev.hg.to_numpy(), ev.ag.to_numpy()
        z_over, z_btts = (hg + ag >= 3).astype(float), ((hg >= 1) & (ag >= 1)).astype(float)

        def bin_metrics(Mx, mask, z):
            p = np.clip((Mx * mask[None]).sum((1, 2)), 1e-9, 1 - 1e-9)
            return -(z * np.log(p) + (1 - z) * np.log(1 - p)), (p - z) ** 2, p
        lo_, bo_, po_ = bin_metrics(M, over, z_over)
        ln_, bn_, pn_ = bin_metrics(Mt, over, z_over)
        lb_, bb_, pb_ = bin_metrics(M, btts, z_btts)
        lbn_, bbn_, pbn_ = bin_metrics(Mt, btts, z_btts)
        d1 = boot.ci(lo_ - ln_)
        d2 = boot.ci(lb_ - lbn_)
        k0, i0, j0 = rec_scores(M, Po, REC_DRAW_THRESHOLD)
        k1, i1, j1 = rec_scores(Mt, Pn, REC_DRAW_THRESHOLD)
        res_out = ev.res.to_numpy()
        hit_out0, hit_out1 = (k0 == res_out).mean(), (k1 == res_out).mean()
        hit_sc0 = ((i0 == hg) & (j0 == ag)).mean()
        hit_sc1 = ((i1 == hg) & (j1 == ag)).mean()
        L += [f"**{label} + {dict(KINDS)[k]}**", "",
              f"- Matrice riponderata (ogni cella × P_nuova/P_vecchia della sua classe di esito): 1X2 della matrice = 1X2 ricalibrato, "
              f"errore massimo {err:.1e}.",
              f"- Over 2.5 (log-loss): prima {lo_.mean():.4f}, dopo {ln_.mean():.4f}; Δ (prima − dopo) {d1[0]:+.5f} [{d1[1]:+.5f}, {d1[2]:+.5f}]. "
              f"Probabilità media prevista: {po_.mean():.4f} → {pn_.mean():.4f} (reale {z_over.mean():.4f}).",
              f"- BTTS (log-loss): prima {lb_.mean():.4f}, dopo {lbn_.mean():.4f}; Δ {d2[0]:+.5f} [{d2[1]:+.5f}, {d2[2]:+.5f}]. "
              f"Probabilità media: {pb_.mean():.4f} → {pbn_.mean():.4f} (reale {z_btts.mean():.4f}).",
              f"- Esito consigliato (regola della produzione, soglia pareggio {REC_DRAW_THRESHOLD}): cambia in {(k0 != k1).mean() * 100:.1f}% delle partite; "
              f"pareggi consigliati {np.mean(k0 == 1) * 100:.1f}% → {np.mean(k1 == 1) * 100:.1f}% (reali {zero_if(res_out == 1) * 100:.1f}%); "
              f"esito giusto {hit_out0 * 100:.1f}% → {hit_out1 * 100:.1f}%; risultato esatto {hit_sc0 * 100:.2f}% → {hit_sc1 * 100:.2f}%.",
              f"- Senza riponderazione (si cambiano solo le tre probabilità 1X2 e si lascia la matrice com'è) la matrice resterebbe "
              f"incoerente: scarto medio tra P ricalibrata e 1X2 della matrice {np.abs(models.probs_1x2(M) - Pn).mean() * 100:.2f} punti "
              f"percentuali (massimo {np.abs(models.probs_1x2(M) - Pn).max() * 100:.1f}); in {np.mean(np.argmax(models.probs_1x2(M), 1) != np.argmax(Pn, 1)) * 100:.1f}% "
              f"delle partite l'esito più probabile della matrice non coincide con quello delle probabilità ricalibrate.", ""]
    L += ["**Come gestirlo in produzione (proposta).** Se la ricalibrazione entrasse, non va applicata solo alle tre probabilità 1X2: "
          "va applicata alla matrice dei punteggi. Si riscala ogni cella (i, j) per P_nuova/P_vecchia dell'esito a cui appartiene "
          "(casa / pareggio / trasferta) e si rinormalizza. Così 1X2, punteggio consigliato, 5 risultati esatti, Over/Under e BTTS "
          "derivano tutti dalla stessa matrice e restano coerenti per costruzione; la forma dei punteggi dentro ciascun esito non "
          "cambia. I parametri del ricalibratore (pochi numeri) si rifittano nel job settimanale di training e si salvano in "
          "models/ (JSON), il job giornaliero li applica con numpy. La soglia REC_DRAW_THRESHOLD va riverificata dopo il cambio, "
          "perché sposta la distribuzione di P(X).", ""]
    with open(os.path.join(PARTS, "exp3.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    # salva i migliori per la tabella finale
    for label, st in store.items():
        for k, desc, ri, rb in st["rows"]:
            sp2 = st["sp"].copy()
            sp2[["pH", "pD", "pA"]] = st["res"][k]
            C.reg_save(f"E3 {label} + {desc}", sp2)
    pd.to_pickle({lab: dict(rows=[(k, d, ri, rb) for k, d, ri, rb in st["rows"]], best=st["best"], burn=st["burn"])
                  for lab, st in store.items()}, os.path.join(C.R2_DIR, "exp3_results.pkl"))
    print("\n".join(L))


def zero_if(m):
    return m.mean()


if __name__ == "__main__":
    main()
