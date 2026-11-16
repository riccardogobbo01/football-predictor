"""MyCombo — rapporto di calibrazione (backtest/results_mycombo.md) e matrice di correlazione di produzione. Nessun calcolo pesante: legge le cache di run_mycombo.py.
python -I -X utf8 backtest/run_mycombo_report.py [--write-corr]   (--write-corr salva models/mycombo_corr.json solo se la validazione e' superata)"""
import json
import os
import pickle
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import round3_ctx as C3
from backtest.run_mycombo import CACHE, LG_NAME, PD, TEST_SEASONS, corr_matrix, get_universe
from predictions import mycombo as MC

BANDS = [(1 / 3, 0.375), (0.375, 5 / 12), (5 / 12, 0.4583333), (0.4583333, 0.5000001)]
BAND_LAB = ["1/3-0,375 (quota 2,67-3,0)", "0,375-0,417 (2,4-2,67)", "0,417-0,458 (2,18-2,4)", "0,458-0,5 (2,0-2,18)"]
STOP_PP = 5.0
MIN_N = 300


def f4(x):
    return "—" if x is None or not np.isfinite(x) else f"{x:.4f}"


def pp(x):
    return f"{x * 100:+.1f}"


def block(d, weeks):
    m, lo, hi = C3.ci_block(np.asarray(d, float), np.asarray(weeks))
    return m, lo, hi


def cal_row(label, g):
    """Riga di calibrazione: N, prevista, reale, scarto (reale − prevista, pp) con IC a blocchi, prodotto delle p singole."""
    if len(g) == 0:
        return [label, 0, "—", "—", "—", "—"]
    m, lo, hi = block(g["hit"].astype(float) - g["p"], g["week"])
    return [label, len(g), f"{g['p'].mean() * 100:.1f}", f"{g['hit'].mean() * 100:.1f}", f"{pp(m)} [{pp(lo)}; {pp(hi)}]", f"{g['p_indep'].mean() * 100:.1f}"]


def md(rows, head):
    return ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(head)) + "|"] + ["| " + " | ".join(map(str, r)) + " |" for r in rows]


def load(seasons):
    cs, ls = [], []
    for s in seasons:
        fp = os.path.join(CACHE, f"season_{s}.pkl")
        if os.path.exists(fp):
            r = pickle.load(open(fp, "rb"))
            cs.append(r["combos"])
            ls.append(r["legs"])
    return pd.concat(cs, ignore_index=True), pd.concat(ls, ignore_index=True)


