"""Round 7 — diagnosi e correzione del livello stagionale (solo backtest). Criteri in backtest/round7_parts/prereg.md.
Da lanciare in modalità isolata:  python -I -X utf8 backtest/run_round7.py   (scrive backtest/results_round7.md e backtest/round7_parts/*.md)"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import round3_ctx as C3, round6_lib as R6, round7_lib as L7, stats_v3
from backtest.run_intervals import side_alphas

P7 = L7.P7
GRID = [(H, k) for H in (4, 8, 12) for k in (5, 15, 40)]
TIE = 0.0002
LG_NAME = {"I1": "Serie A", "E0": "Premier League", "D1": "Bundesliga", "SP1": "La Liga", "F1": "Ligue 1"}
SPEC = {s: dict(R6.SPECS[s]) for s in L7.STATS}
CACHE = os.path.join(os.path.dirname(L7.CTX7), "stage.pkl")


def fmt(x, d=3):
    return f"{x:.{d}f}"


def simp_key(c):
    H, k = c
    return (-k, -H)                       # più semplice = k più alto, poi H più alto


# ───────────────────────────── preparazione ─────────────────────────────
def prepare():
    feat = L7.build_ctx7()
    gw = L7.goals_walk_forward(feat)
    weeks = feat.date.dt.strftime("%G-%V").to_numpy()
    st = {}
    for s in L7.STATS:
        spec = SPEC[s]
        run = R6.run_model(feat, spec, stats_v3.design(feat, s, True))
        for sea, f in run.folds.items():                     # in campione per il 2016/17-2018/19 (previsioni del primo fold): servono solo come storico del livello
            if sea == L7.FIRST_TEST:
                run.mh[f["idx"]] = f["mh"]
                run.ma[f["idx"]] = f["ma"]
        al = side_alphas(run, feat, spec)[1] if s in stats_v3.SIDE_ALPHA else R6.alphas(run, "global")
        st[s] = dict(run=run, al=al)
    return feat, gw, weeks, st


# ───────────────────────────── diagnosi ─────────────────────────────
def diag(feat, gw, weeks, st):
    L = ["## Diagnosi", ""]
    cur = (feat.season == 2026).to_numpy() & gw.mu.notna().to_numpy()
    mk = L7.goal_markets(gw.mu.fillna(1.3), gw.nu.fillna(1.1), gw.rho.fillna(0.0))
    hg, ag = feat.hg.to_numpy(float), feat.ag.to_numpy(float)
    lg = feat.Division.to_numpy()

    def row(mask, pred, obs):
        r, lo, hi = L7.ratio_ci(pred[mask], obs[mask], weeks[mask])
        return pred[mask].mean(), obs[mask].mean(), r, lo, hi

    n26 = int(cur.sum())
    L += [f"### 1. Livello del 2026/27 (previsione walk-forward del modello di produzione; {n26} partite giocate nei 5 campionati, dati fino al {feat.date.max().date()})", "",
          "Rapporto = Σ reali / Σ previsti; IC 95% a blocchi per settimana ISO. Un rapporto > 1 vuol dire che il modello ha previsto meno di quanto è successo.", "",
          "**Gol**", "", "| Lega | N | Casa prev. | Casa reale | Rapporto casa [IC] | Ospite prev. | Ospite reale | Rapporto ospite [IC] | Totale prev. | Totale reale | Rapporto totale [IC] |", "|---|---:|---:|---:|---|---:|---:|---|---:|---:|---|"]
    diag_ratio = {}
    for name, m in [(LG_NAME[x], cur & (lg == x)) for x in L7.LEAGUES] + [("**Tutte**", cur)]:
        a, b, c = row(m, gw.mu.to_numpy(), hg), row(m, gw.nu.to_numpy(), ag), row(m, (gw.mu + gw.nu).to_numpy(), hg + ag)
        diag_ratio[name] = c[2]
        L.append(f"| {name} | {int(m.sum())} | {a[0]:.2f} | {a[1]:.2f} | {a[2]:.3f} [{a[3]:.3f}, {a[4]:.3f}] | {b[0]:.2f} | {b[1]:.2f} | {b[2]:.3f} [{b[3]:.3f}, {b[4]:.3f}] | {c[0]:.2f} | {c[1]:.2f} | {c[2]:.3f} [{c[3]:.3f}, {c[4]:.3f}] |")
    L += ["", "**Statistiche (totali per partita: previsto → reale, rapporto [IC])**", "", "| Lega | N | " + " | ".join(L7.KEYS[s] for s in L7.STATS) + " |", "|---|---:|" + "---:|" * len(L7.STATS)]
    for name, m0 in [(LG_NAME[x], (lg == x)) for x in L7.LEAGUES] + [("**Tutte**", np.ones(len(feat), bool))]:
        cells, ns = [], []
        for s in L7.STATS:
            run, spec = st[s]["run"], SPEC[s]
            pred = (run.mh + run.ma).to_numpy()
            obs = (feat[spec["hc"]] + feat[spec["ac"]]).to_numpy(float)
            m = m0 & (feat.season == 2026).to_numpy() & np.isfinite(pred) & np.isfinite(obs)
            a = row(m, pred, obs)
            cells.append(f"{a[0]:.1f} → {a[1]:.1f} ({a[2]:.3f} [{a[3]:.3f}, {a[4]:.3f}])")
            ns.append(int(m.sum()))
        L.append(f"| {name} | {min(ns)} | " + " | ".join(cells) + " |")
    # 2. inizio stagione
    L += ["", "### 2. Inizio di stagione: prime 8 giornate contro il resto, dal 2019/20", "",
          "Rapporto reale/previsto dei gol totali (e, sotto, delle statistiche) per le prime 8 giornate di ciascuna stagione (giornata ≤ 8) e per il resto della stessa stagione (2026/27: ancora nessuna partita dopo la giornata 8, salvo dove indicato).", "",
          "| Stagione | N prime 8 | Rapporto gol, prime 8 [IC] | N resto | Rapporto gol, resto [IC] | Gol previsti / reali, prime 8 |", "|---|---:|---|---:|---|---|"]
    early = (feat.gday <= 8).to_numpy()
    tot_pred, tot_obs = (gw.mu + gw.nu).to_numpy(), hg + ag
    seas = feat.season.to_numpy()
    ratios_e = {}
    for s_ in range(2019, 2027):
        me = (seas == s_) & early & np.isfinite(tot_pred)
        mr = (seas == s_) & ~early & np.isfinite(tot_pred)
        a = row(me, tot_pred, tot_obs)
        ratios_e[s_] = a
        r = row(mr, tot_pred, tot_obs) if mr.sum() > 50 else None
        L.append(f"| {s_}/{(s_ + 1) % 100:02d} | {int(me.sum())} | {a[2]:.3f} [{a[3]:.3f}, {a[4]:.3f}] | {int(mr.sum())} | " + (f"{r[2]:.3f} [{r[3]:.3f}, {r[4]:.3f}]" if r else "—") + f" | {a[0]:.2f} / {a[1]:.2f} |")
    prev = [ratios_e[s_][2] for s_ in range(2019, 2026)]
    a26 = ratios_e[2026]
    anomalo = (a26[2] > max(prev) or a26[2] < min(prev)) and not (a26[3] <= np.mean(prev) <= a26[4])
    L += ["", f"Rapporto gol delle prime 8 giornate nelle sette stagioni precedenti: min {min(prev):.3f}, media {np.mean(prev):.3f}, max {max(prev):.3f}; 2026/27: {a26[2]:.3f} [{a26[3]:.3f}, {a26[4]:.3f}]. "
          f"Secondo la regola del prereg il 2026/27 è **{'anomalo' if anomalo else 'nella norma'}** per i gol.", "",
          "**Statistiche, rapporto reale/previsto dei totali nelle prime 8 giornate**", "", "| Stagione | " + " | ".join(L7.KEYS[s] for s in L7.STATS) + " |", "|---|" + "---:|" * len(L7.STATS)]
    for s_ in range(2019, 2027):
        cells = []
        for s in L7.STATS:
            run, spec = st[s]["run"], SPEC[s]
            pred = (run.mh + run.ma).to_numpy()
            obs = (feat[spec["hc"]] + feat[spec["ac"]]).to_numpy(float)
            m = (seas == s_) & early & np.isfinite(pred) & np.isfinite(obs)
            a = row(m, pred, obs)
            cells.append(f"{a[2]:.3f} [{a[3]:.3f}, {a[4]:.3f}]")
        L.append(f"| {s_}/{(s_ + 1) % 100:02d} | " + " | ".join(cells) + " |")
    # 3. calibrazione 2026/27
    L += ["", "### 3. Calibrazione dei mercati dei gol nel 2026/27", "", "| Mercato | N | Probabilità media prevista | Frequenza osservata | Scarto (previsto − osservato) [IC a blocchi] |", "|---|---:|---:|---:|---|"]
    tot = hg + ag
    obs_m = {"Over 1,5": tot >= 2, "Over 2,5": tot >= 3, "Over 3,5": tot >= 4, "BTTS": (hg >= 1) & (ag >= 1)}
    for lab, key in (("Over 1,5", "o15"), ("Over 2,5", "o25"), ("Over 3,5", "o35"), ("BTTS", "btts")):
        o = obs_m[lab][cur].astype(float)
        p = mk[key][cur]
        m_, lo, hi = L7.ci_block_mean(p - o, weeks[cur])
        L.append(f"| {lab} | {int(cur.sum())} | {p.mean():.3f} | {o.mean():.3f} | {m_:+.3f} [{lo:+.3f}, {hi:+.3f}] |")
    L += ["", "Per lega (Over 2,5): " + "; ".join(f"{LG_NAME[x]} previsto {mk['o25'][cur & (lg == x)].mean():.3f}, osservato {(tot >= 3)[cur & (lg == x)].mean():.3f}" for x in L7.LEAGUES) + ".", ""]
    return L, dict(anomalo=bool(anomalo), r26=a26[2], prev=prev)


# ───────────────────────────── gol: L1, L2 ─────────────────────────────
def levels(feat, mu, nu, H, k):
    d, lg = feat.date, feat.Division.to_numpy()
    rh = L7.dynamic_level(d, lg, mu.to_numpy(), feat.hg.to_numpy(float), H, k)
    ra = L7.dynamic_level(d, lg, nu.to_numpy(), feat.ag.to_numpy(float), H, k)
    return rh, ra


def eval_goals(feat, mu, nu, rho, rows):
    mk = L7.goal_markets(mu[rows].to_numpy(), nu[rows].to_numpy(), rho[rows].to_numpy())
    return L7.goal_metrics(mk, feat.hg[rows].to_numpy(), feat.ag[rows].to_numpy())


def delta_row(vb, vv, key, weeks, masks):
    """Δ = base − var (positivo = variante migliore) con IC a blocchi: tutte, validazione, held-out, prime 10, resto, 2026/27."""
    d = vb[key] - vv[key]
    out = {}
    for name, m in masks.items():
        if m.sum() < 5:
            out[name] = None
            continue
        mean, lo, hi = C3.ci_block(d[m], weeks[m])
        out[name] = (mean, lo, hi)
    return out


def verdict_goal(res_ll, res_ou):
    h = res_ll["held-out"]
    sec = res_ou["held-out"][0]
    if h[0] > 0 and h[1] > 0 and sec >= 0:
        return "migliora"
    if h[0] < 0 and h[2] < 0:
        return "peggiora"
    return "non distinguibile dal rumore"


def goals_experiments(feat, gw, weeks, diagres):
    ev = (feat.season >= L7.FIRST_TEST).to_numpy() & gw.mu.notna().to_numpy() & feat.hg.notna().to_numpy()
    rows = feat.index[ev]
    w = weeks[ev]
    seas = feat.season.to_numpy()[ev]
    masks = {"tutte": np.ones(ev.sum(), bool), "validazione": np.isin(seas, L7.VALIDATION), "held-out": ~np.isin(seas, L7.VALIDATION),
             "prime 10": (feat.gday.to_numpy()[ev] <= 10), "resto": (feat.gday.to_numpy()[ev] > 10), "2026/27": seas == 2026}
    base = eval_goals(feat, gw.mu, gw.nu, gw.rho, rows)
    L = []
    results = {}

    def table(name, cfgs, variants):
        t = ["| Configurazione | Δ ll 1X2 tutte [IC] | Δ validazione | Δ held-out [IC] | Δ ll O/U 2,5 held-out [IC] | Δ RPS held-out [IC] | Δ ll 1X2 prime 10 | Δ ll 1X2 resto | Δ ll 1X2 2026/27 | Verdetto |",
             "|---|---|---:|---|---|---|---:|---:|---:|---|"]
        out = {}
        for c in cfgs:
            v = variants[c]
            dl = delta_row(base, v, "ll", w, masks)
            do = delta_row(base, v, "ou", w, masks)
            dr = delta_row(base, v, "rps", w, masks)
            ver = verdict_goal(dl, do)
            out[c] = dict(ll=dl, ou=do, rps=dr, verdict=ver, ll_all=v["ll"].mean())
            f = lambda x: "—" if x is None else f"{x[0]:+.5f} [{x[1]:+.5f}, {x[2]:+.5f}]"
            g = lambda x: "—" if x is None else f"{x[0]:+.5f}"
            t.append(f"| H={c[0]} sett., k={c[1]} | {f(dl['tutte'])} | {g(dl['validazione'])} | {f(dl['held-out'])} | {f(do['held-out'])} | {f(dr['held-out'])} | {g(dl['prime 10'])} | {g(dl['resto'])} | {g(dl['2026/27'])} | {ver} |")
        return t, out

    def choose(res_by_cfg, cfgs):
        best = max(res_by_cfg[c]["ll"]["validazione"][0] for c in cfgs)
        cand = [c for c in cfgs if res_by_cfg[c]["ll"]["validazione"][0] >= best - TIE]
        return min(cand, key=simp_key)

    mb = base["ll"].mean()
    L += ["## Esperimenti sui gol", "", f"Baseline (modello v6 di produzione): log-loss 1X2 {mb:.5f}, log-loss O/U 2,5 {base['ou'].mean():.5f}, RPS {base['rps'].mean():.5f} su {int(ev.sum())} partite di test (dal 2019/20). "
          f"Prime 10 giornate: {int(masks['prime 10'].sum())} partite; resto: {int(masks['resto'].sum())}; 2026/27: {int(masks['2026/27'].sum())}.", ""]
    # L1
    var1, mu1, nu1 = {}, {}, {}
    for c in GRID:
        rh, ra = levels(feat, gw.mu, gw.nu, *c)
        mu1[c], nu1[c] = gw.mu * rh, gw.nu * ra
        var1[c] = eval_goals(feat, mu1[c], nu1[c], gw.rho, rows)
        print("L1", c, f"{(base['ll'] - var1[c]['ll']).mean():+.5f}", flush=True)
    t, r1 = table("L1", GRID, var1)
    ch1 = choose(r1, GRID)
    L += ["### L1 — livello dinamico di lega per i gol", "", f"Griglia H (emivita, settimane) × k (pseudo-partite). Scelta sulle validazioni: **H = {ch1[0]}, k = {ch1[1]}**.", ""] + t + [""]
    results["L1"] = dict(chosen=ch1, res=r1, vec=var1[ch1])
    # L2
    var2, gw2s = {}, {}
    for c in GRID:
        rh, ra = levels(feat, pd.Series(np.exp(feat.dc_lmu.to_numpy()), index=feat.index), pd.Series(np.exp(feat.dc_lnu.to_numpy()), index=feat.index), *c)
        shift = pd.DataFrame({"dc_lmu": np.log(rh), "dc_lnu": np.log(ra)}, index=feat.index)
        g2 = L7.goals_walk_forward(feat, extra_shift=shift)
        gw2s[c] = g2
        var2[c] = eval_goals(feat, g2.mu, g2.nu, g2.rho, rows)
        print("L2", c, f"{(base['ll'] - var2[c]['ll']).mean():+.5f}", flush=True)
    t, r2 = table("L2", GRID, var2)
    ch2 = choose(r2, GRID)
    L += ["### L2 — livello medio dei Dixon-Coles con decadimento più veloce", "", f"Scelta sulle validazioni: **H = {ch2[0]}, k = {ch2[1]}**.", ""] + t + [""]
    results["L2"] = dict(chosen=ch2, res=r2, vec=var2[ch2])
    # combinazione: L1 sopra L2 (se L2 migliora), (H,k) di L1 riscelti
    comb = None
    if r2[ch2]["verdict"] == "migliora" or r1[ch1]["verdict"] == "migliora":
        g2 = gw2s[ch2]
        v12, mu12, nu12 = {}, {}, {}
        for c in GRID:
            rh, ra = levels(feat, g2.mu, g2.nu, *c)
            mu12[c], nu12[c] = g2.mu * rh, g2.nu * ra
            v12[c] = eval_goals(feat, mu12[c], nu12[c], g2.rho, rows)
        t, r12 = table("L1+L2", GRID, v12)
        ch12 = choose(r12, GRID)
        L += ["### Combinazione: L1 sopra L2", "", f"L2 con H = {ch2[0]}, k = {ch2[1]}; L1 riscelto sull'uscita di L2: **H = {ch12[0]}, k = {ch12[1]}**.", ""] + t + [""]
        results["L12"] = dict(chosen=ch12, res=r12, vec=v12[ch12])
    # riepilogo
    L += ["### Riepilogo gol (configurazioni scelte in validazione)", "", "| Variante | Configurazione | Δ ll 1X2 tutte [IC] | Δ held-out [IC] | Δ ll O/U 2,5 held-out [IC] | Δ RPS held-out | Δ prime 10 | Δ resto | Δ 2026/27 | Verdetto |", "|---|---|---|---|---|---:|---:|---:|---:|---|"]
    for key, lab in (("L1", "L1 livello dinamico"), ("L2", "L2 decadimento veloce del livello DC"), ("L12", "L1 sopra L2")):
        if key not in results:
            continue
        r = results[key]
        c = r["chosen"]
        x = r["res"][c]
        f = lambda z: "—" if z is None else f"{z[0]:+.5f} [{z[1]:+.5f}, {z[2]:+.5f}]"
        g = lambda z: "—" if z is None else f"{z[0]:+.5f}"
        L.append(f"| {lab} | H={c[0]}, k={c[1]} | {f(x['ll']['tutte'])} | {f(x['ll']['held-out'])} | {f(x['ou']['held-out'])} | {g(x['rps']['held-out'])} | {g(x['ll']['prime 10'])} | {g(x['ll']['resto'])} | {g(x['ll']['2026/27'])} | {x['verdict']} |")
    L.append("")
    # medie previste con livello corretto nel 2026/27 e calibrazione
    cur = masks["2026/27"]
    L += ["### Effetto sul livello del 2026/27", "", "| Variante | Gol totali previsti (media 2026/27) | Gol reali | Over 2,5 previsto | Over 2,5 reale | Over 3,5 previsto | Over 3,5 reale | BTTS previsto | BTTS reale |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    hgv, agv = feat.hg.to_numpy(float)[ev][cur], feat.ag.to_numpy(float)[ev][cur]
    tt = hgv + agv
    variants_show = [("Baseline", gw.mu, gw.nu, gw.rho)]
    variants_show.append((f"L1 (H={ch1[0]}, k={ch1[1]})", mu1[ch1], nu1[ch1], gw.rho))
    variants_show.append((f"L2 (H={ch2[0]}, k={ch2[1]})", gw2s[ch2].mu, gw2s[ch2].nu, gw2s[ch2].rho))
    if "L12" in results:
        c12 = results["L12"]["chosen"]
        g2 = gw2s[ch2]
        rh, ra = levels(feat, g2.mu, g2.nu, *c12)
        variants_show.append((f"L1 sopra L2 (H={c12[0]}, k={c12[1]})", g2.mu * rh, g2.nu * ra, g2.rho))
    for lab, mu, nu, rho in variants_show:
        mk = L7.goal_markets(mu[rows].to_numpy()[cur], nu[rows].to_numpy()[cur], rho[rows].to_numpy()[cur])
        L.append(f"| {lab} | {(mu[rows].to_numpy()[cur] + nu[rows].to_numpy()[cur]).mean():.2f} | {tt.mean():.2f} | {mk['o25'].mean():.3f} | {(tt >= 3).mean():.3f} | {mk['o35'].mean():.3f} | {(tt >= 4).mean():.3f} | {mk['btts'].mean():.3f} | {((hgv >= 1) & (agv >= 1)).mean():.3f} |")
    L.append("")
    # livello corrente di ogni lega (per la proposta del pannello)
    cur_lvl = current_levels(feat, gw, ch1)
    L += ["### Moltiplicatore corrente di lega (L1, configurazione scelta) dopo l'ultima partita giocata", "", "| Lega | Gol casa | Gol ospite | Gol totali (stima) |", "|---|---:|---:|---:|"]
    for lgc in L7.LEAGUES:
        a, b, c3 = cur_lvl[lgc]
        L.append(f"| {LG_NAME[lgc]} | {a:.3f} | {b:.3f} | {c3:.3f} ({(c3 - 1) * 100:+.0f}%) |")
    L.append("")
    results["cur_lvl"] = cur_lvl
    return L, results


def current_levels(feat, gw, cfg):
    """Moltiplicatori R dopo l'ultima partita: righe fittizie al giorno successivo all'ultima data, per lega."""
    last = feat.date.max() + pd.Timedelta(days=1)
    out = {}
    for lg in L7.LEAGUES:
        m = (feat.Division == lg) & gw.mu.notna()
        d = pd.concat([feat.date[m], pd.Series([last])], ignore_index=True)
        l = np.r_[feat.Division[m].to_numpy(), [lg]]
        rh = L7.dynamic_level(d, l, np.r_[gw.mu[m].to_numpy(), [np.nan]], np.r_[feat.hg[m].to_numpy(float), [np.nan]], *cfg)[-1]
        ra = L7.dynamic_level(d, l, np.r_[gw.nu[m].to_numpy(), [np.nan]], np.r_[feat.ag[m].to_numpy(float), [np.nan]], *cfg)[-1]
        mu_m, nu_m = gw.mu[m & (feat.season == 2026)].mean(), gw.nu[m & (feat.season == 2026)].mean()
        out[lg] = (float(rh), float(ra), float((rh * mu_m + ra * nu_m) / (mu_m + nu_m)))
    return out


# ───────────────────────────── statistiche: L3 ─────────────────────────────
def interval_gaps(feat, spec_s, run_like, al, rows):
    """Scarti (frequenza reale − probabilità dichiarata) degli intervalli per squadra (casa+ospite) e totale, tutte le stagioni e 2026/27."""
    K = stats_v3.INTERVAL_K[spec_s]
    sp = SPEC[spec_s]
    mh, ma = run_like.mh[rows].to_numpy(float), run_like.ma[rows].to_numpy(float)
    yh, ya = feat.loc[rows, sp["hc"]].to_numpy(float), feat.loc[rows, sp["ac"]].to_numpy(float)
    ah, aa, aT = al.loc[rows, "ah"].to_numpy(), al.loc[rows, "aa"].to_numpy(), al.loc[rows, "aT"].to_numpy()
    out = {}
    for key, m, y, a, kk in (("home", mh, yh, ah, K), ("away", ma, ya, aa, K), ("total", mh + ma, yh + ya, aT, 2 * K)):
        lo = np.empty(len(rows), int)
        hi = np.empty(len(rows), int)
        pr = np.empty(len(rows))
        for av in np.unique(a):
            sel = a == av
            lo[sel], hi[sel], pr[sel] = stats_v3.nb_interval(m[sel], av, kk)
        out[key] = ((y >= lo) & (y <= hi)).astype(float), pr
    seas = feat.loc[rows, "season"].to_numpy()
    res = {}
    for lab, msk in (("tutte", np.ones(len(rows), bool)), ("2026/27", seas == 2026)):
        t_hit = np.r_[out["home"][0][msk], out["away"][0][msk]]
        t_p = np.r_[out["home"][1][msk], out["away"][1][msk]]
        res[lab] = dict(team=float(t_hit.mean() - t_p.mean()), total=float(out["total"][0][msk].mean() - out["total"][1][msk].mean()),
                        p_team=float(t_p.mean()), p_tot=float(out["total"][1][msk].mean()))
    return res


def stats_experiments(feat, weeks, st):
    L = ["## Esperimenti sulle statistiche (L3)", "",
         "Livello dinamico per lega e lato sulle medie delle statistiche (stessa formula di L1), (H, k) scelto per statistica sulla log-loss del totale in validazione. Δ = baseline − variante (positivo = la variante migliora).", ""]
    ev_all = {}
    results = {}
    summary = ["| Statistica | Configurazione | Δ ll totale tutte [IC] | Δ totale held-out [IC] | Δ per squadra held-out [IC] | Δ O/U totale held-out | Δ ll totale 2026/27 | Verdetto |", "|---|---|---|---|---|---:|---:|---|"]
    cov = ["| Statistica | Scarto intervallo squadra, tutte (base → L3) | Scarto intervallo totale, tutte (base → L3) | Scarto squadra 2026/27 (base → L3) | Scarto totale 2026/27 (base → L3) |", "|---|---|---|---|---|"]
    for s in L7.STATS:
        run, al, spec = st[s]["run"], st[s]["al"], SPEC[s]
        ok = (run.mh.notna() & feat[spec["hc"]].notna() & feat[spec["ac"]].notna() & (feat.season >= L7.FIRST_TEST)).to_numpy()
        rows = feat.index[ok]
        wk = weeks[ok]
        seas = feat.season.to_numpy()[ok]
        is_val = np.isin(seas, L7.VALIDATION)
        v0 = R6.evaluate(run, rows, al)
        res, vec, runs = {}, {}, {}
        for c in GRID:
            rh = L7.dynamic_level(feat.date, feat.Division.to_numpy(), run.mh.to_numpy(), feat[spec["hc"]].to_numpy(float), *c)
            ra = L7.dynamic_level(feat.date, feat.Division.to_numpy(), run.ma.to_numpy(), feat[spec["ac"]].to_numpy(float), *c)
            run2 = R6.Run(feat, SPEC[s], run.mh * rh, run.ma * ra, run.folds)
            runs[c] = run2
            vec[c] = R6.evaluate(run2, rows, al)
            res[c] = R6.compare(v0, vec[c], wk, is_val)
        best = max(res[c]["ll_tot_val"]["d"] for c in GRID)
        cand = [c for c in GRID if res[c]["ll_tot_val"]["d"] >= best - TIE]
        ch = min(cand, key=simp_key)
        r = res[ch]
        ver = R6.verdict(r)
        d26 = (v0["ll_tot"] - vec[ch]["ll_tot"])[seas == 2026].mean()
        summary.append(f"| {L7.KEYS[s]} | H={ch[0]}, k={ch[1]} | {r['ll_tot']['d']:+.5f} [{r['ll_tot']['lob']:+.5f}, {r['ll_tot']['hib']:+.5f}] | {r['ll_tot_held']['d']:+.5f} [{r['ll_tot_held']['lob']:+.5f}, {r['ll_tot_held']['hib']:+.5f}] | "
                       f"{r['ll_team_held']['d']:+.5f} [{r['ll_team_held']['lob']:+.5f}, {r['ll_team_held']['hib']:+.5f}] | {r['ou_tot']['d']:+.5f} | {d26:+.5f} | {ver} |")
        g0, g1 = interval_gaps(feat, s, run, al, rows), interval_gaps(feat, s, runs[ch], al, rows)
        cov.append(f"| {L7.KEYS[s]} | {g0['tutte']['team'] * 100:+.1f} → {g1['tutte']['team'] * 100:+.1f} pp | {g0['tutte']['total'] * 100:+.1f} → {g1['tutte']['total'] * 100:+.1f} pp | "
                   f"{g0['2026/27']['team'] * 100:+.1f} → {g1['2026/27']['team'] * 100:+.1f} pp | {g0['2026/27']['total'] * 100:+.1f} → {g1['2026/27']['total'] * 100:+.1f} pp |")
        results[s] = dict(chosen=ch, verdict=ver, res=res, gaps=(g0, g1))
        L += [f"### {L7.KEYS[s]}", "", "| H (sett.) | k | Δ ll totale (tutte) [IC a blocchi] | Δ totale validazione | Δ totale held-out [IC a blocchi] | Δ per squadra held-out | Verdetto |", "|---:|---:|---|---:|---|---:|---|"]
        for c in GRID:
            q = res[c]
            L.append(f"| {c[0]} | {c[1]} | {q['ll_tot']['d']:+.5f} [{q['ll_tot']['lob']:+.5f}, {q['ll_tot']['hib']:+.5f}] | {q['ll_tot_val']['d']:+.5f} | {q['ll_tot_held']['d']:+.5f} [{q['ll_tot_held']['lob']:+.5f}, {q['ll_tot_held']['hib']:+.5f}] | {q['ll_team_held']['d']:+.5f} | {R6.verdict(q)}{' ← scelta' if c == ch else ''} |")
        L.append("")
        print("L3", s, ch, ver, flush=True)
    L += ["### Riepilogo L3 (configurazioni scelte in validazione)", ""] + summary + ["", "### Copertura degli intervalli (frequenza reale − probabilità dichiarata)", ""] + cov + [""]
    return L, results


def main():
    feat, gw, weeks, st = prepare()
    dl, dres = diag(feat, gw, weeks, st)
    open(os.path.join(P7, "DIAG.md"), "w", encoding="utf-8").write("\n".join(dl))
    print("diagnosi ok", flush=True)
    gl, gres = goals_experiments(feat, gw, weeks, dres)
    open(os.path.join(P7, "GOALS.md"), "w", encoding="utf-8").write("\n".join(gl))
    sl, sres = stats_experiments(feat, weeks, st)
    open(os.path.join(P7, "STATS.md"), "w", encoding="utf-8").write("\n".join(sl))
    pd.to_pickle(dict(diag=dres, goals={k: v for k, v in gres.items() if k != "cur_lvl"}, cur_lvl=gres["cur_lvl"], stats=sres), os.path.join(os.path.dirname(L7.CTX7), "round7_results.pkl"))
    print("fatto", flush=True)


if __name__ == "__main__":
    main()
