"""Round 11 — margine sul mercato (V1 informazione aggiuntiva, V2 closing line value, V3 scommesse). Solo backtest.
Criteri in backtest/round11_parts/prereg.md (scritto prima dell'esecuzione).
Da lanciare:  python -I -X utf8 backtest/run_round11.py [V1|V2|V3|ALL]
Scrive backtest/round11_parts/{V1,V2,V3}.md e summary_{V1,V2,V3}.json; results_round11.md si assembla con run_round11_final.py."""
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

P11 = os.path.join(REPO_ROOT, "backtest", "round11_parts")
os.makedirs(P11, exist_ok=True)
VAL = (2019, 2020, 2021)
LG_NAME = {"I1": "Serie A", "E0": "Premier", "D1": "Bundesliga", "SP1": "La Liga", "F1": "Ligue 1"}
N_BOOT = 5000
N_BOOT_W = int(os.environ.get("R11_BOOT_W", "2000"))
EPS = 1e-9


def prepare():
    feat = L7.build_ctx7()
    gw = L7.goals_walk_forward(feat)
    mk = L7.goal_markets(gw.mu.fillna(1.3), gw.nu.fillna(1.1), gw.rho.fillna(0.0))
    od = R.load_odds(feat)
    ev = ((feat.season >= L7.FIRST_TEST) & gw.mu.notna() & feat.hg.notna()).to_numpy()
    weeks = feat.date.dt.strftime("%G-%V").to_numpy()
    return feat, gw, mk, od, ev, weeks


def sets(season):
    s = np.asarray(season)
    return {"val": np.isin(s, VAL), "held": s >= 2022, "cur": s == 2026}


def f(x, d=4):
    return "—" if x is None or not np.isfinite(x) else f"{x:.{d}f}"


def ci(t, d=4, pct=False):
    m, lo, hi = t
    k = 100 if pct else 1
    if not np.isfinite(m):
        return "—"
    return f"{m * k:.{d}f} [{lo * k:.{d}f}; {hi * k:.{d}f}]"


def md(rows, head):
    return ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(head)) + "|"] + ["| " + " | ".join(map(str, r)) + " |" for r in rows]


def ll_rows(P, y):
    return -np.log(np.clip(P[np.arange(len(y)), y], EPS, 1.0))


# ═════════════════════════════════════ V1 ═════════════════════════════════════
def v1_cfg(name, Pm, Pk, y, season, weeks, league, k):
    """Walk-forward conditional logit. Pm, Pk: (n,k) probabilità modello e mercato (stesso campione, nessun NaN)."""
    Lm, Lk = np.log(np.clip(Pm, EPS, 1)), np.log(np.clip(Pk, EPS, 1))
    n = len(y)
    llm, llk = ll_rows(Pm, y), ll_rows(Pk, y)
    llc, llb = np.full(n, np.nan), np.full(n, np.nan)
    wts = {}
    for s in sorted(set(season)):
        te = season == s
        tr = (season < s) & (season >= L7.FIRST_TEST)
        if s == L7.FIRST_TEST or tr.sum() < 200:
            continue
        a, w = R.fit_clogit([Lm[tr], Lk[tr]], y[tr], k)
        llc[te] = ll_rows(R.predict_clogit([Lm[te], Lk[te]], a, w), y[te])
        a1, w1 = R.fit_clogit([Lk[tr]], y[tr], k)
        llb[te] = ll_rows(R.predict_clogit([Lk[te]], a1, w1), y[te])
    out = {"name": name, "n": n}
    S = sets(season)
    res = {}
    ok = np.isfinite(llc)
    for nm, msk in (("val", S["val"] & ok), ("held", S["held"] & ok), ("cur", S["cur"] & ok)):
        if msk.sum() == 0:
            continue
        d_cal = llb[msk] - llc[msk]
        d_raw = llk[msk] - llc[msk]
        res[nm] = {"n": int(msk.sum()), "ll_model": float(llm[msk].mean()), "ll_mkt": float(llk[msk].mean()), "ll_mktcal": float(llb[msk].mean()),
                   "ll_comb": float(llc[msk].mean()),
                   "gain_cal": C3.ci_block(d_cal, weeks[msk]), "gain_cal_match": C3.ci_match(d_cal),
                   "gain_raw": C3.ci_block(d_raw, weeks[msk]), "gain_raw_match": C3.ci_match(d_raw)}
    out["res"] = res
    # per lega (held-out): guadagno rispetto al mercato calibrato
    perlg = {}
    for lg in LG_NAME:
        msk = S["held"] & ok & (league == lg)
        perlg[lg] = (int(msk.sum()), C3.ci_block(llb[msk] - llc[msk], weeks[msk])) if msk.sum() else None
    out["perlg"] = perlg
    # pesi: held-out e tutte le stagioni, rifacendo la stima a ogni ricampionamento
    for nm, msk in (("held", S["held"]), ("all", np.ones(n, bool))):
        w0, B = R.boot_weights([Lm[msk], Lk[msk]], y[msk], k, weeks[msk], n_boot=N_BOOT_W)
        out[f"w_{nm}"] = {"w_m": (float(w0[0]),) + R.pct(B[:, 0]), "w_k": (float(w0[1]),) + R.pct(B[:, 1]),
                          "sum": (float(w0.sum()),) + R.pct(B.sum(1)), "n": int(msk.sum())}
    perseason = {}
    for s in sorted(set(season)):
        msk = season == s
        _, w = R.fit_clogit([Lm[msk], Lk[msk]], y[msk], k)
        perseason[int(s)] = (int(msk.sum()), float(w[0]), float(w[1]))
    out["perseason"] = perseason
    return out


