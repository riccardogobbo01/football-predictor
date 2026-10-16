"""Round 2 — Esperimento 2: forze implicite dalle quote passate (solo backtest).

Stage A  gol attesi impliciti per ogni partita (quote di chiusura, margine rimosso, Poisson+rho fisso)
Stage B  modello di forza Dixon-Coles (senza tau) con target = lambda impliciti, walk-forward settimanale,
         stesso decadimento esponenziale (xi da ottimizzare) e stessa ridge degli xG
Stage C  stack Poisson con feature in più; variante Elo-Odds
Regola anti-leakage: nel walk-forward ogni rifit usa solo partite con data < data del rifit (come per gli xG).
"""
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from backtest import data, round2_ctx as C, round2_implied as I, round2_models as RM, stack
from backtest.round2_lib import Boot, ll_vec, run_stack

PARTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "round2_parts")
os.makedirs(PARTS, exist_ok=True)
RHO_FIX = -0.08            # scelto sul solo mercato (minimizza l'errore di ricostruzione delle probabilità)
XI_GRID = [0.002, 0.003, 0.004, 0.005]
MK_START = "2016-07-04"
RIDGE = 2.0


def cpath(name):
    return os.path.join(C.R2_DIR, name)


def cached(name, fn, key):
    p = cpath(name)
    if os.path.exists(p):
        d = pd.read_pickle(p)
        if d["key"] == key:
            return d["v"]
    v = fn()
    pd.to_pickle(dict(key=key, v=v), p)
    return v


def _job(g, xi, ridge, col_h, col_a):
    return RM.walk_forward_ext(g, xi=xi, start=MK_START, use_tau=False, gx=col_h, gy=col_a, ridge=ridge)


def mk_features(df, imp, xi, ridge=RIDGE, tag=""):
    """DC (senza tau) sui lambda impliciti. imp: DataFrame con imp_h, imp_a (indice df). -> DataFrame mk_lmu, mk_lnu."""
    key = (len(df), str(df.date.max()), tag, xi, ridge)

    def go():
        d = df.assign(imp_h=imp.imp_h, imp_a=imp.imp_a)
        res = Parallel(n_jobs=8)(delayed(_job)(d[d.Division == lg], xi, ridge, "imp_h", "imp_a") for lg in data.LEAGUES)
        r = pd.concat(res).sort_index()
        return pd.DataFrame({"mk_lmu": np.log(r.mu), "mk_lnu": np.log(r.nu)}, index=r.index)
    return cached(f"exp2_mk_{tag}_xi{xi:g}_r{ridge:g}.pkl", go, key)


def pre_test_error(mk, imp, df):
    """Errore (log-scala) tra lambda predetto e lambda implicito nelle stagioni 2016-2018 (prima del test):
    criterio per scegliere xi SENZA usare né gli esiti né il periodo di test."""
    m = (df.season.isin([2016, 2017, 2018])) & mk.mk_lmu.notna().reindex(df.index).fillna(False)
    m = m & imp.imp_h.notna()
    a = (mk.mk_lmu.reindex(df.index)[m] - np.log(imp.imp_h[m])) ** 2
    b = (mk.mk_lnu.reindex(df.index)[m] - np.log(imp.imp_a[m])) ** 2
    return float((a.mean() + b.mean()) / 2), int(m.sum())


