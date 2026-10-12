#!/usr/bin/env python3
"""
Backtest walk-forward delle "Statistiche attese" (tiri, corner, gialli): modello (Poisson attacco/difesa
+ regressioni di Poisson + Binomiale Negativa, vedi backtest/stats_model.py) contro il metodo a medie
(backtest/stats_baseline.py), test dalla stagione 2019/20.

Il modello è stimato stagione per stagione sulle sole stagioni precedenti (dal 2016/17), tutte le leghe
insieme; il metodo a medie è rifatto ogni settimana con le sole partite precedenti.

Metriche (per statistica): correlazione per squadra (casa e ospite insieme), correlazione della
differenza casa-ospite, MAE del totale, copertura dell'intervallo 80% del totale, log-loss delle
linee Over/Under. Il risultato è confrontato con i valori del backtest di riferimento; se i numeri
sono molto diversi lo script si ferma (exit 2) e li stampa.

Uso (dalla root del repo):
  python -m backtest.run_stats_backtest
"""
import argparse
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import numpy as np
import pandas as pd
from scipy.stats import nbinom, poisson

from backtest import data, features, stats_baseline, stats_model as sm, understat

TEST_START = "2019-07-01"
FIRST_TEST_SEASON = 2019
RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_stats.md")

# valori del backtest di riferimento (test 2019 -> oggi, 12.403 partite, modello con xG)
REF_N = 12403
REF = {
    "tiri":   dict(team=(0.475, 0.508), diff=(0.506, 0.535), cover=0.82),
    "corner": dict(team=(0.316, 0.361), diff=(0.339, 0.393), cover=0.84),
    "gialli": dict(team=(0.242, 0.262), diff=None, cover=0.87),
}
TOL_CORR, TOL_COVER, TOL_N = 0.015, 0.03, 0.03
LABEL = {"tiri": "Tiri", "corner": "Corner", "gialli": "Gialli"}
COUNT_COLS = ["HS", "AS", "HC", "AC", "HY", "AY"]


def corr(a, b):
    return float(np.corrcoef(a, b)[0, 1])


def walk_forward(feat, stat, with_xg):
    """Medie attese e alpha out-of-sample, rifit di stagione in stagione (finestra espansiva dal 2016/17)."""
    X = sm.design(feat, stat, with_xg)
    hc, ac = sm.STATS[stat][:2]
    ok = X.notna().all(axis=1)
    out = pd.DataFrame(np.nan, index=feat.index, columns=["mh", "ma", "alpha"])
    for s in sorted(feat.season.unique()):
        if s < FIRST_TEST_SEASON:
            continue
        tr = ok & (feat.season < s) & (feat.season >= sm.FIRST_TRAIN_SEASON) & feat[hc].notna() & feat[ac].notna()
        te = ok & (feat.season == s)
        if not te.any():
            continue
        m = sm.fit_stat_model(X[tr], feat[hc][tr], feat[ac][tr])
        mh, ma = sm.predict_means(m, X[te])
        out.loc[te, ["mh", "ma"]] = np.column_stack([mh, ma])
        out.loc[te, "alpha"] = m["alpha"]
    return out


