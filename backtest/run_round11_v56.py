"""Round 11 — V5 (favorite in trasferta in Serie A) e V6 (controllo dell'anomalia). Solo backtest.
Criteri in backtest/round11_parts/prereg.md (sezione «Aggiunte», scritta prima dell'esecuzione).
Da lanciare:  python -I -X utf8 backtest/run_round11_v56.py
Scrive backtest/round11_parts/{V5,V6}.md e summary_V56.json."""
import json
import os
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import round3_ctx as C3, round7_lib as L7
from backtest import round11_lib as R
from backtest.round2_lib import devig
from backtest.run_round11 import LG_NAME, ci, f, ll_rows, md

P11 = os.path.join(REPO_ROOT, "backtest", "round11_parts")
N_BOOT = 5000
N_SIM = int(os.environ.get("R11_NSIM", "10000"))
LEAGUES = list(LG_NAME)
OUT = ["1 (casa)", "X (pareggio)", "2 (ospite)"]
THRESH = (0.35, 0.40, 0.45)
WLAB = {"pre": "2013/14-2018/19 (indipendente)", "val": "validazione 2019/20-2021/22", "held": "held-out 2022/23+", "disc": "scoperta 2019/20+"}


def prep():
    feat = L7.build_ctx7()
    gw = L7.goals_walk_forward(feat)
    mk = L7.goal_markets(gw.mu.fillna(1.3), gw.nu.fillna(1.1), gw.rho.fillna(0.0))
    od = feat[["odds_h", "odds_d", "odds_a"]].to_numpy(float)
    cl = feat[["cl_h", "cl_d", "cl_a"]].to_numpy(float)
    D = dict(season=feat.season.to_numpy(), lg=feat.Division.to_numpy(), date=feat.date.to_numpy(), week=feat.date.dt.strftime("%G-%V").to_numpy(),
             y=feat.res.to_numpy().astype(int), od=od, cl=cl, pf=R.fair(od), pc=R.fair(cl), pm=mk["P"], mvalid=gw.mu.notna().to_numpy())
    D["ok"] = np.isfinite(D["pf"]).all(1) & np.isfinite(D["pc"]).all(1)
    return D


def wins(season):
    s = np.asarray(season)
    return {"pre": s <= 2018, "val": (s >= 2019) & (s <= 2021), "held": s >= 2022, "disc": s >= 2019}


def cell_stats(D, m, o, ci_on=True):
    idx = np.where(m & D["ok"])[0]
    if len(idx) == 0:
        return None
    p, win = D["pf"][idx, o], (D["y"][idx] == o).astype(float)
    od, ocl, pcl = D["od"][idx, o], D["cl"][idx, o], D["pc"][idx, o]
    wk = D["week"][idx]
    prof = od * win - 1
    out = dict(n=len(idx), impl=float(p.mean()), obs=float(win.mean()),
               z=float((win - p).sum() / np.sqrt((p * (1 - p)).sum())),
               zroi=float((prof - (od * p - 1)).sum() / np.sqrt((od ** 2 * p * (1 - p)).sum())))
    if ci_on:
        one = np.ones(len(idx))
        out["ex"] = C3.ci_block(win - p, wk)
        out["roi"] = R.block_ratio(prof, one, wk, N_BOOT)
        out["roi_c"] = R.block_ratio(ocl * win - 1, one, wk, N_BOOT)
        out["clv"] = R.block_ratio(od * pcl - 1, one, wk, N_BOOT)
    return out


def row_cell(label, w, s):
    if s is None or s["n"] < 5:
        return [label, w, 0, "—", "—", "—", "—", "—", "—"]
    return [label, w, s["n"], f(s["impl"] * 100, 1), f(s["obs"] * 100, 1), ci(s["ex"], 1, True), ci(s["roi"], 1, True), ci(s["roi_c"], 1, True), ci(s["clv"], 1, True)]


HEAD = ["Soglia / gruppo", "Finestra", "N", "% implicita", "% osservata", "eccesso (pt) [IC blocchi]", "ROI quota pre (%) [IC]", "ROI quota chiusura (%) [IC]", "CLV (%) [IC]"]


