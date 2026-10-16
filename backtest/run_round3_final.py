"""Round 3 — assemblaggio di backtest/results_round3.md (criteri, A-D, tabella riassuntiva, commento)."""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import round3_ctx as C3

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results_round3.md")


def main():
    c = C3.get_ctx3()
    P = c.base_sp[["pH", "pD", "pA"]].to_numpy()
    from backtest.round2_lib import ll_vec
    base_ll = float(ll_vec(P, c.y).mean())
    cl = C3.closing_logloss(c)
    gap = base_ll - cl
    A = pd.read_pickle(os.path.join(C3.R3_DIR, "r3_A.pkl"))
    B = pd.read_pickle(os.path.join(C3.R3_DIR, "r3_B.pkl"))
    Cc = pd.read_pickle(os.path.join(C3.R3_DIR, "r3_C.pkl"))
    D = pd.read_pickle(os.path.join(C3.R3_DIR, "r3_D.pkl"))
    for r in Cc["res"]:
        r["name"] = "C — " + r["name"]
    rows = [A["res"][k] for k in ("A1", "A2", "A3", "A4")] + B["res"] + Cc["res"] + [r for r in D["res"] if r["name"] == D["chosen"]]
    names = {}
    for r in rows:
        names[r["name"]] = r
    S = ["## Tabella riassuntiva", "",
         f"Baseline = modello in produzione v6-eloodds (with_xg): log-loss **{base_ll:.4f}** su {len(c.y)} partite 2019/20 → 2026-10-12. "
         f"Quote di chiusura senza margine (power) = **{cl:.4f}**; divario baseline − chiusura = {gap:.4f}. Δ = baseline − variante "
         "(positivo = variante migliore). Validazione = 2019/20-2021/22 (dove si scelgono i parametri), held-out = 2022/23 → oggi. "
         "Per D è riportata la sola configurazione scelta sulle validazione (le altre 7 sono nella sezione D).", "",
         "| Variante | Log-loss | Δ tutte [IC per partita] | IC a blocchi | Δ validazione | Δ held-out [IC a blocchi] | Stagioni migliorate | Distanza dalla chiusura | Divario recuperato |",
         "|---|---:|---|---|---:|---|---:|---:|---:|",
         f"| *Quote di chiusura (power)* | {cl:.4f} | — | — | — | — | — | 0.0000 | 100% |",
         f"| **Baseline v6-eloodds** | {base_ll:.4f} | — | — | — | — | — | {gap:+.4f} | 0% |"]
    for r in rows:
        a, v, h = r["all"], r["val"], r["held"]
        S.append(f"| {r['name']} | {r['ll']:.4f} | {a['d']:+.5f} [{a['lo']:+.5f}, {a['hi']:+.5f}] | [{a['lob']:+.5f}, {a['hib']:+.5f}] | "
                 f"{v['d']:+.5f} | {h['d']:+.5f} [{h['lob']:+.5f}, {h['hib']:+.5f}] | {r['seasons_better'][0]}/{r['seasons_better'][1]} | "
                 f"{r['ll'] - cl:+.4f} | {a['d'] / gap * 100:.1f}% |")
    S.append("")
    parts = []
    for fn in ("prereg.md", "A.md", "B.md", "C.md", "D.md"):
        with open(os.path.join(C3.PARTS, fn), encoding="utf-8") as fh:
            parts.append(fh.read())
    commento = ""
    cp = os.path.join(C3.PARTS, "commento.md")
    if os.path.exists(cp):
        commento = open(cp, encoding="utf-8").read()
    head = ["# Round 3 — esperimenti sul modello dei campionati (solo backtest)", "",
            "**Nulla della produzione è stato toccato.** Codice in `backtest/round3_*.py`, `backtest/run_round3_*.py`, "
            "`backtest/eloodds`-derivati solo in lettura, `backtest/transfermarkt.py` e `backtest/transfermarkt_aliases.py`. "
            "Stesse regole del round 2: stesse 12.751 partite per tutte le varianti, bootstrap appaiato con 5000 ricampionamenti, "
            "IC 95% percentile sia per partita sia a blocchi per settimana ISO.", "", "---", ""]
    text = "\n".join(head) + "\n\n".join(parts) + "\n\n" + "\n".join(S) + "\n" + commento
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("\n".join(S))


if __name__ == "__main__":
    main()
