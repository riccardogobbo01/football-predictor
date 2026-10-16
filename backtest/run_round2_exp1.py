"""Round 2 — Esperimento 1: dummy "porte chiuse" e vantaggio casa per lega (solo backtest)."""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from backtest import data, round2_ctx as C, round2_models as RM, stack
from backtest.round2_lib import Boot, run_stack

PARTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "round2_parts")
os.makedirs(PARTS, exist_ok=True)
FEAT_PATH = os.path.join(C.R2_DIR, "exp1_feats.pkl")

# Ripresa post-lockdown 2019/20 (verificata sui dati: primo incontro dopo la pausa più lunga di 25 giorni)
# Ligue 1 2019/20: stagione interrotta l'8/3/2020 senza ripresa -> nessuna partita a porte chiuse nel 2019/20.
RESTART_2019 = {"I1": "2020-06-20", "E0": "2020-06-17", "D1": "2020-05-16", "SP1": "2020-06-11", "F1": None}


def closed_flag(df):
    f = np.zeros(len(df), int)
    for lg, dt in RESTART_2019.items():
        if dt:
            f[((df.Division == lg) & (df.season == 2019) & (df.date >= pd.Timestamp(dt))).to_numpy()] = 1
    f[(df.season == 2020).to_numpy()] = 1        # tutta la stagione 2020/21
    return pd.Series(f, index=df.index, name="closed")


def build_feats(df, closed):
    d = df.assign(closed=closed)
    jobs = [(k, lg) for k in RM.SETS for lg in data.LEAGUES]
    res = Parallel(n_jobs=8)(delayed(RM.build_set)(k, d[d.Division == lg], "closed") for k, lg in jobs)
    parts = {}
    for (k, lg), r in zip(jobs, res):
        parts.setdefault(k, []).append(r)
    out = {k: pd.concat(v).sort_index() for k, v in parts.items()}
    f = pd.DataFrame(index=out["goals"].index)
    f["dc_lmu"], f["dc_lnu"] = np.log(out["goals"].mu), np.log(out["goals"].nu)
    f["sot_lmu"], f["sot_lnu"] = np.log(out["sot"].mu.reindex(f.index)), np.log(out["sot"].nu.reindex(f.index))
    f["xg_lmu"], f["xg_lnu"] = np.log(out["xg"].mu.reindex(f.index)), np.log(out["xg"].nu.reindex(f.index))
    f["H_goals"], f["delta_goals"] = out["goals"].H, out["goals"].delta
    f["H_xg"], f["delta_xg"] = out["xg"].H.reindex(f.index), out["xg"].delta.reindex(f.index)
    return f


