"""Round 12 — gialli della Serie A 2026/27: il livello si applica? il decadimento dell'effetto arbitro riduce il livello di lega? correzione L4 (livello a due scale di tempo).
Solo backtest. Criteri in backtest/round12_parts/prereg.md. Da lanciare:  python -I -X utf8 backtest/run_round12.py   (scrive backtest/round12_parts/R12.md)"""
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import refeffect, round3_ctx as C3, round6_lib as R6, round7_lib as L7, stats_v3
from backtest.run_round7 import SPEC
from config import LEVEL_PARAMS, REFEREE_HALF_LIFE_DAYS, REFEREE_K
from predictions.levels import Levels

P12 = os.path.join(REPO_ROOT, "backtest", "round12_parts")
LG = {"I1": "Serie A", "E0": "Premier League", "D1": "Bundesliga", "SP1": "La Liga", "F1": "Ligue 1"}
H0, K0 = LEVEL_PARAMS["gialli"]
GRID = [(H, k) for H in (12, 26, 52) for k in (5, 15, 40)]
TIE = 0.0002
SPEC_G = SPEC["gialli"]


def md(rows, head):
    return ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(head)) + "|"] + ["| " + " | ".join(map(str, r)) + " |" for r in rows]


def fmt(x, d=3):
    return f"{x:.{d}f}"


def ci(t, d=3):
    return f"{t[0]:+.{d}f} [{t[1]:+.{d}f}; {t[2]:+.{d}f}]"


def build():
    feat = L7.build_ctx7()
    keys = refeffect.load_history_keys(feat).reindex(feat.index)
    feat["ref_u"], _ = refeffect.compute(feat, keys, REFEREE_K, None)
    feat["ref_d"], _ = refeffect.compute(feat, keys, REFEREE_K, REFEREE_HALF_LIFE_DAYS["gialli"])
    runs = {}
    for nm, col in (("noref", None), ("unif", "ref_u"), ("decay", "ref_d")):
        f = feat.copy()
        if col:
            f["ref_logR"] = f[col]
        X = stats_v3.design(f, "gialli", True, referee=col is not None)
        run = R6.run_model(f, SPEC_G, X)
        for sea, fo in run.folds.items():
            if sea == L7.FIRST_TEST:                          # in campione per il 2016/17-2018/19: storico del livello (come in produzione)
                run.mh[fo["idx"]] = fo["mh"]
                run.ma[fo["idx"]] = fo["ma"]
        runs[nm] = run
    return feat, runs


def level(feat, mh, ma, H, k):
    dates = feat.date.dt.strftime("%Y-%m-%d").to_numpy()
    lg = feat.Division.to_numpy()
    yh, ya = feat.HY.to_numpy(float), feat.AY.to_numpy(float)
    rh = L7.dynamic_level(dates, lg, mh, yh, H, k)
    ra = L7.dynamic_level(dates, lg, ma, ya, H, k)
    return rh, ra


def two_scale(feat, mh, ma, Hs, ks, Hf=H0, kf=K0):
    rsh, rsa = level(feat, mh, ma, Hs, ks)
    mh2, ma2 = mh * rsh, ma * rsa
    rfh, rfa = level(feat, mh2, ma2, Hf, kf)
    return mh2 * rfh, ma2 * rfa, rsh, rsa, rfh, rfa