# ═════════════════════════════════════ V6: simulazione nulla ═════════════════════════════════════
def family_cells(D, idx):
    pf, lg = D["pf"][idx], D["lg"][idx]
    cells = []
    for l in LEAGUES:
        ml = lg == l
        for o in (0, 2):
            for t in (0.35, 0.40, 0.45, 0.50, 0.55, 0.60):
                cells.append(dict(name=f"{LG_NAME[l]} · esito {'1' if o == 0 else '2'} con p ≥ {int(t * 100)}%", lg=l, o=o, kind="up", par=t, mask=ml & (pf[:, o] >= t)))
        for dl in (0.05, 0.10, 0.15):
            cells.append(dict(name=f"{LG_NAME[l]} · pareggio con |p1−p2| ≤ {int(dl * 100)} pt", lg=l, o=1, kind="draw", par=dl, mask=ml & (np.abs(pf[:, 0] - pf[:, 2]) <= dl)))
        for o in (0, 2):
            for t in (0.20, 0.25, 0.30):
                cells.append(dict(name=f"{LG_NAME[l]} · esito {'1' if o == 0 else '2'} con p ≤ {int(t * 100)}%", lg=l, o=o, kind="low", par=t, mask=ml & (pf[:, o] <= t)))
    return cells


def v6_null(D, L, summ):
    t0 = time.time()
    idx = np.where(D["ok"] & (D["season"] >= 2019))[0]
    cells = [c for c in family_cells(D, idx) if c["mask"].sum() >= 100]
    key = next(c for c in cells if c["lg"] == "I1" and c["o"] == 2 and c["kind"] == "up" and abs(c["par"] - 0.40) < 1e-9)
    seas = D["season"][idx]
    extra = [dict(name=f"chiave stagione {s}", lg="I1", o=2, mask=key["mask"] & (seas == s)) for s in range(2019, 2027)]
    allc = cells + extra
    nfam, nc = len(cells), len(allc)
    pf, od, y = D["pf"][idx], D["od"][idx], D["y"][idx]
    M = np.stack([c["mask"] for c in allc]).astype(np.float32)
    oc = np.array([c["o"] for c in allc])
    Po, Od = pf[:, oc].T.astype(np.float32), od[:, oc].T.astype(np.float32)
    Np = M.sum(1)
    Sp, Vp = (M * Po).sum(1), (M * Po * (1 - Po)).sum(1)
    Ep, Vr = (M * (Od * Po - 1)).sum(1), (M * Od ** 2 * Po * (1 - Po)).sum(1)
    MO = M * Od
    Wobs = (y[None, :] == oc[:, None]).astype(np.float32)
    z_obs = ((M * Wobs).sum(1) - Sp) / np.sqrt(np.maximum(Vp, 1e-9))
    zr_obs = ((MO * Wobs).sum(1) - Np - Ep) / np.sqrt(np.maximum(Vr, 1e-9))
    ki = cells.index(key)
    sd = np.arange(nfam, nc)
    rng = np.random.default_rng(2026)
    S = 500
    n_chunks = N_SIM // S
    maxz, maxzr = np.empty(N_SIM), np.empty(N_SIM)
    maxz_two = np.empty(N_SIM)
    cnt = {k: np.zeros(N_SIM) for k in ("z2", "z25", "z3", "a2", "a25", "a3")}
    zkey, zrkey = np.empty(N_SIM), np.empty(N_SIM)
    npos = np.empty(N_SIM)
    c1, c2 = pf[:, 0].astype(np.float32), (pf[:, 0] + pf[:, 1]).astype(np.float32)
    for ch in range(n_chunks):
        u = rng.random((len(y), S), dtype=np.float32)
        ys = (u > c1[:, None]).astype(np.int8) + (u > c2[:, None]).astype(np.int8)
        win = np.empty((nc, S), np.float32)
        winr = np.empty((nc, S), np.float32)
        for o in range(3):
            sel = np.where(oc == o)[0]
            if len(sel) == 0:
                continue
            Wo = (ys == o).astype(np.float32)
            win[sel] = M[sel] @ Wo
            winr[sel] = MO[sel] @ Wo
        z = (win - Sp[:, None]) / np.sqrt(np.maximum(Vp, 1e-9))[:, None]
        zr = (winr - Np[:, None] - Ep[:, None]) / np.sqrt(np.maximum(Vr, 1e-9))[:, None]
        sl = slice(ch * S, (ch + 1) * S)
        zf, zrf = z[:nfam], zr[:nfam]
        maxz[sl], maxzr[sl], maxz_two[sl] = zf.max(0), zrf.max(0), np.abs(zf).max(0)
        for k, thr in (("z2", 2.0), ("z25", 2.5), ("z3", 3.0)):
            cnt[k][sl] = (zf >= thr).sum(0)
        for k, thr in (("a2", 2.0), ("a25", 2.5), ("a3", 3.0)):
            cnt[k][sl] = (np.abs(zf) >= thr).sum(0)
        zkey[sl], zrkey[sl] = z[ki], zr[ki]
        npos[sl] = ((win[sd] - Sp[sd][:, None]) > 0).sum(0)
    zk, zrk = float(z_obs[ki]), float(zr_obs[ki])
    obs_cnt = {"z2": int((z_obs[:nfam] >= 2).sum()), "z25": int((z_obs[:nfam] >= 2.5).sum()), "z3": int((z_obs[:nfam] >= 3).sum()),
               "a2": int((np.abs(z_obs[:nfam]) >= 2).sum()), "a25": int((np.abs(z_obs[:nfam]) >= 2.5).sum()), "a3": int((np.abs(z_obs[:nfam]) >= 3).sum())}
    seas_pos_obs = int(((M[sd] * Wobs[sd]).sum(1) - Sp[sd] > 0).sum())
    res = dict(n_cells=nfam, z_key=zk, zroi_key=zrk, n_key=int(Np[ki]),
               p_cell_z=float((zkey >= zk).mean()), p_cell_zroi=float((zrkey >= zrk).mean()),
               p_fam_z=float((maxz >= zk).mean()), p_fam_zroi=float((maxzr >= zrk).mean()),
               p_fam_z_two=float((maxz_two >= abs(zk)).mean()),
               max_z_null_q=[float(np.percentile(maxz, q)) for q in (50, 90, 95, 99)],
               p_ge7=float((npos >= 7).mean()), seas_pos_obs=seas_pos_obs, n_seasons=len(sd),
               exp_cnt={k: float(v.mean()) for k, v in cnt.items()}, obs_cnt=obs_cnt, n_sim=N_SIM)
    L += ["## V6 — controllo dell'anomalia", "",
          f"### 1. Quante anomalie emergono per caso (simulazione nulla, {N_SIM} simulazioni)", "",
          f"Ipotesi nulla: il mercato (pre-partita, senza margine) è calibrato; esiti 1X2 di tutte le partite 2019/20+ ({len(y)}) estratti dalle sue probabilità. "
          f"Famiglia E: **{nfam} celle** (lega × condizione, almeno 100 partite). Cella chiave = Serie A, esito 2, p_ospite ≥ 40 % ({res['n_key']} partite).", ""]
    rows = [["z dell'eccesso (vittorie osservate − attese)", f(zk, 2), f"{res['p_cell_z'] * 100:.2f} %", f"{res['p_fam_z'] * 100:.1f} %"],
            ["z del ROI alla quota media pre-partita", f(zrk, 2), f"{res['p_cell_zroi'] * 100:.2f} %", f"{res['p_fam_zroi'] * 100:.1f} %"]]
    L += md(rows, ["Statistica (cella chiave, dati reali)", "valore osservato", "p-value di cella (unilaterale)", f"p-value di famiglia (almeno una delle {nfam} celle altrettanto estrema)"]) + [""]
    L += [f"Massimo di z nella famiglia sotto l'ipotesi nulla: mediana {f(res['max_z_null_q'][0], 2)}, 90° percentile {f(res['max_z_null_q'][1], 2)}, 95° {f(res['max_z_null_q'][2], 2)}, 99° {f(res['max_z_null_q'][3], 2)} "
          f"(contro lo z osservato nella cella chiave: {f(zk, 2)}). P(massimo bilaterale |z| ≥ |z chiave|) = {res['p_fam_z_two'] * 100:.1f} %.", "",
          f"Stagioni positive della cella chiave: osservate {seas_pos_obs} su {len(sd)}; probabilità sotto l'ipotesi nulla di ottenerne almeno 7: {res['p_ge7'] * 100:.1f} % (nella singola cella).", ""]
    rows = []
    for lab, k in (("z ≥ 2,0", "z2"), ("z ≥ 2,5", "z25"), ("z ≥ 3,0", "z3"), ("|z| ≥ 2,0", "a2"), ("|z| ≥ 2,5", "a25"), ("|z| ≥ 3,0", "a3")):
        rows.append([lab, f(res["exp_cnt"][k], 2), obs_cnt[k]])
    L += ["**Celle della famiglia oltre soglia: attese per caso contro osservate nei dati reali (le celle sono sovrapposte, il confronto è tra medie):**", ""]
    L += md(rows, ["Soglia", "attese sotto l'ipotesi nulla (media)", "osservate nei dati reali"]) + [""]
    order = np.argsort(-z_obs[:nfam])[:12]
    rows = [[cells[i]["name"], int(Np[i]), f(z_obs[i], 2), f(zr_obs[i], 2)] for i in order]
    L += ["**Le 12 celle con z più alto nei dati reali:**", ""] + md(rows, ["Cella", "N", "z eccesso", "z ROI"]) + [""]
    summ["null"] = res
    print(f"V6 null fatto in {time.time() - t0:.0f}s")
    return res


