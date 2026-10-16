"""Round 6 — K (nuovi mercati derivati: primo tempo, «chi fa più» e handicap, falli). Solo backtest.
Da lanciare in modalità isolata:  python -I -X utf8 backtest/run_round6_K.py"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd
from scipy.stats import poisson
from sklearn.linear_model import PoissonRegressor

from backtest import refeffect, round3_ctx as C3, round6_lib as R6, stats_baseline
from backtest.run_round6_IJ import HEAD, md_baseline, md_row
from config import REFEREE_K

PARTS6 = os.path.join(REPO_ROOT, "backtest", "round6_parts")
TIE = 0.0002
LG_DUMMIES = ["E0", "D1", "SP1", "F1"]


# ───────────────────────────── K1: primo tempo ─────────────────────────────
def ht_probs(m1, n1, G=8):
    """1X2 al riposo, Over 0.5 e Over 1.5 dei gol del primo tempo (Poisson indipendenti)."""
    k = np.arange(G + 1)
    pm, pn = poisson.pmf(k[None, :], m1[:, None]), poisson.pmf(k[None, :], n1[:, None])
    J = pm[:, :, None] * pn[:, None, :]
    J /= J.sum((1, 2), keepdims=True)
    i, j = np.indices((G + 1, G + 1))
    P = np.column_stack([(J * (i > j)).sum((1, 2)), (J * (i == j)).sum((1, 2)), (J * (i < j)).sum((1, 2))])
    lam = m1 + n1
    return P, 1 - np.exp(-lam), 1 - np.exp(-lam) * (1 + lam)


def ht_fit_predict(feat, variant, s, tr, te):
    """Medie dei gol del primo tempo (casa, ospite) per le righe te, stimate sulle righe tr (stagioni precedenti)."""
    mu_tr, nu_tr = np.exp(feat.loc[tr, "v6_lmu"].to_numpy()), np.exp(feat.loc[tr, "v6_lnu"].to_numpy())
    mu_te, nu_te = np.exp(feat.loc[te, "v6_lmu"].to_numpy()), np.exp(feat.loc[te, "v6_lnu"].to_numpy())
    hh, ha = feat.loc[tr, "HTHG"].to_numpy(float), feat.loc[tr, "HTAG"].to_numpy(float)
    fh, fa = feat.loc[tr, "hg"].to_numpy(float), feat.loc[tr, "ag"].to_numpy(float)
    dv_tr, dv_te = feat.loc[tr, "Division"].to_numpy(), feat.loc[te, "Division"].to_numpy()
    out_h, out_a = np.zeros(len(mu_te)), np.zeros(len(mu_te))
    if variant == "clim":
        for lg in np.unique(dv_te):
            m = dv_tr == lg
            out_h[dv_te == lg], out_a[dv_te == lg] = hh[m].mean(), ha[m].mean()
        return out_h, out_a
    if variant in ("a", "b"):
        for lg in np.unique(dv_te):
            m = dv_tr == lg
            if variant == "a":
                sh = sa = (hh[m].sum() + ha[m].sum()) / (fh[m].sum() + fa[m].sum())
            else:
                sh, sa = hh[m].sum() / fh[m].sum(), ha[m].sum() / fa[m].sum()
            t = dv_te == lg
            out_h[t], out_a[t] = sh * mu_te[t], sa * nu_te[t]
        return out_h, out_a
    # c: regressione di Poisson con esposizione = gol attesi FT, dummy di lega e log(mu+nu) come covariata
    def X(dv, mu, nu):
        return np.column_stack([(dv == lg).astype(float) for lg in LG_DUMMIES] + [np.log(mu + nu) - np.log(2.7)])
    for (y, expo_tr, expo_te, tag) in ((hh, mu_tr, mu_te, "h"), (ha, nu_tr, nu_te, "a")):
        m = PoissonRegressor(alpha=1e-6, max_iter=500).fit(X(dv_tr, mu_tr, nu_tr), y / expo_tr, sample_weight=expo_tr)
        pred = expo_te * m.predict(X(dv_te, mu_te, nu_te))
        if tag == "h":
            out_h = pred
            coef_h = m.coef_[-1]
        else:
            out_a = pred
            coef_a = m.coef_[-1]
    ht_fit_predict.last_coef = (coef_h, coef_a)
    return out_h, out_a


def k1(feat):
    L = ["### K1 — Primo tempo", ""]
    ok = feat[["HTHG", "HTAG", "v6_lmu", "v6_lnu"]].notna().all(axis=1)
    test = (feat.date >= pd.Timestamp("2019-07-01")) & ok
    rows = feat.index[test]
    weeks = feat.loc[rows, "date"].dt.strftime("%G-%V").to_numpy()
    is_val = feat.loc[rows, "season"].isin(C3.VALIDATION).to_numpy()
    hh, ha = feat.loc[rows, "HTHG"].to_numpy(int), feat.loc[rows, "HTAG"].to_numpy(int)
    cls = np.where(hh > ha, 0, np.where(hh == ha, 1, 2))
    tot = hh + ha
    res, means = {}, {}
    for variant in ("clim", "a", "b", "c"):
        m1, n1 = np.zeros(len(rows)), np.zeros(len(rows))
        for s in sorted(feat.loc[rows, "season"].unique()):
            tr = ok & (feat.season >= R6.FIRST_TRAIN) & (feat.season < s)
            te_idx = feat.index[(feat.index.isin(rows)) & (feat.season == s)]
            a, b = ht_fit_predict(feat, variant, s, feat.index[tr], te_idx)
            pos = rows.get_indexer(te_idx)
            m1[pos], n1[pos] = a, b
        means[variant] = (m1, n1)
        P, o05, o15 = ht_probs(m1, n1)
        ll12 = -np.log(np.clip(P[np.arange(len(P)), cls], 1e-12, 1))
        p05, p15 = np.clip(o05, 1e-9, 1 - 1e-9), np.clip(o15, 1e-9, 1 - 1e-9)
        y05, y15 = (tot >= 1).astype(float), (tot >= 2).astype(float)
        ll05 = -(y05 * np.log(p05) + (1 - y05) * np.log(1 - p05))
        ll15 = -(y15 * np.log(p15) + (1 - y15) * np.log(1 - p15))
        res[variant] = dict(P=P, p05=p05, p15=p15, ll12=ll12, ll05=ll05, ll15=ll15, avg=(ll12 + ll05 + ll15) / 3,
                            coef=getattr(ht_fit_predict, "last_coef", None) if variant == "c" else None)
    y05, y15 = (tot >= 1).astype(float), (tot >= 2).astype(float)

    def calib(r):
        pool_p = r["P"].ravel()
        pool_o = np.eye(3)[cls].ravel()
        return dict(ece12=R6._ece(pool_p, pool_o), bias_h=float(r["P"][:, 0].mean() - (cls == 0).mean()),
                    bias_x=float(r["P"][:, 1].mean() - (cls == 1).mean()), bias_a=float(r["P"][:, 2].mean() - (cls == 2).mean()),
                    ece05=R6._ece(r["p05"], y05), bias05=float(r["p05"].mean() - y05.mean()),
                    ece15=R6._ece(r["p15"], y15), bias15=float(r["p15"].mean() - y15.mean()))

    L += [f"{len(rows)} partite di test con punteggio al riposo (dal 2019/20). Frequenze osservate: 1X2 al riposo "
          f"{np.mean(cls == 0):.3f}/{np.mean(cls == 1):.3f}/{np.mean(cls == 2):.3f}, Over 0.5 {y05.mean():.3f}, Over 1.5 {y15.mean():.3f}; gol medi del primo tempo "
          f"casa {hh.mean():.3f}, ospite {ha.mean():.3f}; quota media dei gol nel primo tempo {(hh.sum() + ha.sum()) / (feat.loc[rows, 'hg'].sum() + feat.loc[rows, 'ag'].sum()):.3f}.", "",
          "| Variante | Log-loss 1X2 | Log-loss Over 0.5 | Log-loss Over 1.5 | Media dei tre | ECE 1X2 | ECE O0.5 | ECE O1.5 | Scarto O0.5 | Scarto O1.5 | Scarto 1/X/2 |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    names = {"clim": "Riferimento: medie di lega (nessuna informazione sulla partita)", "a": "K1a — quota 1T per lega", "b": "K1b — quote 1T casa/ospite per lega",
             "c": "K1c — regressione con gol attesi totali"}
    for v in ("clim", "a", "b", "c"):
        r = res[v]
        cb = calib(r)
        L.append(f"| {names[v]} | {r['ll12'].mean():.4f} | {r['ll05'].mean():.4f} | {r['ll15'].mean():.4f} | {r['avg'].mean():.4f} | {cb['ece12']:.4f} | "
                 f"{cb['ece05']:.4f} | {cb['ece15']:.4f} | {cb['bias05']:+.4f} | {cb['bias15']:+.4f} | {cb['bias_h']:+.3f}/{cb['bias_x']:+.3f}/{cb['bias_a']:+.3f} |")
    # scelta sulle validazione tra a, b, c
    order = ["a", "b", "c"]
    best = min(res[v]["avg"][is_val].mean() for v in order)
    chosen = next(v for v in order if res[v]["avg"][is_val].mean() <= best + TIE)
    L += ["", f"Scelta sulle validazione tra (a), (b), (c) (log-loss media dei tre mercati; parità entro {TIE} → la più semplice): **K1{chosen}**.", ""]
    L += ["Δ log-loss rispetto al riferimento (medie di lega) e rispetto a K1a (positivo = migliore; IC 95% a blocchi per settimana):", "",
          "| Variante | Mercato | Δ vs riferimento [IC a blocchi] | Δ held-out vs riferimento [IC a blocchi] | Δ vs K1a [IC a blocchi] |", "|---|---|---|---|---|"]
    out = {}
    for v in order:
        for mk, key in (("1X2 al riposo", "ll12"), ("Over 0.5 1T", "ll05"), ("Over 1.5 1T", "ll15"), ("media dei tre", "avg")):
            d = res["clim"][key] - res[v][key]
            _, lob, hib = C3.ci_block(d, weeks)
            _, lobh, hibh = C3.ci_block(d[~is_val], weeks[~is_val])
            da = res["a"][key] - res[v][key]
            _, loba, hiba = C3.ci_block(da, weeks) if v != "a" else (0, 0, 0)
            L.append(f"| {names[v]}{' (scelta)' if v == chosen else ''} | {mk} | {d.mean():+.5f} [{lob:+.5f}, {hib:+.5f}] | "
                     f"{d[~is_val].mean():+.5f} [{lobh:+.5f}, {hibh:+.5f}] | " + ("—" if v == "a" else f"{da.mean():+.5f} [{loba:+.5f}, {hiba:+.5f}]") + " |")
            out[(v, key)] = dict(d=float(d.mean()), lob=lob, hib=hib, held=float(d[~is_val].mean()), lobh=lobh, hibh=hibh)
    c_coef = res["c"]["coef"]
    L += ["", f"K1c: coefficiente di log(μ+ν) sulla quota del primo tempo (ultimo fold; negativo = quota minore quando ci si aspettano più gol): casa {c_coef[0]:+.3f}, ospite {c_coef[1]:+.3f}.", ""]
    shares = {lg: float((feat[(feat.Division == lg) & ok & (feat.season < 2026)][["HTHG", "HTAG"]].sum().sum()) /
                        (feat[(feat.Division == lg) & ok & (feat.season < 2026)][["hg", "ag"]].sum().sum())) for lg in ("I1", "E0", "D1", "SP1", "F1")}
    L += ["Quota media dei gol nel primo tempo per lega (tutte le stagioni dal 2016/17): " + ", ".join(f"{k} {v:.3f}" for k, v in shares.items()) + ".", ""]
    return L, dict(chosen=chosen, res={v: {k: float(x.mean()) for k, x in r.items() if k in ("ll12", "ll05", "ll15", "avg")} for v, r in res.items()},
                   cal={v: calib(res[v]) for v in res}, cmp=out, shares=shares)


# ───────────────────────────── K2 e K3 ─────────────────────────────
def joint_for(run, rows, M, per_league):
    al0 = R6.alphas(run, "global")
    rho = R6.estimate_rho(run, al0, per_league=per_league)
    rr = np.where(np.isfinite(R6.rho_rows(run, rho, rows, per_league)), R6.rho_rows(run, rho, rows, per_league), 0.0)
    a = (run.mh[rows].to_numpy(), run.ma[rows].to_numpy(), al0.loc[rows, "ah"].to_numpy(), al0.loc[rows, "aa"].to_numpy())
    tot, dif = R6.joint_dists(*a, rr, M)
    return tot, dif, rho


def k2(feat, runs, rows, weeks, is_val):
    L = ["### K2 — «Chi fa più» e handicap ±1,5 dai modelli congiunti", ""]
    out = {}
    for stat in ("corner", "gialli"):
        spec = R6.SPECS[stat]
        run = runs[stat]
        M = spec["M"]
        al0 = R6.alphas(run, "global")
        yh, ya = feat.loc[rows, spec["hc"]].to_numpy(int), feat.loc[rows, spec["ac"]].to_numpy(int)
        yd = yh - ya
        cls = np.where(yd > 0, 0, np.where(yd == 0, 1, 2))
        v = R6.vectors(spec, yh.astype(float), ya.astype(float), *R6.make_dists(run, al0, rows))
        # ρ scelta con la regola di J3 (log-loss del totale in validazione)
        cand = {}
        for pl in (False, True):
            tot, dif, rho = joint_for(run, rows, M, pl)
            vj = R6.vectors(spec, yh.astype(float), ya.astype(float), *R6.make_dists(run, al0, rows)[:2], R6.GridDist(tot))
            cand[pl] = dict(dif=dif, ll=vj["ll_tot"], rho=rho)
        best = min(cand[k]["ll"][is_val].mean() for k in cand)
        pl = False if cand[False]["ll"][is_val].mean() <= best + TIE else True
        dif_c = cand[pl]["dif"]
        _, dif_0 = R6.joint_dists(run.mh[rows].to_numpy(), run.ma[rows].to_numpy(), al0.loc[rows, "ah"].to_numpy(), al0.loc[rows, "aa"].to_numpy(),
                                  np.zeros(len(rows)), M)

        def p3(dif):
            return np.column_stack([dif[:, M + 1:].sum(1), dif[:, M], dif[:, :M].sum(1)])

        def hcap(dif):      # casa −1,5 (diff ≥ 2) e ospite −1,5 (diff ≤ −2)
            return dif[:, M + 2:].sum(1), dif[:, :M - 1].sum(1)
        res_s = {"rho": cand[pl]["rho"], "per_league": pl}
        rows_md = []
        P_c, P_0 = p3(dif_c), p3(dif_0)
        for lab, P in (("copula", P_c), ("indipendenza", P_0)):
            ll = -np.log(np.clip(P[np.arange(len(P)), cls], 1e-12, 1))
            res_s[lab] = dict(ll3=ll, ece3=R6._ece(P.ravel(), np.eye(3)[cls].ravel()),
                              bias=(float(P[:, 0].mean() - (cls == 0).mean()), float(P[:, 1].mean() - (cls == 1).mean()), float(P[:, 2].mean() - (cls == 2).mean())))
        d3 = res_s["indipendenza"]["ll3"] - res_s["copula"]["ll3"]
        L += [f"**{stat}**: ρ {'per lega' if pl else 'unica'} (ultimo fold {'/'.join(f'{k} {x:+.3f}' for k, x in cand[pl]['rho'][max(cand[pl]['rho'])].items()) if pl else format(cand[pl]['rho'][max(cand[pl]['rho'])], '+.3f')}).", "",
              "| Mercato | Log-loss copula | Log-loss indipendenza | Δ [IC a blocchi] | Δ held-out [IC a blocchi] | ECE copula / indip. | Scarto medio copula (casa/pari/ospite) | Frequenze osservate |",
              "|---|---:|---:|---|---|---|---|---|"]
        _, lo, hi = C3.ci_block(d3, weeks)
        _, loh, hih = C3.ci_block(d3[~is_val], weeks[~is_val])
        bc = res_s["copula"]["bias"]
        L.append(f"| Chi ha più {stat} (casa / pari / ospite) | {res_s['copula']['ll3'].mean():.4f} | {res_s['indipendenza']['ll3'].mean():.4f} | {d3.mean():+.5f} [{lo:+.5f}, {hi:+.5f}] | "
                 f"{d3[~is_val].mean():+.5f} [{loh:+.5f}, {hih:+.5f}] | {res_s['copula']['ece3']:.4f} / {res_s['indipendenza']['ece3']:.4f} | "
                 f"{bc[0]:+.3f}/{bc[1]:+.3f}/{bc[2]:+.3f} | {np.mean(cls == 0):.3f}/{np.mean(cls == 1):.3f}/{np.mean(cls == 2):.3f} |")
        res_s["d3"] = dict(d=float(d3.mean()), lob=lo, hib=hi, held=float(d3[~is_val].mean()), lobh=loh, hibh=hih)
        if stat == "corner":
            for side, ev_c, ev_0, ev_y in (("Casa −1,5 (casa vince di almeno 2 corner)", hcap(dif_c)[0], hcap(dif_0)[0], (yd >= 2)),
                                            ("Ospite −1,5 (ospite vince di almeno 2 corner)", hcap(dif_c)[1], hcap(dif_0)[1], (yd <= -2))):
                o = ev_y.astype(float)
                lls = {}
                for lab, p in (("copula", ev_c), ("indipendenza", ev_0)):
                    p = np.clip(p, 1e-9, 1 - 1e-9)
                    lls[lab] = (-(o * np.log(p) + (1 - o) * np.log(1 - p)), R6._ece(p, o), float(p.mean() - o.mean()))
                dh_ = lls["indipendenza"][0] - lls["copula"][0]
                _, lo, hi = C3.ci_block(dh_, weeks)
                _, loh, hih = C3.ci_block(dh_[~is_val], weeks[~is_val])
                L.append(f"| Handicap {side} | {lls['copula'][0].mean():.4f} | {lls['indipendenza'][0].mean():.4f} | {dh_.mean():+.5f} [{lo:+.5f}, {hi:+.5f}] | "
                         f"{dh_[~is_val].mean():+.5f} [{loh:+.5f}, {hih:+.5f}] | {lls['copula'][1]:.4f} / {lls['indipendenza'][1]:.4f} | "
                         f"{lls['copula'][2]:+.4f} (indip. {lls['indipendenza'][2]:+.4f}) | frequenza {o.mean():.3f} |")
                res_s[side] = dict(d=float(dh_.mean()), lob=lo, hib=hi, held=float(dh_[~is_val].mean()), lobh=loh, hibh=hih)
        L.append("")
        out[stat] = res_s
    return L, out


def main():
    feat, keys, c = R6.prepare()
    SP = R6.SPECS
    L = ["## Esperimento K — Nuovi mercati derivati", ""]
    l1, r1 = k1(feat)
    L += l1

    # modelli per K2 / K3
    runs = {s: R6.run_model(feat, SP[s], R6.design(feat, SP[s], extra=(["ref_logR"] if s == "gialli" else []))) for s in ("corner", "gialli")}
    # K3: falli (a) senza arbitro, (b) con effetto arbitro sui falli
    run_fa = R6.run_model(feat, SP["falli"], R6.design(feat, SP["falli"]))
    m_tot = run_fa.mh + run_fa.ma
    # per le righe 2016-2018 servono le medie in campione del primo fold
    fold0 = run_fa.folds[R6.FIRST_TEST]
    m_all = m_tot.copy()
    m_all.loc[fold0["idx"]] = fold0["mh"] + fold0["ma"]
    R, _ = refeffect.referee_ratio(feat, feat.HF + feat.AF, m_all, keys, REFEREE_K, refeffect.mbar_by_league(feat, m_all))
    feat2 = feat.copy()
    feat2["ref_logR_f"] = np.log(R)
    run_fb = R6.run_model(feat2, SP["falli"], R6.design(feat2, SP["falli"], extra=["ref_logR_f"]))
    # baseline semplice dei falli: metodo «a medie»
    stats_baseline.STAT_COLS = {"falli": ("HF", "AF")}
    df = c.df
    base = stats_baseline.walk_forward(df, start="2016-07-01")
    bh, ba = base["falli_bh"].reindex(feat.index), base["falli_ba"].reindex(feat.index)
    simple_folds = {s: dict(idx=fd["idx"], mh=bh.loc[fd["idx"]].to_numpy(), ma=ba.loc[fd["idx"]].to_numpy()) for s, fd in run_fa.folds.items()}
    run_fs = R6.Run(feat, SP["falli"], bh, ba, simple_folds)

    complete = feat[["HS", "AS", "HST", "AST", "HC", "AC", "HY", "AY", "HF", "AF"]].notna().all(axis=1)
    ok = (feat.date >= pd.Timestamp("2019-07-01")) & complete
    for r_ in list(runs.values()) + [run_fa, run_fb, run_fs]:
        ok &= r_.mh.notna()
    rows = feat.index[ok]
    weeks = feat.loc[rows, "date"].dt.strftime("%G-%V").to_numpy()
    is_val = feat.loc[rows, "season"].isin(C3.VALIDATION).to_numpy()
    L += [f"Per K2 e K3 l'insieme di valutazione è quello dei campionati: {len(rows)} partite dal 2019/20.", ""]
    l2, r2 = k2(feat, runs, rows, weeks, is_val)
    L += l2

    L += ["### K3 — Falli per squadra e totali", ""]
    v_s = R6.evaluate(run_fs, rows)
    v_a = R6.evaluate(run_fa, rows)
    v_b = R6.evaluate(run_fb, rows)
    L += md_baseline("Baseline semplice: metodo «a medie» sui falli", SP["falli"], R6.summarize(v_s))
    L += md_baseline("K3a — modello dei falli (struttura degli altri, senza arbitro)", SP["falli"], R6.summarize(v_a))
    L += md_baseline("K3b — modello dei falli con effetto arbitro", SP["falli"], R6.summarize(v_b))
    ca = R6.compare(v_s, v_a, weeks, is_val)
    cb = R6.compare(v_a, v_b, weeks, is_val)
    cs = R6.compare(v_s, v_b, weeks, is_val)
    L += ["Δ = baseline − variante (positivo = variante migliore); IC 95% a blocchi per settimana.", ""] + HEAD + \
         [md_row("K3a vs baseline a medie", ca, R6.verdict(ca)), md_row("K3b (con arbitro) vs K3a", cb, R6.verdict(cb)),
          md_row("K3b vs baseline a medie", cs, R6.verdict(cs))] + [""]
    strip = lambda r: r
    res = dict(k1=r1, k2=r2, k3=dict(sum_simple=R6.summarize(v_s), sum_a=R6.summarize(v_a), sum_b=R6.summarize(v_b), a_vs_simple=ca, b_vs_a=cb, b_vs_simple=cs,
                                      verdicts=dict(a=R6.verdict(ca), b_vs_a=R6.verdict(cb), b_vs_simple=R6.verdict(cs))))
    with open(os.path.join(PARTS6, "K.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    pd.to_pickle(res, os.path.join(C3.R3_DIR, "r6_K.pkl"))
    print("\n".join(L))


if __name__ == "__main__":
    main()
