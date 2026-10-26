"""Round 8 — M1 (dispersione dei tiri per lega), M2 (corner e stato di gara), M3 (effetto arbitro sui gialli nel 2026/27). Solo backtest.
Criteri in backtest/round8_parts/prereg.md.  Da lanciare:  python -I -X utf8 backtest/run_round8.py
Scrive backtest/round8_parts/M1.md, M2.md, M3.md (e results_round8.md si assembla con run_round8_final.py)."""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy.stats import skellam

from backtest import round3_ctx as C3, round6_lib as R6, round7_lib as L7, stats_v3
from backtest.run_round7 import LG_NAME, SPEC, TIE, prepare
from backtest.run_round7_prod import level_run
from config import LEVEL_PARAMS

P8 = os.path.join(REPO_ROOT, "backtest", "round8_parts")
os.makedirs(P8, exist_ok=True)
LEAGUES = L7.LEAGUES
TOL = 3.0
MIN_N_FLAG = 150
SPLITS = ("tutte", "validazione", "held-out", "2026/27")


def split_masks(seas):
    return {"tutte": np.ones(len(seas), bool), "validazione": np.isin(seas, L7.VALIDATION), "held-out": ~np.isin(seas, L7.VALIDATION), "2026/27": seas == 2026}


def interval_hits(feat, stat, mh, ma, al, rows):
    """Per riga di test: esito (1 = dentro) e probabilità dichiarata dell'intervallo per casa, ospite e totale."""
    spec = SPEC[stat]
    K = stats_v3.INTERVAL_K[stat]
    mh_, ma_ = mh[rows].to_numpy(float), ma[rows].to_numpy(float)
    yh, ya = feat.loc[rows, spec["hc"]].to_numpy(float), feat.loc[rows, spec["ac"]].to_numpy(float)
    out = pd.DataFrame({"season": feat.loc[rows, "season"].to_numpy(), "league": feat.loc[rows, "Division"].to_numpy(),
                        "week": feat.loc[rows, "date"].dt.strftime("%G-%V").to_numpy()}, index=rows)
    for key, m, y, a, kk in (("h", mh_, yh, al.loc[rows, "ah"].to_numpy(), K), ("a", ma_, ya, al.loc[rows, "aa"].to_numpy(), K),
                             ("t", mh_ + ma_, yh + ya, al.loc[rows, "aT"].to_numpy(), 2 * K)):
        lo, hi, pr = np.empty(len(rows), int), np.empty(len(rows), int), np.empty(len(rows))
        for av in np.unique(a):
            sel = a == av
            lo[sel], hi[sel], pr[sel] = stats_v3.nb_interval(m[sel], av, kk)
        out[f"{key}_hit"] = ((y >= lo) & (y <= hi)).astype(float)
        out[f"{key}_p"] = pr
    return out


def cov_cells(hits: pd.DataFrame, level: str):
    """(n, dichiarata, reale, scarto in pp) per 'team' (casa+ospite), 'home', 'away', 'tot'."""
    if level == "team":
        h, p = np.r_[hits.h_hit, hits.a_hit], np.r_[hits.h_p, hits.a_p]
    else:
        k = {"home": "h", "away": "a", "tot": "t"}[level]
        h, p = hits[f"{k}_hit"].to_numpy(), hits[f"{k}_p"].to_numpy()
    if not len(h):
        return None
    return len(h), float(p.mean()), float(h.mean()), 100 * float(h.mean() - p.mean())


def cell_txt(c, flag=True):
    if c is None:
        return "–"
    n, p, r, g = c
    bad = flag and abs(g) > TOL and n >= (MIN_N_FLAG if flag else 0)
    return f"{100 * p:.0f}→{100 * r:.0f} ({g:+.1f}){' **' if bad else ''} <sub>{n}</sub>"