# ═════════════════════════════════════ V6: condizioni scelte in anticipo ═════════════════════════════════════
CONDS = {"H": ("favorita in casa: p_casa ≥ 60 % → vittoria in casa", 0, lambda pf: pf[:, 0] >= 0.60),
         "D": ("equilibrio: |p_casa − p_ospite| ≤ 10 pt → pareggio", 1, lambda pf: np.abs(pf[:, 0] - pf[:, 2]) <= 0.10),
         "O": ("outsider in casa: p_casa ≤ 25 % → vittoria in casa", 0, lambda pf: pf[:, 0] <= 0.25),
         "A": ("favorita in trasferta (V5): p_ospite ≥ 40 % → vittoria dell'ospite", 2, lambda pf: pf[:, 2] >= 0.40)}


def v6_conditions(D, L, summ):
    W = wins(D["season"])
    L += ["### 2. Le quattro condizioni scelte prima di guardare i dati, nei cinque campionati", "",
          "Una soglia per condizione, nessuna ottimizzazione. Cella = « N · eccesso in punti [IC blocchi] · ROI a quota media pre-partita [IC] ». z e stagioni positive nella finestra di scoperta.", ""]
    for cn, (desc, o, fn) in CONDS.items():
        rows = []
        msk = np.where(D["ok"], fn(np.nan_to_num(D["pf"], nan=0.5)), False)
        for l in LEAGUES + [None]:
            ml = msk & ((D["lg"] == l) if l else True)
            cellv = []
            for w in ("pre", "val", "held", "disc"):
                s = cell_stats(D, ml & W[w], o)
                cellv.append("—" if s is None or s["n"] < 5 else f"{s['n']} · {s['ex'][0] * 100:+.1f} [{s['ex'][1] * 100:+.1f}; {s['ex'][2] * 100:+.1f}] · {s['roi'][0] * 100:+.1f} [{s['roi'][1] * 100:+.1f}; {s['roi'][2] * 100:+.1f}]")
                if w == "disc" and s:
                    zdisc = s["z"]
                    summ[f"cond|{cn}|{l}|disc"] = {k: s[k] for k in ("n", "impl", "obs", "z", "zroi")}
                    summ[f"cond|{cn}|{l}|disc"]["ex"] = s["ex"]; summ[f"cond|{cn}|{l}|disc"]["roi"] = s["roi"]
                if w == "held" and s:
                    summ[f"cond|{cn}|{l}|held"] = {"n": s["n"], "ex": s["ex"], "roi": s["roi"]}
                if w == "pre" and s:
                    summ[f"cond|{cn}|{l}|pre"] = {"n": s["n"], "ex": s["ex"], "roi": s["roi"]}
            sp = 0; tot = 0
            for sea in range(2019, 2027):
                s = cell_stats(D, ml & (D["season"] == sea), o, ci_on=False)
                if s and s["n"] >= 5:
                    tot += 1; sp += s["obs"] > s["impl"]
            sd = cell_stats(D, ml & W["disc"], o, ci_on=False)
            rows.append([LG_NAME.get(l, "Tutti i campionati")] + cellv + [f(sd["z"], 2) if sd else "—", f"{sp}/{tot}"])
        L += [f"**{cn} — {desc}**", ""] + md(rows, ["Lega", "pre-2019 (indipendente)", "validazione", "held-out", "scoperta", "z (scoperta)", "stagioni con eccesso > 0"]) + [""]
    return


