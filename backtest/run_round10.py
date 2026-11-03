"""Round 10 — livello di stagione per lega (bayesiano) per gol e statistiche. Solo backtest. Criteri in backtest/round10_parts/prereg.md.
Da lanciare in modalità isolata:  python -I -X utf8 backtest/run_round10.py [GOALS|STATS|REF]
Scrive backtest/round10_parts/{GOALS,CASE,STATS,REF}.md; results_round10.md si assembla con run_round10_final.py."""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import refeffect, round3_ctx as C3, round6_lib as R6, round7_lib as L7, stats_v3
from backtest.round2_lib import devig
from backtest.run_round7 import LG_NAME, SPEC, eval_goals, interval_gaps, prepare
from backtest.run_round7_prod import level_run
from config import LEVEL_PARAMS, REFEREE_K

P10 = os.path.join(REPO_ROOT, "backtest", "round10_parts")
os.makedirs(P10, exist_ok=True)
KGRID = [10, 20, 40, 80, 160, 320]
TIE = 0.0002
ZTHR = 2.0
LEAGUES = L7.LEAGUES


# ───────────────────────────── livello di stagione bayesiano ─────────────────────────────
def season_level(days, leagues, seasons, pred, obs, k, var=None):
    """Per riga: (R, z) con R = (Σy + k·m̄)/(Σμ + k·m̄), z = (Σy − Σμ)/√Σvar, somme sulle partite della stessa lega e stagione di GIORNI PRECEDENTI.
    pred = medie attese, obs = osservati, var = varianza attesa per partita (default = pred, Poisson). R = 1 e z = 0 senza partite precedenti."""
    days = np.asarray(days, float)
    pred, obs = np.asarray(pred, float), np.asarray(obs, float)
    var = pred if var is None else np.asarray(var, float)
    key = np.asarray(leagues).astype(str) + "|" + np.asarray(seasons).astype(str)
    R, Z = np.ones(len(days)), np.zeros(len(days))
    for kk in np.unique(key):
        idx = np.where(key == kk)[0]
        ok = np.isfinite(pred[idx]) & np.isfinite(obs[idx])
        ud, inv = np.unique(days[idx], return_inverse=True)
        sy = np.bincount(inv, weights=np.where(ok, obs[idx], 0.0), minlength=len(ud))
        sm = np.bincount(inv, weights=np.where(ok, pred[idx], 0.0), minlength=len(ud))
        sv = np.bincount(inv, weights=np.where(ok, var[idx], 0.0), minlength=len(ud))
        sn = np.bincount(inv, weights=ok.astype(float), minlength=len(ud))
        cy, cm, cv, cn = (np.cumsum(a) - a for a in (sy, sm, sv, sn))          # solo giorni precedenti
        with np.errstate(divide="ignore", invalid="ignore"):
            mb = np.where(cn > 0, cm / cn, 0.0)
            r = np.where(cn > 0, (cy + k * mb) / (cm + k * mb), 1.0)
            z = np.where(cv > 0, (cy - cm) / np.sqrt(cv), 0.0)
        R[idx], Z[idx] = r[inv], z[inv]
    return R, Z


def gate(R, Z):
    return np.where(np.abs(Z) > ZTHR, R, 1.0)


def simp(c):
    return -c if np.isscalar(c) else tuple(-x for x in c)


def verdict(d, lo, hi, sec=0.0):
    if d > 0 and lo > 0 and sec >= 0:
        return "migliora"
    if d < 0 and hi < 0:
        return "peggiora"
    return "non distinguibile dal rumore"


