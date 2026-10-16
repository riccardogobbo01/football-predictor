"""Round 6 — I (tiri in porta) e J (miglioramenti di tiri, tiri in porta, corner). Solo backtest.
Da lanciare in modalità isolata:  python -I -X utf8 backtest/run_round6_IJ.py"""
import os
import sys
from collections import defaultdict, deque

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import round2_ctx as C2, round3_ctx as C3, round6_lib as R6, stats_model as sm

PARTS6 = os.path.join(REPO_ROOT, "backtest", "round6_parts")
os.makedirs(PARTS6, exist_ok=True)
TIE = 0.0002
GAP_GRID = [(0.02, 0.0), (0.05, 0.0), (0.02, 0.5), (0.05, 0.5)]        # ordine di semplicità
J1_EXTRA = ["eo_diff", "v6_lmu", "v6_lnu"]


def share_series(feat):
    """Quota in porta della squadra (HST/HS) prima di ogni partita: ultime 20 partite, shrinkage 100 tiri verso la lega."""
    f = feat.sort_values("date", kind="stable")
    last = defaultdict(lambda: deque(maxlen=20))
    lg_hs, lg_hst = defaultdict(float), defaultdict(float)
    sh = pd.Series(np.nan, index=feat.index)
    sa = pd.Series(np.nan, index=feat.index)
    for i, dv, h, a, hs, as_, hst, ast in zip(f.index, f.Division, f.HomeTeam, f.AwayTeam, f.HS, f.AS, f.HST, f.AST):
        pL = lg_hst[dv] / lg_hs[dv] if lg_hs[dv] > 0 else 0.33
        for team, out in ((h, sh), (a, sa)):
            q = last[(dv, team)]
            s_hs, s_hst = sum(x[0] for x in q), sum(x[1] for x in q)
            out[i] = (s_hst + 100 * pL) / (s_hs + 100)
        if np.isfinite(hs) and np.isfinite(as_) and np.isfinite(hst) and np.isfinite(ast):
            last[(dv, h)].append((hs, hst))
            last[(dv, a)].append((as_, ast))
            lg_hs[dv] += hs + as_
            lg_hst[dv] += hst + ast
    return sh, sa


def f(x, nd=4):
    return f"{x:.{nd}f}"