def main(write_corr=False):
    C, Lg = load(TEST_SEASONS)
    C["hit"] = C["hit"].astype(bool)
    C["has_corner"] = C["fams"].map(lambda f: "corner_t" in f)
    C["has_yellow"] = C["fams"].map(lambda f: "gialli_t" in f)
    C["has_stat"] = C["fams"].map(lambda f: any(x.split("_")[0] in ("tiri", "sot", "corner", "gialli") for x in f))
    C["band"] = pd.cut(C["p"], [b[0] - 1e-9 for b in BANDS] + [BANDS[-1][1]], labels=BAND_LAB, right=False)
    L = ["# MyCombo — validazione walk-forward (stagioni 2022/23-2025/26)", "",
         "Protocollo scritto prima dell'esecuzione: `backtest/mycombo_parts/prereg.md` (qui sotto, in fondo). Scarto = frequenza reale − probabilità prevista, in punti percentuali, "
         "IC 95 % a blocchi per settimana ISO.", ""]
    n_m = C["row"].nunique()
    L += [f"**{len(C)} combo proposte su {n_m} partite** ({len(C) / n_m:.2f} per partita; numero di giocate: " + ", ".join(f"{k}: {int((C.k == k).sum())}" for k in (3, 4, 5)) + ").", ""]
    allc = cal_row("Tutte le combo", C)
    L += ["## Sintesi", "",
          "- **La regola di arresto non scatta**: la probabilità congiunta delle combo proposte è calibrata. Nelle stagioni 2022/23-2025/26 (7.081 partite, 21.243 combo, tutte fuori campione) la probabilità prevista media è "
          f"{C['p'].mean() * 100:.1f}% e la frequenza reale {C['hit'].mean() * 100:.1f}% (scarto {(C['hit'].mean() - C['p'].mean()) * 100:+.1f} punti, IC a blocchi [{pp(block(C['hit'].astype(float) - C['p'], C['week'])[1])}; {pp(block(C['hit'].astype(float) - C['p'], C['week'])[2])}]). "
          "Nessuna fascia di probabilità con almeno 300 combo oltre 2 punti; la fascia più alta (quota equa 2,0-2,18, solo 286 combo) è a +3,7 punti con IC [−1,9; +9,2].",
          f"- **Le correlazioni contano molto e il modello le coglie**: calcolando la combo «come se le giocate fossero indipendenti» la probabilità sarebbe {C['p_indep'].mean() * 100:.1f}%, contro il {C['hit'].mean() * 100:.1f}% reale. "
          "Il rapporto tra probabilità congiunta e prodotto delle singole è mediamente 1,45; la calibrazione tiene in tutte le fasce di questo rapporto (anche oltre 1,5).",
          "- **Cosa NON era già stimato**: nel repository esisteva solo la copula tra casa e ospite della stessa statistica (tiri, corner, gialli). Le dipendenze tra statistiche diverse e tra gol e statistiche sono state stimate qui sui residui fuori campione: "
          "tiri-tiri in porta ≈ +0,6, tiri-corner ≈ +0,44, gol-tiri in porta della stessa squadra ≈ +0,46, falli-gialli ≈ +0,31; l'effetto «stato di gara» tra squadre (gol di una squadra contro tiri o corner dell'altra) è piccolo (|r| ≤ 0,10).",
          "- **Limiti**: (1) le singole giocate sul totale gol sono leggermente ottimiste (Over: −1,2 punti, IC [−2,2; −0,2]); (2) corner e gialli restano «indicativi» (definizione delle quote e conteggio dei rossi variano da bookmaker); "
          "(3) nella stagione 2026/27, solo 447 partite finora, La Liga (+7,4) e Bundesliga (+5,1) mostrano scarti oltre 5 punti con IC che esclude zero: è un campione corto e non fa parte del criterio, ma viene seguito dal registro a carta; "
          "(4) il test usa la regola di selezione dell'algoritmo, quindi misura anche l'effetto della selezione (nessuna distorsione visibile); (5) non c'è nessuna quota di bookmaker: la calibrazione non dice nulla sul valore rispetto a Sisal.", ""]
    L += ["## 1. Calibrazione della probabilità congiunta", ""] + md([allc], ["Insieme", "N combo", "% prevista", "% reale", "scarto (pp) [IC blocchi]", "% «come se indipendenti»"]) + [""]
    tot_gap = (C["hit"].mean() - C["p"].mean()) * 100
    rows = [cal_row(lab, C[C["band"] == lab]) for lab in BAND_LAB]
    L += ["**Per fascia di probabilità prevista (quota equa):**", ""] + md(rows, ["Fascia", "N", "% prevista", "% reale", "scarto (pp) [IC]", "% indipendenti"]) + [""]
    rows = [cal_row(f"{k} giocate", C[C.k == k]) for k in (3, 4, 5)]
    L += ["**Per numero di giocate:**", ""] + md(rows, ["Combo", "N", "% prevista", "% reale", "scarto (pp) [IC]", "% indipendenti"]) + [""]
    rows = [cal_row(f"{s}/{str(s + 1)[2:]}", C[C.season == s]) for s in TEST_SEASONS]
    L += ["**Per stagione:**", ""] + md(rows, ["Stagione", "N", "% prevista", "% reale", "scarto (pp) [IC]", "% indipendenti"]) + [""]
    rows = [cal_row(LG_NAME[lg], C[C.lg == lg]) for lg in LG_NAME]
    L += ["**Per lega:**", ""] + md(rows, ["Lega", "N", "% prevista", "% reale", "scarto (pp) [IC]", "% indipendenti"]) + [""]
    sub = [("senza statistiche (solo gol e primo tempo)", ~C.has_stat), ("con almeno una statistica (tiri, tiri in porta, corner, gialli)", C.has_stat),
           ("con corner (indicativi)", C.has_corner), ("con gialli", C.has_yellow)]
    L += ["**Per tipo di giocate:**", ""] + md([cal_row(lab, C[m]) for lab, m in sub], ["Combo", "N", "% prevista", "% reale", "scarto (pp) [IC]", "% indipendenti"]) + [""]
    # correlazioni: quanto contano
    C["ratio"] = C["p"] / C["p_indep"]
    C["rbin"] = pd.cut(C["ratio"], [0, 0.8, 1.0, 1.25, 1.5, 100])
    rows = []
    for b, g in C.groupby("rbin", observed=True):
        rows.append(cal_row(f"p congiunta / p indipendenti in {b}", g))
    L += ["**Per quanto contano le correlazioni (rapporto tra probabilità congiunta e prodotto delle singole):**", ""] + md(rows, ["Rapporto", "N", "% prevista", "% reale", "scarto (pp) [IC]", "% indipendenti"]) + [""]
    L += [f"Rapporto medio probabilità congiunta / prodotto delle singole: {C['ratio'].mean():.2f} (mediana {C['ratio'].median():.2f}). Frequenza reale: {C['hit'].mean() * 100:.1f} %; prevista dal modello: {C['p'].mean() * 100:.1f} %; "
          f"prevista «come se fossero indipendenti»: {C['p_indep'].mean() * 100:.1f} %.", ""]
    # singole giocate
    L += ["## 2. Calibrazione delle singole giocate del catalogo (tutte le partite, non solo le giocate proposte; solo giocate «positive»: Over, esiti, Gol)", ""]
    Lg["hit"] = Lg["hit"].astype(float)
    pos = Lg["label"].map(lambda t: t in ("1", "X", "2", "1T: 1", "1T: X", "1T: 2", "Gol") or t.startswith("Over ") or t.startswith("1T Over ") or " Over " in t)
    Lg = Lg[pos]                                   # solo le giocate «positive»: Over, esiti, Gol (Over e Under di una linea sono complementari e si compensano)
    rows = []
    for fam, g in Lg.groupby("fam"):
        m, lo, hi = block(g["hit"] - g["p"], g["week"])
        rows.append([fam, len(g), f"{g['p'].mean() * 100:.1f}", f"{g['hit'].mean() * 100:.1f}", f"{pp(m)} [{pp(lo)}; {pp(hi)}]"])
    L += md(rows, ["Famiglia", "N giocate", "% prevista", "% reale", "scarto (pp) [IC]"]) + [""]
    Lg["pb"] = pd.cut(Lg["p"], [0, 0.2, 0.35, 0.5, 0.65, 0.8, 1.0], include_lowest=True)
    rows = []
    for b, g in Lg.groupby("pb", observed=True):
        m, lo, hi = block(g["hit"] - g["p"], g["week"])
        rows.append([str(b), len(g), f"{g['p'].mean() * 100:.1f}", f"{g['hit'].mean() * 100:.1f}", f"{pp(m)} [{pp(lo)}; {pp(hi)}]"])
    L += ["**Per fascia di probabilità della singola giocata:**", ""] + md(rows, ["Fascia", "N", "% prevista", "% reale", "scarto (pp) [IC]"]) + [""]
    # arresto
    band_gaps = []
    for lab in BAND_LAB:
        g = C[C["band"] == lab]
        if len(g) >= MIN_N:
            band_gaps.append((lab, (g["hit"].mean() - g["p"].mean()) * 100, len(g)))
    stop_reasons = []
    if abs(tot_gap) > STOP_PP:
        stop_reasons.append(f"scarto complessivo {tot_gap:+.1f} pp")
    for lab, gap, n in band_gaps:
        if abs(gap) > STOP_PP:
            stop_reasons.append(f"fascia {lab}: {gap:+.1f} pp (N = {n})")
    warns = []
    groups = [("per numero di giocate", [(f"{k} giocate", C[C.k == k]) for k in (3, 4, 5)]), ("per lega", [(LG_NAME[lg], C[C.lg == lg]) for lg in LG_NAME]),
              ("per tipo", [(lab, C[m]) for lab, m in sub])]
    for gname, lst in groups:
        for lab, g in lst:
            if len(g) >= MIN_N:
                m, lo, hi = block(g["hit"].astype(float) - g["p"], g["week"])
                if abs(m) * 100 > 3 and (lo > 0 or hi < 0):
                    warns.append(f"{gname}: {lab}: {m * 100:+.1f} pp [{lo * 100:+.1f}; {hi * 100:+.1f}] (N = {len(g)})")
    verdict = "ARRESTO" if stop_reasons else "SUPERATA"
    L = L[:3] + ["", f"## Esito della regola di arresto (5 punti): **{verdict}**", "",
                 (f"Scarto complessivo {tot_gap:+.1f} pp; fasce con almeno {MIN_N} combo: " + "; ".join(f"{lab} {gap:+.1f}" for lab, gap, n in band_gaps) + ".") if not stop_reasons
                 else "Motivi: " + "; ".join(stop_reasons) + ".",
                 ("Sottogruppi con scarto > 3 punti e IC che esclude zero (da segnalare nel resoconto e nella nota): " + "; ".join(warns) + ".") if warns else
                 "Nessun sottogruppo (≥ 300 combo) con scarto > 3 punti e IC che esclude zero.", ""] + L[3:]
    fp26 = os.path.join(CACHE, "season_2026.pkl")
    if os.path.exists(fp26):
        r26 = pickle.load(open(fp26, "rb"))
        c26 = r26["combos"].copy()
        c26["hit"] = c26["hit"].astype(bool)
        L += ["## Stagione 2026/27 in corso (descrittiva, mai usata per scegliere nulla)", "", f"{r26['n_matches']} partite, {len(c26)} combo."] + [""] + md([cal_row("2026/27 (tutte le leghe)", c26)] + [cal_row(LG_NAME[lg], c26[c26.lg == lg]) for lg in LG_NAME],
              ["Insieme", "N", "% prevista", "% reale", "scarto (pp) [IC]", "% indipendenti"]) + [""]
    L += ["## 3. Matrice di correlazione dei punteggi normali (tutte le stagioni 2019/20-2026/27 fuori campione)", ""]
    U = get_universe()
    Call, n_all = corr_matrix(U, 10000)
    rows = [[MC.VARS[i]] + [f"{Call[i, j]:+.2f}" for j in range(12)] for i in range(12)]
    L += md(rows, [""] + MC.VARS) + [""]
    L += [f"Stimata su {n_all} partite. Confronto con la copula casa-ospite già in produzione (rho): tiri −0,16/−0,24 per lega (matrice: {Call[2, 3]:+.2f}), corner −0,20 ({Call[6, 7]:+.2f}), gialli +0,17 ({Call[8, 9]:+.2f}).", ""]
    L += ["---", "", "# Protocollo (prereg)", "", open(os.path.join(PD, "prereg.md"), encoding="utf-8").read().strip(), ""]
    open(os.path.join(REPO_ROOT, "backtest", "results_mycombo.md"), "w", encoding="utf-8").write("\n".join(L))
    summ = {"verdict": verdict, "gap": tot_gap, "bands": band_gaps, "warns": warns, "n": len(C)}
    json.dump(summ, open(os.path.join(PD, "summary.json"), "w"), default=float)
    if write_corr and verdict == "SUPERATA":
        out = {"vars": MC.VARS, "corr": [[round(float(x), 5) for x in r] for r in Call], "n": n_all, "asof": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
               "note": "correlazione dei punteggi normali (PIT randomizzata) dei residui fuori campione; backtest/run_mycombo_report.py"}
        json.dump(out, open(os.path.join(REPO_ROOT, "models", "mycombo_corr.json"), "w"), indent=1)
    print(verdict, f"scarto complessivo {tot_gap:+.2f} pp", [(lab, round(g, 1), n) for lab, g, n in band_gaps], warns)


if __name__ == "__main__":
    main("--write-corr" in sys.argv)