# ───────────────────────────── gol ─────────────────────────────
def goals_part(feat, gw, weeks):
    days = (feat.date - pd.Timestamp("2000-01-01")).dt.days.to_numpy(float)
    lg, se = feat.Division.to_numpy(), feat.season.to_numpy()
    ev = (feat.season >= L7.FIRST_TEST).to_numpy() & gw.mu.notna().to_numpy() & feat.hg.notna().to_numpy()
    main = ev & (se <= 2025)
    cur = ev & (se == 2026)
    rows_m, rows_c = feat.index[main], feat.index[cur]
    wk_m, se_m = weeks[main], se[main]
    is_val = np.isin(se_m, L7.VALIDATION)
    base_m = eval_goals(feat, gw.mu, gw.nu, gw.rho, rows_m)
    base_c = eval_goals(feat, gw.mu, gw.nu, gw.rho, rows_c)
    hg, ag = feat.hg.to_numpy(float), feat.ag.to_numpy(float)
    cfgs = {}
    for k in KGRID:
        rh, zh = season_level(days, lg, se, gw.mu.to_numpy(), hg, k)
        ra, za = season_level(days, lg, se, gw.nu.to_numpy(), ag, k)
        for name, (a, b) in (("N1", (rh, ra)), ("N2", (gate(rh, zh), gate(ra, za)))):
            mu, nu = gw.mu * a, gw.nu * b
            cfgs[(name, k)] = dict(mu=mu, nu=nu, vm=eval_goals(feat, mu, nu, gw.rho, rows_m), vc=eval_goals(feat, mu, nu, gw.rho, rows_c))
        print("goals k", k, flush=True)

    def dvec(vb, vv, key):
        return vb[key] - vv[key]

    out = {}
    L = ["## N1 e N2 — gol", "", f"Baseline: stack v6 di produzione senza livello di stagione. Insiemi: validazione {int(is_val.sum())} partite, held-out 2022/23-2025/26 {int((~is_val).sum())}, 2026/27 {int(cur.sum())}. "
         "Δ = baseline − variante (positivo = migliora).", ""]
    for name in ("N1", "N2"):
        best = max(dvec(base_m, cfgs[(name, k)]["vm"], "ll")[is_val].mean() for k in KGRID)
        cand = [k for k in KGRID if dvec(base_m, cfgs[(name, k)]["vm"], "ll")[is_val].mean() >= best - TIE]
        kch = max(cand)
        out[name] = kch
        L += [f"### {name}: griglia di k", "", "| k | Δ ll 1X2 validazione | Δ ll 1X2 held-out [IC a blocchi] | Δ ll O/U 2,5 held-out [IC] | Δ RPS held-out | Δ ll 1X2 2026/27 (descrittivo) | Verdetto |", "|---:|---:|---|---|---:|---:|---|"]
        for k in KGRID:
            c = cfgs[(name, k)]
            dl, do_, dr = dvec(base_m, c["vm"], "ll"), dvec(base_m, c["vm"], "ou"), dvec(base_m, c["vm"], "rps")
            m, lo, hi = C3.ci_block(dl[~is_val], wk_m[~is_val])
            mo, loo, hio = C3.ci_block(do_[~is_val], wk_m[~is_val])
            ver = verdict(m, lo, hi, mo)
            L.append(f"| {k} | {dl[is_val].mean():+.5f} | {m:+.5f} [{lo:+.5f}, {hi:+.5f}] | {mo:+.5f} [{loo:+.5f}, {hio:+.5f}] | {dr[~is_val].mean():+.5f} | {dvec(base_c, c['vc'], 'll').mean():+.5f} | {ver}{' ← scelta' if k == kch else ''} |")
        L.append("")
    # riepilogo con gli IC e gli altri mercati
    L += ["### Riepilogo delle configurazioni scelte in validazione", "", "| Variante | k | Δ ll 1X2 held-out [IC] | Δ ll O/U 2,5 held-out [IC] | Δ RPS held-out | Δ O/U 1,5 | Δ O/U 3,5 | Δ BTTS | Verdetto |", "|---|---:|---|---|---:|---:|---:|---:|---|"]
    summ = {}
    for name in ("N1", "N2"):
        k = out[name]
        c = cfgs[(name, k)]
        dl, do_ = dvec(base_m, c["vm"], "ll"), dvec(base_m, c["vm"], "ou")
        m, lo, hi = C3.ci_block(dl[~is_val], wk_m[~is_val])
        mo, loo, hio = C3.ci_block(do_[~is_val], wk_m[~is_val])
        ver = verdict(m, lo, hi, mo)
        summ[name] = dict(k=k, d=m, lo=lo, hi=hi, d_ou=mo, verdict=ver)
        L.append(f"| {name} | {k} | {m:+.5f} [{lo:+.5f}, {hi:+.5f}] | {mo:+.5f} [{loo:+.5f}, {hio:+.5f}] | {dvec(base_m, c['vm'], 'rps')[~is_val].mean():+.5f} | "
                 f"{dvec(base_m, c['vm'], 'ou_o15')[~is_val].mean():+.5f} | {dvec(base_m, c['vm'], 'ou_o35')[~is_val].mean():+.5f} | {dvec(base_m, c['vm'], 'ou_btts')[~is_val].mean():+.5f} | {ver} |")
    L.append("")
    # prime 10 giornate / resto (held-out)
    g10 = (feat.gday.to_numpy()[main] <= 10)
    L += ["Δ ll 1X2 held-out per fase della stagione (configurazioni scelte):", "", "| Variante | Prime 10 giornate | Resto |", "|---|---:|---:|"]
    for name in ("N1", "N2"):
        dl = dvec(base_m, cfgs[(name, out[name])]["vm"], "ll")
        L.append(f"| {name} | {dl[(~is_val) & g10].mean():+.5f} | {dl[(~is_val) & ~g10].mean():+.5f} |")
    L.append("")
    return L, dict(out=out, summ=summ, cfgs=cfgs, base_c=base_c, rows_c=rows_c, days=days, lg=lg, se=se, hg=hg, ag=ag)