def md_baseline(name, spec, s):
    L = [f"**{name}**", "", "| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for lvl, lab in (("team", "Per squadra"), ("tot", "Totale")):
        L.append(f"| {lab} | {f(s['ll_' + lvl])} | {f(s['mae_' + lvl])} | {f(s['corr_' + lvl], 3)} | {f(s['c80_' + lvl], 3)} | {f(s['c90_' + lvl], 3)} | "
                 f"{f(s['ou_' + lvl])} | {f(s['ece_' + lvl], 4)} | {s['bias_' + lvl]:+.4f} |")
    return L + [""]


HEAD = ["| Variante | Δ log-loss totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ log-loss per squadra (tutte) [IC a blocchi] | Δ per squadra held-out | Δ MAE tot. | Δ corr. tot. [IC] | Δ corr. squadra [IC] | Copertura 80% tot. (var.) | Copertura 90% tot. (var.) | ECE O/U tot. (base → var.) | Verdetto |",
        "|---|---|---|---|---:|---:|---|---|---:|---:|---|---|"]


def md_row(name, r, verdict_txt):
    a, h = r["ll_tot"], r["ll_tot_held"]
    t, th = r["ll_team"], r["ll_team_held"]
    return (f"| {name} | {a['d']:+.5f} [{a['lob']:+.5f}, {a['hib']:+.5f}] | {h['d']:+.5f} [{h['lob']:+.5f}, {h['hib']:+.5f}] | "
            f"{t['d']:+.5f} [{t['lob']:+.5f}, {t['hib']:+.5f}] | {th['d']:+.5f} | {r['mae_tot']['d']:+.4f} | "
            f"{r['corr_tot']['d']:+.4f} [{r['corr_tot']['lob']:+.4f}, {r['corr_tot']['hib']:+.4f}] | "
            f"{r['corr_team']['d']:+.4f} [{r['corr_team']['lob']:+.4f}, {r['corr_team']['hib']:+.4f}] | {r['c80_tot']['var']:.3f} | {r['c90_tot']['var']:.3f} | "
            f"{r['ece_tot']['base']:.4f} → {r['ece_tot']['var']:.4f} | {verdict_txt} |")


def main():
    feat, keys, c = R6.prepare()
    SP = R6.SPECS
    L = ["## Esperimenti I e J — tiri in porta (nuovo modello) e miglioramenti di tiri, tiri in porta e corner", ""]

    # ── modelli di base ───────────────────────────────────────────────────────
    base_extra = {"tiri": [], "sot": [], "corner": [], "gialli": ["ref_logR"]}
    runs = {s: R6.run_model(feat, SP[s], R6.design(feat, SP[s], extra=base_extra[s])) for s in base_extra}
    # controllo: il baseline dei tiri coincide con il modello di produzione (stesse feature)
    Xp = sm.design(feat, "tiri", True)
    Xd = R6.design(feat, SP["tiri"])
    assert np.allclose(Xp.to_numpy(), Xd.to_numpy(), equal_nan=True), "baseline tiri != stats_model.design"

    # baseline semplice dei tiri in porta: tiri previsti × quota in porta storica della squadra
    sh, sa = share_series(feat)
    rt = runs["tiri"]
    simple_folds = {s: dict(idx=fd["idx"], mh=fd["mh"] * sh.loc[fd["idx"]].to_numpy(), ma=fd["ma"] * sa.loc[fd["idx"]].to_numpy())
                    for s, fd in rt.folds.items()}
    run_simple = R6.Run(feat, SP["sot"], rt.mh * sh, rt.ma * sa, simple_folds)

    complete = feat[["HS", "AS", "HST", "AST", "HC", "AC", "HY", "AY", "HF", "AF"]].notna().all(axis=1)
    ok = (feat.date >= pd.Timestamp("2019-07-01")) & complete
    for r_ in list(runs.values()) + [run_simple]:
        ok &= r_.mh.notna()
    rows = feat.index[ok]
    weeks = feat.loc[rows, "date"].dt.strftime("%G-%V").to_numpy()
    is_val = feat.loc[rows, "season"].isin(C3.VALIDATION).to_numpy()
    L += [f"Insieme di valutazione: {len(rows)} partite di campionato dal 2019/20 (stesso insieme per tutte le statistiche e varianti). "
          f"Validazione {int(is_val.sum())} partite, held-out {int((~is_val).sum())}.", ""]
    L += ["Controllo: la matrice delle feature del baseline dei tiri coincide con `stats_model.design` di produzione.", ""]

    results = {}

    def eval_run(run, mode="global", **kw):
        return R6.evaluate(run, rows, al=R6.alphas(run, mode), **kw)

    # ── I ─────────────────────────────────────────────────────────────────────
    L += ["### I — Modello dei tiri in porta per squadra (HST/AST)", ""]
    vI, vS = eval_run(runs["sot"]), eval_run(run_simple)
    sI, sS = R6.summarize(vI), R6.summarize(vS)
    cmpI = R6.compare(vS, vI, weeks, is_val)
    L += md_baseline("Baseline semplice: tiri previsti × quota in porta storica", SP["sot"], sS)
    L += md_baseline("Nuovo modello dei tiri in porta (struttura degli altri modelli)", SP["sot"], sI)
    L += ["Δ del nuovo modello rispetto al baseline semplice (positivo = nuovo modello migliore):", ""] + HEAD + \
         [md_row("I — modello dei tiri in porta vs baseline semplice", cmpI, R6.verdict(cmpI))] + [""]
    results["I"] = dict(simple=sS, model=sI, cmp=cmpI)

    # ── J per statistica ──────────────────────────────────────────────────────
    base_name = {"tiri": "modello dei tiri attuale", "sot": "modello I dei tiri in porta", "corner": "modello dei corner attuale"}
    for stat in ("tiri", "sot", "corner"):
        spec = SP[stat]
        run0 = runs[stat]
        v0 = eval_run(run0)
        s0 = R6.summarize(v0)
        L += [f"### J — {stat}: {base_name[stat]} come baseline", ""] + md_baseline("Baseline", spec, s0)
        var_rows = []
        stat_res = {"base": s0}

        # J1: eo_diff + gol attesi v6
        run1 = R6.run_model(feat, spec, R6.design(feat, spec, extra=J1_EXTRA))
        r1 = R6.compare(v0, eval_run(run1), weeks, is_val)
        var_rows.append(("J1 — + eo_diff e gol attesi v6", r1))

        # J2a / J2b: dispersione
        r2a = R6.compare(v0, eval_run(run0, "league"), weeks, is_val)
        var_rows.append(("J2a — alpha per lega", r2a))
        r2b = R6.compare(v0, eval_run(run0, "team"), weeks, is_val)
        var_rows.append(("J2b — alpha per squadra con shrinkage (30)", r2b))

        # J4: GAP ratings, griglia scelta in validazione
        gap_res = []
        for eta, gam in GAP_GRID:
            g = R6.gap_ratings(c.df, spec["hc"], spec["ac"], eta, gam)
            f2 = feat.copy()
            f2["gap_lh"], f2["gap_la"] = np.log(g.gap_h.reindex(f2.index)), np.log(g.gap_a.reindex(f2.index))
            run4 = R6.run_model(f2, spec, R6.design(f2, spec, extra=base_extra.get(stat, []), own=("gap_lh", "gap_la")))
            r4 = R6.compare(v0, eval_run(run4), weeks, is_val)
            gap_res.append(((eta, gam), r4))
        best = max(r["ll_tot_val"]["d"] for _, r in gap_res)
        chosen = next(x for x in gap_res if x[1]["ll_tot_val"]["d"] >= best - TIE)
        for (eta, gam), r4 in gap_res:
            var_rows.append((f"J4 — GAP η={eta}, γ={gam}" + (" (scelta in validazione)" if (eta, gam) == chosen[0] else ""), r4))

        # J3: copula gaussiana, ρ unica o per lega
        al0 = R6.alphas(run0, "global")
        j3 = {}
        for per_league in (False, True):
            rho = R6.estimate_rho(run0, al0, per_league=per_league)
            rr = R6.rho_rows(run0, rho, rows, per_league)
            rr = np.where(np.isfinite(rr), rr, 0.0)
            tot, dif = R6.joint_dists(run0.mh[rows].to_numpy(), run0.ma[rows].to_numpy(), al0.loc[rows, "ah"].to_numpy(),
                                      al0.loc[rows, "aa"].to_numpy(), rr, spec["M"])
            dh, da, _ = R6.make_dists(run0, al0, rows)
            f0 = run0.feat
            y_h, y_a = f0.loc[rows, spec["hc"]].to_numpy(float), f0.loc[rows, spec["ac"]].to_numpy(float)
            vj = R6.vectors(spec, y_h, y_a, dh, da, R6.GridDist(tot))
            rj = R6.compare(v0, vj, weeks, is_val)
            j3[per_league] = dict(rho=rho, res=rj, dif=dif, tot=tot)
        best3 = max(j3[k]["res"]["ll_tot_val"]["d"] for k in (False, True))
        ch3 = False if j3[False]["res"]["ll_tot_val"]["d"] >= best3 - TIE else True
        for pl in (False, True):
            lab = "J3 — copula gaussiana, ρ " + ("per lega" if pl else "unica")
            var_rows.append((lab + (" (scelta in validazione)" if pl == ch3 else ""), j3[pl]["res"]))
        # «chi ha più» (casa / pari / ospite): copula scelta contro indipendenza
        rr0 = np.zeros(len(rows))
        _, dif0 = R6.joint_dists(run0.mh[rows].to_numpy(), run0.ma[rows].to_numpy(), al0.loc[rows, "ah"].to_numpy(),
                                 al0.loc[rows, "aa"].to_numpy(), rr0, spec["M"])
        M = spec["M"]
        yd = (feat.loc[rows, spec["hc"]] - feat.loc[rows, spec["ac"]]).to_numpy(int)
        cls = np.where(yd > 0, 0, np.where(yd == 0, 1, 2))

        def three_way(dif):
            P = np.column_stack([dif[:, M + 1:].sum(1), dif[:, M], dif[:, :M].sum(1)])
            return P, -np.log(np.clip(P[np.arange(len(P)), cls], 1e-12, 1))
        Pc, ll_c = three_way(j3[ch3]["dif"])
        P0, ll_0 = three_way(dif0)
        d3 = ll_0 - ll_c
        m3, lo3, hi3 = C3.ci_match(d3)
        _, lob3, hib3 = C3.ci_block(d3, weeks)
        _, lob3h, hib3h = C3.ci_block(d3[~is_val], weeks[~is_val])
        stat_res["who_more"] = dict(d=m3, lo=lo3, hi=hi3, lob=lob3, hib=hib3, held=float(d3[~is_val].mean()), lobh=lob3h, hibh=hib3h,
                                    ll_copula=float(ll_c.mean()), ll_indep=float(ll_0.mean()),
                                    p_home=float(Pc[:, 0].mean()), p_draw=float(Pc[:, 1].mean()), p_away=float(Pc[:, 2].mean()),
                                    f_home=float((cls == 0).mean()), f_draw=float((cls == 1).mean()), f_away=float((cls == 2).mean()))

        # verdetti e tabella
        L += ["Δ = baseline − variante (positivo = variante migliore); IC 95% a blocchi per settimana.", ""] + HEAD
        for name, r in var_rows:
            if name.startswith("J3"):
                sec = stat_res["who_more"]["held"]
                h = r["ll_tot_held"]
                vt = "migliora" if (h["d"] > 0 and h["lob"] > 0 and sec >= 0) else ("peggiora" if (h["d"] < 0 and h["hib"] < 0) else "non distinguibile dal rumore")
            else:
                vt = R6.verdict(r)
            L.append(md_row(name, r, vt))
            stat_res[name] = dict(res=r, verdict=vt)
        L += ["", f"**J3, «chi ha più {stat}»** (esito casa / pari / ospite) con ρ {'per lega' if ch3 else 'unica'}: log-loss {ll_c.mean():.4f} contro {ll_0.mean():.4f} "
                  f"con l'indipendenza (ρ = 0): Δ {m3:+.5f}, IC a blocchi [{lob3:+.5f}, {hib3:+.5f}], held-out {d3[~is_val].mean():+.5f} "
                  f"[{lob3h:+.5f}, {hib3h:+.5f}]. Probabilità medie previste casa/pari/ospite {Pc[:, 0].mean():.3f}/{Pc[:, 1].mean():.3f}/{Pc[:, 2].mean():.3f}, "
                  f"frequenze osservate {np.mean(cls == 0):.3f}/{np.mean(cls == 1):.3f}/{np.mean(cls == 2):.3f}.", ""]
        rho_last = j3[ch3]["rho"]
        L += ["ρ stimata (ultimo fold): " + (", ".join(f"{k} {v:+.3f}" for k, v in rho_last[max(rho_last)].items()) if ch3 else f"{rho_last[max(rho_last)]:+.3f}") + ".", ""]
        stat_res["chosen_gap"] = chosen[0]
        stat_res["chosen_rho_per_league"] = ch3
        stat_res["rho_last"] = rho_last[max(rho_last)]
        results[stat] = stat_res
        pd.to_pickle(dict(rows_n=len(rows)), os.path.join(C3.R3_DIR, "r6_IJ_progress.pkl"))
        print(stat, "fatto", flush=True)

    with open(os.path.join(PARTS6, "IJ.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    pd.to_pickle(results, os.path.join(C3.R3_DIR, "r6_IJ.pkl"))
    print("\n".join(L))


if __name__ == "__main__":
    main()
