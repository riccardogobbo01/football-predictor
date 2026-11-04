"""Round 10 — verifica di produzione dell'effetto arbitro con decadimento (STATS_VERSION s6-arbitro-decay).
Il codice di produzione (`refeffect.compute` con emivita da config.REFEREE_HALF_LIFE_DAYS e `refeffect.ratio` con data di riferimento) ricostruisce il Δ
del round 10 (h = 0,5 anni), gli intervalli dei gialli restano entro 3 punti, e il serving riproduce il walk-forward.
Da lanciare:  python -I -X utf8 backtest/run_round10_prod.py   (scrive backtest/round10_parts/PROD.md)"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import refeffect, round6_lib as R6, round7_lib as L7, stats_v3
from backtest.run_round7 import SPEC, interval_gaps, prepare
from backtest.run_round7_prod import level_run
from config import LEVEL_PARAMS, REFEREE_HALF_LIFE_DAYS, REFEREE_K

P10 = os.path.join(REPO_ROOT, "backtest", "round10_parts")
HL = REFEREE_HALF_LIFE_DAYS["gialli"]


def main():
    feat, gw, weeks, st = prepare()
    stat = "gialli"
    spec = SPEC[stat]
    keys = refeffect.load_history_keys(feat).reindex(feat.index)
    ref_new, state = refeffect.compute(feat, keys, REFEREE_K, HL)                      # codice di produzione
    f2 = feat.copy()
    f2["ref_logR"] = ref_new
    run0, al0 = st[stat]["run"], st[stat]["al"]                                         # baseline: peso uniforme (s5)
    run1 = R6.run_model(f2, SPEC[stat], stats_v3.design(f2, stat, True))
    for sea, f in run1.folds.items():
        if sea == L7.FIRST_TEST:
            run1.mh[f["idx"]] = f["mh"]
            run1.ma[f["idx"]] = f["ma"]
    al1 = R6.alphas(run1, "global")
    se = feat.season.to_numpy()
    ok = (run0.mh.notna() & run1.mh.notna() & feat[spec["hc"]].notna() & feat[spec["ac"]].notna() & (feat.season >= L7.FIRST_TEST)).to_numpy()
    main_m, cur = ok & (se <= 2025), ok & (se == 2026)
    rows_m, rows_c = feat.index[main_m], feat.index[cur]
    wk_m, se_m = weeks[main_m], se[main_m]
    is_val = np.isin(se_m, L7.VALIDATION)
    v0, v1 = R6.evaluate(run0, rows_m, al0), R6.evaluate(run1, rows_m, al1)
    c = R6.compare(v0, v1, wk_m, is_val)
    ref = pd.read_pickle(os.path.join(os.path.dirname(L7.CTX7), "round10_all.pkl"))["ref"]["res"][0.5]      # (held, lo, hi, d26, verdetto) del round 10
    d_held, d_val = c["ll_tot_held"]["d"], c["ll_tot_val"]["d"]
    vc0, vc1 = R6.evaluate(run0, rows_c, al0), R6.evaluate(run1, rows_c, al1)
    d26 = float((vc0["ll_tot"] - vc1["ll_tot"]).mean())
    ok_delta = abs(d_held - ref[0]) < 1e-6 and abs(d26 - ref[3]) < 1e-6
    L = ["## Round 10 — verifica di produzione dell'effetto arbitro con decadimento (s6-arbitro-decay)", "",
         f"Emivita {HL} giorni (0,5 anni), k = {REFEREE_K}. Il codice di produzione (`refeffect.compute` con emivita) ricalcola `ref_logR`; modello dei gialli come in produzione (senza livello stagionale, come nel round 10).", "",
         "| Misura | Produzione | Round 10 | Differenza |", "|---|---:|---:|---:|",
         f"| Δ ll totale held-out 2022/23-2025/26 | {d_held:+.5f} [{c['ll_tot_held']['lob']:+.5f}, {c['ll_tot_held']['hib']:+.5f}] | {ref[0]:+.5f} [{ref[1]:+.5f}, {ref[2]:+.5f}] | {d_held - ref[0]:+.1e} |",
         f"| Δ ll totale 2026/27 (descrittivo) | {d26:+.5f} | {ref[3]:+.5f} | {d26 - ref[3]:+.1e} |",
         f"| Δ ll per squadra held-out | {c['ll_team_held']['d']:+.5f} | | |", f"| Δ ll totale validazione | {d_val:+.5f} | | |", "",
         f"**Riproduzione del Δ del round 10: {'riprodotta' if ok_delta else 'NON RIPRODOTTA'}.**", ""]
    # intervalli con il livello di produzione (L3) sopra il nuovo modello dei gialli
    params = {k: LEVEL_PARAMS[k] for k in stats_v3.ORDER}
    means = {t: (st[t]["run"].mh, st[t]["run"].ma) for t in stats_v3.ORDER}
    means_old = dict(means)
    lv_old = stats_v3.build_level(feat, params, means=means_old)
    means[stat] = (run1.mh, run1.ma)
    lv_new = stats_v3.build_level(feat, params, means=means)
    ok_all = ok
    rows_all = feat.index[ok_all]
    mh_o, ma_o = level_run(feat, stat, run0.mh, run0.ma, lv_old, ok_all)
    mh_n, ma_n = level_run(feat, stat, run1.mh, run1.ma, lv_new, ok_all)
    g_old = interval_gaps(feat, stat, R6.Run(feat, SPEC[stat], mh_o, ma_o, run0.folds), al0, rows_all)
    g_new = interval_gaps(feat, stat, R6.Run(feat, SPEC[stat], mh_n, ma_n, run1.folds), al1, rows_all)
    worst = max(abs(g_new["tutte"]["team"]), abs(g_new["tutte"]["total"])) * 100
    L += ["**Intervalli dei gialli con il livello stagionale di produzione** (frequenza reale − probabilità dichiarata, punti percentuali; s5 → s6):", "",
          "| Insieme | Squadra | Totale |", "|---|---:|---:|",
          f"| Tutte le stagioni | {g_old['tutte']['team'] * 100:+.1f} → {g_new['tutte']['team'] * 100:+.1f} | {g_old['tutte']['total'] * 100:+.1f} → {g_new['tutte']['total'] * 100:+.1f} |",
          f"| 2026/27 | {g_old['2026/27']['team'] * 100:+.1f} → {g_new['2026/27']['team'] * 100:+.1f} | {g_old['2026/27']['total'] * 100:+.1f} → {g_new['2026/27']['total'] * 100:+.1f} |", "",
          f"**Criterio (≤ 3 punti su tutte le stagioni): {'rispettato' if worst <= 3 else 'NON rispettato'}** (massimo {worst:.1f} punti).", ""]
    # coerenza del serving: stato fino a una data di taglio + ratio() con data = ratio walk-forward delle partite di quel giorno
    y = feat["HY"] + feat["AY"]
    mh0, ma0 = refeffect.base_predictions(feat)
    m_tot = mh0 + ma0
    mbar = refeffect.mbar_by_league(feat, m_tot)
    R_full, _ = refeffect.referee_ratio(feat, y, m_tot, keys, REFEREE_K, mbar, HL)
    worst_diff, n_cmp = 0.0, 0
    for cut in ("2023-02-04", "2025-03-01", "2026-10-03", "2026-10-31"):
        t = pd.Timestamp(cut)
        sub = feat[feat.date < t]
        _, st_cut = refeffect.compute_stat(sub, keys.loc[sub.index], mh0.loc[sub.index], ma0.loc[sub.index], y.loc[sub.index], REFEREE_K, HL)
        day = feat[(feat.date >= t) & (feat.date < t + pd.Timedelta(days=3))]
        for i, r in day.iterrows():
            key = keys.loc[i]
            if not isinstance(key, str):
                continue
            R_srv, _, known = refeffect.ratio(st_cut, r.Division, key, asof=r.date)
            if not known:
                continue
            # il walk-forward vede anche le partite dei giorni tra il taglio e la partita: si confrontano solo le partite del primo giorno dopo il taglio
            if r.date != day.date.min():
                continue
            worst_diff = max(worst_diff, abs(R_srv - R_full.loc[i]))
            n_cmp += 1
    L += [f"**Coerenza del serving**: stato salvato fino a quattro date di taglio e `refeffect.ratio(stato, lega, arbitro, data)` contro il rapporto del walk-forward per le partite del primo giorno dopo il taglio ({n_cmp} partite): scarto massimo {worst_diff:.1e} (arrotondamento delle somme a 4 decimali).", ""]
    good = ok_delta and worst <= 3 and worst_diff < 1e-3
    L += [f"**Esito complessivo: {'riprodotto' if good else 'DIFFERENZE: controllare'}**", ""]
    open(os.path.join(P10, "PROD.md"), "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))
    if not good:
        sys.exit(1)


if __name__ == "__main__":
    main()