def per_league_alpha(feat, run, al, stat):
    """Alpha per lega e per lato (momenti sul training del fold) per la distribuzione per squadra; alpha del totale invariato."""
    spec = SPEC[stat]
    out = al.copy()
    for s, f in run.folds.items():
        i = f["idx"]
        te = run.mh.notna() & (feat.season == s)
        yh, ya = feat.loc[i, spec["hc"]].to_numpy(float), feat.loc[i, spec["ac"]].to_numpy(float)
        lg_tr = feat.loc[i, "Division"].to_numpy()
        lg_te = feat.loc[te, "Division"]
        ah, aa = out.loc[te, "ah"].copy(), out.loc[te, "aa"].copy()
        for lg in np.unique(lg_tr):
            m = lg_tr == lg
            if m.sum() < 500:
                continue
            sel = (lg_te == lg).to_numpy()
            ah[sel] = R6.moments(yh[m], f["mh"][m])
            aa[sel] = R6.moments(ya[m], f["ma"][m])
        out.loc[te, "ah"], out.loc[te, "aa"] = ah, aa
    return out


# ───────────────────────────── M1 ─────────────────────────────
def m1(feat, weeks, st):
    stat = "tiri"
    run, al = st[stat]["run"], st[stat]["al"]
    spec = SPEC[stat]
    params = {k: LEVEL_PARAMS[k] for k in stats_v3.ORDER}
    ok = (run.mh.notna() & feat[spec["hc"]].notna() & feat[spec["ac"]].notna() & (feat.season >= L7.FIRST_TEST)).to_numpy()
    rows = feat.index[ok]
    wk, seas = weeks[ok], feat.season.to_numpy()[ok]
    lv = stats_v3.build_level(feat, params, means={t: (st[t]["run"].mh, st[t]["run"].ma) for t in stats_v3.ORDER})
    mh2, ma2 = level_run(feat, stat, run.mh, run.ma, lv, ok)
    run_l = R6.Run(feat, SPEC[stat], mh2, ma2, run.folds)
    al_lg = per_league_alpha(feat, run, al, stat)
    hits0 = interval_hits(feat, stat, mh2, ma2, al, rows)
    hits1 = interval_hits(feat, stat, mh2, ma2, al_lg, rows)
    masks = split_masks(seas)
    L = ["## M1 — dispersione dei tiri per lega", "",
         "Baseline = produzione (livello stagionale + alpha casa/ospite globali del fold). Celle: probabilità dichiarata → frequenza reale (scarto in punti), numero di partite; "
         f"**grassetto** = |scarto| > {TOL:.0f} punti con almeno {MIN_N_FLAG} partite.", ""]
    for lab, hits in (("Baseline (alpha globali)", hits0), ("Variante M1 (alpha per lega e lato, solo per squadra)", hits1)):
        L += [f"### Copertura degli intervalli dei tiri — {lab}", "", "| Lega | Insieme | Casa | Ospite | Squadra (casa+ospite) | Totale |", "|---|---|---|---|---|---|"]
        for lg in LEAGUES + ["TUTTE"]:
            for sp in SPLITS:
                m = masks[sp] & ((hits.league == lg).to_numpy() if lg != "TUTTE" else True)
                h = hits[m]
                if not len(h):
                    continue
                L.append(f"| {LG_NAME.get(lg, 'Tutte')} | {sp} | " + " | ".join(cell_txt(cov_cells(h, lv_)) for lv_ in ("home", "away", "team", "tot")) + " |")
        L.append("")
    # per stagione e lega (squadra), baseline
    L += ["### Baseline: copertura per squadra, per stagione e lega (probabilità dichiarata → reale)", "", "| Stagione | " + " | ".join(LG_NAME[x] for x in LEAGUES) + " |", "|---|" + "---|" * len(LEAGUES)]
    for s_ in sorted(set(seas)):
        L.append(f"| {s_}/{(s_ + 1) % 100:02d} | " + " | ".join(cell_txt(cov_cells(hits0[(hits0.season == s_) & (hits0.league == lg)], "team")) for lg in LEAGUES) + " |")
    L.append("")
    # livello: rapporto reale/previsto delle medie per lega e lato nel 2026/27
    m26 = masks["2026/27"]
    L += ["### Livello nel 2026/27: rapporto reale / previsto (medie dopo il livello stagionale)", "", "| Lega | Casa prev. → reale | Rapporto casa | Ospite prev. → reale | Rapporto ospite | Totale prev. → reale | Rapporto totale |", "|---|---|---|---|---|---|---|"]
    yh, ya = feat.loc[rows, spec["hc"]].to_numpy(float), feat.loc[rows, spec["ac"]].to_numpy(float)
    ph, pa = mh2[rows].to_numpy(float), ma2[rows].to_numpy(float)
    lg_arr = feat.loc[rows, "Division"].to_numpy()
    for lg in LEAGUES:
        m = m26 & (lg_arr == lg)
        if not m.any():
            continue
        rh, lo1, hi1 = L7.ratio_ci(ph[m], yh[m], wk[m])
        ra, lo2, hi2 = L7.ratio_ci(pa[m], ya[m], wk[m])
        rt, lo3, hi3 = L7.ratio_ci(ph[m] + pa[m], yh[m] + ya[m], wk[m])
        L.append(f"| {LG_NAME[lg]} | {ph[m].mean():.1f} → {yh[m].mean():.1f} | {rh:.3f} [{lo1:.3f}, {hi1:.3f}] | {pa[m].mean():.1f} → {ya[m].mean():.1f} | {ra:.3f} [{lo2:.3f}, {hi2:.3f}] | "
                 f"{(ph[m] + pa[m]).mean():.1f} → {(yh[m] + ya[m]).mean():.1f} | {rt:.3f} [{lo3:.3f}, {hi3:.3f}] |")
    L.append("")
    # metriche della variante
    is_val = np.isin(seas, L7.VALIDATION)
    v0, v1 = R6.evaluate(run_l, rows, al), R6.evaluate(run_l, rows, al_lg)
    r = R6.compare(v0, v1, wk, is_val)
    ver = R6.verdict(r, primary="ll_team", secondary="ou_team") if False else None
    # verdetto sul per squadra (la variante tocca solo la distribuzione per squadra): Δ held-out per squadra > 0 con IC a blocchi che esclude lo zero e O/U per squadra >= 0
    d_team_held = (v0["ll_team"] - v1["ll_team"])[~is_val]
    d_ou_held = (v0["ou_team"] - v1["ou_team"])[~is_val]
    m_t, lo_t, hi_t = C3.ci_block(d_team_held, wk[~is_val])
    m_o, lo_o, hi_o = C3.ci_block(d_ou_held, wk[~is_val])
    ver = "migliora" if (m_t > 0 and lo_t > 0 and m_o >= 0) else ("peggiora" if (m_t < 0 and hi_t < 0) else "non distinguibile dal rumore")
    d26 = (v0["ll_team"] - v1["ll_team"])[m26].mean()
    # esito sulla copertura
    worst0 = max(abs(cov_cells(hits0[hits0.league == lg], "team")[3]) for lg in LEAGUES)
    worst1 = max(abs(cov_cells(hits1[hits1.league == lg], "team")[3]) for lg in LEAGUES)
    cov_ok = worst1 <= TOL
    L += ["### Metriche della variante M1 contro la baseline", "", "| Metrica | Baseline | M1 | Δ (base − M1) tutte [IC a blocchi] | Δ held-out [IC a blocchi] | Δ 2026/27 |", "|---|---:|---:|---|---|---:|",
          f"| Log-loss per squadra | {r['ll_team']['base']:.5f} | {r['ll_team']['var']:.5f} | {r['ll_team']['d']:+.5f} [{r['ll_team']['lob']:+.5f}, {r['ll_team']['hib']:+.5f}] | {m_t:+.5f} [{lo_t:+.5f}, {hi_t:+.5f}] | {d26:+.5f} |",
          f"| Log-loss Over/Under per squadra | {r['ou_team']['base']:.5f} | {r['ou_team']['var']:.5f} | {r['ou_team']['d']:+.5f} [{r['ou_team']['lob']:+.5f}, {r['ou_team']['hib']:+.5f}] | {m_o:+.5f} [{lo_o:+.5f}, {hi_o:+.5f}] | {(v0['ou_team'] - v1['ou_team'])[m26].mean():+.5f} |",
          f"| Log-loss del totale (invariata per costruzione) | {r['ll_tot']['base']:.5f} | {r['ll_tot']['var']:.5f} | {r['ll_tot']['d']:+.5f} | | |", "",
          f"**Verdetto: {ver}.** Scarto massimo per lega della copertura per squadra (tutte le stagioni): baseline {worst0:.1f} pp, M1 {worst1:.1f} pp → la variante {'risolve' if cov_ok else 'NON risolve'} (criterio: nessuna lega oltre {TOL:.0f} punti).", ""]
    summary = dict(verdict=ver, worst0=worst0, worst1=worst1, cov_ok=cov_ok, d_held=m_t, lo_held=lo_t, hi_held=hi_t, d26=float(d26))
    return L, summary