def activation_part(feat, gw):
    """Attivazioni del filtro di N2 (non dipendono da k) per lega e stagione."""
    days = (feat.date - pd.Timestamp("2000-01-01")).dt.days.to_numpy(float)
    lg, se = feat.Division.to_numpy(), feat.season.to_numpy()
    ev = (feat.season >= L7.FIRST_TEST).to_numpy() & gw.mu.notna().to_numpy() & feat.hg.notna().to_numpy()
    _, zh = season_level(days, lg, se, gw.mu.to_numpy(), feat.hg.to_numpy(float), 10)
    _, za = season_level(days, lg, se, gw.nu.to_numpy(), feat.ag.to_numpy(float), 10)
    rows = []
    for s_ in sorted(set(se[ev])):
        for l_ in LEAGUES:
            m = ev & (se == s_) & (lg == l_)
            if not m.any():
                continue
            n = int(m.sum())
            late = m & (feat.gday.to_numpy() >= 6)                   # con almeno 5 giornate alle spalle lo z non e' dominato dal caso
            d = {}
            for side, z, pred, obs in (("casa", zh, gw.mu.to_numpy(), feat.hg.to_numpy(float)), ("ospite", za, gw.nu.to_numpy(), feat.ag.to_numpy(float))):
                act = np.abs(z[m]) > ZTHR
                zf = (obs[m].sum() - pred[m].sum()) / np.sqrt(pred[m].sum())
                first = feat.date[m][act].min() if act.any() else None
                d[side] = dict(share=float(act.mean()), share_late=float((np.abs(z[late]) > ZTHR).mean()) if late.any() else float("nan"), z_end=float(zf), first=None if first is None else str(first.date()))
            rows.append((s_, l_, n, d))
    L = ["## N2 — quante volte si sarebbe attivato", "", "Filtro |z| > 2 per lato (z = (gol reali − previsti)/√previsti, sulle partite della stagione già giocate). «Quota attiva» = quota di partite della lega in quella stagione giocate con il filtro attivo "
         "(tra parentesi: solo dalla giornata 6, quando z non è più dominato dal caso); z finale = scarto a fine stagione; «prima attivazione» = data della prima partita con filtro attivo.", "",
         "| Stagione | Lega | Partite | Casa: quota attiva (da g.6) | Casa: z finale | Casa: prima attivazione | Ospite: quota attiva (da g.6) | Ospite: z finale | Ospite: prima attivazione |", "|---|---|---:|---|---:|---|---|---:|---|"]
    n_any_h = n_any_a = n_end_h = n_end_a = tot = 0
    for s_, l_, n, d in rows:
        L.append(f"| {s_}/{(s_ + 1) % 100:02d} | {LG_NAME[l_]} | {n} | {100 * d['casa']['share']:.0f}% ({100 * d['casa']['share_late']:.0f}%) | {d['casa']['z_end']:+.2f} | {d['casa']['first'] or '–'} | "
                 f"{100 * d['ospite']['share']:.0f}% ({100 * d['ospite']['share_late']:.0f}%) | {d['ospite']['z_end']:+.2f} | {d['ospite']['first'] or '–'} |")
        if s_ <= 2025:
            tot += 1
            n_any_h += d["casa"]["first"] is not None
            n_any_a += d["ospite"]["first"] is not None
            n_end_h += abs(d["casa"]["z_end"]) > ZTHR
            n_end_a += abs(d["ospite"]["z_end"]) > ZTHR
    L += ["", f"**Stagioni passate (2019/20-2025/26, {tot} coppie lega-stagione):** attivazione in almeno una partita, lato casa {n_any_h}/{tot}, lato ospite {n_any_a}/{tot}; filtro attivo a fine stagione (|z finale| > 2), casa {n_end_h}/{tot}, ospite {n_end_a}/{tot}.", ""]
    return L, dict(n_any_h=n_any_h, n_any_a=n_any_a, n_end_h=n_end_h, n_end_a=n_end_a, tot=tot, rows=rows)


