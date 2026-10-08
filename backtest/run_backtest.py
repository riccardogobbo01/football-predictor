#!/usr/bin/env python3
"""
Backtest walk-forward (Step 1-3 del piano): quote vs Dixon-Coles vs Poisson-stack.

Rifit del Dixon-Coles ogni 7 giorni con SOLO partite precedenti (finestra 5 anni,
xi=0.0018). Lo stack è stimato stagione per stagione sulle sole stagioni precedenti
(dal 2013/14). Test dalla stagione 2019/20 alla corrente; tutti i modelli sono
valutati sulle stesse partite (quelle con quote medie valide).

Uso (dalla root del repo):
  python -m backtest.run_backtest              # completo (serve ClubElo)
  python -m backtest.run_backtest --no-elo     # senza le righe che usano l'Elo
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

from backtest import data, models, features, stack, elo

TEST_START = "2019-07-01"
FIRST_TEST_SEASON = 2019
N_BOOT = 5000

ACCEPT_DC = (0.994, 0.004)
ACCEPT_MARKET = (0.973, 0.004)
ACCEPT_STACK_MAX = 0.987

RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.md")

BASE = ["dc_lmu", "dc_lnu"]
STACK_SETS = {
    "DC ricalibrato (stack su dc_lmu, dc_lnu) *": BASE,
    "DC + Elo": BASE + ["elo_diff"],
    "DC + pi-ratings": BASE + ["pi_gd", "pi_diff"],
    "DC + Elo + pi-ratings": BASE + ["elo_diff", "pi_gd", "pi_diff"],
    "Poisson-stack completo": stack.STACK_FEATURES,
}


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
    ap.add_argument("--no-elo", action="store_true")
    ap.add_argument("--rebuild", action="store_true")
    args = ap.parse_args()
    use_elo = not args.no_elo

    print("Caricamento dati (football-data.co.uk)...")
    df = data.load_matches()

    print("Feature walk-forward (DC gol, DC tiri in porta, pi-ratings)...")
    feat = features.build_features(df, rebuild=args.rebuild)

    if use_elo:
        print("Elo (ClubElo)...")
        try:
            feat = elo.add_elo(feat, strict=True)
        except RuntimeError as e:
            print(f"\n✗ Elo non disponibile:\n{e}")
            print("  Rilancia più tardi, oppure usa --no-elo per le righe senza Elo.")
            sys.exit(3)
    else:
        feat = feat.assign(elo_diff=np.nan)

    test = feat[feat.date >= pd.Timestamp(TEST_START)]
    ok = _valid_odds(test, "odds")
    ev = test[ok].copy()
    print(f"  {len(test)} partite di test, {len(ev)} con quote medie valide")

    P_mkt = models.market_probs(ev.odds_h.values, ev.odds_d.values, ev.odds_a.values, "power")
    cl_ok = _valid_odds(ev, "cl")
    P_cl = np.full((len(ev), 3), np.nan)
    P_cl[cl_ok] = models.market_probs(ev.cl_h.values[cl_ok], ev.cl_d.values[cl_ok],
                                      ev.cl_a.values[cl_ok], "power")

    preds = {
        "Quote medie senza margine (power)": (P_mkt, np.ones(len(ev), bool)),
        "Quote chiusura senza margine (power)": (P_cl, cl_ok),
        "Dixon-Coles attuale (xi=0.0018)": (ev[["dc_pH", "dc_pD", "dc_pA"]].to_numpy(), np.ones(len(ev), bool)),
    }
    sets = dict(STACK_SETS)
    if not use_elo:
        sets["Poisson-stack senza Elo"] = [f for f in stack.STACK_FEATURES if f != "elo_diff"]
    full = "Poisson-stack completo" if use_elo else "Poisson-stack senza Elo"
    for name, cols in sets.items():
        if "elo_diff" in cols and not use_elo:
            continue
        print(f"  stack: {name}")
        sp = stack.walk_forward_stack(feat, cols, FIRST_TEST_SEASON).reindex(ev.index)
        preds[name] = (sp[["pH", "pD", "pA"]].to_numpy(), sp.pH.notna().to_numpy())

    y_all = ev.res.values
    ll_vec, rows = {}, []

    def scope_masks():
        yield "Tutti", np.ones(len(ev), bool)
        for code, name in data.LEAGUE_NAMES.items():
            yield name, (ev.Division == code).to_numpy()

    for scope, smask in scope_masks():
        for model, (P, valid) in preds.items():
            m = smask & valid
            if not m.any():
                continue
            met, ll = models.metrics(P[m], y_all[m])
            rows.append((scope, model, met))
            if scope == "Tutti":
                v = np.full(len(ev), np.nan); v[m] = ll
                ll_vec[model] = v

    lines = [
        "# Backtest walk-forward — Step 1-3",
        "",
        f"Test: {ev.date.min().date()} → {ev.date.max().date()} "
        f"(stagioni 2019/20 → {data.current_season()}/{(data.current_season() + 1) % 100:02d}), "
        f"{len(ev)} partite con quote medie valide. DC rifittato ogni 7 giorni (finestra 5 anni, "
        f"xi=0.0018); stack stimato stagione per stagione sulle sole stagioni precedenti "
        f"(dal 2013/14), 5 campionati insieme. Più basso = meglio (tranne accuratezza).",
        "",
        "## Confronto tra modelli",
        "",
        "| Campionato | Modello | N | Log-loss | RPS | Brier | Accuratezza |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for scope, model, m in rows:
        lines.append(f"| {scope} | {model} | {m['n']} | {m['logloss']:.4f} | {m['rps']:.4f} | "
                     f"{m['brier']:.4f} | {m['acc'] * 100:.1f}% |")
    lines += ["", "\\* Riga aggiuntiva: lo stack con le sole due feature del DC. Serve a separare "
              "l'effetto della semplice ricalibrazione da quello delle feature nuove.", ""]
    if not use_elo:
        lines += ["_Run con `--no-elo`: **le righe DC + Elo e Poisson-stack completo mancano** (api.clubelo.com rispondeva 502). Rigenerare con `python -m backtest.run_backtest` quando ClubElo è raggiungibile; qui 'Poisson-stack senza Elo' usa le 6 feature restanti._", ""]

    # ── bootstrap a blocchi per settimana ─────────────────────────────────────
    weeks = ev.date.dt.strftime("%G-%V").values
    dc_ll = ll_vec["Dixon-Coles attuale (xi=0.0018)"]
    lines += ["## Differenza di log-loss (positivo = lo stack è migliore)", "",
              f"Bootstrap a blocchi per settimana ISO (tutte le leghe della stessa settimana "
              f"restano insieme), {N_BOOT} ricampionamenti, IC 95% percentile.", "",
              "| Confronto | Δ log-loss | IC 95% | Settimane |",
              "|---|---:|---|---:|"]
    n_weeks = len(set(weeks))
    comparisons = [(f"DC attuale − {full}", dc_ll, ll_vec[full])]
    recal = "DC ricalibrato (stack su dc_lmu, dc_lnu) *"
    comparisons.append((f"DC ricalibrato − {full}", ll_vec[recal], ll_vec[full]))
    for label, base_ll, new_ll in comparisons:
        d = base_ll - new_ll
        mask = np.isfinite(d)
        mean, (lo, hi) = block_bootstrap(d[mask], weeks[mask])
        lines.append(f"| {label} | {mean:+.4f} | [{lo:+.4f}, {hi:+.4f}] | {n_weeks} |")
    lines.append("")

    # ── per stagione ──────────────────────────────────────────────────────────
    lines += ["## Per stagione (log-loss)", "",
              f"| Stagione | N | Quote medie | DC attuale | {full} | Δ (DC − stack) |",
              "|---|---:|---:|---:|---:|---:|"]
    seasons_better = []
    mk_ll = ll_vec["Quote medie senza margine (power)"]
    for s in sorted(ev.season.unique()):
        m = (ev.season == s).to_numpy()
        a, b, c = mk_ll[m].mean(), dc_ll[m].mean(), ll_vec[full][m].mean()
        seasons_better.append(c < b)
        lines.append(f"| {s}/{(s + 1) % 100:02d} | {m.sum()} | {a:.4f} | {b:.4f} | {c:.4f} | {b - c:+.4f} |")
    lines.append("")

    # ── check di accettazione ─────────────────────────────────────────────────
    get = lambda model: next(m for s, mod, m in rows if s == "Tutti" and mod == model)
    dc_all = get("Dixon-Coles attuale (xi=0.0018)")["logloss"]
    mk_all = get("Quote medie senza margine (power)")["logloss"]
    st_all = get(full)["logloss"]
    checks = [
        ("Step 1 — DC attuale", f"{dc_all:.4f} (atteso {ACCEPT_DC[0]} ± {ACCEPT_DC[1]})",
         abs(dc_all - ACCEPT_DC[0]) <= ACCEPT_DC[1]),
        ("Step 1 — quote", f"{mk_all:.4f} (atteso {ACCEPT_MARKET[0]} ± {ACCEPT_MARKET[1]})",
         abs(mk_all - ACCEPT_MARKET[0]) <= ACCEPT_MARKET[1]),
        ("Step 3 — stack ≤ 0.987", f"{st_all:.4f}", st_all <= ACCEPT_STACK_MAX),
        ("Step 3 — stack migliore del DC in ogni stagione",
         f"{sum(seasons_better)}/{len(seasons_better)} stagioni", all(seasons_better)),
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
