"""Round 3 — Esperimento D: valore della rosa Transfermarkt (solo backtest).
Da lanciare in modalità isolata:  python -I backtest/run_round3_D.py   (legge file scaricati: nessun import dalla cartella dati)."""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import data, round2_ctx as C2, round3_ctx as C3, stack, transfermarkt as TM
from backtest.round2_lib import run_stack

TIE = 0.0002
COLS = stack.XG_FEATURES_EO
GRID = [(md, w, f) for md in ("jul", "aug") for w in (240, 365) for f in ("F1", "F2")]     # ordine di semplicità: F1 prima di F2
MD = {"jul": (7, 1), "aug": (8, 1)}


def subsets(df, ev):
    """Neopromosse / restanti prime 8 giornate / resto, per le partite di ev (insiemi disgiunti)."""
    teams_by = {(dv, s): set(g.HomeTeam) | set(g.AwayTeam) for (dv, s), g in df.groupby(["Division", "season"])}
    prev = lambda dv, s: teams_by.get((dv, s - 1), set())
    promoted = np.array([(h not in prev(dv, s)) or (a not in prev(dv, s))
                         for dv, s, h, a in zip(ev.Division, ev.season, ev.HomeTeam, ev.AwayTeam)])
    d = df.sort_values("date", kind="stable")
    long = pd.concat([d[["Division", "season", "date", "HomeTeam"]].rename(columns={"HomeTeam": "t"}).assign(idx=d.index, side="h"),
                      d[["Division", "season", "date", "AwayTeam"]].rename(columns={"AwayTeam": "t"}).assign(idx=d.index, side="a")])
    long = long.sort_values(["date"], kind="stable")
    long["k"] = long.groupby(["Division", "season", "t"]).cumcount() + 1
    kh = long[long.side == "h"].set_index("idx").k
    ka = long[long.side == "a"].set_index("idx").k
    early = ((kh.reindex(ev.index) <= 8) & (ka.reindex(ev.index) <= 8)).to_numpy()
    s1 = promoted
    s2 = ~promoted & early
    s3 = ~promoted & ~early
    return {"neopromosse (almeno una squadra)": s1, "restanti prime 8 giornate": s2, "resto": s3}


def main():
    c = C3.get_ctx3()
    df, feat, ev = c.df, c.feat, c.ev
    pv = TM.load_valuations()
    L = ["## Esperimento D — Valore della rosa Transfermarkt", ""]
    TM.check_aliases(df)
    L += ["Dati: dataset dcaribou/transfermarkt-datasets (file `player_valuations.csv.gz`, `clubs.csv.gz`, `players.csv.gz`, "
          "`competitions.csv.gz`, scaricati il 2026-10-16 dal bucket pubblico del progetto, ultima modifica 2026-09-05; ultima "
          f"valutazione nei dati: {pv.date.max().date()}). Abbinamento nomi: tabella esplicita `backtest/transfermarkt_aliases.py` "
          "(176 squadre dei 5 campionati dal 2012/13; controllo di copertura superato: nessuna squadra senza alias).", ""]

    tabs, res = {}, []
    P_cache = {}
    for md, w, f in GRID:
        key = (md, w)
        if key not in tabs:
            tabs[key] = TM.team_table(df, pv, MD[md], w)
        T = tabs[key]
        mf = TM.match_features(df, T, chg=(f == "F2")).reindex(feat.index)
        fr = feat.copy()
        for col in mf.columns:
            fr[col] = mf[col]
        cols = COLS + list(mf.columns)
        sp = run_stack(fr, cols, ev)
        name = f"D — data {md}, finestra {w} g, {f}"
        C2.reg_save("R3 " + name, sp)
        r = C3.compare3(sp[["pH", "pD", "pA"]].to_numpy(), c, name)
        res.append(r)
        print(name, f"{r['all']['d']:+.5f}", flush=True)

    # copertura
    T0 = tabs[("aug", 365)]
    test_T = T0[T0.season >= 2019]
    L += ["### Copertura e affidabilità dei valori (data 1 agosto, finestra 365 giorni)", "",
          f"Club-stagione 2019/20 → oggi: {len(test_T)}; non affidabili (< {TM.MIN_VALUED} giocatori valutati): "
          f"{int((~test_T.reliable).sum())}.", "",
          "| Lega | club-stagione non affidabili (2019/20 →) |", "|---|---|"]
    for lg in data.LEAGUES:
        g = test_T[(test_T.Division == lg) & ~test_T.reliable]
        L.append(f"| {data.LEAGUE_NAMES[lg]} | " + (", ".join(f"{r.team} {C2.season_label(r.season)} ({r.n})" for r in g.itertuples()) or "—") + " |")
    L += ["", f"Giocatori valutati per club (mediana tra club affidabili): {int(test_T[test_T.reliable].n.median())}; "
              f"valore mediano di una rosa: {test_T.value.median() / 1e6:.0f} M€.", ""]

    best_val = max(r["val"]["d"] for r in res)
    chosen = next(r for r in res if r["val"]["d"] >= best_val - TIE)
    L += ["### Griglia di 8 configurazioni (ogni riga da sola vs baseline v6)", ""] + C3.md_table(res) + [""]
    L += [f"Scelta sulle validazione (parità entro {TIE} → la più semplice): **{chosen['name']}** (Δ validazione {chosen['val']['d']:+.5f}). "
          f"Verdetto: **{C3.verdict(chosen)}**.", ""]
    L += C3.md_detail(chosen)

    # sottoinsiemi
    sub = subsets(df, ev)
    d = chosen["d_vec"]
    L += ["### Guadagno per sottoinsieme (variante scelta)", "",
          "Insiemi disgiunti: (1) partite con almeno una neopromossa (squadra assente dallo stesso campionato nella stagione precedente); "
          "(2) restanti partite in cui entrambe le squadre hanno giocato meno di 8 partite nella stagione (prime 8 giornate); (3) resto.", "",
          "| Sottoinsieme | N | Δ log-loss | IC 95% per partita | IC 95% a blocchi | Δ held-out |", "|---|---:|---:|---|---|---:|"]
    for lab, m in sub.items():
        mm, lo, hi = C3.ci_match(d[m])
        _, lob, hib = C3.ci_block(d[m], c.weeks[m])
        held = m & ~c.is_val
        L.append(f"| {lab} | {int(m.sum())} | {mm:+.5f} | [{lo:+.5f}, {hi:+.5f}] | [{lob:+.5f}, {hib:+.5f}] | {d[held].mean():+.5f} |")
    L.append("")
    with open(os.path.join(C3.PARTS, "D.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    pd.to_pickle(dict(res=[{k: v for k, v in r.items() if k not in ("d_vec", "ok")} for r in res], chosen=chosen["name"]),
                 os.path.join(C3.R3_DIR, "r3_D.pkl"))
    print("\n".join(L))


if __name__ == "__main__":
    main()
