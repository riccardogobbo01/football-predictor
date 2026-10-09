#!/usr/bin/env python3
"""
Backtest walk-forward (Step 1-3 e Step 7.1 del piano): quote vs Dixon-Coles vs
Poisson-stack, con e senza gli xG di Understat.

Rifit del Dixon-Coles ogni 7 giorni con SOLO partite precedenti (finestra 5 anni).
Lo stack è stimato stagione per stagione sulle sole stagioni precedenti: dal 2013/14
senza xG, dal 2016/17 con xG (gli xG partono dal 2014). Test dalla stagione 2019/20 alla
corrente; tutti i modelli sono valutati sulle stesse partite (quelle con quote medie valide).

Uso (dalla root del repo):
  python -m backtest.run_backtest              # completo (xG Understat inclusi)
  python -m backtest.run_backtest --elo        # aggiunge le righe con ClubElo (opzionale)
  python -m backtest.run_backtest --rebuild    # ricalcola le feature in cache
"""
import argparse
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import numpy as np
import pandas as pd

from backtest import data, models, features, stack, understat

TEST_START = "2019-07-01"
FIRST_TEST_SEASON = 2019
N_BOOT = 5000

ACCEPT_DC = (0.994, 0.004)
ACCEPT_MARKET = (0.973, 0.004)
ACCEPT_STACK_MAX = 0.987
ACCEPT_XG_MIN_GAIN = 0.0015     # atteso circa +0.002/+0.003
ACCEPT_RIDGE_MIN_GAIN = 0.0003  # ridge sul DC xG: atteso circa +0.0007

RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.md")

BASE = ["dc_lmu", "dc_lnu"]
M_MKT = "Quote medie senza margine (power)"
M_CL = "Quote chiusura senza margine (power)"
M_DC = "Dixon-Coles attuale (xi=0.0018)"
M_RECAL = "DC ricalibrato (stack su dc_lmu, dc_lnu) *"
M_PI = "DC + pi-ratings"
M_PROD = "Stack senza xG (produzione, training dal 2013/14)"
M_CTRL = "Stack senza xG (training dal 2016/17) *"
M_XG = "Stack + xG Understat (training dal 2016/17)"
M_XGR = "Stack + xG con ridge=2 sul DC xG (training dal 2016/17)"
M_ELO = "Stack + Elo (training dal 2013/14)"


def _valid_odds(df, prefix):
    o = df[[f"{prefix}_h", f"{prefix}_d", f"{prefix}_a"]].to_numpy(dtype=float)
    return np.isfinite(o).all(1) & (o > 1).all(1)


