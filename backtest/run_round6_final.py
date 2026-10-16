"""Round 6 — assemblaggio di backtest/results_round6.md."""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import pandas as pd

from backtest import round3_ctx as C3

HERE = os.path.dirname(os.path.abspath(__file__))
P6 = os.path.join(HERE, "round6_parts")


def row(stat, name, r, verdict):
    a, h = r["ll_tot"], r["ll_tot_held"]
    t, th = r["ll_team"], r["ll_team_held"]
    return (f"| {stat} | {name} | {a['d']:+.5f} [{a['lob']:+.5f}, {a['hib']:+.5f}] | {h['d']:+.5f} [{h['lob']:+.5f}, {h['hib']:+.5f}] | "
            f"{t['d']:+.5f} [{t['lob']:+.5f}, {t['hib']:+.5f}] | {th['d']:+.5f} | {r['corr_tot']['d']:+.4f} | {r['c80_tot']['var']:.3f} / {r['c90_tot']['var']:.3f} | "
            f"{r['ece_tot']['base']:.4f} → {r['ece_tot']['var']:.4f} | {verdict} |")


def main():
    IJ = pd.read_pickle(os.path.join(C3.R3_DIR, "r6_IJ.pkl"))
    K = pd.read_pickle(os.path.join(C3.R3_DIR, "r6_K.pkl"))
    X = pd.read_pickle(os.path.join(C3.R3_DIR, "r6_extra.pkl"))
    S = ["## Tabella riassuntiva", "",
         "Δ = baseline − variante (positivo = variante migliore); IC 95% a blocchi per settimana; validazione 2019/20-2021/22, held-out dal 2022/23. "
         "Primaria = log-loss del conteggio totale; secondaria = log-loss per squadra. Per le statistiche non esiste un riferimento di mercato nei dati: "
         "la colonna «distanza dalle quote di chiusura» non si applica.", "",
         "### Miglioramenti di tiri, tiri in porta e corner, e modello dei tiri in porta",
         "", "| Statistica | Variante | Δ totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ per squadra (tutte) [IC a blocchi] | Δ per squadra held-out | Δ corr. totale | Copertura 80% / 90% tot. | ECE O/U tot. (base → var.) | Verdetto |",
         "|---|---|---|---|---|---:|---:|---|---|---|"]
    r = IJ["I"]["cmp"]
    S.append(row("Tiri in porta", "I — nuovo modello vs baseline semplice (tiri × quota in porta)", r, "peggiora (totale) / migliora per squadra"))
    for stat, lab in (("tiri", "Tiri"), ("sot", "Tiri in porta"), ("corner", "Corner")):
        for name, d in IJ[stat].items():
            if isinstance(d, dict) and "res" in d:
                S.append(row(lab, name, d["res"], d["verdict"]))
    S.append(row("Tiri in porta", "(extra) J4 GAP vs baseline semplice", X["cmp"], "non distinguibile (totale); migliora per squadra"))
    S += ["", "### Nuovi mercati", "",
          "| Mercato | Confronto | Δ log-loss [IC a blocchi] | Δ held-out [IC a blocchi] | Note |", "|---|---|---|---|---|"]
    k1 = K["k1"]
    for key, lab in (("ll12", "1X2 al riposo"), ("ll05", "Over 0.5 primo tempo"), ("ll15", "Over 1.5 primo tempo"), ("avg", "media dei tre")):
        c = k1["cmp"][(k1["chosen"], key)]
        S.append(f"| K1{k1['chosen']} — {lab} | vs medie di lega | {c['d']:+.5f} [{c['lob']:+.5f}, {c['hib']:+.5f}] | {c['held']:+.5f} [{c['lobh']:+.5f}, {c['hibh']:+.5f}] | quota 1T per lega |")
    for stat, lab in (("corner", "corner"), ("gialli", "gialli")):
        d = K["k2"][stat]["d3"]
        S.append(f"| K2 — chi ha più {lab} | copula vs indipendenza | {d['d']:+.5f} [{d['lob']:+.5f}, {d['hib']:+.5f}] | {d['held']:+.5f} [{d['lobh']:+.5f}, {d['hibh']:+.5f}] | ρ {K['k2'][stat]['rho'][max(K['k2'][stat]['rho'])]:+.3f} |")
    for key in ("Casa −1,5 (casa vince di almeno 2 corner)", "Ospite −1,5 (ospite vince di almeno 2 corner)"):
        d = K["k2"]["corner"][key]
        S.append(f"| K2 — handicap {key.split(' (')[0]} sui corner | copula vs indipendenza | {d['d']:+.5f} [{d['lob']:+.5f}, {d['hib']:+.5f}] | {d['held']:+.5f} [{d['lobh']:+.5f}, {d['hibh']:+.5f}] | |")
    for key, lab in (("a_vs_simple", "K3a vs metodo a medie"), ("b_vs_a", "K3b (con arbitro) vs K3a"), ("b_vs_simple", "K3b vs metodo a medie")):
        r = K["k3"][key]
        S.append(f"| K3 — falli totali | {lab} | {r['ll_tot']['d']:+.5f} [{r['ll_tot']['lob']:+.5f}, {r['ll_tot']['hib']:+.5f}] | "
                 f"{r['ll_tot_held']['d']:+.5f} [{r['ll_tot_held']['lob']:+.5f}, {r['ll_tot_held']['hib']:+.5f}] | per squadra {r['ll_team']['d']:+.5f}; {K['k3']['verdicts'][key.replace('a_vs_simple', 'a')]} |")
    S.append("")
    parts = [open(os.path.join(P6, fn), encoding="utf-8").read() for fn in ("prereg.md", "IJ.md", "K.md", "extra.md", "proposte.md")]
    cm = open(os.path.join(P6, "commento.md"), encoding="utf-8").read()
    head = ["# Round 6 — tiri in porta, miglioramenti dei modelli delle statistiche e nuovi mercati derivati (solo backtest)", "",
            "**Nulla della produzione è stato toccato** (`stats_model.STATS` non è stato modificato: le statistiche nuove usano specifiche locali di `backtest/round6_lib.py`). "
            "Stesse regole dei round 3-5: criteri scritti prima, validazione 2019/20-2021/22, held-out dal 2022/23, IC bootstrap per partita e a blocchi per settimana ISO.",
            "", "---", ""]
    with open(os.path.join(HERE, "results_round6.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(head) + "\n\n".join(parts[:4]) + "\n\n" + "\n".join(S) + "\n" + parts[4] + "\n" + cm)
    print("\n".join(S))


if __name__ == "__main__":
    main()
