"""Round 2 — Esperimento 2 (parte b): sensibilità, varianti (Pinnacle, Poisson indipendente, ridge, senza xG)
ed Elo-Odds. Usa le funzioni della parte a."""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import data, round2_ctx as C, round2_implied as I, stack
from backtest.round2_lib import Boot, run_stack
from backtest.run_round2_exp2 import (PARTS, RHO_FIX, RIDGE, XI_GRID, cached, cpath, mk_features, pre_test_error)

XI_EXT = [0.006, 0.008, 0.010, 0.015]
K_GRID = [5, 10, 20, 30, 45, 60, 80, 100, 150, 200, 300, 500]


def main():
    c = C.get_ctx()
    ev, feat, df = c.ev, c.feat, c.df
    boot = Boot(len(ev))
    Pb = c.base_sp[["pH", "pD", "pA"]].to_numpy()
    key0 = (len(df), str(df.date.max()))
    a = pd.read_pickle(cpath("exp2a_results.pkl"))
    xi_star = a["xi_star"]
    imp_main = pd.read_pickle(cpath("exp2_imp_main.pkl"))["v"]
    imp_ind = pd.read_pickle(cpath("exp2_imp_ind.pkl"))["v"]
    imp_pin = pd.read_pickle(cpath("exp2_imp_pin.pkl"))["v"]
    L = ["### 2a — sensibilità e varianti", ""]

    def stack_with(mk, extra_cols=None, name="", base_cols=None):
        fr = feat.copy()
        cols = list(base_cols if base_cols is not None else stack.XG_FEATURES) + ["mk_lmu", "mk_lnu"]
        fr["mk_lmu"], fr["mk_lnu"] = mk.mk_lmu.reindex(fr.index), mk.mk_lnu.reindex(fr.index)
        if extra_cols:
            for k, v in extra_cols.items():
                fr[k] = v.reindex(fr.index)
            cols += list(extra_cols)
        sp = run_stack(fr, cols, ev)
        C.reg_save("E2 " + name, sp)
        return C.compare(sp[["pH", "pD", "pA"]].to_numpy(), Pb, ev, boot, name)

    # ── decadimento oltre il range richiesto ──────────────────────────────────
    res_ext, pre = [], {}
    for xi in XI_EXT:
        mk = mk_features(df, imp_main, xi, RIDGE, "main")
        pre[xi] = pre_test_error(mk, imp_main, df)[0]
        res_ext.append(stack_with(mk, name=f"2a — forze implicite, xi={xi:g} (oltre il range richiesto)"))
    L += ["**Decadimento oltre il range 0.002-0.005** (sensibilità: l'ottimo del range richiesto è al bordo).", "",
          "| xi | MSE log-lambda 2016-18 | Δ log-loss totale | IC 95% | Stagioni migliorate |", "|---:|---:|---:|---|---:|"]
    pre_all = {**{xi: a["pre_err"][xi][0] for xi in XI_GRID}, **pre}
    for xi, r in zip(XI_EXT, res_ext):
        L.append(f"| {xi:g} | {pre[xi]:.5f} | {r['d_ll']:+.5f} | [{r['lo_ll']:+.5f}, {r['hi_ll']:+.5f}] | {r['seasons_better'][0]}/{r['seasons_better'][1]} |")
    xi_best_all = min(pre_all, key=pre_all.get)
    L += ["", f"Minimo dell'errore pre-test sull'intera griglia: xi = {xi_best_all:g}. "
              f"Per le varianti sotto si usa xi = {xi_star:g} (miglior valore DENTRO il range richiesto).", ""]

    # ── varianti a xi_star ────────────────────────────────────────────────────
    mk_star = mk_features(df, imp_main, xi_star, RIDGE, "main")
    vs = []
    vs.append(next(r for r in a["results"] if r["name"].endswith(f"(xi={xi_star:g})")))
    vs[0] = dict(vs[0], name=f"2a — principale (closing medio, rho={RHO_FIX}, ridge {RIDGE:g}, xi={xi_star:g})")
    for rg in (0.5, 5.0):
        mk = mk_features(df, imp_main, xi_star, rg, "main")
        vs.append(stack_with(mk, name=f"2a — ridge {rg:g} (xi={xi_star:g})"))
    mk_i = mk_features(df, imp_ind, xi_star, RIDGE, "ind")
    vs.append(stack_with(mk_i, name=f"2a — Poisson indipendente (rho=0), xi={xi_star:g}"))
    mk_p = mk_features(df, imp_pin, xi_star, RIDGE, "pin")
    vs.append(stack_with(mk_p, name=f"2a — Pinnacle in chiusura (dove disponibile), xi={xi_star:g}"))
    vs.append(stack_with(mk_star, name=f"2a — senza xG nello stack (sostituisce l'xG), xi={xi_star:g}",
                         base_cols=stack.PRODUCTION_FEATURES))
    L += ["**Varianti** (xi fisso come sopra; ogni riga da sola vs baseline).", ""] + C.md_summary_rows(vs) + [""]
    L += ["Nota sulla variante Pinnacle: le quote Pinnacle in chiusura mancano per metà del 2025/26 e per tutto il "
          "2026/27; dove mancano si ricade sulla media di mercato in chiusura. La variante \"senza xG\" toglie xg_lmu/xg_lnu "
          "dallo stack e li sostituisce con le forze implicite: dice quanto delle informazioni xG è già contenuto nel mercato.", ""]

    # ── variante b: Elo-Odds ─────────────────────────────────────────────────
    res_eo, eo_pre, eo_store = [], {}, {}
    for K in K_GRID:
        eo = cached(f"exp2_eo_K{K}.pkl", lambda K=K: I.elo_odds(df, K=float(K)), key0 + (K,))
        eo_store[K] = eo
        T, h12, _, _ = I.implied_inputs(df, "avg")
        S = np.where(h12, T[:, 0] + 0.5 * T[:, 1], np.nan)
        m = df.season.isin([2016, 2017, 2018]).to_numpy() & np.isfinite(S)
        eo_pre[K] = float(np.mean((eo.eo_exp.to_numpy()[m] - S[m]) ** 2))
        fr = feat.copy()
        fr["eo_diff"] = eo.eo_diff.reindex(fr.index)
        sp = run_stack(fr, stack.XG_FEATURES + ["eo_diff"], ev)
        nm = f"2b — Elo-Odds, K={K}"
        C.reg_save("E2 " + nm, sp)
        res_eo.append(C.compare(sp[["pH", "pD", "pA"]].to_numpy(), Pb, ev, boot, nm))
        print(nm, f"{res_eo[-1]['d_ll']:+.5f}", flush=True)
    K_star = min(K_GRID, key=lambda k: eo_pre[k])
    L += ["### 2b — Elo-Odds (Wunderlich & Memmert)", "",
          "Elo per campionato in cui il \"risultato\" è S = P(1) + 0.5·P(X) dalle quote di chiusura senza margine (power); "
          "vantaggio casa HFA = media corrente di S nel campionato; squadra nuova = media delle 3 più deboli; feature dello stack "
          "= differenza di rating pre-partita `eo_diff` (rating casa − ospite). K scelto col criterio pre-test: errore "
          "quadratico tra punteggio atteso Elo e S nelle stagioni 2016-2018 (nessun esito, nessun dato di test).", "",
          "| K | MSE(E−S) 2016-18 | Log-loss | Δ log-loss vs baseline | IC 95% | Stagioni migliorate |",
          "|---:|---:|---:|---:|---|---:|"]
    for K, r in zip(K_GRID, res_eo):
        L.append(f"| {K} | {eo_pre[K]:.5f} | {r['ll']:.4f} | {r['d_ll']:+.5f} | [{r['lo_ll']:+.5f}, {r['hi_ll']:+.5f}] | "
                 f"{r['seasons_better'][0]}/{r['seasons_better'][1]} |")
    L += ["", f"K scelto col criterio pre-test: **{K_star}**.", ""]
    r_star = res_eo[K_GRID.index(K_star)]
    L += C.md_variant(r_star, title=f"2b — Elo-Odds K={K_star} — variante principale")

    # ── combinazione 2a + 2b ──────────────────────────────────────────────────
    fr = feat.copy()
    fr["mk_lmu"], fr["mk_lnu"] = mk_star.mk_lmu.reindex(fr.index), mk_star.mk_lnu.reindex(fr.index)
    fr["eo_diff"] = eo_store[K_star].eo_diff.reindex(fr.index)
    sp = run_stack(fr, stack.XG_FEATURES + ["mk_lmu", "mk_lnu", "eo_diff"], ev)
    nm = f"2a+2b — forze implicite (xi={xi_star:g}) + Elo-Odds (K={K_star})"
    C.reg_save("E2 " + nm, sp)
    r_comb = C.compare(sp[["pH", "pD", "pA"]].to_numpy(), Pb, ev, boot, nm)
    L += ["**Combinazione 2a + 2b nello stesso stack**", ""] + C.md_summary_rows([r_comb]) + [""]
    pd.to_pickle(dict(res_ext=res_ext, variants=vs, res_eo=res_eo, K_star=K_star, r_comb=r_comb, xi_star=xi_star,
                      pre_all=pre_all, eo_pre=eo_pre), cpath("exp2b_results.pkl"))
    with open(os.path.join(PARTS, "exp2_b.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
