"""Round 5 — assemblaggio di backtest/results_round5.md."""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import pandas as pd

from backtest import round3_ctx as C3

HERE = os.path.dirname(os.path.abspath(__file__))
P5 = os.path.join(HERE, "round5_parts")


def row(label, r, base_ll):
    nb = r["nb"]
    return (f"| {label} | {nb['base']:.4f} → {nb['var']:.4f} | {nb['d']:+.5f} [{nb['lo']:+.5f}, {nb['hi']:+.5f}] | [{nb['lob']:+.5f}, {nb['hib']:+.5f}] | "
            f"{r['nb_val']['d']:+.5f} | {r['nb_held']['d']:+.5f} [{r['nb_held']['lob']:+.5f}, {r['nb_held']['hib']:+.5f}] | {r['ou']['d']:+.5f} | "
            f"{r['mae']['d']:+.4f} | {r['corr_team']['d']:+.4f} | {r['corr_total']['d']:+.4f} |")


def main():
    G = pd.read_pickle(os.path.join(C3.R3_DIR, "r5_G.pkl"))
    ch = G["chosen"]
    S = ["## Tabella riassuntiva", "",
         f"{G['n_ev']} partite di test (2019/20 → 2026-10-12). Δ = baseline − variante per le perdite (log-loss del totale, Over/Under, MAE), "
         "variante − baseline per le correlazioni; positivo = variante migliore. Validazione = 2019/20-2021/22, held-out = 2022/23 →. "
         "Per le statistiche attese non esiste un riferimento di mercato nei dati: la colonna «distanza dalle quote di chiusura» non si applica.", "",
         "| Variante | Log-loss totale (base → var.) | Δ tutte [IC per partita] | IC a blocchi | Δ validazione | Δ held-out [IC a blocchi] | Δ Over/Under | Δ MAE | Δ corr. squadra | Δ corr. totale |",
         "|---|---|---|---|---:|---|---:|---:|---:|---:|",
         row(f"**G1 — gialli, arbitro forma {ch[0]}, k={ch[1]} (scelta)**", G["res"][ch], 0),
         row("G1 — gialli, forma a (moltiplicativa), k=20", G["res"][("a", 20)], 0),
         row("G1 — gialli, forma b, k=5 (shrinkage minimo)", G["res"][("b", 5)], 0),
         row("G1 — gialli, forma b, k=80 (shrinkage massimo)", G["res"][("b", 80)], 0),
         row("G2 — gialli + arbitro sui falli (b, k=20)", G["g2"], 0),
         row("Placebo — arbitri permutati (b, k=20)", G["placebo"], 0),
         row("**H — corner con arbitro (controllo, b, k=20)**", G["corner"], 0), "",
         f"Verdetto G (regola scritta prima: Δ held-out sul totale gialli > 0 con IC a blocchi che esclude lo zero): **{G['verdict']}**. "
         f"Controllo H: {'distinguibile da zero (vedi commento)' if G['flag'] else 'non distinguibile da zero'}.", ""]
    parts = [open(os.path.join(P5, fn), encoding="utf-8").read() for fn in ("prereg.md", "G.md", "H2.md", "futuri.md")]
    cm = open(os.path.join(P5, "commento.md"), encoding="utf-8").read()
    head = ["# Round 5 — arbitro nel modello dei cartellini (G) e controllo sui corner (H), solo backtest", "",
            "**Nulla della produzione è stato toccato.** Dati: tabella `games` di Transfermarkt (arbitro) e CSV di football-data.co.uk. "
            "Stesse regole dei round 3-4: criteri scritti prima, validazione 2019/20-2021/22, held-out dal 2022/23, IC bootstrap per partita e a blocchi per settimana ISO.",
            "", "---", ""]
    with open(os.path.join(HERE, "results_round5.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(head) + "\n\n".join(parts) + "\n\n" + "\n".join(S) + "\n" + cm)
    print("\n".join(S))


if __name__ == "__main__":
    main()