def evaluate(stat, y_h, y_a, mh, ma, alpha, bh, ba):
    """Metriche del modello (mh, ma) e del metodo a medie (bh, ba) sulle stesse partite."""
    y = y_h + y_a
    res = {}
    for name, (ph, pa) in (("modello", (mh, ma)), ("medie", (bh, ba))):
        m = ph + pa
        n = 1.0 / alpha
        p = n / (n + m)
        r = {"team": corr(np.r_[ph, pa], np.r_[y_h, y_a]), "diff": corr(ph - pa, y_h - y_a),
             "mae": float(np.abs(m - y).mean()),
             "cover": float(((y >= nbinom.ppf(0.10, n, p)) & (y <= nbinom.ppf(0.90, n, p))).mean())}
        ll = {}
        for L in sm.LINES[stat]:
            over = (y > L).astype(float)
            variants = {"nb": 1 - nbinom.cdf(np.floor(L), n, p)}
            if name == "medie":
                variants["poisson"] = 1 - poisson.cdf(np.floor(L), m)
            for vname, po in variants.items():
                po = np.clip(po, 1e-9, 1 - 1e-9)
                ll[(vname, L)] = float(-(over * np.log(po) + (1 - over) * np.log(1 - po)).mean())
        r["ll"] = ll
        res[name] = r
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args()

    print("Caricamento dati e xG...")
    df = data.load_matches()
    df = understat.attach_xg(df, understat.load_xg(), strict=True)

    print("Feature (core, xG con ridge, statistiche)...")
    feat = features.build_features(df, rebuild=args.rebuild)
    feat = feat.join(features.build_xg_features(df, rebuild=args.rebuild)[["xg_lmu", "xg_lnu"]])
    feat = feat.join(features.build_stat_features(df, rebuild=args.rebuild))

    print("Metodo a medie (walk-forward settimanale)...")
    base = stats_baseline.walk_forward(df, TEST_START)
    feat = feat.join(base)

    test = feat[(feat.date >= pd.Timestamp(TEST_START))]
    complete = test[COUNT_COLS].notna().all(axis=1)
    print(f"  {len(test)} partite di test, {int(complete.sum())} con tutte le statistiche")

    runs = {}
    for variant, with_xg in (("with_xg", True), ("without_xg", False)):
        for stat in sm.STATS:
            print(f"  walk-forward {stat} ({variant})")
            runs[(variant, stat)] = walk_forward(feat, stat, with_xg)

    # insieme di valutazione: partite con tutte le statistiche e le previsioni di entrambe le varianti
    ev_mask = complete.copy()
    for r in runs.values():
        ev_mask &= r.loc[test.index, "mh"].notna()
    ev_mask &= feat.loc[test.index, [f"{k}_bh" for k in sm.STATS]].notna().all(axis=1)
    ev = test[ev_mask]
    n_ev = len(ev)
    print(f"  insieme di valutazione: {n_ev} partite (riferimento: {REF_N})")

    lines = ["# Backtest walk-forward — Statistiche attese (tiri, corner, gialli)", "",
             f"Test: {ev.date.min().date()} → {ev.date.max().date()}, {n_ev} partite (stagioni dal 2019/20) con "
             f"tutte le statistiche. Modello stimato stagione per stagione sulle sole stagioni precedenti (dal "
             f"2016/17, tutte le leghe insieme); metodo a medie rifatto ogni settimana. Totale = Binomiale Negativa "
             f"con alpha stimato a momenti sul training.", ""]
    checks = []
    results = {}
    for stat in sm.STATS:
        hc, ac = sm.STATS[stat][:2]
        y_h, y_a = ev[hc].to_numpy(float), ev[ac].to_numpy(float)
        bh, ba = ev[f"{stat}_bh"].to_numpy(float), ev[f"{stat}_ba"].to_numpy(float)
        for variant in ("with_xg", "without_xg"):
            r = runs[(variant, stat)].loc[ev.index]
            results[(variant, stat)] = evaluate(stat, y_h, y_a, r.mh.to_numpy(), r.ma.to_numpy(),
                                                r.alpha.to_numpy(), bh, ba)

    # ── tabella principale ────────────────────────────────────────────────────────
    lines += ["## Confronto modello vs metodo a medie", "",
              "| Statistica | Metodo | Corr. per squadra | Corr. differenza casa−ospite | MAE totale | "
              "Copertura 80% | Log-loss O/U (media linee) |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for stat in sm.STATS:
        wx, wo = results[("with_xg", stat)], results[("without_xg", stat)]
        alpha_mean = float(runs[("with_xg", stat)].loc[ev.index, "alpha"].mean())

        def row(label, r, ll_key):
            lls = [v for (k, L), v in r["ll"].items() if k == ll_key]
            return (f"| {LABEL[stat]} | {label} | {r['team']:.3f} | {r['diff']:.3f} | {r['mae']:.3f} | "
                    f"{r['cover']:.3f} | {np.mean(lls):.4f} |")

        lines.append(row("Medie (Poisson sul totale)", wx["medie"], "poisson"))
        lines.append(row("Medie (NB, alpha del modello)", wx["medie"], "nb"))
        lines.append(row("**Modello con xG**", wx["modello"], "nb"))
        lines.append(row("Modello senza xG (ripiego)", wo["modello"], "nb"))
        lines.append(f"| {LABEL[stat]} | _alpha NB medio_ | | | | | {alpha_mean:.4f} |")
    lines.append("")

    # ── log-loss per linea ─────────────────────────────────────────────────────────
    lines += ["## Log-loss delle linee Over/Under (più basso = meglio)", "",
              "| Statistica | Linea | Medie (Poisson) | Medie (NB) | Modello con xG | Modello senza xG |",
              "|---|---:|---:|---:|---:|---:|"]
    for stat in sm.STATS:
        wx, wo = results[("with_xg", stat)], results[("without_xg", stat)]
        for L in sm.LINES[stat]:
            lines.append(f"| {LABEL[stat]} | {L:g} | {wx['medie']['ll'][('poisson', L)]:.4f} | "
                         f"{wx['medie']['ll'][('nb', L)]:.4f} | {wx['modello']['ll'][('nb', L)]:.4f} | "
                         f"{wo['modello']['ll'][('nb', L)]:.4f} |")
    lines.append("")

    # ── confronto coi valori di riferimento ─────────────────────────────────────────
    lines += ["## Confronto con il backtest di riferimento", "",
              "| Statistica | Metrica | Riferimento | Questo backtest | Esito |",
              "|---|---|---:|---:|---|"]
    n_ok = abs(n_ev - REF_N) / REF_N <= TOL_N
    checks.append(("Numero di partite", f"{n_ev} (riferimento {REF_N})", n_ok))
    for stat in sm.STATS:
        wx = results[("with_xg", stat)]
        ref = REF[stat]
        items = [("Corr. squadra, medie", ref["team"][0], wx["medie"]["team"], TOL_CORR),
                 ("Corr. squadra, modello", ref["team"][1], wx["modello"]["team"], TOL_CORR)]
        if ref["diff"]:
            items += [("Corr. differenza, medie", ref["diff"][0], wx["medie"]["diff"], TOL_CORR),
                      ("Corr. differenza, modello", ref["diff"][1], wx["modello"]["diff"], TOL_CORR)]
        items.append(("Copertura 80% (modello)", ref["cover"], wx["modello"]["cover"], TOL_COVER))
        for label, rv, mv, tol in items:
            ok = abs(mv - rv) <= tol
            checks.append((f"{LABEL[stat]} — {label}", f"{mv:.3f} (rif. {rv:.3f}, tolleranza ±{tol})", ok))
            lines.append(f"| {LABEL[stat]} | {label} | {rv:.3f} | {mv:.3f} | {'OK' if ok else 'DIVERSO'} |")
    lines.append("")

    # ── stabilità per stagione (correlazione per squadra, modello − medie) ───────────
    lines += ["## Stabilità per stagione (correlazione per squadra: modello − medie)", "",
              "| Stagione | N | Tiri | Corner | Gialli |", "|---|---:|---:|---:|---:|"]
    for s in sorted(ev.season.unique()):
        m = (ev.season == s).to_numpy()
        cells = []
        for stat in sm.STATS:
            hc, ac = sm.STATS[stat][:2]
            r = runs[("with_xg", stat)].loc[ev.index][m]
            yy = np.r_[ev[hc].to_numpy(float)[m], ev[ac].to_numpy(float)[m]]
            cm = corr(np.r_[r.mh, r.ma], yy)
            cb = corr(np.r_[ev[f"{stat}_bh"].to_numpy(float)[m], ev[f"{stat}_ba"].to_numpy(float)[m]], yy)
            cells.append(f"{cm - cb:+.3f}")
        lines.append(f"| {s}/{(s + 1) % 100:02d} | {m.sum()} | " + " | ".join(cells) + " |")
    lines.append("")

    lines += ["## Controlli", ""]
    for label, value, ok in checks:
        lines.append(f"- {label}: {value} → {'OK' if ok else 'DIVERSO'}")
    lines.append("")

    text = "\n".join(lines)
    print("\n" + text)
    with open(RESULTS_PATH, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"Salvato in {RESULTS_PATH}")
    if not all(ok for _, _, ok in checks):
        print("\n⚠ STOP: i numeri sono diversi dal backtest di riferimento — verificare prima di andare avanti.")
        sys.exit(2)


if __name__ == "__main__":
    main()