# ═════════════════════════════════════ V5 ═════════════════════════════════════
def max_dd(profit):
    cum = np.concatenate([[0.0], np.cumsum(profit)])
    return float((np.maximum.accumulate(cum) - cum).max())


def v5(D, pfam, L, summ):
    t0 = time.time()
    W = wins(D["season"])
    sa = D["lg"] == "I1"
    pa = np.nan_to_num(D["pf"][:, 2], nan=0.0)
    # passo 0
    disc = sa & W["disc"] & D["ok"] & (pa >= 0.40)
    L += ["## V5 — favorite in trasferta in Serie A", "",
          "### Passo 0 — riproduzione dei numeri dell'analisi originale (solo controllo dei dati, nessuna decisione)", ""]
    rows = []
    for meth in ("norm", "power"):
        pn = devig(D["od"], meth)
        m0 = sa & W["disc"] & np.isfinite(pn).all(1) & (pn[:, 2] >= 0.40)
        win = (D["y"][m0] == 2).astype(float)
        roi_p = (D["od"][m0, 2] * win - 1).mean()
        roi_c = (D["cl"][m0, 2] * win - 1).mean()
        seas = D["season"][m0]
        pos = sum((win[seas == s].mean() > pn[m0, 2][seas == s].mean()) for s in np.unique(seas))
        rows.append([meth, int(m0.sum()), f(win.mean() * 100, 1), f(pn[m0, 2].mean() * 100, 1), f(roi_p * 100, 1), f(roi_c * 100, 1), f"{pos}/{len(np.unique(seas))}"])
    L += md(rows, ["margine tolto con", "N (≥ 40 %)", "% ospite vince", "% implicita", "ROI quota media pre (%)", "ROI quota media chiusura (%)", "stagioni con eccesso > 0"]) + [""]
    L += ["Originale: 827 partite, 61 % contro 53 %, +8,7 % (apertura) e +8,9 % (chiusura), 7 stagioni su 8.", ""]
    summ["step0"] = rows
    # V5a
    L += ["### V5a — verifica con soglia scelta in validazione", ""]
    rows, best = [], []
    res_t = {}
    for t in THRESH:
        mt = sa & (pa >= t)
        for w in ("pre", "val", "held"):
            s = cell_stats(D, mt & W[w], 2)
            res_t[(t, w)] = s
            rows.append(row_cell(f"p_ospite ≥ {int(t * 100)} %" if w == "pre" else "", WLAB[w], s))
        sv = res_t[(t, "val")]
        best.append((sv["ex"][1], t))
    mx = max(b[0] for b in best)
    tstar = min(t for v, t in best if v == mx)
    L += md(rows, HEAD) + [""]
    L += [f"**Soglia scelta in validazione** (limite inferiore dell'IC dell'eccesso più alto): **t* = {int(tstar * 100)} %**.", ""]
    summ["tstar"] = tstar
    held, pre = res_t[(tstar, "held")], res_t[(tstar, "pre")]
    v_held = held["ex"][1] > 0
    v_pre = pre is not None and pre["ex"][1] > 0
    v_fam = pfam < 0.05
    if v_held and v_pre and v_fam:
        verdict = "confermata"
    elif v_held:
        verdict = "coerente nel periodo di scoperta ma non confermata"
    else:
        verdict = "non confermata"
    L += [f"**Verdetto V5a (criteri della preregistrazione):** (i) held-out: eccesso {ci(held['ex'], 1, True)} punti → {'IC esclude zero' if v_held else 'IC comprende zero'}; "
          f"(ii) 2013/14-2018/19: eccesso {ci(pre['ex'], 1, True)} punti → {'IC esclude zero' if v_pre else 'IC comprende zero o negativo'}; "
          f"(iii) p-value di famiglia V6 = {pfam * 100:.1f} % → {'< 5 %' if v_fam else '≥ 5 %'}. **→ {verdict}.**", ""]
    summ["v5a"] = {"verdict": verdict, "held": held, "pre": pre, "val": res_t[(tstar, "val")], "pfam": pfam}
    # per stagione
    rows = []
    mt = sa & (pa >= tstar)
    for sea in range(2013, 2027):
        s = cell_stats(D, mt & (D["season"] == sea), 2)
        rows.append([f"{sea}/{str(sea + 1)[2:]}" + (" (parziale)" if sea == 2026 else "")] + ([s["n"], f(s["impl"] * 100, 1), f(s["obs"] * 100, 1), ci(s["ex"], 1, True), ci(s["roi"], 1, True)] if s else ["—"] * 5))
    L += [f"**Per stagione (Serie A, p_ospite ≥ {int(tstar * 100)} %):**", ""] + md(rows, ["Stagione", "N", "% implicita", "% osservata", "eccesso (pt) [IC]", "ROI quota pre (%) [IC]"]) + [""]
    # altri campionati
    rows = []
    for l in LEAGUES:
        for w in ("pre", "disc"):
            s = cell_stats(D, (D["lg"] == l) & (pa >= tstar) & W[w], 2)
            rows.append(row_cell(LG_NAME[l] if w == "pre" else "", WLAB[w], s))
    L += [f"**Stessa regola negli altri campionati (descrittivo):**", ""] + md(rows, HEAD) + [""]
    # V5b
    L += ["### V5b — il modello v6 cattura l'effetto?", "",
          f"Sottoinsieme: Serie A, p_ospite (mercato pre-partita) ≥ {int(tstar * 100)} %, previsioni fuori campione del modello (2019/20+). Guadagno = log-loss(mercato) − log-loss(modello): positivo = il modello è meglio.", ""]
    rows = []
    for lab, sub in ((f"A_t* (p_ospite ≥ {int(tstar * 100)} %)", sa & (pa >= tstar)), ("tutta la Serie A", sa)):
        for w in ("val", "held"):
            m = sub & W[w] & D["ok"] & D["mvalid"]
            idx = np.where(m)[0]
            pm, pf, pc, y, wk = D["pm"][idx], D["pf"][idx], D["pc"][idx], D["y"][idx], D["week"][idx]
            llm, llk, llc = ll_rows(pm, y), ll_rows(pf, y), ll_rows(pc, y)
            obs = (y == 2).astype(float)
            diff = C3.ci_block(pm[:, 2] - pf[:, 2], wk)
            g_pre, g_clo = C3.ci_block(llk - llm, wk), C3.ci_block(llc - llm, wk)
            rows.append([lab if w == "val" else "", WLAB[w], len(idx), f(pm[:, 2].mean() * 100, 1), f(pf[:, 2].mean() * 100, 1), f(pc[:, 2].mean() * 100, 1), f(obs.mean() * 100, 1),
                         ci(diff, 2, True), f(llm.mean()), f(llk.mean()), ci(g_pre, 4), ci(g_clo, 4)])
            summ[f"v5b|{lab[:3]}|{w}"] = {"n": len(idx), "diff": diff, "gain_pre": g_pre, "gain_clo": g_clo, "pm": float(pm[:, 2].mean()), "pf": float(pf[:, 2].mean()), "obs": float(obs.mean())}
    L += md(rows, ["Sottoinsieme", "Finestra", "N", "% ospite modello", "% ospite mercato pre", "% ospite mercato chiusura", "% osservata", "modello − mercato (pt) [IC]",
                   "ll modello", "ll mercato pre", "guadagno vs mercato pre [IC]", "guadagno vs mercato chiusura [IC]"]) + [""]
    sb = summ[f"v5b|A_t|held"] if f"v5b|A_t|held" in summ else None
    # V5c
    L += ["### V5c — correzione specifica della Serie A (walk-forward)", "",
          "K1 = intercette di classe della Serie A (vantaggio casa); K2 = K1 + interazione «ospite favorito» (p_modello,ospite ≥ t*) per l'esito ospite. Stimate su 2019/20…s−1 sulle sole partite di Serie A, applicate alla Serie A nella stagione s (da 2020/21); altre leghe invariate. Δ = log-loss(baseline) − log-loss(variante): positivo = migliora.", ""]
    Pm, y = D["pm"], D["y"]
    logP = np.log(np.clip(Pm, 1e-9, 1))
    Fm = np.zeros_like(Pm); Fm[:, 2] = (Pm[:, 2] >= tstar).astype(float)
    P1, P2 = Pm.copy(), Pm.copy()
    params = []
    for s in range(2020, 2027):
        tr = sa & D["mvalid"] & D["ok"] & (D["season"] >= 2019) & (D["season"] < s)
        te = sa & D["mvalid"] & (D["season"] == s)
        if te.sum() == 0:
            continue
        a1, w1 = R.fit_clogit([], y[tr], 3, offset=logP[tr])
        P1[te] = R.predict_clogit([], a1, w1, offset=logP[te], k=3)
        a2, w2 = R.fit_clogit([Fm[tr]], y[tr], 3, offset=logP[tr], w_init=0.0)
        P2[te] = R.predict_clogit([Fm[te]], a2, w2, offset=logP[te], k=3)
        params.append([f"{s}/{str(s + 1)[2:]}", int(tr.sum()), f"{a1[0]:+.3f} / {a1[1]:+.3f}", f"{a2[0]:+.3f} / {a2[1]:+.3f}", f"{w2[0]:+.3f}"])
    L += ["Parametri per fold (a_X / a_2 rispetto alla casa; b = coefficiente dell'interazione):", ""]
    L += md(params, ["Test", "N addestramento", "K1: a_X / a_2", "K2: a_X / a_2", "K2: b"]) + [""]
    base, l1, l2 = ll_rows(Pm, y), ll_rows(P1, y), ll_rows(P2, y)
    tst = D["mvalid"] & D["ok"] & (D["season"] >= 2020)
    Wt = wins(D["season"])
    sets_ = {"val": tst & (D["season"] <= 2021), "held": tst & (D["season"] >= 2022)}
    rows = []
    sel = {}
    for w in ("val", "held"):
        m = sets_[w]
        for lab, sub in (("tutte e 5 le leghe (guadagno complessivo)", m), ("solo Serie A", m & sa), (f"Serie A, p_ospite mercato ≥ {int(tstar * 100)} %", m & sa & (pa >= tstar))):
            idx = np.where(sub)[0]
            for kn, lk in (("K1", l1), ("K2", l2)):
                d = base[idx] - lk[idx]
                tt = C3.ci_block(d, D["week"][idx])
                rows.append([lab if (kn == "K1" and w == "val") or (kn == "K1" and lab.startswith("tutte") and False) else (lab if kn == "K1" else ""), WLAB[w].split(" ")[0] if False else ("validazione 2020/21-2021/22" if w == "val" else "held-out 2022/23+"), kn, len(idx), f(base[idx].mean()), f(lk[idx].mean()), ci(tt, 5)])
                summ[f"v5c|{w}|{lab[:5]}|{kn}"] = {"n": len(idx), "d": tt}
        sel[w] = float(base[m & sa].mean())
    L += md(rows, ["Insieme", "Finestra", "Variante", "N", "ll baseline", "ll variante", "Δ [IC blocchi]"]) + [""]
    vsa = sets_["val"] & sa
    k_sel = "K2" if (l1[vsa].mean() - l2[vsa].mean()) >= 0.0002 else "K1"
    dh = base[sets_["held"]] - (l1 if k_sel == "K1" else l2)[sets_["held"]]
    th = C3.ci_block(dh, D["week"][sets_["held"]])
    if th[1] > 0:
        v5c = "migliora"
    elif th[2] < 0:
        v5c = "peggiora"
    else:
        v5c = "non distinguibile dal rumore"
    L += [f"**Scelta in validazione** (log-loss della Serie A: K1 {f(l1[vsa].mean())}, K2 {f(l2[vsa].mean())}, baseline {f(base[vsa].mean())}; K2 solo se migliora di almeno 0,0002): **{k_sel}**. "
          f"Guadagno complessivo nell'held-out con {k_sel}: Δ = {ci(th, 5)} → **{v5c}**.", ""]
    summ["v5c"] = {"selected": k_sel, "held": th, "verdict": v5c}
    # V5d
    L += ["### V5d — scommesse a puntata fissa sulle favorite in trasferta di Serie A (quota media, non massima)", "",
          f"1 unità sull'ospite in ogni partita di Serie A con p_ospite ≥ {int(tstar * 100)} %, alla quota media pre-partita; riferimento alla quota media di chiusura. Drawdown = massima discesa picco-valle del profitto cumulato (in unità, partite in ordine di data).", ""]
    rows = []
    mt = sa & (pa >= tstar) & D["ok"]
    for w in ("pre", "val", "held", "disc"):
        m = mt & W[w]
        idx = np.where(m)[0]
        idx = idx[np.argsort(D["date"][idx], kind="stable")]
        win = (D["y"][idx] == 2).astype(float)
        prof = D["od"][idx, 2] * win - 1
        s = cell_stats(D, m, 2)
        dd = max_dd(prof)
        # distribuzione del drawdown ricampionando le settimane
        wk = D["week"][idx]
        uw = np.unique(wk)
        groups = [prof[wk == u] for u in uw]
        rng = np.random.default_rng(5)
        ddb = np.array([max_dd(np.concatenate([groups[i] for i in rng.integers(0, len(uw), len(uw))])) for _ in range(2000)])
        ev_roi = s["roi"][0]
        rows.append([WLAB[w], s["n"], f"{prof.sum():+.1f}", ci(s["roi"], 1, True), ci(s["roi_c"], 1, True), ci(s["clv"], 1, True), f(dd, 1), f"{np.percentile(ddb, 5):.1f} / {np.percentile(ddb, 50):.1f} / {np.percentile(ddb, 95):.1f}"])
        summ[f"v5d|{w}"] = {"n": s["n"], "roi": s["roi"], "roi_c": s["roi_c"], "clv": s["clv"], "dd": dd, "dd_q": [float(np.percentile(ddb, q)) for q in (5, 50, 95)], "profit": float(prof.sum())}
    L += md(rows, ["Finestra", "N scommesse", "profitto (unità)", "ROI quota pre (%) [IC blocchi]", "ROI quota chiusura (%) [IC]", "CLV (%) [IC]", "max drawdown osservato (unità)",
                   "drawdown ricampionando settimane (5° / 50° / 95° perc.)"]) + [""]
    rows = []
    for lab, sub in (("tutte le trasferte, Serie A", sa), ("favorite in trasferta ≥ soglia, altri 4 campionati", (D["lg"] != "I1") & (pa >= tstar))):
        for w in ("pre", "disc"):
            s = cell_stats(D, sub & W[w], 2)
            rows.append(row_cell(lab if w == "pre" else "", WLAB[w], s))
    L += ["**Riferimenti:**", ""] + md(rows, HEAD) + [""]
    print(f"V5 fatto in {time.time() - t0:.0f}s")


def main():
    D = prep()
    print("campione:", int(D["ok"].sum()), "partite con quote")
    L6, summ = [], {}
    res = v6_null(D, L6, summ)
    v6_conditions(D, L6, summ)
    L5 = []
    v5(D, res["p_fam_z"], L5, summ)
    open(os.path.join(P11, "V5.md"), "w", encoding="utf-8").write("\n".join(L5) + "\n")
    open(os.path.join(P11, "V6.md"), "w", encoding="utf-8").write("\n".join(L6) + "\n")
    json.dump(summ, open(os.path.join(P11, "summary_V56.json"), "w"), default=float)


if __name__ == "__main__":
    main()