def case_part(feat, gw, G):
    cfgs, out = G["cfgs"], G["out"]
    rows_c = G["rows_c"]
    sa = (feat.loc[rows_c, "Division"] == "I1").to_numpy()
    rows_sa = rows_c[sa]
    hg_, ag_ = feat.loc[rows_sa, "hg"].to_numpy(int), feat.loc[rows_sa, "ag"].to_numpy(int)
    y = np.where(hg_ > ag_, 0, np.where(hg_ == ag_, 1, 2))
    L = [f"## Caso di studio: Serie A 2026/27 ({len(rows_sa)} partite giocate)", "",
         f"Simulazione walk-forward con parametri scelti in validazione (N1: k={out['N1']}, N2: k={out['N2']}). Il 2026/27 non entra in nessuna scelta.", ""]
    variants = [("v6 (baseline)", gw.mu, gw.nu)] + [(f"{n} (k={out[n]})", cfgs[(n, out[n])]["mu"], cfgs[(n, out[n])]["nu"]) for n in ("N1", "N2")]
    rows = []
    for lab, mu, nu in variants:
        mk = L7.goal_markets(mu[rows_sa].to_numpy(), nu[rows_sa].to_numpy(), gw.rho[rows_sa].to_numpy())
        P = np.clip(mk["P"], 1e-12, 1)
        P = P / P.sum(1, keepdims=True)
        ll = -np.log(P[np.arange(len(y)), y]).mean()
        o25 = (hg_ + ag_ >= 3)
        ou = -(o25 * np.log(np.clip(mk["o25"], 1e-9, 1 - 1e-9)) + (~o25) * np.log(1 - np.clip(mk["o25"], 1e-9, 1 - 1e-9))).mean()
        rows.append((lab, ll, ou, P[:, 1].mean(), mk["o25"].mean(), (mu[rows_sa] + nu[rows_sa]).mean(), P[:, 0].mean(), P[:, 2].mean()))
    # sensibilita' a k (descrittiva: nessuna scelta) e livello «oracolo» a posteriori (non utilizzabile in produzione)
    sens = []
    for name in ("N1", "N2"):
        for k in KGRID:
            c = cfgs[(name, k)]
            sens.append((f"{name}, k={k}", c["mu"], c["nu"]))
    ra = feat.loc[rows_sa, "ag"].sum() / gw.nu[rows_sa].sum()
    rh_ = feat.loc[rows_sa, "hg"].sum() / gw.mu[rows_sa].sum()
    sens.append((f"Oracolo a posteriori (R casa {rh_:.2f}, R ospite {ra:.2f}: non utilizzabile)", gw.mu * rh_, gw.nu * ra))
    srows = []
    for lab, mu, nu in sens:
        mk = L7.goal_markets(mu[rows_sa].to_numpy(), nu[rows_sa].to_numpy(), gw.rho[rows_sa].to_numpy())
        P = np.clip(mk["P"], 1e-12, 1)
        P = P / P.sum(1, keepdims=True)
        o25_ = (hg_ + ag_ >= 3)
        p25 = np.clip(mk["o25"], 1e-9, 1 - 1e-9)
        srows.append((lab, -np.log(P[np.arange(len(y)), y]).mean(), -(o25_ * np.log(p25) + (~o25_) * np.log(1 - p25)).mean(), P[:, 1].mean(), mk["o25"].mean(), (mu[rows_sa] + nu[rows_sa]).mean()))
    # mercato sulle stesse partite
    f = feat.loc[rows_sa]
    cl = f[["cl_h", "cl_d", "cl_a"]].to_numpy(float)
    okm = np.isfinite(cl).all(1) & (cl > 1).all(1)
    Pm = devig(cl[okm], "power")
    llm = float(-np.log(np.clip(Pm[np.arange(okm.sum()), y[okm]], 1e-12, 1)).mean()) if okm.any() else float("nan")
    ouo, ouu = f["ou_avgc_o"].to_numpy(float), f["ou_avgc_u"].to_numpy(float)
    oku = np.isfinite(ouo) & np.isfinite(ouu) & (ouo > 1) & (ouu > 1)
    pm_o = (1 / ouo[oku]) / (1 / ouo[oku] + 1 / ouu[oku])
    o25 = (hg_ + ag_ >= 3)[oku]
    ll_ou_m = float(-(o25 * np.log(pm_o) + (~o25) * np.log(1 - pm_o)).mean()) if oku.any() else float("nan")
    real = dict(draw=float((y == 1).mean()), o25=float((hg_ + ag_ >= 3).mean()), goals=float((hg_ + ag_).mean()), home=float((y == 0).mean()), away=float((y == 2).mean()))
    L += ["| Modello | Log-loss 1X2 | Log-loss Over 2,5 | Pareggi previsti | Over 2,5 previsto | Gol previsti a partita | 1 previsto | 2 previsto |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for lab, ll, ou, pd_, po, g, ph, pa in rows:
        L.append(f"| {lab} | {ll:.4f} | {ou:.4f} | {100 * pd_:.1f}% | {100 * po:.1f}% | {g:.2f} | {100 * ph:.1f}% | {100 * pa:.1f}% |")
    L.append(f"| Mercato (chiusura media, senza margine; {int(okm.sum())} partite 1X2, {int(oku.sum())} Over/Under) | {llm:.4f} | {ll_ou_m:.4f} | – | {100 * float(pm_o.mean()) if oku.any() else float('nan'):.1f}% | – | – | – |")
    L.append(f"| **Reale** | | | **{100 * real['draw']:.1f}%** | **{100 * real['o25']:.1f}%** | **{real['goals']:.2f}** | **{100 * real['home']:.1f}%** | **{100 * real['away']:.1f}%** |")
    L.append("")
    L += ["**Sensibilità a k, Serie A 2026/27 (descrittiva: la scelta di k resta quella della validazione)**", "", "| Variante | Log-loss 1X2 | Log-loss Over 2,5 | Pareggi previsti | Over 2,5 previsto | Gol previsti a partita |", "|---|---:|---:|---:|---:|---:|"]
    for lab, ll, ou, pd_, po, g in srows:
        L.append(f"| {lab} | {ll:.4f} | {ou:.4f} | {100 * pd_:.1f}% | {100 * po:.1f}% | {g:.2f} |")
    L.append("")
    # andamento giornata per giornata (N1 con k scelto)
    days, lg, se = G["days"], G["lg"], G["se"]
    k = out["N1"]
    rh, zh = season_level(days, lg, se, gw.mu.to_numpy(), G["hg"], k)
    ra, za = season_level(days, lg, se, gw.nu.to_numpy(), G["ag"], k)
    m = (lg == "I1") & (se == 2026) & feat.hg.notna().to_numpy()
    sub = feat[m].assign(rh=rh[m], ra=ra[m], zh=zh[m], za=za[m])
    L += [f"Andamento di R e z della Serie A 2026/27 (N1, k={k}) all'inizio di ogni giornata (valori usati per prevedere le partite di quella giornata):", "",
          "| Giornata | Partite già giocate | R casa | R ospite | z casa | z ospite | Filtro N2 attivo (casa / ospite) |", "|---:|---:|---:|---:|---:|---:|---|"]
    played = 0
    for g, d in sub.groupby("gday"):
        L.append(f"| {int(g)} | {played} | {d.rh.iloc[0]:.3f} | {d.ra.iloc[0]:.3f} | {d.zh.iloc[0]:+.2f} | {d.za.iloc[0]:+.2f} | {'sì' if abs(d.zh.iloc[0]) > ZTHR else 'no'} / {'sì' if abs(d.za.iloc[0]) > ZTHR else 'no'} |")
        played += len(d)
    L.append("")
    # tutte le leghe 2026/27
    L += ["**Tutte le leghe, 2026/27** (parametri scelti in validazione):", "", "| Lega | Partite | Gol reali | Gol previsti v6 | N1 | N2 | Δ ll 1X2 v6 − N1 | Δ ll 1X2 v6 − N2 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for lg_ in LEAGUES:
        mm = (feat.loc[rows_c, "Division"] == lg_).to_numpy()
        rr = rows_c[mm]
        vb = eval_goals(feat, gw.mu, gw.nu, gw.rho, rr)
        v1 = eval_goals(feat, cfgs[("N1", out["N1"])]["mu"], cfgs[("N1", out["N1"])]["nu"], gw.rho, rr)
        v2 = eval_goals(feat, cfgs[("N2", out["N2"])]["mu"], cfgs[("N2", out["N2"])]["nu"], gw.rho, rr)
        L.append(f"| {LG_NAME[lg_]} | {len(rr)} | {(feat.loc[rr, 'hg'] + feat.loc[rr, 'ag']).mean():.2f} | {(gw.mu[rr] + gw.nu[rr]).mean():.2f} | {(cfgs[('N1', out['N1'])]['mu'][rr] + cfgs[('N1', out['N1'])]['nu'][rr]).mean():.2f} | "
                 f"{(cfgs[('N2', out['N2'])]['mu'][rr] + cfgs[('N2', out['N2'])]['nu'][rr]).mean():.2f} | {(vb['ll'] - v1['ll']).mean():+.5f} | {(vb['ll'] - v2['ll']).mean():+.5f} |")
    L.append("")
    return L, dict(rows=rows, market_ll=llm, market_ou=ll_ou_m, real=real)


# ───────────────────────────── statistiche ─────────────────────────────
def stats_part(feat, weeks, st):
    days = (feat.date - pd.Timestamp("2000-01-01")).dt.days.to_numpy(float)
    lg, se = feat.Division.to_numpy(), feat.season.to_numpy()
    params = {k: LEVEL_PARAMS[k] for k in stats_v3.ORDER}
    lv = stats_v3.build_level(feat, params, means={t: (st[t]["run"].mh, st[t]["run"].ma) for t in stats_v3.ORDER})
    L = ["## N3 — statistiche", "", "Baseline = produzione (modello `stats_v3` + livello stagionale di `config.LEVEL_PARAMS`). Varianti: **A1/A2** = livello di stagione (N1 / N2) al posto del livello di produzione; **B1/B2** = sopra il livello di produzione. "
         "Δ = baseline − variante (positivo = migliora), held-out 2022/23-2025/26; per i tiri k è scelto separatamente per casa e ospite.", ""]
    res = {}
    for stat in ("falli", "gialli", "tiri"):
        spec = SPEC[stat]
        run, al = st[stat]["run"], st[stat]["al"]
        ok = (run.mh.notna() & feat[spec["hc"]].notna() & feat[spec["ac"]].notna() & (feat.season >= L7.FIRST_TEST)).to_numpy()
        main, cur = ok & (se <= 2025), ok & (se == 2026)
        rows_m, rows_c = feat.index[main], feat.index[cur]
        wk_m, se_m = weeks[main], se[main]
        is_val = np.isin(se_m, L7.VALIDATION)
        mh_l, ma_l = level_run(feat, stat, run.mh, run.ma, lv, ok)             # produzione: base * livello L3
        base_run = R6.Run(feat, SPEC[stat], mh_l, ma_l, run.folds)
        v0m, v0c = R6.evaluate(base_run, rows_m, al), R6.evaluate(base_run, rows_c, al)
        yh, ya = feat[spec["hc"]].to_numpy(float), feat[spec["ac"]].to_numpy(float)
        ah, aa = al["ah"].to_numpy(float), al["aa"].to_numpy(float)
        ah, aa = np.where(np.isfinite(ah), ah, np.nanmean(ah)), np.where(np.isfinite(aa), aa, np.nanmean(aa))      # righe di training (2016-18): alpha del primo fold
        # R per ogni k, variante (base = medie di base o medie di produzione), con e senza filtro
        Rtab = {}
        for src, (bh, ba) in (("A", (run.mh, run.ma)), ("B", (mh_l, ma_l))):
            for k in KGRID:
                rh, zh = season_level(days, lg, se, bh.to_numpy(), yh, k, var=bh.to_numpy() + ah * bh.to_numpy() ** 2)
                ra, za = season_level(days, lg, se, ba.to_numpy(), ya, k, var=ba.to_numpy() + aa * ba.to_numpy() ** 2)
                Rtab[(src, 1, k)] = (rh, ra)
                Rtab[(src, 2, k)] = (gate(rh, zh), gate(ra, za))
        bases = {"A": (run.mh, run.ma), "B": (mh_l, ma_l)}
        sep = stat == "tiri"
        results = {}
        for src in ("A", "B"):
            for gt in (1, 2):
                ks = [(kh, ka) for kh in KGRID for ka in KGRID] if sep else [(k, k) for k in KGRID]
                best, table = None, {}
                for kh, ka in ks:
                    mh2 = bases[src][0] * Rtab[(src, gt, kh)][0]
                    ma2 = bases[src][1] * Rtab[(src, gt, ka)][1]
                    run2 = R6.Run(feat, SPEC[stat], mh2, ma2, run.folds)
                    v = R6.evaluate(run2, rows_m, al)
                    table[(kh, ka)] = (v, run2)
                dval = {c: (v0m["ll_tot"] - table[c][0]["ll_tot"])[is_val].mean() for c in table}
                bestv = max(dval.values())
                cand = [c for c in table if dval[c] >= bestv - TIE]
                ch = max(cand, key=lambda c: (c[0] + c[1], c[0]))
                v, run2 = table[ch]
                cmp_ = R6.compare(v0m, v, wk_m, is_val)
                vc = R6.evaluate(R6.Run(feat, SPEC[stat], bases[src][0] * Rtab[(src, gt, ch[0])][0], bases[src][1] * Rtab[(src, gt, ch[1])][1], run.folds), rows_c, al)
                d26 = (v0c["ll_tot"] - vc["ll_tot"]).mean()
                g0 = interval_gaps(feat, stat, base_run, al, rows_m)
                g1 = interval_gaps(feat, stat, run2, al, rows_m)
                results[(src, gt)] = dict(ch=ch, cmp=cmp_, d26=float(d26), dval=float(dval[ch]), ver=R6.verdict(cmp_), g0=g0, g1=g1)
                print("stats", stat, src, gt, ch, f"{cmp_['ll_tot_held']['d']:+.5f}", flush=True)
        res[stat] = results
        L += [f"### {L7.KEYS[stat]}", "", "| Variante | k (casa, ospite) | Δ ll totale validazione | Δ totale held-out [IC a blocchi] | Δ per squadra held-out | Δ O/U totale held-out | Δ totale 2026/27 (descrittivo) | Verdetto |", "|---|---|---:|---|---:|---:|---:|---|"]
        for (src, gt), r in results.items():
            c = r["cmp"]
            L.append(f"| {src}{gt} | {r['ch'][0]}, {r['ch'][1]} | {r['dval']:+.5f} | {c['ll_tot_held']['d']:+.5f} [{c['ll_tot_held']['lob']:+.5f}, {c['ll_tot_held']['hib']:+.5f}] | {c['ll_team_held']['d']:+.5f} | {c['ou_tot']['d']:+.5f} | {r['d26']:+.5f} | {r['ver']} |")
        L.append("")
    return L, res


# ───────────────────────────── effetto arbitro con peso sulla stagione in corso ─────────────────────────────
def referee_decay(feat, keys, m_tot, y, k, mbar, half_life_days):
    order = np.argsort(feat.date.to_numpy(), kind="stable")
    st, out = {}, np.ones(len(feat))
    div = feat.Division.to_numpy()
    dd = (feat.date - pd.Timestamp("2000-01-01")).dt.days.to_numpy(float)
    kv = keys.to_numpy(dtype=object)
    default = float(np.mean(list(mbar.values())))
    ym, mm = y.to_numpy(float), m_tot.to_numpy(float)
    for i in order:
        key = kv[i]
        if key is None or (isinstance(key, float) and np.isnan(key)):
            continue
        kk = f"{div[i]}|{key}"
        s = st.setdefault(kk, [0.0, 0.0, dd[i]])
        if half_life_days:
            f = 0.5 ** ((dd[i] - s[2]) / half_life_days)
            s[0] *= f
            s[1] *= f
        s[2] = dd[i]
        mb = mbar.get(div[i], default)
        out[i] = (s[0] + k * mb) / (s[1] + k * mb)
        if np.isfinite(ym[i]) and np.isfinite(mm[i]):
            s[0] += ym[i]
            s[1] += mm[i]
    return out


def ref_part(feat, weeks, st):
    stat = "gialli"
    spec = SPEC[stat]
    keys = refeffect.load_history_keys(feat).reindex(feat.index)
    mh0, ma0 = refeffect.base_predictions(feat)
    m_tot = mh0 + ma0
    y = feat["HY"] + feat["AY"]
    mbar = refeffect.mbar_by_league(feat, m_tot)
    run0, al0 = st[stat]["run"], st[stat]["al"]
    se = feat.season.to_numpy()
    ok = (run0.mh.notna() & feat[spec["hc"]].notna() & feat[spec["ac"]].notna() & (feat.season >= L7.FIRST_TEST)).to_numpy()
    main, cur = ok & (se <= 2025), ok & (se == 2026)
    rows_m, rows_c = feat.index[main], feat.index[cur]
    wk_m, se_m = weeks[main], se[main]
    is_val = np.isin(se_m, L7.VALIDATION)
    v0m, v0c = R6.evaluate(run0, rows_m, al0), R6.evaluate(run0, rows_c, al0)
    uni = referee_decay(feat, keys, m_tot, y, REFEREE_K, mbar, None)
    chk = float(np.nanmax(np.abs(np.log(uni) - feat["ref_logR"].to_numpy())))
    L = ["## N3 — effetto arbitro dei gialli con peso sulla stagione in corso", "",
         f"Controllo: il ricalcolo con peso uniforme riproduce `ref_logR` di produzione (scarto massimo {chk:.1e}). Pesi decrescenti w = 0,5^(giorni/(365·h)) sulle partite passate dell'arbitro; k = {REFEREE_K}. "
         "Modello dei gialli senza livello stagionale (per isolare l'effetto). Δ = produzione − variante.", "",
         "| h (anni) | Δ ll totale validazione | Δ totale held-out [IC a blocchi] | Δ per squadra held-out | Δ totale 2026/27 (descrittivo) | Verdetto |", "|---:|---:|---|---:|---:|---|"]
    res = {}
    for h in (0.5, 1.0, 2.0):
        f2 = feat.copy()
        f2["ref_logR"] = np.log(referee_decay(feat, keys, m_tot, y, REFEREE_K, mbar, 365 * h))
        run = R6.run_model(f2, SPEC[stat], stats_v3.design(f2, stat, True))
        for sea, f in run.folds.items():
            if sea == L7.FIRST_TEST:
                run.mh[f["idx"]] = f["mh"]
                run.ma[f["idx"]] = f["ma"]
        al = R6.alphas(run, "global")
        vm, vc = R6.evaluate(run, rows_m, al), R6.evaluate(run, rows_c, al)
        res[h] = (R6.compare(v0m, vm, wk_m, is_val), float((v0c["ll_tot"] - vc["ll_tot"]).mean()))
        print("ref", h, f"{res[h][0]['ll_tot_held']['d']:+.5f}", flush=True)
    best = max(res[h][0]["ll_tot_val"]["d"] for h in res)
    cand = [h for h in res if res[h][0]["ll_tot_val"]["d"] >= best - TIE]
    hch = max(cand)
    for h, (c, d26) in res.items():
        L.append(f"| {h} | {c['ll_tot_val']['d']:+.5f} | {c['ll_tot_held']['d']:+.5f} [{c['ll_tot_held']['lob']:+.5f}, {c['ll_tot_held']['hib']:+.5f}] | {c['ll_team_held']['d']:+.5f} | {d26:+.5f} | {R6.verdict(c)}{' ← scelta' if h == hch else ''} |")
    L.append("")
    return L, dict(hch=hch, res={h: (c["ll_tot_held"]["d"], c["ll_tot_held"]["lob"], c["ll_tot_held"]["hib"], d26, R6.verdict(c)) for h, (c, d26) in res.items()})


def main():
    only = set(sys.argv[1:])
    feat, gw, weeks, st = prepare()
    pk = {}
    if not only or "GOALS" in only:
        L, G = goals_part(feat, gw, weeks)
        La, A = activation_part(feat, gw)
        Lc, C = case_part(feat, gw, G)
        open(os.path.join(P10, "GOALS.md"), "w", encoding="utf-8").write("\n".join(L + La))
        open(os.path.join(P10, "CASE.md"), "w", encoding="utf-8").write("\n".join(Lc))
        pk["goals"] = dict(summ=G["summ"], out=G["out"], act={k: v for k, v in A.items() if k != "rows"}, case={k: v for k, v in C.items() if k != "rows"})
        print("GOALS", G["summ"], flush=True)
    if not only or "STATS" in only:
        L, R = stats_part(feat, weeks, st)
        open(os.path.join(P10, "STATS.md"), "w", encoding="utf-8").write("\n".join(L))
        pk["stats"] = {s: {f"{a}{g}": dict(ch=r["ch"], ver=r["ver"], d_held=r["cmp"]["ll_tot_held"]["d"], lo=r["cmp"]["ll_tot_held"]["lob"], hi=r["cmp"]["ll_tot_held"]["hib"], d26=r["d26"]) for (a, g), r in rs.items()} for s, rs in R.items()}
    if not only or "REF" in only:
        L, R = ref_part(feat, weeks, st)
        open(os.path.join(P10, "REF.md"), "w", encoding="utf-8").write("\n".join(L))
        pk["ref"] = R
    pd.to_pickle(pk, os.path.join(os.path.dirname(L7.CTX7), f"round10_{'_'.join(sorted(only)) or 'all'}.pkl"))
    print("fatto", flush=True)


if __name__ == "__main__":
    main()