def main():
    c = C.get_ctx()
    ev, feat, df = c.ev, c.feat, c.df
    boot = Boot(len(ev))
    Pb = c.base_sp[["pH", "pD", "pA"]].to_numpy()
    y = c.y
    L = ["## Esperimento 2 — Forze implicite dalle quote passate", ""]
    key0 = (len(df), str(df.date.max()))

    # ── Stage A: gol attesi impliciti ─────────────────────────────────────────
    t = time.time()
    imp_main = cached("exp2_imp_main.pkl", lambda: I.implied_lambdas(df, "avg", "power", RHO_FIX), key0)
    imp_ind = cached("exp2_imp_ind.pkl", lambda: I.implied_lambdas(df, "avg", "power", 0.0), key0)
    imp_pin = cached("exp2_imp_pin.pkl", lambda: I.implied_lambdas(df, "pin", "power", RHO_FIX), key0)
    print("implied", time.time() - t, flush=True)

    T, h12, hou, src = I.implied_inputs(df, "avg")
    evm = df.index.isin(ev.index)
    n_ev = int(evm.sum())
    miss_ou_ev = int((~hou[evm]).sum())
    L += ["### Gol attesi impliciti: copertura e gestione dei dati mancanti", "",
          f"- Quote 1X2 di chiusura: {int(h12.sum())}/{len(df)} partite (2012/13 → oggi; Pinnacle in chiusura fino al 2018/19, "
          f"media di mercato in chiusura dal 2019/20). Senza 1X2 (4 partite) il lambda implicito è NaN e la partita "
          f"non entra nei rifit.",
          f"- Quote Over/Under 2.5: per le stagioni 2012/13-2018/19 la chiusura O/U non esiste nei file; si usa la media "
          f"pre-chiusura dei bookmaker (BbAv>2.5 / BbAv<2.5), dal 2019/20 la chiusura media (AvgC>2.5 / AvgC<2.5). "
          f"Partite con O/U da chiusura: {int((src == 1).sum())}, da media pre-chiusura: {int((src == 2).sum())}, "
          f"**senza alcuna quota O/U: {int((src == 0).sum())}** su {len(df)} (di cui {miss_ou_ev} nel periodo di test, "
          f"{n_ev} partite).",
          "- Gestione: dove manca l'O/U si risolve con le sole tre probabilità 1X2 (2 incognite, 2 equazioni indipendenti: "
          "sistema esattamente identificato, stesso solver). Con una sola partita interessata la scelta è irrilevante.",
          f"- Rimozione del margine: metodo power (il migliore dell'esperimento 0, a pari merito con Shin; differenze ≤ 0.0004).",
          f"- Ricostruzione: Poisson con correlazione Dixon-Coles fissa rho = {RHO_FIX} (scelta guardando solo la capacità di "
          f"riprodurre le probabilità di mercato, minimo dell'errore su una griglia 0 / −0.05 / −0.08 / −0.10 / −0.13 / −0.16: "
          f"nessun esito di partita coinvolto). Con Poisson indipendente (rho=0) il pareggio di mercato è sottostimato di 1.6 punti "
          f"percentuali in media; con rho=−0.08 di circa 0.6.", ""]
    m = imp_main.imp_h.notna()
    L += [f"Qualità della ricostruzione (rho={RHO_FIX}): errore medio assoluto su P(1)/P(X)/P(2): "
          + "/".join(f"{x:.4f}" for x in np.abs(I.model_probs(imp_main.imp_h[m].values, imp_main.imp_a[m].values, RHO_FIX)[:, :3]
                                               - T[m.values][:, :3]).mean(0))
          + f"; gol attesi impliciti medi {imp_main.imp_h[m].mean():.3f} - {imp_main.imp_a[m].mean():.3f} contro gol reali "
            f"{df.hg[m].mean():.3f} - {df.ag[m].mean():.3f}.", ""]

    # ── Stage B+C: forze implicite e stack, griglia su xi ─────────────────────
    frame = feat.copy()
    results, mk_by_xi, pre_err = [], {}, {}
    for xi in XI_GRID:
        t = time.time()
        mk = mk_features(df, imp_main, xi, RIDGE, "main")
        mk_by_xi[xi] = mk
        pre_err[xi] = pre_test_error(mk, imp_main, df)
        fr = frame.assign(mk_lmu=mk.mk_lmu.reindex(frame.index), mk_lnu=mk.mk_lnu.reindex(frame.index))
        sp = run_stack(fr, stack.XG_FEATURES + ["mk_lmu", "mk_lnu"], ev)
        name = f"2a — stack + forze implicite (xi={xi:g})"
        C.reg_save("E2 " + name, sp)
        results.append(C.compare(sp[["pH", "pD", "pA"]].to_numpy(), Pb, ev, boot, name))
        print(name, f"{time.time() - t:.0f}s  Δ={results[-1]['d_ll']:+.5f}", flush=True)

    best_pre = min(XI_GRID, key=lambda x: pre_err[x][0])
    sel = []
    for xi in XI_GRID:
        r = results[XI_GRID.index(xi)]
        seas = r["by_season"]
        early = np.average([seas[s][0] for s in (2019, 2020, 2021)], weights=[seas[s][1] for s in (2019, 2020, 2021)])
        late = np.average([v[0] for s, v in seas.items() if s >= 2022], weights=[v[1] for s, v in seas.items() if s >= 2022])
        sel.append((xi, pre_err[xi][0], early, late))
    best_early = max(sel, key=lambda r: r[2])[0]
    L += ["### 2a — Modello di forza DC sui lambda impliciti → feature dello stack", "",
          "Come per gli xG: DC senza tau (attacco / difesa / casa), finestra 5 anni, rifit settimanale, ridge = 2, target "
          "continuo = lambda implicito della partita. Le feature `mk_lmu`, `mk_lnu` (log gol attesi del modello di forza) si "
          "aggiungono a quelle del baseline (DC gol, tiri in porta, pi-ratings, xG) nelle due regressioni di Poisson; "
          "training dello stack dal 2016/17, test dal 2019/20, come il baseline.", "",
          "**Scelta del decadimento xi.** Tre criteri, mostrati per trasparenza: (i) errore di previsione del lambda implicito "
          "nelle stagioni 2016-2018 (precedenti al test; nessun esito, nessun dato di test); (ii) Δ log-loss dello stack "
          "nelle stagioni 2019/20-2021/22 (periodo di scelta); (iii) Δ log-loss nelle stagioni 2022/23 → oggi (valutazione "
          "fuori dal periodo di scelta).", "",
          "| xi | MSE log-lambda 2016-18 | Δ log-loss 2019-21 | Δ log-loss 2022→ | Δ log-loss totale [IC 95%] |",
          "|---:|---:|---:|---:|---|"]
    for (xi, pe, early, late), r in zip(sel, results):
        L.append(f"| {xi:g} | {pe:.5f} | {early:+.5f} | {late:+.5f} | {r['d_ll']:+.5f} [{r['lo_ll']:+.5f}, {r['hi_ll']:+.5f}] |")
    L += ["", f"Scelto xi = **{best_pre:g}** con il criterio (i) (pre-test, indipendente dal periodo di valutazione); "
              f"il criterio (ii) avrebbe scelto xi = {best_early:g}.", ""]
    xi_star = best_pre
    L += C.md_summary_rows(results) + [""]
    for r in results:
        if r["name"].endswith(f"(xi={xi_star:g})"):
            L += C.md_variant(r, title=r["name"] + " — variante principale")
    pd.to_pickle(dict(results=results, xi_star=xi_star, pre_err=pre_err, sel=sel), cpath("exp2a_results.pkl"))
    with open(os.path.join(PARTS, "exp2_a.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
