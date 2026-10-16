"""Round 2 — combinazioni, tabella riassuntiva, grafico di affidabilità e assemblaggio di results_round2.md."""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import data, round2_ctx as C, round2_recal as RC, stack
from backtest.round2_lib import Boot, devig, ll_vec, run_stack
from backtest.run_round2_exp1 import FEAT_PATH, closed_flag
from backtest.run_round2_exp2 import PARTS, RIDGE, cpath, mk_features

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results_round2.md")
SVG = os.path.join(HERE, "results_round2_affidabilita.svg")


def reliability_svg(chart, path):
    W, H, pad = 330, 360, 46
    panels = list(chart.items())
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W * 3} {H}" font-family="Arial, sans-serif" font-size="11">',
           f'<rect width="{W * 3}" height="{H}" fill="white"/>']
    for pi, (name, pts) in enumerate(panels):
        ox = pi * W
        lo = min(min(p[0], p[1]) for p in pts) - 0.03
        hi = max(max(p[0], p[1]) for p in pts) + 0.03
        lo, hi = max(0.0, lo), min(1.0, hi)

        def X(v): return ox + pad + (v - lo) / (hi - lo) * (W - pad - 20)
        def Y(v): return H - pad - (v - lo) / (hi - lo) * (H - pad - 40)
        svg.append(f'<text x="{ox + W / 2}" y="22" text-anchor="middle" font-size="14" font-weight="bold">{name}</text>')
        svg.append(f'<line x1="{X(lo)}" y1="{Y(lo)}" x2="{X(hi)}" y2="{Y(hi)}" stroke="#999" stroke-dasharray="4 3"/>')
        svg.append(f'<line x1="{X(lo)}" y1="{Y(lo)}" x2="{X(hi)}" y2="{Y(lo)}" stroke="#333"/>')
        svg.append(f'<line x1="{X(lo)}" y1="{Y(lo)}" x2="{X(lo)}" y2="{Y(hi)}" stroke="#333"/>')
        for k in range(5):
            v = lo + (hi - lo) * k / 4
            svg.append(f'<text x="{X(v)}" y="{H - pad + 16}" text-anchor="middle">{v:.2f}</text>')
            svg.append(f'<text x="{X(lo) - 6}" y="{Y(v) + 4}" text-anchor="end">{v:.2f}</text>')
        svg.append(f'<text x="{ox + W / 2}" y="{H - 8}" text-anchor="middle">probabilità prevista (media del bin)</text>')
        svg.append(f'<text x="{ox + 12}" y="{H / 2}" transform="rotate(-90 {ox + 12} {H / 2})" text-anchor="middle">frequenza reale</text>')
        path_pts = " ".join(f"{X(p[0]):.1f},{Y(p[1]):.1f}" for p in pts)
        svg.append(f'<polyline points="{path_pts}" fill="none" stroke="#1f6feb" stroke-width="1.5"/>')
        for pm, fr, se in pts:
            svg.append(f'<line x1="{X(pm):.1f}" y1="{Y(fr - 1.96 * se):.1f}" x2="{X(pm):.1f}" y2="{Y(fr + 1.96 * se):.1f}" stroke="#1f6feb" stroke-opacity="0.5"/>')
            svg.append(f'<circle cx="{X(pm):.1f}" cy="{Y(fr):.1f}" r="3.5" fill="#1f6feb"/>')
    svg.append("</svg>")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(svg))