def main():
    c = C.get_ctx()
    ev, feat, df = c.ev, c.feat, c.df
    boot = Boot(len(ev))
    Pb = c.base_sp[["pH", "pD", "pA"]].to_numpy()
    closed = closed_flag(df)
    L = ["## Esperimento 1 — Porte chiuse e vantaggio casa per lega", ""]

    # ── verifica delle date e del flag ────────────────────────────────────────
    L += ["### Date e flag \"porte chiuse\"", "",
          "Ripresa post-lockdown 2019/20 rilevata sui dati (primo incontro dopo la pausa più lunga): "
          + ", ".join(f"{data.LEAGUE_NAMES[l]} {d}" if d else f"{data.LEAGUE_NAMES[l]} nessuna ripresa (ultima partita 2020-03-08)"
                      for l, d in RESTART_2019.items())
          + ". Flag = 1 dalla ripresa 2019/20 a fine 2019/20 e per tutta la stagione 2020/21 (come da definizione); "
            "non sono marcate le poche partite a porte chiuse prima del lockdown (Serie A 8-9 marzo 2020, "
            "Bundesliga 11 marzo) né le riaperture parziali di pubblico del 2020/21 (autunno 2020, primavera 2021), "
            "che non sono ricostruibili dai dati.", "",
          "| Lega | Partite flag=1 | di cui 2019/20 | Vittorie casa flag=0 | Vittorie casa flag=1 | Gol casa−trasf. flag=0 | flag=1 |",
          "|---|---:|---:|---:|---:|---:|---:|"]
    d0 = df.assign(closed=closed)
    d0 = d0[d0.season >= 2012]
    for lg in data.LEAGUES:
        g = d0[d0.Division == lg]
        a, b = g[g.closed == 0], g[g.closed == 1]
        L.append(f"| {data.LEAGUE_NAMES[lg]} | {len(b)} | {int(((b.season == 2019)).sum())} | {(a.res == 0).mean():.3f} | "
                 f"{(b.res == 0).mean():.3f} | {(a.hg - a.ag).mean():+.3f} | {(b.hg - b.ag).mean():+.3f} |")
    a, b = d0[d0.closed == 0], d0[d0.closed == 1]
    L += [f"| Tutte | {len(b)} | {int((b.season == 2019).sum())} | {(a.res == 0).mean():.3f} | {(b.res == 0).mean():.3f} | "
          f"{(a.hg - a.ag).mean():+.3f} | {(b.hg - b.ag).mean():+.3f} |", "",
          f"Nel solo insieme di test ({len(ev)} partite) le partite con flag=1 sono {int(closed.loc[ev.index].sum())}.", ""]

    # ── feature con dummy ─────────────────────────────────────────────────────
    if os.path.exists(FEAT_PATH) and pd.read_pickle(FEAT_PATH)["key"] == (len(df), str(df.date.max())):
        f1 = pd.read_pickle(FEAT_PATH)["f"]
    else:
        print("walk-forward DC con dummy (goals, sot, xg) ...", flush=True)
        f1 = build_feats(df, closed)
        pd.to_pickle(dict(key=(len(df), str(df.date.max())), f=f1), FEAT_PATH)

    new = feat.copy()
    for col in ["dc_lmu", "dc_lnu", "sot_lmu", "sot_lnu", "xg_lmu", "xg_lnu"]:
        new[col] = f1[col].reindex(new.index)
    new["closed"] = closed.reindex(new.index).astype(float)
    base_c = feat.copy()
    base_c["closed"] = closed.reindex(base_c.index).astype(float)
    for lg in data.LEAGUES:
        new["lg_" + lg] = (new.Division == lg).astype(float)
        base_c["lg_" + lg] = (base_c.Division == lg).astype(float)
        feat["lg_" + lg] = (feat.Division == lg).astype(float)
    LG = ["lg_" + lg for lg in data.LEAGUES]
    XG = stack.XG_FEATURES

    variants = [
        ("1a — dummy nei DC (gol, tiri, xG) + nella regressione", new, XG + ["closed"]),
        ("1a-i — dummy solo nei DC", new, XG),
        ("1a-ii — dummy solo nella regressione", base_c, XG + ["closed"]),
        ("1b — vantaggio casa per lega (intercette di lega nella regressione)", feat, XG + LG),
        ("1a+1b — dummy completa + intercette di lega", new, XG + ["closed"] + LG),
    ]
    results = []
    for name, frame, cols in variants:
        print(" ", name, flush=True)
        sp = run_stack(frame, cols, ev)
        C.reg_save("E1 " + name, sp)
        results.append(C.compare(sp[["pH", "pD", "pA"]].to_numpy(), Pb, ev, boot, name))

    L += ["### Risultati (ogni variante da sola vs baseline)", ""] + C.md_summary_rows(results) + [""]
    L += ["Nota: i DC sono già stimati campionato per campionato, quindi il vantaggio casa H è già separato per "
          "lega a livello di DC; la variante 1b agisce sulla regressione di stack (che mette insieme i 5 campionati), "
          "aggiungendo un'intercetta per lega a gol casa e gol trasferta.", ""]
    for r in results:
        L += C.md_variant(r, title=r["name"])

    # ── dove si vede l'effetto: porte chiuse vs pubblico ──────────────────────
    cl = closed.reindex(ev.index).to_numpy() == 1
    post = (ev.season >= 2021).to_numpy()
    L += ["### Effetto per sottoinsieme (variante 1a completa)", "",
          "| Sottoinsieme | N | Δ log-loss (base − variante) | IC 95% |", "|---|---:|---:|---|"]
    sp1 = C.reg_load()["E1 " + variants[0][0]]["sp"]
    P1 = sp1[["pH", "pD", "pA"]].to_numpy()
    from backtest.round2_lib import ll_vec
    d = ll_vec(Pb, c.y) - ll_vec(P1, c.y)
    for lab, m in (("partite a porte chiuse (flag=1)", cl), ("partite con pubblico (flag=0)", ~cl),
                   ("dalla stagione 2021/22 (H storico ancora contaminato)", post)):
        mean, lo, hi = Boot(int(m.sum())).ci(d[m])
        L.append(f"| {lab} | {int(m.sum())} | {mean:+.5f} | [{lo:+.5f}, {hi:+.5f}] |")
    L.append("")

    # ── stime di H e delta ────────────────────────────────────────────────────
    L += ["### Vantaggio casa stimato dal DC sui gol (media dei rifit settimanali)", "",
          "H = parametro di vantaggio casa (log), delta = variazione stimata a porte chiuse; baseline = H "
          "del modello attuale, stimato su tutte le partite.", ""]
    from backtest import models
    rows = ["| Lega | Periodo | H con dummy (solo pubblico) | delta (porte chiuse) |", "|---|---|---:|---:|"]
    for lg in data.LEAGUES:
        g = f1[f1.index.isin(df.index[df.Division == lg])]
        for lab, a_, b_ in (("2019/20-2020/21", "2020-07-01", "2021-06-30"), ("2021/22", "2021-07-01", "2022-06-30"),
                            ("2023/24", "2023-07-01", "2024-06-30")):
            m = (df.date.reindex(g.index) >= a_) & (df.date.reindex(g.index) <= b_)
            if m.any():
                rows.append(f"| {data.LEAGUE_NAMES[lg]} | {lab} | {g.H_goals[m].mean():.3f} | {g.delta_goals[m].mean():+.3f} |")
    L += rows + [""]

    with open(os.path.join(PARTS, "exp1.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    pd.to_pickle(results, os.path.join(C.R2_DIR, "exp1_results.pkl"))
    print("\n".join(L))


if __name__ == "__main__":
    main()