def main():
    feat, runs = build()
    weeks = feat.date.dt.strftime("%G-%V").to_numpy()
    season = feat.season.to_numpy()
    lg = feat.Division.to_numpy()
    y = (feat.HY + feat.AY).to_numpy(float)
    base = runs["decay"]
    mh0, ma0 = base.mh.to_numpy(float), base.ma.to_numpy(float)
    al = R6.alphas(base, "global")
    # ───────── produzione (baseline) ─────────
    rh, ra = level(feat, mh0, ma0, H0, K0)
    mhP, maP = mh0 * rh, ma0 * ra
    L = ["## Round 12 — gialli della Serie A 2026/27", "", "Contesto dati fino al " + str(feat.date.max().date()) + " (ultimo ricalcolo del contesto di backtest); le partite successive sono solo nello storico emesso (parte 1.1).", ""]

    # ───────── 1.1 il livello si applica? (storico emesso) ─────────
    h = pd.read_csv(os.path.join(REPO_ROOT, "docs", "history.csv"))
    x = h[h.league.eq("serie_a") & h.yellow_real.notna() & (h.match_date >= "2026-08-01") & h.bm_gialli_h.notna()].copy()
    x["bm"] = x.bm_gialli_h + x.bm_gialli_a
    x["lvl"] = x.yellow_pred / x.bm
    rows = []
    for ver, g in x.groupby("stats_version"):
        rows.append([ver, len(g), g.match_date.min(), g.match_date.max(), fmt(g.bm.mean(), 2), fmt(g.yellow_pred.mean(), 2), fmt(g.yellow_real.mean(), 2), fmt(g.lvl.mean(), 3)])
    rows.append(["tutte", len(x), x.match_date.min(), x.match_date.max(), fmt(x.bm.mean(), 2), fmt(x.yellow_pred.mean(), 2), fmt(x.yellow_real.mean(), 2), fmt(x.lvl.mean(), 3)])
    L += ["### 1.1 Il livello dei gialli è applicato alla Serie A? (previsioni emesse, partite giocate con base salvata)", "",
          "bm = media di base (con effetto arbitro) PRIMA del livello; livello implicito = previsione finale / bm.", ""]
    L += md(rows, ["Versione del modello", "N", "dal", "al", "base prima del livello", "previsione finale", "reale", "livello implicito"]) + [""]
    y2 = h[h.league.isin(["premier_league", "bundesliga", "la_liga", "ligue_1"]) & h.yellow_real.notna() & (h.match_date >= "2026-10-16") & h.bm_gialli_h.notna()].copy()
    y2["bm"] = y2.bm_gialli_h + y2.bm_gialli_a
    s16 = x[x.match_date >= "2026-10-16"]
    rows = [["Serie A (dal 16/10)", len(s16), fmt(s16.bm.mean(), 2), fmt(s16.yellow_pred.mean(), 2), fmt(s16.yellow_real.mean(), 2), fmt((s16.yellow_pred / s16.bm).mean(), 3)]]
    for lgk, g in y2.groupby("league"):
        rows.append([lgk + " (dal 16/10)", len(g), fmt(g.bm.mean(), 2), fmt(g.yellow_pred.mean(), 2), fmt(g.yellow_real.mean(), 2), fmt((g.yellow_pred / g.bm).mean(), 3)])
    L += md(rows, ["Lega", "N", "base prima del livello", "previsione finale", "reale", "livello implicito"]) + [""]
    sd = float(np.sqrt((s16.yellow_pred + 0.12 * s16.yellow_pred ** 2).mean()))
    L += [f"Scarto Serie A dal 16/10: previsto {s16.yellow_pred.mean():.2f}, reale {s16.yellow_real.mean():.2f} su {len(s16)} partite = {s16.yellow_real.mean() - s16.yellow_pred.mean():+.2f}; "
          f"errore standard della media reale ≈ {sd / np.sqrt(len(s16)):.2f} (varianza della Binomiale Negativa con dispersione 0,12): scarto ≈ {(s16.yellow_real.mean() - s16.yellow_pred.mean()) / (sd / np.sqrt(len(s16))):+.1f} errori standard.", ""]

    # moltiplicatori di produzione per data (registro + partite dopo l'ultimo allenamento)
    stack = json.load(open(os.path.join(REPO_ROOT, "models", "stack.json"), encoding="utf-8"))
    lv = Levels(stack["stats_v3"]["level"])
    dates = ["2026-10-16", "2026-10-19", "2026-11-02", "2026-11-09", "2026-11-16"]
    d = lv.data[("I1", "gialli")]
    rows = []
    for dt in dates:
        rrh, rra = lv.multipliers("I1", "gialli", [dt])
        t = (pd.Timestamp(dt) - lv.epoch).days
        sel = d["d"] < t
        w = 0.5 ** ((t - d["d"][sel]) / (7.0 * H0))
        sy, sm_, sw = (w * (d["yh"][sel] + d["ya"][sel])).sum(), (w * (d["mh"][sel] + d["ma"][sel])).sum(), (w * d["n"][sel]).sum()
        rows.append([dt, fmt(rrh[0], 3), fmt(rra[0], 3), fmt(sy / sm_, 3), fmt(sw, 1), fmt(K0 / (sw + K0) * 100, 0) + " %"])
    L += ["**Moltiplicatori di produzione della Serie A per i gialli** (registro di `models/stack.json`, aggiornato al " + stack["stats_v3"]["level"]["asof"]["I1"] + "; per le date successive il registro non contiene ancora le partite nuove):", ""]
    L += md(rows, ["Data", "R casa", "R ospite", "rapporto reale/atteso pesato (senza prior)", "partite equivalenti pesate (n)", "peso del prior k/(n+k)"]) + [""]

    # ───────── 1.2 il decadimento riduce il livello di lega? ─────────
    xs = feat[feat.season >= 2019]
    t = xs.groupby(["Division", "season"]).agg(u=("ref_u", "mean"), d=("ref_d", "mean"), n=("ref_u", "size"))
    rows = []
    for dv in LG:
        r = [LG[dv]]
        for s in range(2019, 2027):
            if (dv, s) in t.index:
                r.append(f"{t.loc[(dv, s), 'u'] * 100:+.1f} / {t.loc[(dv, s), 'd'] * 100:+.1f}")
            else:
                r.append("—")
        rows.append(r)
    L += ["### 1.2 L'effetto arbitro a decadimento riduce il livello di lega?", "",
          "Media di log R (effetto arbitro sui gialli, in %) per lega e stagione, **pesi uniformi / decadimento (emivita 182,5 giorni)**. Se il decadimento abbassasse il livello di lega la seconda cifra sarebbe sistematicamente più bassa.", ""]
    L += md(rows, ["Lega"] + [f"{s}/{str(s + 1)[2:]}" for s in range(2019, 2027)]) + [""]
    dd = (t["d"] - t["u"]).groupby(level=0).mean()
    L += ["Differenza media (decadimento − uniforme), punti percentuali per lega: " + ", ".join(f"{LG[k]} {v * 100:+.2f}" for k, v in dd.items()) + ". "
          f"Nella Serie A 2026/27 l'effetto arbitro medio è {t.loc[('I1', 2026), 'u'] * 100:+.1f} % con pesi uniformi e {t.loc[('I1', 2026), 'd'] * 100:+.1f} % con il decadimento: **il decadimento non cambia il livello di lega**.", ""]

    # ───────── 1.3 dove nasce lo scarto ─────────
    is26 = ((lg == "I1") & (season == 2026))
    mo = feat.date.dt.strftime("%Y-%m").to_numpy()
    rows = []
    for m_ in sorted(set(mo[is26])):
        mm = is26 & (mo == m_)
        rows.append([m_, int(mm.sum()), fmt(np.nanmean(y[mm]), 2)] + [fmt(np.nanmean((runs[nm].mh + runs[nm].ma).to_numpy()[mm]), 2) for nm in ("noref", "unif", "decay")] + [fmt(np.nanmean((mhP + maP)[mm]), 2)])
    mm = is26
    rows.append(["2026/27", int(mm.sum()), fmt(np.nanmean(y[mm]), 2)] + [fmt(np.nanmean((runs[nm].mh + runs[nm].ma).to_numpy()[mm]), 2) for nm in ("noref", "unif", "decay")] + [fmt(np.nanmean((mhP + maP)[mm]), 2)])
    L += ["### 1.3 Dove nasce lo scarto della Serie A (gialli totali per partita, 2026/27)", ""]
    L += md(rows, ["Mese", "N", "reale", "modello senza arbitro", "con arbitro (pesi uniformi)", "con arbitro a decadimento", "decadimento + livello di produzione"]) + [""]
    rr = {}
    for nm, (a, b) in (("base (con arbitro a decadimento)", (mh0, ma0)), ("dopo il livello di produzione", (mhP, maP))):
        okk = is26 & np.isfinite(a + b) & np.isfinite(y)
        rr[nm] = L7.ratio_ci((a + b)[okk], y[okk], weeks[okk])
    L += ["Rapporto reale/previsto della Serie A 2026/27 (Σ reali / Σ previsti, IC a blocchi per settimana): " + "; ".join(f"{k}: {v[0]:.3f} [{v[1]:.3f}; {v[2]:.3f}]" for k, v in rr.items()) + ".", ""]

    # ───────── 1.4 quanto è insolito ─────────
    N = int(is26.sum())
    rows, vals_b, vals_l = [], [], []
    for dv in LG:
        for s in range(2019, 2027):
            idx = np.where((lg == dv) & (season == s) & np.isfinite(mh0 + ma0) & np.isfinite(y))[0]
            idx = idx[np.argsort(feat.date.to_numpy()[idx], kind="stable")][:N]
            if len(idx) < N:
                continue
            rb = y[idx].sum() / (mh0 + ma0)[idx].sum()
            rl = y[idx].sum() / (mhP + maP)[idx].sum()
            vals_b.append((dv, s, rb))
            vals_l.append((dv, s, rl))
    arr = np.array([v[2] for v in vals_l if not (v[0] == "I1" and v[1] == 2026)])
    arrb = np.array([v[2] for v in vals_b if not (v[0] == "I1" and v[1] == 2026)])
    ser = [v[2] for v in vals_l if v[0] == "I1" and v[1] == 2026][0]
    serb = [v[2] for v in vals_b if v[0] == "I1" and v[1] == 2026][0]
    L += ["### 1.4 Quanto è insolito lo scarto della Serie A 2026/27", "",
          f"Rapporto reale/previsto sulle prime {N} partite di ciascuna lega-stagione 2019/20-2026/27 (stesso numero di partite della Serie A 2026/27), prima e dopo il livello di produzione:", ""]
    L += md([["senza livello (base)", f"{arrb.mean():.3f}", f"{arrb.std():.3f}", f"{arrb.min():.3f}", f"{arrb.max():.3f}", f"{serb:.3f}", f"{(serb - arrb.mean()) / arrb.std():+.1f}", int((arrb <= serb).sum()) + 1],
             ["con il livello di produzione", f"{arr.mean():.3f}", f"{arr.std():.3f}", f"{arr.min():.3f}", f"{arr.max():.3f}", f"{ser:.3f}", f"{(ser - arr.mean()) / arr.std():+.1f}", int((arr <= ser).sum()) + 1]],
            ["", "media delle altre lega-stagioni", "dev. std", "minimo", "massimo", "Serie A 2026/27", "scarto in dev. std", f"posizione su {len(arr) + 1} (1 = la più bassa)"]) + [""]

    # ───────── 2. L4 ─────────
    ok = (base.mh.notna() & feat.HY.notna() & feat.AY.notna() & (feat.season >= L7.FIRST_TEST)).to_numpy() & np.isfinite(al["ah"].to_numpy())
    main = ok & (season <= 2025)
    rows_m = feat.index[main]
    is_val = np.isin(season[main], L7.VALIDATION)
    wk = weeks[main]
    v0 = R6.evaluate(R6.Run(feat, SPEC_G, pd.Series(mhP, index=feat.index), pd.Series(maP, index=feat.index), base.folds), rows_m, al)
    res = {}
    for Hs, ks in GRID:
        mh2, ma2, *_ = two_scale(feat, mh0, ma0, Hs, ks)
        v1 = R6.evaluate(R6.Run(feat, SPEC_G, pd.Series(mh2, index=feat.index), pd.Series(ma2, index=feat.index), base.folds), rows_m, al)
        res[(Hs, ks)] = v1
    L += ["### 2. Correzione L4 (livello lento sotto quello di produzione)", "",
          "Baseline = produzione (effetto arbitro a decadimento + livello H = 4, k = 15). Δ log-loss del totale = baseline − variante (positivo = migliora). Scelta sulla sola validazione 2019/20-2021/22.", ""]
    tab = []
    best = None
    for (Hs, ks), v1 in res.items():
        dv_ = (v0["ll_tot"] - v1["ll_tot"])
        dval = dv_[is_val].mean()
        tab.append([Hs, ks, f"{dval:+.5f}", f"{dv_[~is_val].mean():+.5f}"])
        if best is None or dval > best[0] + TIE or (abs(dval - best[0]) <= TIE and (ks, Hs) > (best[2], best[1])):
            best = (dval, Hs, ks)
    L += md(tab, ["H lenta (settimane)", "k lento", "Δ validazione", "Δ held-out (solo informativo)"]) + [""]
    _, Hs, ks = best
    v1 = res[(Hs, ks)]
    dt = v0["ll_tot"] - v1["ll_tot"]
    dtm = v0["ll_team"] - v1["ll_team"]
    held = ~is_val
    ci_t = C3.ci_block(dt[held], wk[held])
    ci_m = C3.ci_block(dtm[held], wk[held])
    ci_v = C3.ci_block(dt[is_val], wk[is_val])
    if ci_t[0] > 0 and ci_t[1] > 0 and ci_m[0] >= 0:
        verdict = "migliora"
    elif ci_t[0] < 0 and ci_t[2] < 0:
        verdict = "peggiora"
    else:
        verdict = "non distinguibile dal rumore"
    L += [f"**Scelta in validazione: H lenta = {Hs}, k lento = {ks}.** Δ validazione {ci(ci_v, 5)}; **Δ held-out 2022/23-2025/26: totale {ci(ci_t, 5)}, per squadra {ci(ci_m, 5)} → {verdict}.**", ""]
    # per stagione e lega, copertura
    rows = []
    for s in (2022, 2023, 2024, 2025):
        mk = season[main] == s
        rows.append([f"{s}/{str(s + 1)[2:]}", int(mk.sum()), f"{dt[mk].mean():+.5f}"])
    L += ["Δ del totale per stagione di held-out:", ""] + md(rows, ["Stagione", "N", "Δ"]) + [""]
    rows = []
    for dv in LG:
        mk = held & (lg[main] == dv)
        rows.append([LG[dv], int(mk.sum()), f"{dt[mk].mean():+.5f}"])
    L += ["Δ del totale per lega (held-out):", ""] + md(rows, ["Lega", "N", "Δ"]) + [""]
    # 2026/27 descrittivo
    m26 = (base.mh.notna() & feat.HY.notna() & feat.AY.notna()).to_numpy() & (season == 2026) & np.isfinite(al["ah"].to_numpy())
    rows26 = feat.index[m26]
    mh2, ma2, *_ = two_scale(feat, mh0, ma0, Hs, ks)
    v0_26 = R6.evaluate(R6.Run(feat, SPEC_G, pd.Series(mhP, index=feat.index), pd.Series(maP, index=feat.index), base.folds), rows26, al)
    v1_26 = R6.evaluate(R6.Run(feat, SPEC_G, pd.Series(mh2, index=feat.index), pd.Series(ma2, index=feat.index), base.folds), rows26, al)
    rows = []
    for dv in list(LG) + [None]:
        mk = (lg[m26] == dv) if dv else np.ones(m26.sum(), bool)
        if mk.sum() == 0:
            continue
        d26 = (v0_26["ll_tot"] - v1_26["ll_tot"])[mk]
        pr0 = (mhP + maP)[m26][mk]
        pr1 = (mh2 + ma2)[m26][mk]
        rows.append([LG.get(dv, "Tutte"), int(mk.sum()), fmt(y[m26][mk].mean(), 2), fmt(pr0.mean(), 2), fmt(pr1.mean(), 2), f"{d26.mean():+.5f}"])
    L += ["**2026/27 (descrittivo, mai usato per scegliere):**", ""] + md(rows, ["Lega", "N", "reale", "previsto produzione", "previsto L4", "Δ log-loss (produzione − L4)"]) + [""]
    summ = {"best": [Hs, ks], "verdict": verdict, "held_tot": ci_t, "held_team": ci_m, "val": ci_v, "gap": rr, "ratio_serie_a_prod": ser, "ratio_serie_a_base": serb}
    json.dump(summ, open(os.path.join(P12, "summary.json"), "w"), default=float)
    open(os.path.join(P12, "R12.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("verdetto L4:", verdict, f"H={Hs} k={ks}", ci(ci_t, 5))


if __name__ == "__main__":
    main()
