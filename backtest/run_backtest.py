#!/usr/bin/env python3
"""
Backtest walk-forward (Step 1 del piano): Dixon-Coles attuale vs quote senza margine.

Rifit ogni 7 giorni usando SOLO partite precedenti alla data di taglio, finestra di
5 anni, xi = 0.0018. Test dalla stagione 2019/20 alla corrente. I due modelli sono
confrontati sulle stesse partite (quelle con quote medie valide).

Uso (dalla root del repo):
  python -m backtest.run_backtest
  python backtest/run_backtest.py
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import numpy as np
import pandas as pd

from backtest import data, models

XI = 0.0018
YEARS_WINDOW = 5
STEP_DAYS = 7
TEST_START = "2019-07-01"

ACCEPT_DC = (0.994, 0.004)       # (valore atteso, tolleranza) log-loss DC attuale
ACCEPT_MARKET = (0.973, 0.004)   # (valore atteso, tolleranza) log-loss quote

RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.md")


def _valid_odds(df, prefix):
    cols = [f"{prefix}_h", f"{prefix}_d", f"{prefix}_a"]
    o = df[cols].to_numpy(dtype=float)
    return np.isfinite(o).all(1) & (o > 1).all(1)


def _eval(P, y):
    m, _ = models.metrics(P, y)
    return m


def main():
    print("Caricamento dati (football-data.co.uk)...")
    df = data.load_matches()

    print(f"Walk-forward Dixon-Coles (xi={XI}, finestra {YEARS_WINDOW} anni, "
          f"rifit ogni {STEP_DAYS} giorni, test da {TEST_START})...")
    wf = models.walk_forward_dc(df, XI, years_window=YEARS_WINDOW, step_days=STEP_DAYS,
                                start=TEST_START)
    wf = models.add_dc_probs(wf)
    test = df.loc[wf.index].join(wf)
    print(f"  {len(test)} partite di test previste")

    ok = _valid_odds(test, "odds")
    cl_ok = ok & _valid_odds(test, "cl")
    n_no_odds = int((~ok).sum())
    ev = test[ok].copy()
    print(f"  {len(ev)} con quote medie valide ({n_no_odds} escluse per quote mancanti)")

    P_mkt = models.market_probs(ev.odds_h.values, ev.odds_d.values, ev.odds_a.values, "power")
    ev[["mH", "mD", "mA"]] = P_mkt
    ev_cl = test[cl_ok].copy()
    P_cl = models.market_probs(ev_cl.cl_h.values, ev_cl.cl_d.values, ev_cl.cl_a.values, "power")

    rows = []

    def add_rows(label_scope, sub, sub_cl, P_cl_sub):
        y = sub.res.values
        rows.append((label_scope, "Quote medie senza margine (power)",
                     _eval(sub[["mH", "mD", "mA"]].to_numpy(), y)))
        rows.append((label_scope, "Dixon-Coles attuale (xi=0.0018)",
                     _eval(sub[["pH", "pD", "pA"]].to_numpy(), y)))
        if len(sub_cl):
            rows.append((label_scope, "Quote chiusura senza margine (power) *",
                         _eval(P_cl_sub, sub_cl.res.values)))

    add_rows("Tutti", ev, ev_cl, P_cl)
    for code, name in data.LEAGUE_NAMES.items():
        sel = (ev.Division == code).values
        sel_cl = (ev_cl.Division == code).values
        add_rows(name, ev[sel], ev_cl[sel_cl], P_cl[sel_cl])

    lines = [
        "# Backtest walk-forward — Step 1",
        "",
        f"Test: {ev.date.min().date()} → {ev.date.max().date()} "
        f"(stagioni 2019/20 → {data.current_season()}/{(data.current_season() + 1) % 100:02d}), "
        f"{len(ev)} partite con quote medie valide. Rifit ogni {STEP_DAYS} giorni, "
        f"finestra {YEARS_WINDOW} anni, xi={XI}. Più basso = meglio (tranne accuratezza).",
        "",
        "| Campionato | Modello | N | Log-loss | RPS | Brier | Accuratezza |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for scope, model, m in rows:
        lines.append(f"| {scope} | {model} | {m['n']} | {m['logloss']:.4f} | {m['rps']:.4f} | "
                     f"{m['brier']:.4f} | {m['acc'] * 100:.1f}% |")
    lines += ["", "\\* Le quote di chiusura sono valutate sulle partite che le hanno (N può differire).", ""]

    dc_all = next(m for s, mod, m in rows if s == "Tutti" and mod.startswith("Dixon"))
    mk_all = next(m for s, mod, m in rows if s == "Tutti" and mod.startswith("Quote medie"))
    dc_pass = abs(dc_all["logloss"] - ACCEPT_DC[0]) <= ACCEPT_DC[1]
    mk_pass = abs(mk_all["logloss"] - ACCEPT_MARKET[0]) <= ACCEPT_MARKET[1]
    lines += [
        "## Check di accettazione",
        "",
        f"- Dixon-Coles attuale: log-loss {dc_all['logloss']:.4f} "
        f"(atteso {ACCEPT_DC[0]} ± {ACCEPT_DC[1]}) → {'OK' if dc_pass else 'FUORI RANGE'}",
        f"- Quote senza margine: log-loss {mk_all['logloss']:.4f} "
        f"(atteso {ACCEPT_MARKET[0]} ± {ACCEPT_MARKET[1]}) → {'OK' if mk_pass else 'FUORI RANGE'}",
        "",
    ]

    text = "\n".join(lines)
    print("\n" + text)
    with open(RESULTS_PATH, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"Salvato in {RESULTS_PATH}")

    if not (dc_pass and mk_pass):
        print("\n⚠ CHECK DI ACCETTAZIONE NON SUPERATO — fermarsi e verificare leakage/parsing.")
        sys.exit(2)


if __name__ == "__main__":
    main()