def block_bootstrap(d, blocks, n_boot=N_BOOT, seed=42):
    """Media di d (differenza di log-loss per partita) con IC 95% bootstrap a blocchi."""
    codes, uniq = pd.factorize(blocks)
    sums = np.bincount(codes, d)
    cnt = np.bincount(codes).astype(float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(uniq), size=(n_boot, len(uniq)))
    est = sums[idx].sum(1) / cnt[idx].sum(1)
    return float(d.mean()), tuple(np.percentile(est, [2.5, 97.5]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elo", action="store_true", help="aggiunge la riga con ClubElo (opzionale)")
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args()

    print("Caricamento dati (football-data.co.uk)...")
    df = data.load_matches()

    print("xG Understat...")
    xg_raw = understat.load_xg()
    try:
        df = understat.attach_xg(df, xg_raw, strict=True)
    except understat.UnderstatError as e:
        print(f"\n✗ STOP — abbinamento xG insufficiente:\n{e}")
        sys.exit(3)
    scope = df[(df.season >= understat.FIRST_SEASON)]
    xg_cov = (int(scope.xg_h.notna().sum()), len(scope))

    print("Feature walk-forward (DC gol, DC tiri in porta, pi-ratings, DC xG)...")
    feat = features.build_features(df, rebuild=args.rebuild)
    feat = feat.join(features.build_xg_features(df, ridge=0.0, rebuild=args.rebuild)[["xg_lmu", "xg_lnu"]])
    xg_r = features.build_xg_features(df, ridge=features.XG_RIDGE, rebuild=args.rebuild)
    feat_r = feat.assign(xg_lmu=xg_r.xg_lmu, xg_lnu=xg_r.xg_lnu)   # stesso frame, xG con ridge

    if args.elo:
        from backtest import elo
        print("Elo (ClubElo)...")
        try:
            feat = elo.add_elo(feat, strict=True)
        except RuntimeError as e:
            print(f"\n✗ Elo non disponibile:\n{e}")
            sys.exit(3)

    test = feat[feat.date >= pd.Timestamp(TEST_START)]
    ok = _valid_odds(test, "odds")
    ev = test[ok].copy()
    print(f"  {len(test)} partite di test, {len(ev)} con quote medie valide")

    P_mkt = models.market_probs(ev.odds_h.values, ev.odds_d.values, ev.odds_a.values, "power")
    cl_ok = _valid_odds(ev, "cl")
    P_cl = np.full((len(ev), 3), np.nan)
    P_cl[cl_ok] = models.market_probs(ev.cl_h.values[cl_ok], ev.cl_d.values[cl_ok],
                                      ev.cl_a.values[cl_ok], "power")

    all_true = np.ones(len(ev), bool)
    preds = {
        M_MKT: (P_mkt, all_true),
        M_CL: (P_cl, cl_ok),
        M_DC: (ev[["dc_pH", "dc_pD", "dc_pA"]].to_numpy(), all_true),
    }

    runs = [
        (M_RECAL, BASE, None, feat),
        (M_PI, BASE + ["pi_gd", "pi_diff"], None, feat),
        (M_PROD, stack.PRODUCTION_FEATURES, None, feat),
        (M_CTRL, stack.PRODUCTION_FEATURES, stack.XG_FIRST_TRAIN_SEASON, feat),
        (M_XG, stack.XG_FEATURES, stack.XG_FIRST_TRAIN_SEASON, feat),
        (M_XGR, stack.XG_FEATURES, stack.XG_FIRST_TRAIN_SEASON, feat_r),
    ]
    if args.elo:
        runs.append((M_ELO, stack.PRODUCTION_FEATURES + ["elo_diff"], None, feat))
    for name, cols, min_train, frame in runs:
        print(f"  stack: {name}")
        sp = stack.walk_forward_stack(frame, cols, FIRST_TEST_SEASON, min_train).reindex(ev.index)
        preds[name] = (sp[["pH", "pD", "pA"]].to_numpy(), sp.pH.notna().to_numpy())

    y_all = ev.res.values
    ll_vec, rows = {}, []

    def scope_masks():
        yield "Tutti", np.ones(len(ev), bool)
        for code, name in data.LEAGUE_NAMES.items():
            yield name, (ev.Division == code).to_numpy()

    for scope_name, smask in scope_masks():
        for model, (P, valid) in preds.items():
            m = smask & valid
            if not m.any():
                continue
            met, ll = models.metrics(P[m], y_all[m])
            rows.append((scope_name, model, met))
            if scope_name == "Tutti":
                v = np.full(len(ev), np.nan); v[m] = ll
                ll_vec[model] = v

    cur = data.current_season()
    lines = [
        "# Backtest walk-forward — Step 1-3 e 7.1 (xG Understat)",
        "",
        f"Test: {ev.date.min().date()} → {ev.date.max().date()} "
        f"(stagioni 2019/20 → {cur}/{(cur + 1) % 100:02d}), {len(ev)} partite con quote medie valide. "
        f"DC rifittato ogni 7 giorni (finestra 5 anni, xi=0.0018); xG: DC senza tau su xG Understat, "
        f"xi=0.003, finestra 5 anni (nelle righe \"ridge\" con penalità ridge=2 sul solo DC degli xG; "
        f"il DC dei gol non usa ridge). Lo stack è stimato stagione per stagione sulle sole stagioni "
        f"precedenti, 5 campionati insieme. Più basso = meglio (tranne accuratezza).",
        "",
        f"Copertura xG: {xg_cov[0]}/{xg_cov[1]} partite dal 2014/15 abbinate a Understat "
        f"({xg_cov[0] / xg_cov[1] * 100:.2f}%).",
        "",
        "## Confronto tra modelli",
        "",
        "| Campionato | Modello | N | Log-loss | RPS | Brier | Accuratezza |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for scope_name, model, m in rows:
        lines.append(f"| {scope_name} | {model} | {m['n']} | {m['logloss']:.4f} | {m['rps']:.4f} | "
                     f"{m['brier']:.4f} | {m['acc'] * 100:.1f}% |")
    lines += ["", "\\* Righe di controllo: servono a separare l'effetto delle feature nuove da quello "
              "della semplice ricalibrazione (DC ricalibrato) e della finestra di training più corta "
              "(stack senza xG dal 2016/17).", ""]

    # ── bootstrap a blocchi per settimana ─────────────────────────────────────
    weeks = ev.date.dt.strftime("%G-%V").values
    n_weeks = len(set(weeks))
    lines += ["## Differenza di log-loss (positivo = il secondo modello è migliore)", "",
              f"Bootstrap a blocchi per settimana ISO (tutte le leghe della stessa settimana "
              f"restano insieme), {N_BOOT} ricampionamenti, IC 95% percentile.", "",
              "| Confronto | Δ log-loss | IC 95% | Settimane |",
              "|---|---:|---|---:|"]
    comparisons = [
        (f"{M_PROD} → {M_XG}", M_PROD, M_XG),
        (f"{M_CTRL} → {M_XG}", M_CTRL, M_XG),
        (f"{M_XG} → {M_XGR}", M_XG, M_XGR),
        (f"{M_PROD} → {M_XGR}", M_PROD, M_XGR),
        (f"{M_DC} → {M_XGR}", M_DC, M_XGR),
        (f"{M_DC} → {M_PROD}", M_DC, M_PROD),
        (f"{M_DC} → {M_XG}", M_DC, M_XG),
    ]
    boot = {}
    for label, a, b in comparisons:
        d = ll_vec[a] - ll_vec[b]
        mask = np.isfinite(d)
        mean, (lo, hi) = block_bootstrap(d[mask], weeks[mask])
        boot[(a, b)] = (mean, lo, hi)
        lines.append(f"| {label} | {mean:+.4f} | [{lo:+.4f}, {hi:+.4f}] | {n_weeks} |")
    lines.append("")

    # ── per stagione ──────────────────────────────────────────────────────────
    lines += ["## Per stagione (log-loss)", "",
              "| Stagione | N | Quote medie | DC attuale | Stack senza xG | Stack + xG | Stack + xG ridge | Δ (senza xG − con xG) | Δ (xG − xG ridge) |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    xg_better, stack_better, worse_notes, ridge_better = [], [], [], []
    for s in sorted(ev.season.unique()):
        m = (ev.season == s).to_numpy()
        a, b, c, d_ = (ll_vec[M_MKT][m].mean(), ll_vec[M_DC][m].mean(),
                       ll_vec[M_PROD][m].mean(), ll_vec[M_XG][m].mean())
        xg_better.append(d_ < c)
        stack_better.append(c < b)
        r_ = ll_vec[M_XGR][m].mean()
        ridge_better.append(r_ < d_)
        lines.append(f"| {s}/{(s + 1) % 100:02d} | {m.sum()} | {a:.4f} | {b:.4f} | {c:.4f} | {d_:.4f} | {r_:.4f} | "
                     f"{c - d_:+.4f} | {d_ - r_:+.4f} |")
        if d_ >= c:
            diff = (ll_vec[M_PROD] - ll_vec[M_XG])[m]
            se = diff.std(ddof=1) / np.sqrt(m.sum())
            worse_notes.append(f"{s}/{(s + 1) % 100:02d}: Δ {c - d_:+.4f} su {m.sum()} partite "
                               f"(errore standard ±{se:.4f}, {abs(c - d_) / se:.1f} errori standard)")
    lines.append("")
    if worse_notes:
        lines += ["Stagioni in cui l'xG non migliora (Δ ≤ 0): " + "; ".join(worse_notes) + ".", ""]

    # ── stagione in corso e neopromosse ───────────────────────────────────────
    cur_m = (ev.season == cur).to_numpy()
    teams_by = {(dv, ss): set(g.HomeTeam) | set(g.AwayTeam) for (dv, ss), g in feat.groupby(["Division", "season"])}
    prev = lambda dv, ss: teams_by.get((dv, ss - 1), set())
    promoted = np.array([(h not in prev(dv, ss)) or (a not in prev(dv, ss))
                         for dv, ss, h, a in zip(ev.Division, ev.season, ev.HomeTeam, ev.AwayTeam)])
    early = ev.date.dt.month.isin([8, 9]).to_numpy()

    def sub_row(label, m):
        if not m.any():
            return None
        cols_ = [ll_vec[k][m].mean() for k in (M_PROD, M_XG, M_XGR)]
        diff = (ll_vec[M_XG] - ll_vec[M_XGR])[m]
        se = diff.std(ddof=1) / np.sqrt(m.sum()) if m.sum() > 1 else float("nan")
        return (f"| {label} | {m.sum()} | {cols_[0]:.4f} | {cols_[1]:.4f} | {cols_[2]:.4f} | "
                f"{cols_[1] - cols_[2]:+.4f} (±{se:.4f}) |")

    lines += ["## Stagione in corso e neopromosse (log-loss)", "",
              "Neopromossa = squadra assente dallo stesso campionato nella stagione precedente. "
              "Tra parentesi l'errore standard del Δ (xG − xG ridge).", "",
              "| Sottoinsieme | N | Stack senza xG | Stack + xG | Stack + xG ridge | Δ (xG − xG ridge) |",
              "|---|---:|---:|---:|---:|---:|"]
    for label, m in ((f"{cur}/{(cur + 1) % 100:02d} (stagione in corso)", cur_m),
                     (f"{cur}/{(cur + 1) % 100:02d} con ridge, solo partite con neopromosse", cur_m & promoted),
                     ("Tutte le stagioni, neopromosse ad agosto-settembre", early & promoted),
                     ("Tutte le stagioni, resto delle partite", ~(early & promoted))):
        row_ = sub_row(label, m)
        if row_:
            lines.append(row_)
    lines.append("")

    # ── check di accettazione ─────────────────────────────────────────────────
    get = lambda model: next(m for s, mod, m in rows if s == "Tutti" and mod == model)
    dc_all, mk_all, st_all = get(M_DC)["logloss"], get(M_MKT)["logloss"], get(M_PROD)["logloss"]
    xg_all = get(M_XG)["logloss"]
    xgr_all = get(M_XGR)["logloss"]
    gain, lo, hi = boot[(M_PROD, M_XG)]
    rgain, rlo, rhi = boot[(M_XG, M_XGR)]
    checks = [
        ("Step 1 — DC attuale", f"{dc_all:.4f} (atteso {ACCEPT_DC[0]} ± {ACCEPT_DC[1]})",
         abs(dc_all - ACCEPT_DC[0]) <= ACCEPT_DC[1]),
        ("Step 1 — quote", f"{mk_all:.4f} (atteso {ACCEPT_MARKET[0]} ± {ACCEPT_MARKET[1]})",
         abs(mk_all - ACCEPT_MARKET[0]) <= ACCEPT_MARKET[1]),
        ("Step 3 — stack senza xG ≤ 0.987", f"{st_all:.4f}", st_all <= ACCEPT_STACK_MAX),
        ("Step 3 — stack migliore del DC in ogni stagione",
         f"{sum(stack_better)}/{len(stack_better)} stagioni", all(stack_better)),
        ("Step 7.1 — abbinamento nomi xG (≥ 99% delle partite)",
         f"{xg_cov[0] / xg_cov[1] * 100:.2f}%", xg_cov[0] / xg_cov[1] >= 1 - understat.MAX_UNMATCHED),
        (f"Step 7.1 — guadagno xG ≥ +{ACCEPT_XG_MIN_GAIN} (atteso circa +0.002/+0.003)",
         f"{gain:+.4f} (stack {st_all:.4f} → {xg_all:.4f})", gain >= ACCEPT_XG_MIN_GAIN),
        ("Step 7.1 — IC 95% del guadagno xG esclude lo zero", f"[{lo:+.4f}, {hi:+.4f}]", lo > 0),
        ("Step 7.1 — stack + xG migliore in ogni stagione",
         f"{sum(xg_better)}/{len(xg_better)} stagioni", all(xg_better)),
        (f"Ridge xG — guadagno ≥ +{ACCEPT_RIDGE_MIN_GAIN} (atteso circa +0.0007)",
         f"{rgain:+.4f} (stack + xG {xg_all:.4f} → con ridge {xgr_all:.4f})", rgain >= ACCEPT_RIDGE_MIN_GAIN),
        ("Ridge xG — IC 95% del guadagno esclude lo zero", f"[{rlo:+.4f}, {rhi:+.4f}]", rlo > 0),
        ("Ridge xG — migliore in ogni stagione (informativo)",
         f"{sum(ridge_better)}/{len(ridge_better)} stagioni", all(ridge_better)),
    ]
    lines += ["## Check di accettazione", ""]
    for label, value, passed in checks:
        lines.append(f"- {label}: {value} → {'OK' if passed else 'NON SUPERATO'}")
    lines.append("")

    text = "\n".join(lines)
    print("\n" + text)
    with open(RESULTS_PATH, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"Salvato in {RESULTS_PATH}")
    if not all(p for _, _, p in checks):
        print("\n⚠ Almeno un check di accettazione non è superato.")
        sys.exit(2)


if __name__ == "__main__":
    main()
