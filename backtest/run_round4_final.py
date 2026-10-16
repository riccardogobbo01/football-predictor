"""Round 4 — assemblaggio di backtest/results_round4.md."""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import round3_ctx as C3
from backtest.round2_lib import ll_vec

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    c = C3.get_ctx3()
    P = c.base_sp[["pH", "pD", "pA"]].to_numpy()
    base_ll = float(ll_vec(P, c.y).mean())
    cl = C3.closing_logloss(c)
    gap = base_ll - cl
    E = pd.read_pickle(os.path.join(C3.R3_DIR, "r4_E.pkl"))
    F = pd.read_pickle(os.path.join(C3.R3_DIR, "r4_F.pkl"))
    S = ["## Tabella riassuntiva", "",
         "### E — campionati (formazione NOTA: limite massimo, non ottenibile in produzione)", "",
         f"Baseline v6-eloodds {base_ll:.4f}, quote di chiusura {cl:.4f}, divario {gap:.4f}. Δ = baseline − variante (positivo = meglio); "
         "validazione = 2019/20-2021/22, held-out = 2022/23 → oggi (comprende il 2026/27, senza dati di formazione). «Divario recuperato» = Δ tutte / divario.", "",
         "| Variante | Log-loss | Δ tutte [IC per partita] | IC a blocchi | Δ validazione | Δ held-out [IC a blocchi] | Stagioni migliorate | Distanza dalla chiusura | Divario recuperato |",
         "|---|---:|---|---|---:|---|---:|---:|---:|",
         f"| *Quote di chiusura (power)* | {cl:.4f} | — | — | — | — | — | 0.0000 | 100% |",
         f"| **Baseline v6-eloodds** | {base_ll:.4f} | — | — | — | — | — | {gap:+.4f} | 0% |"]
    for r in E["res"]:
        a, v, h = r["all"], r["val"], r["held"]
        mark = " (scelta sulle validazione)" if r["name"] == E["chosen"] else ""
        S.append(f"| {r['name']}{mark} | {r['ll']:.4f} | {a['d']:+.5f} [{a['lo']:+.5f}, {a['hi']:+.5f}] | [{a['lob']:+.5f}, {a['hib']:+.5f}] | "
                 f"{v['d']:+.5f} | {h['d']:+.5f} [{h['lob']:+.5f}, {h['hib']:+.5f}] | {r['seasons_better'][0]}/{r['seasons_better'][1]} | "
                 f"{r['ll'] - cl:+.4f} | {a['d'] / gap * 100:.1f}% |")
    S += ["", "Formazione prevista: non eseguita (condizione Δ held-out ≥ +0.002 con IC che esclude lo zero non soddisfatta).", "",
          "### F — coppe, gare di ritorno", "",
          f"Baseline = modello Elo delle coppe riallenato in walk-forward su Elo ricostruito: log-loss {F['ll0']:.4f} su {F['res']['F1']['all']['n']} partite del test "
          f"({F['n_ret']} gare di ritorno). Non esiste un riferimento di mercato nei dati delle coppe, quindi niente distanza dalle quote di chiusura. "
          "Δ = baseline − variante.", "",
          "| Forma | Δ tutte le partite [IC a blocchi] | Δ gare di ritorno [IC per partita] | IC a blocchi (ritorni) | Δ ritorni validazione | Δ ritorni held-out [IC a blocchi] |",
          "|---|---|---|---|---:|---|"]
    for k in ("F1", "F2", "F3"):
        r = F["res"][k]
        a, b, v, h = r["all"], r["ret"], r["ret_val"], r["ret_held"]
        mark = " (scelta)" if k == F["chosen"] else ""
        S.append(f"| {r['name']}{mark} | {a['d']:+.5f} [{a['lob']:+.5f}, {a['hib']:+.5f}] | {b['d']:+.5f} [{b['lo']:+.5f}, {b['hi']:+.5f}] | "
                 f"[{b['lob']:+.5f}, {b['hib']:+.5f}] | {v['d']:+.5f} | {h['d']:+.5f} [{h['lob']:+.5f}, {h['hib']:+.5f}] |")
    S += ["", f"Verdetto F secondo la regola scritta prima (Δ sulle gare di ritorno held-out, IC a blocchi): **{F['verdict']}**; vedi il commento per i limiti.", ""]
    parts = [open(os.path.join(C3.PARTS.replace("round3_parts", "round4_parts"), fn), encoding="utf-8").read()
             for fn in ("prereg.md", "E.md", "E2.md", "F.md")]
    cm = open(os.path.join(HERE, "round4_parts", "commento.md"), encoding="utf-8").read()
    head = ["# Round 4 — formazione titolare (E) e gare di ritorno nelle coppe (F), solo backtest", "",
            "**Nulla della produzione è stato toccato.** Dati: dataset dcaribou/transfermarkt-datasets (tabelle `game_lineups`, `appearances`, "
            "`games`, `player_valuations`, `clubs`; cache in `data/cache/transfermarkt/`, ignorata da git). Stesse regole del round 3: "
            "criteri scritti prima, validazione 2019/20-2021/22, held-out dal 2022/23, IC bootstrap (5000) per partita e a blocchi per settimana ISO.",
            "", "---", ""]
    with open(os.path.join(HERE, "results_round4.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(head) + "\n\n".join(parts) + "\n\n" + "\n".join(S) + "\n" + cm)
    print("\n".join(S))


if __name__ == "__main__":
    main()