# ───────────────────────────── M2 ─────────────────────────────
def trail_features(mu, nu, n_t=20):
    """Frazione attesa della partita in cui casa / ospite stanno perdendo (Poisson indipendenti di medie μt, νt, t∈(0,1))."""
    mu, nu = np.asarray(mu, float), np.asarray(nu, float)
    th = np.zeros(len(mu))
    ta = np.zeros(len(mu))
    for i in range(n_t):
        t = (i + 0.5) / n_t
        th += skellam.cdf(-1, mu * t, nu * t)                      # D = H - A < 0
        ta += 1 - skellam.cdf(0, mu * t, nu * t)                   # D > 0
    return th / n_t, ta / n_t


def m2(feat, gw, weeks, st):
    stat = "corner"
    spec = SPEC[stat]
    run0, al0 = st[stat]["run"], st[stat]["al"]
    H, k = LEVEL_PARAMS[stat]
    ok_idx = gw.mu.notna().to_numpy()
    th, ta = np.full(len(feat), np.nan), np.full(len(feat), np.nan)
    th[ok_idx], ta[ok_idx] = trail_features(gw.mu[ok_idx], gw.nu[ok_idx])
    f2 = feat.copy()
    f2["trail_h"], f2["trail_a"] = th, ta
    f2["shots_share"] = np.log(st["tiri"]["run"].mh / st["tiri"]["run"].ma)
    X0 = stats_v3.design(f2, stat, True)
    variants = {"a": ["trail_h", "trail_a"], "b": ["shots_share"], "c": ["trail_h", "trail_a", "shots_share"]}
    ok = (run0.mh.notna() & feat[spec["hc"]].notna() & feat[spec["ac"]].notna() & (feat.season >= L7.FIRST_TEST)).to_numpy()
    rows = feat.index[ok]
    wk, seas = weeks[ok], feat.season.to_numpy()[ok]
    is_val = np.isin(seas, L7.VALIDATION)
    masks = split_masks(seas)

    def with_level(run):
        rh = L7.dynamic_level(feat.date, feat.Division.to_numpy(), run.mh.to_numpy(), feat[spec["hc"]].to_numpy(float), H, k)
        ra = L7.dynamic_level(feat.date, feat.Division.to_numpy(), run.ma.to_numpy(), feat[spec["ac"]].to_numpy(float), H, k)
        return R6.Run(feat, SPEC[stat], run.mh * rh, run.ma * ra, run.folds), run.mh, run.ma

    base_l, bmh, bma = with_level(run0)
    v0 = R6.evaluate(base_l, rows, al0)
    h0 = interval_hits(feat, stat, base_l.mh, base_l.ma, al0, rows)
    L = ["## M2 — corner e stato di gara", "",
         "Feature pre-partita: `trail_h`/`trail_a` = frazione attesa della partita in cui la casa/l'ospite sta perdendo (dai gol attesi del modello 1X2 v6); `shots_share` = log(tiri attesi casa / tiri attesi ospite). "
         "Baseline = produzione (modello dei corner attuale + livello stagionale H=%d, k=%d). Δ = baseline − variante (positivo = la variante migliora); livello ricalcolato sulla variante." % (H, k), "",
         "| Variante | Δ ll totale tutte [IC a blocchi] | Δ totale validazione | Δ totale held-out [IC a blocchi] | Δ per squadra held-out | Δ O/U totale held-out | Δ totale 2026/27 | Verdetto |", "|---|---|---:|---|---:|---:|---:|---|"]
    res, vec, runs, alphas = {}, {}, {}, {}
    for name, cols in variants.items():
        X = X0.copy()
        for c in cols:
            X[c] = f2[c]
        for c in ("trail_h", "trail_a", "shots_share"):
            if c not in cols and c in X.columns:
                X = X.drop(columns=[c])
        X = X[[c for c in X.columns]]
        run = R6.run_model(f2, SPEC[stat], X)
        for sea, f in run.folds.items():
            if sea == L7.FIRST_TEST:
                run.mh[f["idx"]] = f["mh"]
                run.ma[f["idx"]] = f["ma"]
        al = R6.alphas(run, "global")
        rl, _, _ = with_level(run)
        v = R6.evaluate(rl, rows, al)
        res[name] = R6.compare(v0, v, wk, is_val)
        vec[name], runs[name], alphas[name] = v, rl, al
        print("M2", name, f"{res[name]['ll_tot']['d']:+.5f}", flush=True)
    # scelta in validazione: parita' entro TIE -> la piu' semplice (b, poi a, poi c)
    order = ["b", "a", "c"]
    best = max(res[c]["ll_tot_val"]["d"] for c in order)
    chosen = next(c for c in order if res[c]["ll_tot_val"]["d"] >= best - TIE)
    for name in variants:
        r = res[name]
        d26 = (v0["ll_tot"] - vec[name]["ll_tot"])[masks["2026/27"]].mean()
        L.append(f"| ({name}) {'+'.join(variants[name])}{' ← scelta' if name == chosen else ''} | {r['ll_tot']['d']:+.5f} [{r['ll_tot']['lob']:+.5f}, {r['ll_tot']['hib']:+.5f}] | {r['ll_tot_val']['d']:+.5f} | "
                 f"{r['ll_tot_held']['d']:+.5f} [{r['ll_tot_held']['lob']:+.5f}, {r['ll_tot_held']['hib']:+.5f}] | {r['ll_team_held']['d']:+.5f} | {r['ou_tot']['d']:+.5f} | {d26:+.5f} | {R6.verdict(r)} |")
    r = res[chosen]
    ver = R6.verdict(r)
    h1 = interval_hits(feat, stat, runs[chosen].mh, runs[chosen].ma, alphas[chosen], rows)
    L += ["", f"**Variante scelta in validazione: ({chosen}). Verdetto: {ver}.** Log-loss del totale baseline {r['ll_tot']['base']:.5f}, variante {r['ll_tot']['var']:.5f}; "
          f"per squadra {r['ll_team']['base']:.5f} → {r['ll_team']['var']:.5f}.", "",
          "**Copertura degli intervalli dei corner (dichiarata → reale, scarto in pp) baseline → variante scelta**", "", "| Insieme | Squadra | Totale |", "|---|---|---|"]
    for sp in SPLITS:
        a0, a1 = h0[masks[sp]], h1[masks[sp]]
        L.append(f"| {sp} | {cell_txt(cov_cells(a0, 'team'), False)} → {cell_txt(cov_cells(a1, 'team'), False)} | {cell_txt(cov_cells(a0, 'tot'), False)} → {cell_txt(cov_cells(a1, 'tot'), False)} |")
    # coefficienti (ultimo fold) della variante scelta: segno dell'effetto
    mdl = R6.run_model  # noqa: F841
    X = X0.copy()
    cols = variants[chosen]
    for c in cols:
        X[c] = f2[c]
    for c in ("trail_h", "trail_a", "shots_share"):
        if c not in cols and c in X.columns:
            X = X.drop(columns=[c])
    last = max(runs[chosen].folds)
    tr = X.notna().all(axis=1) & feat[spec["hc"]].notna() & feat[spec["ac"]].notna() & (feat.season >= L7.FIRST_TRAIN) & (feat.season < last)
    from backtest import stats_model as sm
    mdl = sm.fit_stat_model(X[tr], feat[spec["hc"]][tr], feat[spec["ac"]][tr])
    names = list(X.columns)
    def coefs(pipe):
        reg = pipe.named_steps["poissonregressor"]
        return dict(zip(names, reg.coef_))
    ch, ca = coefs(mdl["home"]), coefs(mdl["away"])
    L += ["", f"Coefficienti standardizzati dell'ultimo fold (training fino al {last - 1}/{str(last)[2:]}) per le feature aggiunte: " +
          "; ".join(f"{c}: casa {ch[c]:+.4f}, ospite {ca[c]:+.4f}" for c in cols if c in ch) + ".", ""]
    if ver != "migliora":
        L += ["**Nessuna variante migliora il totale dei corner in modo distinguibile dal rumore**: come concordato, si propone di mostrare i corner con meno enfasi nel pannello (ad es. sezione chiusa di default, senza handicap e «chi ne fa di più» in primo piano).", ""]
    return L, dict(chosen=chosen, verdict=ver, d_all=r["ll_tot"]["d"], d_held=r["ll_tot_held"]["d"], lo_held=r["ll_tot_held"]["lob"], hi_held=r["ll_tot_held"]["hib"])


