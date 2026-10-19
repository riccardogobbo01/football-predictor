"""Round 7, fase 2 — verifica di produzione del livello stagionale (s5-livello): il codice messo in produzione (`stats_v3.walk_forward_means`,
`stats_v3.build_level` -> registro in models/stack.json, `predictions.levels.Levels`) ricalcola i risultati del round 7 esteso (L3EXT.md) e
rispetta il criterio sugli intervalli (scarto ≤ 3 punti su tutte le stagioni). In piu', controllo di robustezza con un riallenamento periodico
(ogni 28 giorni, come il training settimanale di produzione) al posto di un solo fit per stagione.
Da lanciare:  python -I -X utf8 backtest/run_round7_prod.py   (scrive backtest/round7_parts/PROD.md)"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import round6_lib as R6, round7_lib as L7, stats_v3
from backtest.run_round7 import SPEC, interval_gaps, prepare
from config import LEVEL_PARAMS
from predictions.levels import Levels

TOL_PP = 3.0


def level_run(feat, stat, mh, ma, level, ok_rows):
    """Medie corrette con i moltiplicatori di PRODUZIONE (Levels) per le righe di test."""
    lv = Levels(level)
    mh2, ma2 = mh.copy(), ma.copy()
    div = feat.Division.to_numpy()
    dates = feat.date.dt.strftime("%Y-%m-%d").to_numpy()
    idx = np.where(ok_rows)[0]
    # raggruppo per (lega, data): un solo calcolo per giorno
    key = pd.DataFrame({"div": div[idx], "date": dates[idx]})
    uniq = key.drop_duplicates()
    cache = {}
    for dv, g in uniq.groupby("div"):
        rh, ra = lv.multipliers(dv, stat, g["date"].tolist())
        for dt, a, b in zip(g["date"], rh, ra):
            cache[(dv, dt)] = (a, b)
    rh = np.array([cache[(d, t)][0] for d, t in zip(key["div"], key["date"])])
    ra = np.array([cache[(d, t)][1] for d, t in zip(key["div"], key["date"])])
    mh2.iloc[idx] = mh.iloc[idx].to_numpy() * rh
    ma2.iloc[idx] = ma.iloc[idx].to_numpy() * ra
    return mh2, ma2


def main():
    feat, gw, weeks, st = prepare()
    ext = pd.read_pickle(os.path.join(os.path.dirname(L7.CTX7), "l3ext.pkl"))
    L = ["## Round 7, fase 2 — verifica di produzione del livello stagionale", "",
         "Codice di produzione (`stats_v3.walk_forward_means`, `stats_v3.build_level` con il registro come lo salva il training, `predictions.levels.Levels` come lo usa il sito) sul backtest walk-forward; parametri da `config.LEVEL_PARAMS`.", "",
         "| Statistica | (H, k) | Medie di base: scarto massimo vs backtest | Δ ll totale produzione (tutte) | Δ round 7 esteso | Differenza | Δ held-out produzione [IC a blocchi] | Verdetto |", "|---|---|---:|---:|---:|---:|---|---|"]
    ok_all = True
    cov_rows = []
    rob_rows = []
    for s in L7.STATS:
        run, al, spec = st[s]["run"], st[s]["al"], SPEC[s]
        ok = (run.mh.notna() & feat[spec["hc"]].notna() & feat[spec["ac"]].notna() & (feat.season >= L7.FIRST_TEST)).to_numpy()
        rows = feat.index[ok]
        wk = weeks[ok]
        seas = feat.season.to_numpy()[ok]
        is_val = np.isin(seas, L7.VALIDATION)
        # 1. medie di base dal codice di produzione = quelle del backtest
        mh, ma = stats_v3.walk_forward_means(feat, s)
        dmax = float(np.nanmax(np.abs(np.r_[mh.to_numpy() - run.mh.to_numpy(), ma.to_numpy() - run.ma.to_numpy()])))
        # 2. registro come nel training, moltiplicatori come nel sito
        params = {k: LEVEL_PARAMS[k] for k in stats_v3.ORDER}
        level = stats_v3.build_level(feat, params, means={s: (mh, ma)} | {t: (st[t]["run"].mh, st[t]["run"].ma) for t in stats_v3.ORDER if t != s})
        mh2, ma2 = level_run(feat, s, mh, ma, level, ok)
        run2 = R6.Run(feat, SPEC[s], mh2, ma2, run.folds)
        v0 = R6.evaluate(run, rows, al)
        v1 = R6.evaluate(run2, rows, al)
        r = R6.compare(v0, v1, wk, is_val)
        d_ext = ext[s]["d_all"]
        diff = r["ll_tot"]["d"] - d_ext
        good = abs(diff) < 2e-4 and dmax < 1e-9 and tuple(ext[s]["chosen"]) == tuple(LEVEL_PARAMS[s])
        ok_all &= good
        L.append(f"| {L7.KEYS[s]} | {LEVEL_PARAMS[s][0]}, {LEVEL_PARAMS[s][1]} | {dmax:.1e} | {r['ll_tot']['d']:+.5f} | {d_ext:+.5f} | {diff:+.1e} | "
                 f"{r['ll_tot_held']['d']:+.5f} [{r['ll_tot_held']['lob']:+.5f}, {r['ll_tot_held']['hib']:+.5f}] | {R6.verdict(r)} |")
        g0, g1 = interval_gaps(feat, s, run, al, rows), interval_gaps(feat, s, run2, al, rows)
        worst = max(abs(g1["tutte"]["team"]), abs(g1["tutte"]["total"])) * 100
        ok_all &= worst <= TOL_PP
        cov_rows.append(f"| {L7.KEYS[s]} | {g1['tutte']['team'] * 100:+.1f} | {g1['tutte']['total'] * 100:+.1f} | {g1['2026/27']['team'] * 100:+.1f} | {g1['2026/27']['total'] * 100:+.1f} | {'ok' if worst <= TOL_PP else '**FUORI**'} |")
        # 3. robustezza: riallenamento ogni 28 giorni
        mhp, map_ = stats_v3.walk_forward_means(feat, s, refit_days=28)
        runp = R6.Run(feat, SPEC[s], mhp, map_, run.folds)
        lvp = stats_v3.build_level(feat, params, means={t: (mhp, map_) if t == s else (st[t]["run"].mh, st[t]["run"].ma) for t in stats_v3.ORDER})
        mh3, ma3 = level_run(feat, s, mhp, map_, lvp, ok)
        runp2 = R6.Run(feat, SPEC[s], mh3, ma3, run.folds)
        okp = ok & mhp.notna().to_numpy()
        rp = feat.index[okp]
        wp = weeks[okp]
        vp0, vp1 = R6.evaluate(runp, rp, al), R6.evaluate(runp2, rp, al)
        isv = np.isin(feat.season.to_numpy()[okp], L7.VALIDATION)
        rr = R6.compare(vp0, vp1, wp, isv)
        sea = feat.season.to_numpy()[okp]
        d26 = (vp0["ll_tot"] - vp1["ll_tot"])[sea == 2026].mean()
        gp0, gp1 = interval_gaps(feat, s, runp, al, rp), interval_gaps(feat, s, runp2, al, rp)
        rob_rows.append(f"| {L7.KEYS[s]} | {rr['ll_tot']['d']:+.5f} [{rr['ll_tot']['lob']:+.5f}, {rr['ll_tot']['hib']:+.5f}] | {rr['ll_tot_held']['d']:+.5f} [{rr['ll_tot_held']['lob']:+.5f}, {rr['ll_tot_held']['hib']:+.5f}] | "
                        f"{rr['ll_team_held']['d']:+.5f} | {d26:+.5f} | {gp0['tutte']['team'] * 100:+.1f} → {gp1['tutte']['team'] * 100:+.1f} / {gp0['tutte']['total'] * 100:+.1f} → {gp1['tutte']['total'] * 100:+.1f} | {R6.verdict(rr)} |")
        print(s, f"dmax {dmax:.1e}", f"prod {r['ll_tot']['d']:+.5f} ext {d_ext:+.5f}", f"refit28 {rr['ll_tot']['d']:+.5f}", flush=True)
    L += ["", f"**Esito della riproduzione: {'riprodotto' if ok_all else 'NON RIPRODOTTO / FUORI CRITERIO'}** (tolleranza sul Δ: 2e-4, dovuta all'arrotondamento del registro; medie di base identiche; scarto degli intervalli ≤ {TOL_PP:.0f} punti).", "",
          "**Copertura degli intervalli con il livello di produzione (frequenza reale − probabilità dichiarata, punti percentuali)**", "",
          "| Statistica | Squadra, tutte | Totale, tutte | Squadra, 2026/27 | Totale, 2026/27 | Criterio ≤ 3 pp (tutte) |", "|---|---:|---:|---:|---:|---|"] + cov_rows
    L += ["", "**Robustezza: riallenamento ogni 28 giorni** (le medie di base vengono da modelli rifatti ogni 28 giorni con tutte le partite precedenti, come il training settimanale di produzione, invece di un fit per stagione; il livello è ricalcolato su quelle previsioni. Δ rispetto allo stesso baseline a riallenamento periodico; alpha del baseline a un fit per stagione).", "",
          "| Statistica | Δ ll totale tutte [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ per squadra held-out | Δ totale 2026/27 | Scarto intervalli squadra / totale (base → livello) | Verdetto |", "|---|---|---|---:|---:|---|---|"] + rob_rows + [""]
    open(os.path.join(L7.P7, "PROD.md"), "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))
    if not ok_all:
        sys.exit(1)


if __name__ == "__main__":
    main()
