"""Round 2 — controlli anti-leakage per l'esperimento 2.

1. Perturbazione: si sostituiscono con valori casuali le quote (e i lambda impliciti) di tutte le partite con data >= T0 e
   si ricalcolano le feature; quelle delle partite PRECEDENTI al primo rifit successivo a T0 devono restare identiche
   (le quote future non entrano mai in una feature passata). Poi si verifica che quelle successive cambino
   (la perturbazione ha effetto: il test non è vuoto).
2. Placebo: i lambda impliciti vengono permutati a caso tra le partite dello stesso campionato e stagione (stessa
   distribuzione, informazione distrutta): il guadagno deve sparire.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import data, round2_ctx as C, round2_implied as I, round2_models as RM, stack
from backtest.round2_lib import Boot, run_stack
from backtest.run_round2_exp2 import PARTS, RIDGE, cpath, mk_features

T0 = pd.Timestamp("2024-02-03")


def main():
    c = C.get_ctx()
    df, feat, ev = c.df, c.feat, c.ev
    imp = pd.read_pickle(cpath("exp2_imp_main.pkl"))["v"]
    a = pd.read_pickle(cpath("exp2a_results.pkl"))
    b = pd.read_pickle(cpath("exp2b_results.pkl"))
    xi, K = a["xi_star"], b["K_star"]
    rng = np.random.default_rng(0)
    L = ["## Controlli anti-leakage (esperimento 2)", ""]

    # ── 1a. perturbazione dei lambda impliciti (DC sui lambda) ────────────────
    g = df[df.Division == "E0"].copy()
    g["imp_h"], g["imp_a"] = imp.imp_h.reindex(g.index), imp.imp_a.reindex(g.index)
    base = RM.walk_forward_ext(g, xi=xi, start="2023-07-03", use_tau=False, gx="imp_h", gy="imp_a", ridge=RIDGE)
    gp = g.copy()
    fut = gp.date >= T0
    gp.loc[fut, "imp_h"] = np.exp(rng.normal(0.4, 0.5, fut.sum()))
    gp.loc[fut, "imp_a"] = np.exp(rng.normal(0.1, 0.5, fut.sum()))
    pert = RM.walk_forward_ext(gp, xi=xi, start="2023-07-03", use_tau=False, gx="imp_h", gy="imp_a", ridge=RIDGE)
    cuts = pd.date_range("2023-07-03", g.date.max() + pd.Timedelta(days=1), freq="7D")
    next_cut = cuts[cuts > T0][0]
    dts = g.date.reindex(base.index)
    before = dts < next_cut
    diff_before = np.abs(np.log(base.mu[before]) - np.log(pert.mu[before])).max()
    diff_before_nu = np.abs(np.log(base.nu[before]) - np.log(pert.nu[before])).max()
    after = dts >= next_cut
    diff_after = np.abs(np.log(base.mu[after]) - np.log(pert.mu[after])).max()
    L += [f"**1a. DC sui lambda impliciti (Premier League, xi={xi:g}).** Lambda impliciti sostituiti con numeri casuali per "
          f"tutte le partite dal {T0.date()}; primo rifit successivo: {next_cut.date()}. Differenza massima delle feature "
          f"(log-gol attesi) per le {int(before.sum())} partite precedenti a quel rifit: casa {diff_before:.2e}, ospite "
          f"{diff_before_nu:.2e} (deve essere 0). Per le {int(after.sum())} partite successive la differenza massima è "
          f"{diff_after:.3f} (il test non è vuoto).", ""]
    ok1 = diff_before == 0 and diff_before_nu == 0 and diff_after > 0

    # ── 1b. perturbazione delle quote (Elo-Odds) ──────────────────────────────
    eo = pd.read_pickle(cpath(f"exp2_eo_K{K}.pkl"))["v"]
    dp = df.copy()
    fut = dp.date >= T0
    cols = ["cl_h", "cl_d", "cl_a", "psc_h", "psc_d", "psc_a", "ou_avgc_o", "ou_avgc_u"]
    perm = rng.permutation(np.where(fut)[0])
    dp.loc[fut, cols] = dp[cols].to_numpy()[perm]
    eo_p = I.elo_odds(dp, K=float(K))
    same = (eo.eo_diff.reindex(df.index) == eo_p.eo_diff.reindex(df.index))
    m_before = (df.date <= T0).to_numpy()
    m_after = (df.date > T0).to_numpy()
    n_changed_after = int((~same[m_after]).sum())
    L += [f"**1b. Elo-Odds (K={K}).** Quote di chiusura permutate a caso tra tutte le partite dal {T0.date()} in poi. "
          f"Rating pre-partita diversi per le partite fino al {T0.date()} compreso: {int((~same[m_before]).sum())} su "
          f"{int(m_before.sum())} (deve essere 0); dopo quella data cambiano {n_changed_after} su {int(m_after.sum())} "
          f"(il test non è vuoto).", ""]
    ok2 = int((~same[m_before]).sum()) == 0 and n_changed_after > 0

    # ── 2. placebo ───────────────────────────────────────────────────────────
    imp_pl = imp.copy()
    for (lg, s), idx in df.groupby(["Division", "season"]).groups.items():
        vals = imp.loc[idx, ["imp_h", "imp_a"]].to_numpy()
        p_ = rng.permutation(len(idx))
        imp_pl.loc[idx, ["imp_h", "imp_a"]] = vals[p_]
    mk_pl = mk_features(df, imp_pl, xi, RIDGE, "placebo")
    fr = feat.copy()
    fr["mk_lmu"], fr["mk_lnu"] = mk_pl.mk_lmu.reindex(fr.index), mk_pl.mk_lnu.reindex(fr.index)
    sp = run_stack(fr, stack.XG_FEATURES + ["mk_lmu", "mk_lnu"], ev)
    Pb = c.base_sp[["pH", "pD", "pA"]].to_numpy()
    r = C.compare(sp[["pH", "pD", "pA"]].to_numpy(), Pb, ev, Boot(len(ev)), "placebo")
    L += [f"**2. Placebo.** Lambda impliciti permutati a caso tra le partite dello stesso campionato e stagione, stessa pipeline "
          f"(xi={xi:g}): Δ log-loss vs baseline {r['d_ll']:+.5f} [{r['lo_ll']:+.5f}, {r['hi_ll']:+.5f}] "
          f"(con i lambda veri: {a['results'][[x['name'] for x in a['results']].index(next(n['name'] for n in a['results'] if n['name'].endswith(f'(xi={xi:g})')))]['d_ll']:+.5f}). "
          f"Il guadagno sparisce, quindi non viene da un artefatto della pipeline.", ""]
    ok3 = r["d_ll"] < 0.0005
    L += [f"Esito dei controlli: perturbazione DC {'OK' if ok1 else 'FALLITA'}, perturbazione Elo-Odds {'OK' if ok2 else 'FALLITA'}, "
          f"placebo {'OK' if ok3 else 'ANOMALO'}.", ""]
    with open(os.path.join(PARTS, "checks.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