def v1(feat, gw, mk, od, ev, weeks):
    t0 = time.time()
    y3 = feat.res.to_numpy()
    y2 = ((feat.hg + feat.ag) >= 3).astype(int).to_numpy()
    season, league = feat.season.to_numpy(), feat.Division.to_numpy()
    import pickle
    cache_dir = os.path.join(P11, "_v1cache")
    os.makedirs(cache_dir, exist_ok=True)
    budget = int(os.environ.get("R11_MAXNEW", "99"))            # configurazioni nuove da calcolare per invocazione (ognuna ~4-5 minuti)
    cfgs = []

    def run_cfg(group, lab, args):
        nonlocal budget
        fp = os.path.join(cache_dir, f"{len(cfgs)}.pkl")
        if os.path.exists(fp):
            cfgs.append((group, lab, pickle.load(open(fp, "rb"))))
            return
        if budget <= 0:
            cfgs.append((group, lab, None))
            return
        budget -= 1
        c = v1_cfg(lab, *args)
        pickle.dump(c, open(fp, "wb"))
        print(f"  calcolata: {lab} ({time.time() - t0:.0f}s)", flush=True)
        cfgs.append((group, lab, c))

    for lab, pre_src, clo_src in (("1X2 chiusura (AvgC)", None, "avg"), ("1X2 pre-partita (Avg)", "avg", None),
                                  ("1X2 pre-partita (B365) — sensibilità", "b365", None), ("1X2 chiusura Pinnacle — sensibilità", None, "ps")):
        key = ("pre", pre_src) if pre_src else ("clo", clo_src)
        base = ev & np.isfinite(od[key]["x"]).all(1) & np.isfinite(od[("pre", "avg")]["x"]).all(1) & np.isfinite(od[("clo", "avg")]["x"]).all(1)
        if clo_src == "ps":
            base = ev & np.isfinite(od[key]["x"]).all(1)
        Pk = R.fair(od[key]["x"][base])
        run_cfg("1X2", lab, (mk["P"][base], Pk, y3[base], season[base], weeks[base], league[base], 3))
    for lab, key in (("Over/Under 2,5 chiusura (AvgC)", ("clo", "avg")), ("Over/Under 2,5 pre-partita (Avg)", ("pre", "avg")),
                     ("Over/Under 2,5 pre-partita (B365) — sensibilità", ("pre", "b365")), ("Over/Under 2,5 chiusura Pinnacle — sensibilità", ("clo", "ps"))):
        base = ev & np.isfinite(R.fair(od[key]["o"])).all(1)             # esclude le quote non valide (es. Over a 0,42 in una riga di chiusura, 0,00 in Pinnacle)
        if key == ("clo", "avg") or key == ("pre", "avg"):
            base &= np.isfinite(R.fair(od[("pre", "avg")]["o"])).all(1) & np.isfinite(R.fair(od[("clo", "avg")]["o"])).all(1)
        Pk1 = R.fair(od[key]["o"][base])[:, ::-1]                      # colonne (Under, Over)
        po = mk["o25"][base]
        run_cfg("OU", lab, (np.column_stack([1 - po, po]), Pk1, y2[base], season[base], weeks[base], league[base], 2))
    if any(c is None for _, _, c in cfgs):
        print("V1: configurazioni mancanti, rilanciare per completare", flush=True)
        return
    L = ["## V1 — il modello aggiunge informazione al mercato?", "",
         "Conditional logit walk-forward (utilità = a_c + w_m·log p_modello + w_k·log p_mercato). Δ = log-loss(riferimento) − log-loss(combinato): **positivo = il combinato è meglio**. "
         "Validazione = 2020/21-2021/22, held-out = 2022/23+, «2026/27» = stagione in corso (solo descrittivo). IC 95% a blocchi per settimana ISO.", ""]
    summ = {}
    for group, title in (("1X2", "### 1X2"), ("OU", "### Over/Under 2,5")):
        L += [title, ""]
        rows = []
        for g, lab, c in cfgs:
            if g != group:
                continue
            for nm, nmlab in (("val", "validazione"), ("held", "held-out"), ("cur", "2026/27")):
                r = c["res"].get(nm)
                if not r:
                    continue
                rows.append([lab if nm == "val" else "", nmlab, r["n"], f(r["ll_model"]), f(r["ll_mkt"]), f(r["ll_mktcal"]), f(r["ll_comb"]),
                             ci(r["gain_cal"], 5), ci(r["gain_raw"], 5)])
        L += md(rows, ["Configurazione", "Insieme", "N", "ll modello", "ll mercato grezzo", "ll mercato calibrato", "ll combinato",
                       "Δ vs mercato calibrato [IC blocchi]", "Δ vs mercato grezzo [IC blocchi]"]) + [""]
        L += ["**Pesi** (conditional logit su tutte le partite dell'insieme; IC a blocchi con ristima, " + str(N_BOOT_W) + " ricampionamenti):", ""]
        rows = []
        for g, lab, c in cfgs:
            if g != group:
                continue
            for nm, nmlab in (("held", "held-out 2022/23+"), ("all", "tutte (2019/20+)")):
                w = c[f"w_{nm}"]
                rows.append([lab if nm == "held" else "", nmlab, w["n"], ci(w["w_m"], 3), ci(w["w_k"], 3), ci(w["sum"], 3)])
        L += md(rows, ["Configurazione", "Campione", "N", "peso modello w_m [IC]", "peso mercato w_k [IC]", "w_m + w_k [IC]"]) + [""]
        rows = []
        for g, lab, c in cfgs:
            if g != group:
                continue
            ps = c["perseason"]
            rows.append([lab] + [f"{ps[s][1]:+.2f} / {ps[s][2]:.2f}" if s in ps else "—" for s in range(2019, 2027)])
        L += ["**Pesi per stagione** (w_m / w_k, stima sulla sola stagione):", ""]
        L += md(rows, ["Configurazione"] + [f"{s}/{str(s + 1)[2:]}" for s in range(2019, 2027)]) + [""]
        rows = []
        for g, lab, c in cfgs:
            if g != group or "sensibilità" in lab:
                continue
            rows.append([lab] + [(f"{c['perlg'][lg][1][0] * 1e3:+.2f} ({c['perlg'][lg][0]})" if c["perlg"][lg] else "—") for lg in LG_NAME])
        L += ["**Δ vs mercato calibrato per lega, held-out** (×10⁻³, tra parentesi N):", ""]
        L += md(rows, ["Configurazione"] + list(LG_NAME.values())) + [""]
    for g, lab, c in cfgs:
        summ[lab] = {"res": c["res"], "w_held": c["w_held"], "w_all": c["w_all"]}
    open(os.path.join(P11, "V1.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(summ, open(os.path.join(P11, "summary_V1.json"), "w"), default=float)
    print(f"V1 fatto in {time.time() - t0:.0f}s")


# ═════════════════════════════════════ V2 ═════════════════════════════════════
def long_1x2(feat, mk, od, ev, weeks):
    base = ev & np.isfinite(od[("pre", "avg")]["x"]).all(1) & np.isfinite(od[("clo", "avg")]["x"]).all(1)
    Pp, Pc, Pm = R.fair(od[("pre", "avg")]["x"][base]), R.fair(od[("clo", "avg")]["x"][base]), mk["P"][base]
    n = base.sum()
    df = pd.DataFrame({"d": (Pm - Pp).ravel() * 100, "m": (Pc - Pp).ravel() * 100, "lvl": Pp.ravel() * 100,
                       "o": np.tile(np.arange(3), n), "season": np.repeat(feat.season.to_numpy()[base], 3),
                       "league": np.repeat(feat.Division.to_numpy()[base], 3), "week": np.repeat(weeks[base], 3)})
    return df


def long_ou(feat, mk, od, ev, weeks):
    base = ev & np.isfinite(od[("pre", "avg")]["o"]).all(1) & np.isfinite(od[("clo", "avg")]["o"]).all(1)
    pp, pc = R.fair(od[("pre", "avg")]["o"][base])[:, 0], R.fair(od[("clo", "avg")]["o"][base])[:, 0]       # Over
    po = mk["o25"][base]
    return pd.DataFrame({"d": (po - pp) * 100, "m": (pc - pp) * 100, "lvl": pp * 100, "o": 0, "season": feat.season.to_numpy()[base],
                         "league": feat.Division.to_numpy()[base], "week": weeks[base]})


def zmat(df, outcome_dummies):
    cols = [np.ones(len(df)), df.d.to_numpy(), df.lvl.to_numpy()]
    if outcome_dummies:
        cols += [(df.o == 1).to_numpy(float), (df.o == 2).to_numpy(float)]
    return np.column_stack(cols)


def corr_row(df, dummies):
    if len(df) < 30:
        return ["—"] * 4
    c = R.block_corr(df.d, df.m, df.week, N_BOOT)
    s0 = R.block_slope(np.column_stack([np.ones(len(df)), df.d]), df.m, df.week, 1, N_BOOT)
    s1 = R.block_slope(zmat(df, dummies), df.m, df.week, 1, N_BOOT)
    return [len(df), ci(c, 3), ci(s0, 3), ci(s1, 3)]


def thr_row(df, tau):
    x = df[df.d.abs() > tau]
    if len(x) < 20:
        return len(x), None, None, None
    sg = np.sign(x.d.to_numpy()); mv = x.m.to_numpy()
    nz = mv != 0
    toward = ((np.sign(mv) == sg) & nz).astype(float)
    frac = R.block_ratio(toward, nz.astype(float), x.week.to_numpy(), N_BOOT)
    mean = R.block_ratio(mv * sg, np.ones(len(x)), x.week.to_numpy(), N_BOOT)
    return len(x), frac, mean, float(1 - nz.mean())


def v2(feat, gw, mk, od, ev, weeks):
    t0 = time.time()
    A, B = long_1x2(feat, mk, od, ev, weeks), long_ou(feat, mk, od, ev, weeks)
    SA, SB = sets(A.season), sets(B.season)
    L = ["## V2 — closing line value", "",
         "Per ogni partita ed esito: **d = p_modello − p_pre** (Avg pre-partita senza margine) e **m = p_chiusura − p_pre** (AvgC senza margine meno Avg senza margine), in punti percentuali. "
         "1X2: 3 righe per partita; Over/Under 2,5: lato Over (per divario negativo il segno porta al lato Under). Validazione = 2019/20-2021/22, held-out = 2022/23+. "
         "IC 95% a blocchi per settimana ISO. La pendenza «controllata» include il livello della probabilità pre-partita (e per il 1X2 le variabili di esito).", ""]
    desc = []
    for nm, df, S in (("1X2", A, SA), ("Over 2,5", B, SB)):
        for sn, lab in (("val", "validazione"), ("held", "held-out"), ("cur", "2026/27")):
            x = df[S[sn]]
            desc.append([nm, lab, len(x), f(x.d.std(), 2), f(x.m.std(), 2), f((x.d.abs() > 3).mean() * 100, 1), f((x.d.abs() > 5).mean() * 100, 1), f((x.d.abs() > 8).mean() * 100, 1)])
    L += ["### Descrizione dei divari", ""] + md(desc, ["Mercato", "Insieme", "N", "dev. std d (pt)", "dev. std m (pt)", "% |d|>3", "% |d|>5", "% |d|>8"]) + [""]
    summ = {}
    L += ["### 1. Correlazione e pendenza", "",
          "Pendenza = di quanti punti si sposta in media la probabilità per ogni punto di divario modello − pre-partita (1 = il mercato recupera tutto il divario, 0 = nessuna relazione).", ""]
    rows = []
    for nm, df, S, dm in (("1X2 (tutti gli esiti)", A, SA, True), ("Over 2,5", B, SB, False)):
        for sn, lab in (("val", "validazione"), ("held", "held-out"), ("cur", "2026/27")):
            r = corr_row(df[S[sn]], dm)
            rows.append([nm if sn == "val" else "", lab] + r)
            if sn == "held":
                summ[nm] = {"corr": R.block_corr(df[S[sn]].d, df[S[sn]].m, df[S[sn]].week, N_BOOT), "slope_ctrl": R.block_slope(zmat(df[S[sn]], dm), df[S[sn]].m, df[S[sn]].week, 1, N_BOOT)}
    L += md(rows, ["Mercato", "Insieme", "N", "correlazione [IC]", "pendenza [IC]", "pendenza controllata [IC]"]) + [""]
    L += ["**Per esito (1X2), held-out e validazione:**", ""]
    rows = []
    for o, ol in enumerate(["1 (casa)", "X (pareggio)", "2 (ospite)"]):
        for sn, lab in (("val", "validazione"), ("held", "held-out")):
            r = corr_row(A[SA[sn] & (A.o == o).to_numpy()], False)
            rows.append([ol if sn == "val" else "", lab] + r)
    L += md(rows, ["Esito", "Insieme", "N", "correlazione [IC]", "pendenza [IC]", "pendenza controllata [IC]"]) + [""]
    L += ["**Per lega (1X2 tutti gli esiti e Over 2,5), held-out:**", ""]
    rows = []
    for lg, lgn in LG_NAME.items():
        ra = corr_row(A[SA["held"] & (A.league == lg).to_numpy()], True)
        rb = corr_row(B[SB["held"] & (B.league == lg).to_numpy()], False)
        rows.append([lgn, ra[0], ra[1], ra[3], rb[0], rb[1], rb[3]])
    L += md(rows, ["Lega", "N 1X2", "correlazione 1X2", "pend. controllata 1X2", "N Over", "correlazione Over", "pend. controllata Over"]) + [""]
    # soglie
    L += ["### 2. Partite con divergenza > soglia", "",
          "«Verso il modello» = il segno dello spostamento m coincide con quello del divario d (i movimenti esattamente nulli sono esclusi dalla frazione; la loro quota è riportata). "
          "Caso nullo: 50 % e 0 punti. Movimento medio = m·segno(d), in punti percentuali.", ""]
    best = {}
    rows = []
    for nm, df, S in (("1X2", A, SA), ("Over 2,5", B, SB)):
        for tau in (3, 5, 8):
            for sn, lab in (("val", "validazione"), ("held", "held-out"), ("cur", "2026/27")):
                n, fr, mv, z = thr_row(df[S[sn]], tau)
                rows.append([nm if (tau == 3 and sn == "val") else "", tau if sn == "val" else "", lab, n, ci(fr, 1, True) if fr else "—", ci(mv, 3) if mv else "—", f(z * 100, 1) if z is not None else "—"])
                if sn == "val" and mv:
                    best.setdefault(nm, []).append((mv[1], tau))
                summ[f"{nm}|{tau}|{sn}"] = {"n": n, "frac": fr, "move": mv}
    L += md(rows, ["Mercato", "τ (pt)", "Insieme", "N coppie", "% verso il modello [IC]", "movimento medio verso il modello (pt) [IC]", "% movimenti nulli"]) + [""]
    chosen = {}
    for nm, lst in best.items():
        mx = max(v[0] for v in lst)
        chosen[nm] = min(t for v, t in lst if v == mx)
    L += [f"**Soglia scelta in validazione** (limite inferiore dell'IC del movimento medio verso il modello più alto; parità → τ più bassa): 1X2 τ = {chosen.get('1X2')}, Over/Under 2,5 τ = {chosen.get('Over 2,5')}.", ""]
    summ["chosen"] = chosen
    tau = chosen.get("1X2", 3)
    L += [f"### 3. Per esito, per lega e per Over/Under 2,5 (τ = {tau} per il 1X2; τ = {chosen.get('Over 2,5')} per Over/Under)", ""]
    rows = []
    for o, ol in enumerate(["1 (casa)", "X (pareggio)", "2 (ospite)"]):
        for sn, lab in (("val", "validazione"), ("held", "held-out")):
            n, fr, mv, z = thr_row(A[SA[sn] & (A.o == o).to_numpy()], tau)
            rows.append([ol if sn == "val" else "", lab, n, ci(fr, 1, True) if fr else "—", ci(mv, 3) if mv else "—"])
            summ[f"esito|{o}|{sn}"] = {"n": n, "frac": fr, "move": mv}
    L += md(rows, ["Esito", "Insieme", "N", "% verso il modello [IC]", "movimento medio (pt) [IC]"]) + [""]
    rows = []
    for lg, lgn in LG_NAME.items():
        for sn, lab in (("val", "validazione"), ("held", "held-out")):
            n, fr, mv, z = thr_row(A[SA[sn] & (A.league == lg).to_numpy()], tau)
            rows.append([lgn if sn == "val" else "", lab, n, ci(fr, 1, True) if fr else "—", ci(mv, 3) if mv else "—"])
    L += md(rows, ["Lega (1X2)", "Insieme", "N", "% verso il modello [IC]", "movimento medio (pt) [IC]"]) + [""]
    tauo = chosen.get("Over 2,5", 3)
    rows = []
    for lg, lgn in list(LG_NAME.items()) + [(None, "Tutte le leghe")]:
        for sn, lab in (("val", "validazione"), ("held", "held-out")):
            x = B[SB[sn] & ((B.league == lg).to_numpy() if lg else True)]
            n, fr, mv, z = thr_row(x, tauo)
            rows.append([lgn if sn == "val" else "", lab, n, ci(fr, 1, True) if fr else "—", ci(mv, 3) if mv else "—"])
            if lg is None:
                summ[f"ou_all|{sn}"] = {"n": n, "frac": fr, "move": mv}
    L += md(rows, ["Lega (Over/Under 2,5)", "Insieme", "N", "% verso il modello [IC]", "movimento medio (pt) [IC]"]) + [""]
    # per lato (Over/Under) al segno del divario
    rows = []
    for sd, lab in ((1, "modello più alto del mercato sull'Over"), (-1, "modello più alto sull'Under")):
        for sn, lbl in (("val", "validazione"), ("held", "held-out")):
            x = B[SB[sn]]
            x = x[np.sign(x.d) == sd]
            n, fr, mv, z = thr_row(x, tauo)
            rows.append([lab if sn == "val" else "", lbl, n, ci(fr, 1, True) if fr else "—", ci(mv, 3) if mv else "—"])
    L += md(rows, ["Lato (Over/Under 2,5)", "Insieme", "N", "% verso il modello [IC]", "movimento medio (pt) [IC]"]) + [""]
    open(os.path.join(P11, "V2.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(summ, open(os.path.join(P11, "summary_V2.json"), "w"), default=float)
    print(f"V2 fatto in {time.time() - t0:.0f}s")


# ═════════════════════════════════════ V3 ═════════════════════════════════════
THETAS = [0.0, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20]
MIN_BETS_VAL = 150
OUTL_X = ["1", "X", "2"]
OUTL_O = ["Over 2,5", "Under 2,5"]


def long_bets(feat, mk, od, ev, weeks, market):
    """Una riga per partita-esito: p modello, quote Max e Avg pre-partita, p chiusura senza margine, quota di chiusura media, esito vinto."""
    key = "x" if market == "x" else "o"
    need = [("pre", "max"), ("pre", "avg"), ("clo", "avg")]
    base = ev.copy()
    for k in need:
        base &= np.isfinite(od[k][key]).all(1)
    if market == "x":
        P = mk["P"][base]; win = np.zeros_like(P); win[np.arange(base.sum()), feat.res.to_numpy()[base]] = 1
    else:
        po = mk["o25"][base]; P = np.column_stack([po, 1 - po])
        over = ((feat.hg + feat.ag) >= 3).to_numpy()[base]; win = np.column_stack([over, ~over]).astype(float)
    mx, av, cl = od[("pre", "max")][key][base], od[("pre", "avg")][key][base], od[("clo", "avg")][key][base]
    pc = R.fair(cl)
    k = P.shape[1]
    n = base.sum()
    return pd.DataFrame({"p": P.ravel(), "max": mx.ravel(), "avg": av.ravel(), "pclose": pc.ravel(), "oclose": cl.ravel(), "win": win.ravel(),
                         "o": np.tile(np.arange(k), n), "season": np.repeat(feat.season.to_numpy()[base], k),
                         "league": np.repeat(feat.Division.to_numpy()[base], k), "week": np.repeat(weeks[base], k)})


def bet_stats(x, col):
    """x: righe giocate. ROI e CLV (quota giocata `col`) con IC a blocchi."""
    if len(x) == 0:
        return {"n": 0}
    odds = x[col].to_numpy()
    profit = odds * x.win.to_numpy() - 1
    w = x.week.to_numpy()
    one = np.ones(len(x))
    return {"n": len(x), "roi": R.block_ratio(profit, one, w, N_BOOT), "clo": R.block_ratio(odds * x.pclose.to_numpy() - 1, one, w, N_BOOT),
            "clo_raw": R.block_ratio(odds / x.oclose.to_numpy() - 1, one, w, N_BOOT)}


def pick_theta(x, sig_col):
    rows = []
    v = x[x.season.isin(VAL)]
    for th in THETAS:
        b = v[v.p * v[sig_col] > 1 + th]
        r = (b[sig_col] * b.win - 1).mean() if len(b) else np.nan
        rows.append((th, len(b), r))
    ok = [(th, n, r) for th, n, r in rows if n >= MIN_BETS_VAL and np.isfinite(r)]
    mx = max(r for _, _, r in ok) if ok else None
    best = max([th for th, n, r in ok if r == mx]) if ok else None
    return best, rows


def v3_market(x, labels, market_name, L, summ):
    L += [f"### {market_name}", ""]
    S = sets(x.season)
    strategies = [("Max (quote massime: segnale e regolamento)", "max", "max"), ("Avg (quote medie: segnale e regolamento)", "avg", "avg"),
                  ("Segnale con Max, regolamento alle quote medie", "max", "avg")]
    thetas = {}
    for lab, sig, st in strategies[:2]:
        thetas[sig], tab = pick_theta(x, sig)
        L += [f"**Scelta della soglia in validazione ({lab})** — scommesse e ROI nelle stagioni 2019/20-2021/22 (almeno {MIN_BETS_VAL} scommesse):", ""]
        L += md([[f"{th:.2f}", n, f(r * 100, 2) if np.isfinite(r) else "—", "◄ scelta" if th == thetas[sig] else ""] for th, n, r in tab], ["θ", "N scommesse", "ROI (%)", ""]) + [""]
    summ[market_name] = {"theta_max": thetas["max"], "theta_avg": thetas["avg"]}
    # riferimento: puntare tutto
    rows = []
    for sn, slab in (("val", "validazione"), ("held", "held-out"), ("cur", "2026/27")):
        xs = x[S[sn]]
        for qlab, col in (("tutti gli esiti alla Max", "max"), ("tutti gli esiti alle Avg", "avg")):
            b = bet_stats(xs, col)
            rows.append([qlab, slab, b["n"], ci(b["roi"], 2, True), ci(b["clo"], 2, True)])
    L += ["**Riferimento: puntare su tutti gli esiti** (CLV = valore atteso della quota giocata alle probabilità di chiusura senza margine: è il punto di partenza da cui leggere il CLV delle scommesse selezionate; la Max è la quota più alta tra i bookmaker raccolti, ma resta sotto il prezzo «giusto» della chiusura):", ""]
    L += md(rows, ["Strategia", "Insieme", "N scommesse", "ROI (%) [IC blocchi]", "CLV (%) [IC blocchi]"]) + [""]
    for lab, sig, st in strategies:
        th = thetas.get("max" if sig == "max" else "avg")
        sel = x[(x.p * x[sig] > 1 + th)]
        L += [f"**{lab}** — θ = {th:.2f}" if th is not None else f"**{lab}** — θ non determinabile", ""]
        if th is None:
            continue
        rows = []
        for sn, slab in (("val", "validazione"), ("held", "held-out"), ("cur", "2026/27")):
            b = bet_stats(sel[S[sn][sel.index]], st)
            rows.append([slab, b["n"]] + ([ci(b["roi"], 2, True), ci(b["clo"], 2, True), ci(b["clo_raw"], 2, True)] if b["n"] else ["—"] * 3))
            summ[f"{market_name}|{sig}|{st}|{sn}"] = b
        L += md(rows, ["Insieme", "N scommesse", "ROI (%) [IC blocchi]", "CLV (%) vs chiusura senza margine [IC]", "CLV (%) vs quota di chiusura grezza, margine incluso [IC]"]) + [""]
        if sig == "max" and st == "max" or (sig == "avg" and st == "avg"):
            held = sel[S["held"][sel.index]]
            rows = []
            for s in sorted(held.season.unique()):
                b = bet_stats(held[held.season == s], st)
                rows.append([f"{s}/{str(s + 1)[2:]}", b["n"], ci(b["roi"], 2, True) if b["n"] else "—", ci(b["clo"], 2, True) if b["n"] else "—"])
            L += ["Per stagione (held-out):", ""] + md(rows, ["Stagione", "N", "ROI (%) [IC]", "CLV (%) [IC]"]) + [""]
            rows = []
            for lg, lgn in LG_NAME.items():
                b = bet_stats(held[held.league == lg], st)
                rows.append([lgn, b["n"], ci(b["roi"], 2, True) if b["n"] else "—", ci(b["clo"], 2, True) if b["n"] else "—"])
            L += ["Per lega (held-out):", ""] + md(rows, ["Lega", "N", "ROI (%) [IC]", "CLV (%) [IC]"]) + [""]
            rows = []
            for o, ol in enumerate(labels):
                b = bet_stats(held[held.o == o], st)
                rows.append([ol, b["n"], ci(b["roi"], 2, True) if b["n"] else "—", ci(b["clo"], 2, True) if b["n"] else "—"])
            L += ["Per esito (held-out):", ""] + md(rows, ["Esito", "N", "ROI (%) [IC]", "CLV (%) [IC]"]) + [""]
            # validazione per esito
            vv = sel[S["val"][sel.index]]
            rows = []
            for o, ol in enumerate(labels):
                b = bet_stats(vv[vv.o == o], st)
                rows.append([ol, b["n"], ci(b["roi"], 2, True) if b["n"] else "—", ci(b["clo"], 2, True) if b["n"] else "—"])
            L += ["Per esito (validazione):", ""] + md(rows, ["Esito", "N", "ROI (%) [IC]", "CLV (%) [IC]"]) + [""]


def v3(feat, gw, mk, od, ev, weeks):
    t0 = time.time()
    L = ["## V3 — simulazione di scommesse a puntata fissa (verifica finale)", "",
         "1 unità su ogni esito con **p_modello × quota > 1 + θ**. Quote: Max e Avg **pre-partita** (raccolte giorni prima). θ scelta in validazione (ROI massimo con almeno "
         f"{MIN_BETS_VAL} scommesse), poi invariata. CLV = media di (quota giocata × p_chiusura senza margine − 1) con p_chiusura da AvgC. IC 95% a blocchi per settimana ISO.", ""]
    summ = {}
    X = long_bets(feat, mk, od, ev, weeks, "x")
    X.index = np.arange(len(X))
    v3_market(X, OUTL_X, "1X2", L, summ)
    O = long_bets(feat, mk, od, ev, weeks, "o")
    O.index = np.arange(len(O))
    v3_market(O, OUTL_O, "Over/Under 2,5", L, summ)
    open(os.path.join(P11, "V3.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    json.dump(summ, open(os.path.join(P11, "summary_V3.json"), "w"), default=float)
    print(f"V3 fatto in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    part = sys.argv[1] if len(sys.argv) > 1 else "ALL"
    ctx = prepare()
    print("campione:", int(ctx[4].sum()), "partite OOS 2019/20+")
    for nm, fn in (("V1", v1), ("V2", v2), ("V3", v3)):
        if part in (nm, "ALL"):
            fn(*ctx)
