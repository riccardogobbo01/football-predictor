"""Intervalli delle statistiche attese (tiri, tiri in porta, corner, gialli, falli): verifica in walk-forward.

Per ogni statistica, in ogni stagione di test (2019/20 in poi), il modello di produzione (backtest/stats_v3.py, variante with_xg, parametri
e dispersioni stimati sul solo training precedente, come in produzione) prevede la distribuzione di casa, ospite e totale; l'intervallo
(`stats_v3.nb_interval`: valori interi consecutivi attorno ai più probabili, probabilità reale più vicina all'80%, a parità la maggiore)
dichiara una probabilità; qui si confronta la probabilità media dichiarata con la frequenza con cui il valore reale cade nell'intervallo.
Criterio: scarto massimo 3 punti percentuali, per squadra (casa e ospite) e per il totale.

Da lanciare in modalità isolata:  python -I -X utf8 backtest/run_intervals.py   (scrive backtest/results_intervals.md)"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import refeffect, round3_ctx as C3, round6_lib as R6, stats_v3
from config import REFEREE_K

TOL = 0.03
NAMES = {"tiri": "Tiri", "sot": "Tiri in porta", "corner": "Corner", "gialli": "Gialli", "falli": "Falli"}
LEVELS = [("home", "Casa"), ("away", "Ospite"), ("team", "Squadra (casa+ospite)"), ("total", "Totale")]


def build_feat():
    feat, keys, c = R6.prepare()
    pri = stats_v3.gap_priors(c.df)
    gf = stats_v3.gap_features(c.df, pri)
    for col in gf.columns:
        feat[col] = gf[col].reindex(feat.index)
    feat["ref_logR"], _ = refeffect.compute(feat, keys, REFEREE_K)
    mhf, maf = stats_v3.base_predictions(feat, "falli")
    feat["ref_logR_f"], _ = refeffect.compute_stat(feat, keys, mhf, maf, feat["HF"] + feat["AF"], REFEREE_K)
    return feat


def side_alphas(run, feat, spec):
    """(alpha globali attuali, alpha con casa e ospite separati) come DataFrame ah/aa/aT per riga di test; casa e ospite a momenti sul training del fold."""
    al = R6.alphas(run, mode="global")
    out = al.copy()
    for s, f in run.folds.items():
        i = f["idx"]
        te = run.mh.notna() & (feat.season == s)
        out.loc[te, "ah"] = R6.moments(feat.loc[i, spec["hc"]].to_numpy(float), f["mh"])
        out.loc[te, "aa"] = R6.moments(feat.loc[i, spec["ac"]].to_numpy(float), f["ma"])
    return al, out


def stat_intervals(feat, stat, side=None):
    """DataFrame (righe di test): per casa, ospite, totale: lo, hi, probabilità dichiarata, esito (1 se il valore reale è nell'intervallo), più campionato e stagione."""
    spec = stats_v3.STATS3[stat]
    run = R6.run_model(feat, R6.SPECS.get(stat, spec), stats_v3.design(feat, stat, True))
    al = side_alphas(run, feat, spec)[1] if (stat in stats_v3.SIDE_ALPHA if side is None else side) else R6.alphas(run, mode="global")
    rows = run.mh.notna() & feat[spec["hc"]].notna() & feat[spec["ac"]].notna()
    idx = feat.index[rows]
    mh, ma = run.mh[idx].to_numpy(float), run.ma[idx].to_numpy(float)
    yh, ya = feat.loc[idx, spec["hc"]].to_numpy(float), feat.loc[idx, spec["ac"]].to_numpy(float)
    K = stats_v3.INTERVAL_K[stat]
    out = pd.DataFrame({"season": feat.loc[idx, "season"].to_numpy(), "league": feat.loc[idx, "Division"].to_numpy(),
                        "week": feat.loc[idx, "date"].dt.strftime("%G-%V").to_numpy()}, index=idx)
    # dispersioni per fold, come in produzione (alpha per squadra e del totale stimati sul training del fold)
    for key, m, y, a, kk in (("home", mh, yh, al.loc[idx, "ah"].to_numpy(), K), ("away", ma, ya, al.loc[idx, "aa"].to_numpy(), K),
                             ("total", mh + ma, yh + ya, al.loc[idx, "aT"].to_numpy(), 2 * K)):
        lo = np.empty(len(idx), int)
        hi = np.empty(len(idx), int)
        pr = np.empty(len(idx))
        for av in np.unique(a):                           # un alpha per fold: raggruppo
            sel = a == av
            lo[sel], hi[sel], pr[sel] = stats_v3.nb_interval(m[sel], av, kk)
        out[f"{key}_lo"], out[f"{key}_hi"], out[f"{key}_p"] = lo, hi, pr
        out[f"{key}_in"] = ((y >= lo) & (y <= hi)).astype(float)
        out[f"{key}_w"] = hi - lo + 1
    return out


def block_ci(gap, weeks, n_boot=2000, seed=5):
    """IC 95% a blocchi (settimana ISO) dello scarto medio frequenza − probabilità dichiarata."""
    gap = np.asarray(gap, float)
    wk, inv = np.unique(weeks, return_inverse=True)
    s = np.bincount(inv, gap)
    c = np.bincount(inv)
    rng = np.random.default_rng(seed)
    b = rng.integers(0, len(wk), size=(n_boot, len(wk)))
    est = s[b].sum(1) / c[b].sum(1)
    return float(np.percentile(est, 2.5)), float(np.percentile(est, 97.5))


def summarize(df, level):
    if level == "team":
        p = np.r_[df.home_p, df.away_p]
        hit = np.r_[df.home_in, df.away_in]
        w = np.r_[df.home_w, df.away_w]
        wk = np.r_[df.week, df.week]
    else:
        p, hit, w, wk = df[f"{level}_p"].to_numpy(), df[f"{level}_in"].to_numpy(), df[f"{level}_w"].to_numpy(), df.week.to_numpy()
    gap = hit - p
    lo, hi = block_ci(gap, wk)
    return dict(n=len(p), p=float(p.mean()), freq=float(hit.mean()), gap=float(gap.mean()), lo=lo, hi=hi, width=float(w.mean()))


def main():
    feat = build_feat()
    L = ["# Intervalli delle statistiche attese — verifica in walk-forward", "",
         "**Metodo (uguale per tutte le statistiche).** Dalla distribuzione prevista dal modello (Binomiale Negativa; per i gialli la dispersione stimata è quasi nulla, quindi di fatto Poisson) "
         "si prende l'intervallo di valori interi consecutivi centrato sui valori più probabili (per ogni ampiezza la finestra di probabilità massima) la cui probabilità reale è la più vicina all'80%, "
         "a parità quella maggiore (`stats_v3.nb_interval`). Nel pannello compare con la probabilità arrotondata, ad es. «1–3 (78%)».", "",
         "**Verifica.** Walk-forward per stagione (training dal 2016/17 sulle sole stagioni precedenti, test dal 2019/20; variante with_xg, parametri e dispersioni stimati nel training di ogni fold come in produzione). "
         f"Per ogni partita e livello si confronta la probabilità dichiarata dall'intervallo con l'esito reale (1 se il valore osservato cade nell'intervallo). **Criterio: scarto massimo {TOL * 100:.0f} punti** tra probabilità media dichiarata e frequenza reale, per squadra e totale. "
         "IC 95% dello scarto a blocchi per settimana ISO (2000 ricampionamenti).", ""]
    allres = {}
    for stat in stats_v3.ORDER:
        df = stat_intervals(feat, stat)
        allres[stat] = df
        print(stat, len(df), flush=True)
    for title, sel in (("Tutte le stagioni di test (2019/20–2025/26)", lambda d: d),
                       ("Solo held-out (dal 2022/23)", lambda d: d[~d.season.isin(C3.VALIDATION)])):
        L += [f"## {title}", "", "| Statistica | Livello | N | Prob. media dichiarata | Frequenza reale | Scarto (reale − dichiarata) [IC a blocchi] | Ampiezza media | Esito |", "|---|---|---:|---:|---:|---|---:|---|"]
        worst = {}
        for stat in stats_v3.ORDER:
            d = sel(allres[stat])
            for lv, lab in LEVELS:
                s = summarize(d, lv)
                ok = abs(s["gap"]) <= TOL
                worst[stat] = max(worst.get(stat, 0.0), abs(s["gap"]))
                L.append(f"| {NAMES[stat]} | {lab} | {s['n']} | {s['p'] * 100:.1f}% | {s['freq'] * 100:.1f}% | {s['gap'] * 100:+.1f} [{s['lo'] * 100:+.1f}, {s['hi'] * 100:+.1f}] pp | {s['width']:.1f} | {'ok' if ok else '**FUORI**'} |")
        L += ["", "Scarto massimo per statistica: " + "; ".join(f"{NAMES[k]} {v * 100:.1f} pp" for k, v in worst.items()), ""]
    # tiri: confronto con l'alpha unico per squadra (prima versione) e verifica che l'alpha separato non peggiori le log-loss
    old = stat_intervals(feat, "tiri", side=False)
    L += ["## Tiri: alpha unico per squadra (prima versione) contro alpha separato per casa e ospite (versione finale)", "",
          "Con un solo alpha per squadra l'ospite stava a −3,0 punti (tutte le stagioni) e −3,4 (held-out), fuori dal criterio dei 3 punti; la causa era la varianza reale dei tiri dell'ospite, circa il 13% sopra quella del modello. "
          "Con alpha separati (momenti sul training del fold) tutti i livelli rientrano. Le tabelle sopra sono quelle finali (alpha separato).", "",
          "| Insieme | Livello | Alpha unico: dichiarata → reale (scarto) | Alpha separato: dichiarata → reale (scarto) |", "|---|---|---|---|"]
    for lab, sel in (("Tutte le stagioni", lambda d: d), ("Held-out (dal 2022/23)", lambda d: d[~d.season.isin(C3.VALIDATION)])):
        for lv, lvlab in LEVELS:
            a, b = summarize(sel(old), lv), summarize(sel(allres["tiri"]), lv)
            L.append(f"| {lab} | {lvlab} | {a['p'] * 100:.1f}% → {a['freq'] * 100:.1f}% ({a['gap'] * 100:+.1f} pp) | {b['p'] * 100:.1f}% → {b['freq'] * 100:.1f}% ({b['gap'] * 100:+.1f} pp) |")
    L.append("")
    fp = os.path.join(REPO_ROOT, "backtest", "round6_parts", "alpha_side.md")
    if os.path.exists(fp):
        L += [open(fp, encoding="utf-8").read(), ""]
    # per stagione e per campionato (solo scarto massimo dei livelli squadra/totale)
    L += ["## Dettaglio per campionato (tutte le stagioni di test)", "", "| Statistica | " + " | ".join(["D1", "E0", "F1", "I1", "SP1"]) + " |", "|---|" + "---:|" * 5]
    for stat in stats_v3.ORDER:
        d = allres[stat]
        cells = []
        for lg in ["D1", "E0", "F1", "I1", "SP1"]:
            x = d[d.league == lg]
            cells.append(" / ".join(f"{summarize(x, lv)['gap'] * 100:+.1f}" for lv in ("team", "total")))
        L.append(f"| {NAMES[stat]} (squadra / totale, pp) | " + " | ".join(cells) + " |")
    L += ["", "## Dettaglio per stagione (scarto in pp, squadra / totale)", "", "| Statistica | " + " | ".join(str(s) for s in sorted(allres['tiri'].season.unique())) + " |",
          "|---|" + "---:|" * len(allres['tiri'].season.unique())]
    for stat in stats_v3.ORDER:
        d = allres[stat]
        cells = []
        for s_ in sorted(d.season.unique()):
            x = d[d.season == s_]
            cells.append(" / ".join(f"{summarize(x, lv)['gap'] * 100:+.1f}" for lv in ("team", "total")))
        L.append(f"| {NAMES[stat]} | " + " | ".join(cells) + " |")
    L.append("")
    with open(os.path.join(REPO_ROOT, "backtest", "results_intervals.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    pd.to_pickle(allres, os.path.join(C3.R3_DIR, "intervals.pkl"))
    print("\n".join(L))


if __name__ == "__main__":
    main()