def main():
    c = C.get_ctx()
    ev, feat, df = c.ev, c.feat, c.df
    boot = Boot(len(ev))
    Pb = c.base_sp[["pH", "pD", "pA"]].to_numpy()
    y = c.y
    a = pd.read_pickle(cpath("exp2a_results.pkl"))
    b = pd.read_pickle(cpath("exp2b_results.pkl"))
    xi, K = a["xi_star"], b["K_star"]
    imp = pd.read_pickle(cpath("exp2_imp_main.pkl"))["v"]
    mk = mk_features(df, imp, xi, RIDGE, "main")
    eo = pd.read_pickle(cpath(f"exp2_eo_K{K}.pkl"))["v"]
    f1 = pd.read_pickle(FEAT_PATH)["f"]
    closed = closed_flag(df)

    new = feat.copy()
    for col in ["dc_lmu", "dc_lnu", "sot_lmu", "sot_lnu", "xg_lmu", "xg_lnu"]:
        new[col] = f1[col].reindex(new.index)
    new["closed"] = closed.reindex(new.index).astype(float)
    for fr in (new, feat):
        fr["mk_lmu"], fr["mk_lnu"] = mk.mk_lmu.reindex(fr.index), mk.mk_lnu.reindex(fr.index)
        fr["eo_diff"] = eo.eo_diff.reindex(fr.index)
    XG = stack.XG_FEATURES
    combos = [
        ("C1 — 2a + 2b (i due positivi significativi)", feat, XG + ["mk_lmu", "mk_lnu", "eo_diff"]),
        ("C2 — 2b + 1a (Elo-Odds + porte chiuse)", new, XG + ["eo_diff", "closed"]),
        ("C3 — 2a + 2b + 1a (tutti i positivi, anche non significativi)", new, XG + ["mk_lmu", "mk_lnu", "eo_diff", "closed"]),
    ]
    comb_res = []
    for name, frame, cols in combos:
        sp = run_stack(frame, cols, ev)
        C.reg_save("C " + name, sp)
        comb_res.append(C.compare(sp[["pH", "pD", "pA"]].to_numpy(), Pb, ev, boot, name))
        print(name, f"{comb_res[-1]['d_ll']:+.5f}", flush=True)
    best_c = max(comb_res, key=lambda r: r["d_ll"])
    sp_best = C.reg_load()["C " + best_c["name"]]["sp"]
    # ricalibrazione sulla migliore combinazione
    res, burn, hist = RC.walk_forward_recal(ev.date, sp_best.mu.to_numpy(), sp_best.nu.to_numpy(),
                                            sp_best[["pH", "pD", "pA"]].to_numpy(), y, ["olflex", "ts_b", "ts_d"])
    recal_rows = []
    for k, lab in (("olflex", "ordered logit flessibile"), ("ts_b", "temperature scaling + bias pareggio"),
                   ("ts_d", "temperature scaling con T pareggio separata")):
        nm = f"{best_c['name'].split(' — ')[0]} + ricalibrazione ({lab})"
        sp2 = sp_best.copy(); sp2[["pH", "pD", "pA"]] = res[k]
        C.reg_save("C " + nm, sp2)
        recal_rows.append(C.compare(res[k], Pb, ev, boot, nm))
        recal_rows[-1]["d_vs_partenza"] = C.compare(res[k], sp_best[["pH", "pD", "pA"]].to_numpy(), ev, boot, nm)

    L = ["## Combinazione dei positivi", "",
         f"Positivi = varianti con Δ log-loss > 0 e IC 95% che esclude lo zero: **2a** (forze implicite, xi={xi:g}) e **2b** (Elo-Odds, K={K}). "
         "L'esperimento 1 (porte chiuse / lega) e l'esperimento 3 (ricalibrazione) non hanno prodotto guadagni distinguibili dal rumore; "
         "la riga C3 li include comunque per vedere se aggiungono qualcosa. Ogni riga confrontata col baseline.", ""]
    L += C.md_summary_rows(comb_res) + [""]
    for r in comb_res:
        L += C.md_variant(r, title=r["name"])
    L += [f"**Ricalibrazione sulla combinazione migliore ({best_c['name']})**", "",
          "| Variante | Log-loss | Δ vs baseline [IC 95%] | Δ vs combinazione non ricalibrata [IC 95%] |", "|---|---:|---|---|"]
    for r in recal_rows:
        d = r["d_vs_partenza"]
        L.append(f"| {r['name']} | {r['ll']:.4f} | {r['d_ll']:+.5f} [{r['lo_ll']:+.5f}, {r['hi_ll']:+.5f}] | "
                 f"{d['d_ll']:+.5f} [{d['lo_ll']:+.5f}, {d['hi_ll']:+.5f}] |")
    L.append("")

    # ── confronti diretti tra varianti (non col baseline) ─────────────────────
    regp = C.reg_load()
    Pk = lambda key: regp[key]["sp"][["pH", "pD", "pA"]].to_numpy()
    k2a, k2b = f"E2 2a — stack + forze implicite (xi={xi:g})", f"E2 2b — Elo-Odds, K={K}"
    kc2 = "C " + comb_res[1]["name"]
    pairs = [("2b (Elo-Odds) vs 2a (forze implicite)", k2b, k2a),
             ("2a+2b vs 2b da solo", "C " + comb_res[0]["name"], k2b),
             ("C2 (2b + porte chiuse) vs 2b da solo", kc2, k2b),
             ("C3 vs C2", "C " + comb_res[2]["name"], kc2),
             ("C2 + ordered logit flessibile vs C2", "C " + recal_rows[0]["name"], kc2)]
    L += ["**Confronti diretti tra varianti** (Δ = log-loss(seconda) − log-loss(prima): positivo = la prima "
          "variante di ogni coppia è migliore della seconda; IC 95% bootstrap appaiato per partita)", "",
          "| Confronto | Δ log-loss | IC 95% |", "|---|---:|---|"]
    for lab, ka, kb in pairs:
        r = C.compare(Pk(ka), Pk(kb), ev, boot, lab)
        L.append(f"| {lab} | {r['d_ll']:+.5f} | [{r['lo_ll']:+.5f}, {r['hi_ll']:+.5f}] |")
    L += ["", "Le combinazioni sono state scelte DOPO aver visto i singoli esperimenti (3 combinazioni + 3 ricalibrazioni provate): "
              "i guadagni di C2 e C3 rispetto a 2b da solo vanno letti con questa cautela (forking paths), anche se la direzione "
              "è coerente nelle stagioni.", ""]

    # ── tabella riassuntiva ───────────────────────────────────────────────────
    reg = C.reg_load()
    exp0 = pd.read_pickle(os.path.join(C.R2_DIR, "exp0a.pkl"))
    cl_ll = exp0["res0a"][("Quote medie di chiusura", "power")]["ll"]
    cl_ll_norm = exp0["res0a"][("Quote medie di chiusura", "norm")]["ll"]
    base_ll = float(ll_vec(Pb, y).mean())
    gap = base_ll - cl_ll
    picks = [
        ("Baseline (stack + xG ridge)", None),
        ("E1 1a — dummy porte chiuse (DC + regressione)", "E1 1a — dummy nei DC (gol, tiri, xG) + nella regressione"),
        ("E1 1a-ii — dummy solo nella regressione", "E1 1a-ii — dummy solo nella regressione"),
        ("E1 1b — intercette di lega", "E1 1b — vantaggio casa per lega (intercette di lega nella regressione)"),
        ("E1 1a+1b", "E1 1a+1b — dummy completa + intercette di lega"),
        ("E2 2a — forze implicite, xi=0.005 (ridge 2)", f"E2 2a — stack + forze implicite (xi={xi:g})"),
        ("E2 2a — xi=0.010 (oltre il range, sensibilità)", "E2 2a — forze implicite, xi=0.01 (oltre il range richiesto)"),
        ("E2 2a — ridge 0.5", f"E2 2a — ridge 0.5 (xi={xi:g})"),
        ("E2 2a — Pinnacle", f"E2 2a — Pinnacle in chiusura (dove disponibile), xi={xi:g}"),
        ("E2 2a — Poisson indipendente", f"E2 2a — Poisson indipendente (rho=0), xi={xi:g}"),
        ("E2 2a — senza xG nello stack", f"E2 2a — senza xG nello stack (sostituisce l'xG), xi={xi:g}"),
        ("E2 2b — Elo-Odds K=60", "E2 2b — Elo-Odds, K=60"),
        (f"E2 2b — Elo-Odds K={K} (scelto)", f"E2 2b — Elo-Odds, K={K}"),
        ("E2 2b — Elo-Odds K=300", "E2 2b — Elo-Odds, K=300"),
        ("E2 2a+2b", f"E2 2a+2b — forze implicite (xi={xi:g}) + Elo-Odds (K={K})"),
        ("E3 baseline + temperature scaling + bias pareggio", "E3 baseline + Temperature scaling + bias sul pareggio"),
        ("E3 baseline + temperature scaling, T pareggio separata", "E3 baseline + Temperature scaling con T separata per il pareggio"),
        ("E3 baseline + ordered logit flessibile", "E3 baseline + Ordered logit flessibile (banda del pareggio dipende da gol attesi)"),
        (f"E3 Elo-Odds K={K} + ordered logit flessibile", f"E3 migliore tra 1 e 2 (Elo-Odds K=200) + Ordered logit flessibile (banda del pareggio dipende da gol attesi)"),
        (f"E3 Elo-Odds K={K} + temperature scaling + bias", "E3 migliore tra 1 e 2 (Elo-Odds K=200) + Temperature scaling + bias sul pareggio"),
    ] + [(r["name"], "C " + r["name"]) for r in comb_res] + [(r["name"], "C " + r["name"]) for r in recal_rows]
    rows = []
    for lab, key in picks:
        if key is None:
            rows.append(dict(name=lab, ll=base_ll, d_ll=0.0, lo_ll=0.0, hi_ll=0.0, sb=(0, 0), early=0.0, late=0.0))
            continue
        if key not in reg:
            print("MANCA", key)
            continue
        sp = reg[key]["sp"]
        r = C.compare(sp[["pH", "pD", "pA"]].to_numpy(), Pb, ev, boot, lab)
        bs = r["by_season"]
        wavg = lambda sel: sum(v[0] * v[1] for s_, v in bs.items() if sel(s_)) / sum(v[1] for s_, v in bs.items() if sel(s_))
        rows.append(dict(name=lab, ll=r["ll"], d_ll=r["d_ll"], lo_ll=r["lo_ll"], hi_ll=r["hi_ll"], sb=r["seasons_better"],
                         early=wavg(lambda s_: s_ <= 2021), late=wavg(lambda s_: s_ >= 2022)))
    S = ["## Tabella riassuntiva", "",
         f"Baseline = stack Poisson (DC gol, DC tiri in porta, pi-ratings, DC xG con ridge 2; training dal 2016/17), "
         f"{len(ev)} partite 2019/20 → 2026-10-12. Δ = log-loss(baseline) − log-loss(variante): positivo = meglio. "
         f"Riferimento: quote di chiusura senza margine (power) = **{cl_ll:.4f}** (con normalizzazione semplice {cl_ll_norm:.4f}); "
         f"divario baseline − chiusura = {gap:.4f}. «Divario recuperato» = Δ / divario.", "",
         "| Variante | Log-loss | Δ vs baseline | IC 95% | Stagioni migliorate | Δ 2019/20-2021/22 | Δ 2022/23→oggi | Distanza dalle quote di chiusura | Divario recuperato |",
         "|---|---:|---:|---|---:|---:|---:|---:|---:|",
         f"| *Quote di chiusura (power)* | {cl_ll:.4f} | {base_ll - cl_ll:+.5f} | — | — | — | — | 0.0000 | 100% |"]
    for r in rows:
        sb = f"{r['sb'][0]}/{r['sb'][1]}" if r["sb"][1] else "—"
        ic = "—" if r["name"].startswith("Baseline") else f"[{r['lo_ll']:+.5f}, {r['hi_ll']:+.5f}]"
        S.append(f"| {r['name']} | {r['ll']:.4f} | {r['d_ll']:+.5f} | {ic} | {sb} | {r['early']:+.4f} | {r['late']:+.4f} | "
                 f"{r['ll'] - cl_ll:+.4f} | {r['d_ll'] / gap * 100:.1f}% |")
    S.append("")

    # ── assemblaggio ─────────────────────────────────────────────────────────
    chart = pd.read_pickle(os.path.join(C.R2_DIR, "exp0b_chart.pkl"))
    reliability_svg(chart, SVG)
    parts = []
    for fn in ("exp0.md", "exp1.md", "exp2_a.md", "exp2_b.md", "extra.md", "exp3.md", "checks.md"):
        with open(os.path.join(PARTS, fn), encoding="utf-8") as fh:
            parts.append(fh.read())
    parts[0] = parts[0].replace("### 0b — Diagramma di affidabilità del baseline (stack + xG ridge)",
                                "### 0b — Diagramma di affidabilità del baseline (stack + xG ridge)\n\n"
                                "![Diagramma di affidabilità](results_round2_affidabilita.svg)\n\n(Il grafico è in `backtest/results_round2_affidabilita.svg`: "
                                "punti = bin per decili, barre = IC 95%, linea tratteggiata = calibrazione perfetta.)")
    head = ["# Round 2 — esperimenti sul modello dei campionati (solo backtest)", "",
            "**Nulla della produzione è stato toccato** (generate_static.py, train_stack.py, models/, docs/, workflow): tutto il codice è in "
            "`backtest/round2_*.py` e `backtest/run_round2_*.py`.", "",
            "## Impostazione", "",
            f"- **Baseline** = modello attuale: Poisson-stack con DC sui gol (tau), DC sui tiri in porta, pi-ratings e DC sugli xG Understat con "
            f"ridge = 2; due regressioni di Poisson (gol casa, gol trasferta), stimate stagione per stagione sulle sole stagioni precedenti "
            f"(training dal 2016/17), test dalla stagione 2019/20 a oggi: {len(ev)} partite con quote medie valide, 5 campionati. "
            f"Con i dati aggiornati al 2026-10-12 il baseline dà log-loss {base_ll:.4f} (il file results.md, generato con meno partite, "
            f"riportava 0.9834 su 12708: stessa pipeline).",
            "- **Stesse partite per tutte le varianti**; il bootstrap è appaiato per partita (5000 ricampionamenti, stessi indici per ogni "
            "confronto, IC 95% percentile). Δ = baseline − variante (positivo = variante migliore). Il bootstrap per partita ignora la "
            "correlazione tra partite della stessa settimana: gli IC vanno letti come leggermente ottimistici (il backtest ufficiale usa "
            "blocchi per settimana).",
            "- **Anti-leakage**: ogni feature di una partita usa solo partite con data strettamente precedente al rifit settimanale; le quote "
            "della partita da prevedere non entrano mai. Verificato con test di perturbazione e placebo (sezione finale «Controlli»).",
            "- **Scelta degli iperparametri**: dove possibile con un criterio che non usa il periodo di test (errore di previsione del lambda "
            "implicito / del punteggio atteso Elo nelle stagioni 2016-2018). Le griglie complete sono riportate, così si vede la "
            "sensibilità. Ogni scelta è dichiarata nella sezione corrispondente.", "",
            "---", ""]
    commento = ""
    cp = os.path.join(PARTS, "commento.md")
    if os.path.exists(cp):
        with open(cp, encoding="utf-8") as fh:
            commento = fh.read()
    text = ("\n".join(head) + "\n\n".join(parts[:6]) + "\n\n" + "\n".join(L) + "\n" + parts[6] + "\n\n" +
            "\n".join(S) + "\n" + commento)
    with open(RESULTS, "w", encoding="utf-8") as fh:
        fh.write(text)
    with open(os.path.join(PARTS, "summary.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(S))
    print("\n".join(L))
    print("\n".join(S))


if __name__ == "__main__":
    main()