# ───────────────────────────── M3 ─────────────────────────────
def poisson_beta(y, m0, x):
    """β di y ~ Poisson(m0·exp(β·x)) per massima verosimiglianza."""
    y, m0, x = np.asarray(y, float), np.asarray(m0, float), np.asarray(x, float)

    def nll(b):
        mu = m0 * np.exp(b * x)
        return float((mu - y * np.log(mu)).sum())
    return float(minimize_scalar(nll, bounds=(-3, 4), method="bounded").x)


def beta_ci(y, m0, x, wk, n_boot=1500, seed=41):
    uw, inv = np.unique(wk, return_inverse=True)
    groups = [np.where(inv == g)[0] for g in range(len(uw))]
    rng = np.random.default_rng(seed)
    est = []
    for _ in range(n_boot):
        idx = np.concatenate([groups[g] for g in rng.integers(0, len(uw), len(uw))])
        est.append(poisson_beta(y[idx], m0[idx], x[idx]))
    return poisson_beta(y, m0, x), float(np.percentile(est, 2.5)), float(np.percentile(est, 97.5))


def m3(feat, weeks, st):
    stat = "gialli"
    spec = SPEC[stat]
    run_w, al_w = st[stat]["run"], st[stat]["al"]
    X0 = stats_v3.design(feat, stat, True, referee=False)
    run_0 = R6.run_model(feat, SPEC[stat], X0)
    al_0 = R6.alphas(run_0, "global")
    ok = (run_w.mh.notna() & run_0.mh.notna() & feat[spec["hc"]].notna() & feat[spec["ac"]].notna() & (feat.season >= L7.FIRST_TEST)).to_numpy()
    rows = feat.index[ok]
    wk, seas = weeks[ok], feat.season.to_numpy()[ok]
    y = (feat.loc[rows, spec["hc"]] + feat.loc[rows, spec["ac"]]).to_numpy(float)
    m0 = (run_0.mh[rows] + run_0.ma[rows]).to_numpy(float)
    x = feat.loc[rows, "ref_logR"].to_numpy(float)
    known = (x != 0)
    # sottoinsiemi del 2026/27 dallo storico
    from predictions import monitor
    hist = monitor.load_history()
    inv_code = {v: k for k, v in monitor.LEAGUE_CODE.items()}
    hk = {}
    for r in hist[hist["referee_first_seen"].notna() | hist["referee"].notna()].itertuples(index=False):
        if r.league in monitor.LEAGUE_CODE and isinstance(r.home_dc, str):
            hk.setdefault((monitor.LEAGUE_CODE[r.league], r.home_dc, r.away_dc), []).append(r)
    cat = np.array(["C"] * len(rows), dtype=object)
    for j, (idx, row) in enumerate(feat.loc[rows].iterrows()):
        if row.season != 2026:
            continue
        cand = [r for r in hk.get((row.Division, row.HomeTeam, row.AwayTeam), []) if abs((pd.Timestamp(r.match_date) - row.date).days) <= 3]
        if cand:
            r = cand[0]
            kn = isinstance(r.referee_first_seen, str) and isinstance(r.kickoff, str) and pd.Timestamp(r.referee_first_seen) < pd.Timestamp(r.kickoff)
            cat[j] = "A" if kn else "B"
    masks = {"2019/20-2025/26": seas < 2026, "2026/27": seas == 2026, "2026/27, A (arbitro noto prima)": (seas == 2026) & (cat == "A"),
             "2026/27, B (non noto prima)": (seas == 2026) & (cat == "B"), "2026/27, C (non tracciate, prima del 9/10)": (seas == 2026) & (cat == "C")}
    v_w, v_0 = R6.evaluate(run_w, rows, al_w), R6.evaluate(run_0, rows, al_0)
    L = ["## M3 — gialli: l'effetto arbitro nel 2026/27", "",
         "β = coefficiente di log R (effetto arbitro) in una regressione di Poisson dei gialli totali con offset log(media attesa SENZA arbitro): 1 = effetto ben calibrato, 0 = nessun effetto. "
         "Δ = (modello senza arbitro) − (modello con arbitro): positivo = l'arbitro migliora. IC a blocchi per settimana ISO.", "",
         "| Insieme | Partite | Con arbitro noto (R≠1) | β [IC a blocchi] | Δ ll totale [IC] | Δ ll per squadra [IC] | Gialli previsti (senza arbitro) → reali |", "|---|---:|---:|---|---|---|---|"]
    summ = {}
    for name, m in masks.items():
        if m.sum() < 10:
            L.append(f"| {name} | {int(m.sum())} | – | – | – | – | – |")
            continue
        b, lo, hi = beta_ci(y[m], m0[m], x[m], wk[m])
        d_t = (v_0["ll_tot"] - v_w["ll_tot"])[m]
        d_s = (v_0["ll_team"] - v_w["ll_team"])[m]
        mt, lt, ht = C3.ci_block(d_t, wk[m])
        ms, ls, hs = C3.ci_block(d_s, wk[m])
        summ[name] = (b, lo, hi)
        L.append(f"| {name} | {int(m.sum())} | {int(known[m].sum())} | {b:.2f} [{lo:.2f}, {hi:.2f}] | {mt:+.5f} [{lt:+.5f}, {ht:+.5f}] | {ms:+.5f} [{ls:+.5f}, {hs:+.5f}] | {m0[m].mean():.2f} → {y[m].mean():.2f} |")
    hist_b = summ.get("2019/20-2025/26")
    cur = summ.get("2026/27")
    if cur and hist_b:
        b, lo, hi = cur
        if lo > 0 and lo <= hist_b[0] <= hi:
            verdict = "regge"
        elif lo <= 0 <= hi and (hi - lo) <= 1:
            verdict = "non regge"
        elif (hi - lo) > 1:
            verdict = "indeterminato"
        else:
            verdict = "regge in parte (IC che esclude lo zero ma non include il valore storico)"
    else:
        verdict = "n/d"
    L += ["", f"**Verdetto sull'effetto arbitro nel 2026/27: {verdict}** (β storico {hist_b[0]:.2f} [{hist_b[1]:.2f}, {hist_b[2]:.2f}]; β 2026/27 {cur[0]:.2f} [{cur[1]:.2f}, {cur[2]:.2f}]).", ""]
    # produzione: righe di history con yellow_pred / yellow_real
    h = hist[hist["yellow_pred"].notna() & hist["yellow_real"].notna() & hist["league"].isin(monitor.LEAGUE_CODE)].copy()
    if len(h):
        known_h = h["referee_first_seen"].notna() & h["kickoff"].notna()
        known_h = known_h & (pd.to_datetime(h["referee_first_seen"], errors="coerce") < pd.to_datetime(h["kickoff"], errors="coerce"))
        L += ["**Produzione (righe di `history.csv`, previsioni emesse prima del calcio d'inizio)**", "", "| Arbitro | Partite | Gialli previsti | Gialli reali | Scarto medio (reale − previsto) | Errore medio assoluto |", "|---|---:|---:|---:|---:|---:|"]
        for lab, m in (("noto prima del calcio d'inizio", known_h), ("non noto prima", ~known_h), ("tutte", pd.Series(True, index=h.index))):
            g = h[m.to_numpy()]
            if len(g):
                L.append(f"| {lab} | {len(g)} | {g.yellow_pred.mean():.2f} | {g.yellow_real.mean():.2f} | {(g.yellow_real - g.yellow_pred).mean():+.2f} | {(g.yellow_real - g.yellow_pred).abs().mean():.2f} |")
        L.append("")
    return L, dict(verdict=verdict, beta=summ)


def main():
    feat, gw, weeks, st = prepare()
    parts = {}
    for name, fn in (("M1", lambda: m1(feat, weeks, st)), ("M2", lambda: m2(feat, gw, weeks, st)), ("M3", lambda: m3(feat, weeks, st))):
        L, s = fn()
        open(os.path.join(P8, f"{name}.md"), "w", encoding="utf-8").write("\n".join(L))
        parts[name] = s
        print(name, s, flush=True)
    pd.to_pickle(parts, os.path.join(os.path.dirname(L7.CTX7), "round8.pkl"))


if __name__ == "__main__":
    main()
