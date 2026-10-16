"""Round 3 — Esperimento A: lunghezza del training dello stack (solo backtest)."""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from backtest import data, round2_ctx as C2, round2_models as RM, round3_ctx as C3, stack

ORDER = ["A1", "A2", "A3", "A4"]          # ordine di semplicità (parità entro 0.0002 -> vince il primo)
TIE = 0.0002
BASE_START = pd.Timestamp("2016-07-04")
WARM = {12: "2015-08-03", 6: "2015-02-02"}


def _xg_job(g, start):
    return RM.walk_forward_ext(g, xi=0.003, start=start, use_tau=False, gx="xg_h", gy="xg_a", ridge=2.0)


def xg_series(df, months):
    path = os.path.join(C3.R3_DIR, f"r3_xg_warm{months}.pkl")
    key = (len(df), str(df.date.max()))
    if os.path.exists(path):
        d = pd.read_pickle(path)
        if d["key"] == key:
            return d["v"]
    start = WARM[months]
    assert (BASE_START - pd.Timestamp(start)).days % 7 == 0, "griglia settimanale non allineata al baseline"
    res = Parallel(n_jobs=8)(delayed(_xg_job)(df[df.Division == lg], start) for lg in data.LEAGUES)
    r = pd.concat(res).sort_index()
    v = pd.DataFrame({"xg_lmu": np.log(r.mu), "xg_lnu": np.log(r.nu)}, index=r.index)
    pd.to_pickle(dict(key=key, v=v), path)
    return v


def train_table(frame, cols, min_train, ev):
    usable = frame[cols].notna().all(axis=1) & (frame.season >= min_train)
    out = {}
    for s in sorted(ev.season.unique()):
        m = usable & (frame.season < s)
        out[int(s)] = (int(frame.season[m].nunique()), int(m.sum()))
    return out


def main():
    c = C3.get_ctx3()
    df, feat, ev = c.df, c.feat, c.ev
    base_cols = stack.XG_FEATURES_EO
    L = ["## Esperimento A — Lunghezza del training dello stack", ""]

    # stagioni di training per stagione di test
    tab_base = train_table(feat, base_cols, stack.XG_FIRST_TRAIN_SEASON, ev)
    L += ["### Quante stagioni di training ha lo stack in ogni stagione di test (baseline)", "",
          "Stack allenato dal 2016/17 sulle sole stagioni precedenti alla stagione di test (gli xG partono dal 2014/15 e il DC xG "
          "richiede 2 anni di storia: prima feature xG nell'estate 2016).", "",
          "| Stagione di test | " + " | ".join(C2.season_label(s) for s in tab_base) + " |",
          "|---|" + "---:|" * len(tab_base),
          "| Stagioni di training | " + " | ".join(str(v[0]) for v in tab_base.values()) + " |",
          "| Partite di training | " + " | ".join(str(v[1]) for v in tab_base.values()) + " |", ""]

    xg12, xg6 = xg_series(df, 12), xg_series(df, 6)
    def with_xg(x):
        fr = feat.copy()
        fr["xg_lmu"], fr["xg_lnu"] = x.xg_lmu.reindex(fr.index), x.xg_lnu.reindex(fr.index)
        return fr
    def with_imputed(x):
        fr = with_xg(x) if x is not None else feat.copy()
        fr["xg_miss"] = fr.xg_lmu.isna().astype(float)
        fr["xg_lmu_i"] = fr.xg_lmu.where(fr.xg_lmu.notna(), fr.dc_lmu)
        fr["xg_lnu_i"] = fr.xg_lnu.where(fr.xg_lnu.notna(), fr.dc_lnu)
        return fr
    imp_cols = stack.PRODUCTION_FEATURES_EO + ["xg_lmu_i", "xg_lnu_i", "xg_miss"]
    spec = {
        "A1": ("A1 — xG con 12 mesi di riscaldamento, training dal 2015/16", with_xg(xg12), base_cols, 2015),
        "A2": ("A2 — xG con 6 mesi di riscaldamento, training dal 2014/15", with_xg(xg6), base_cols, 2014),
        "A3": ("A3 — training dal 2013/14 con xG mancante gestito (imputazione + indicatore)", with_imputed(None), imp_cols, 2013),
        "A4": ("A4 — xG a 6 mesi + training dal 2013/14 con xG mancante gestito", with_imputed(xg6), imp_cols, 2013),
    }
    res, tabs = {}, {}
    for k in ORDER:
        name, fr, cols, mt = spec[k]
        sp = stack.walk_forward_stack(fr, cols, 2019, mt).reindex(ev.index)
        C2.reg_save("R3 " + name, sp)
        res[k] = C3.compare3(sp[["pH", "pD", "pA"]].to_numpy(), c, name)
        tabs[k] = train_table(fr, cols, mt, ev)
        print(name, f"{res[k]['all']['d']:+.5f}", flush=True)

    # scelta sulle sole stagioni di validazione
    best_val = max(res[k]["val"]["d"] for k in ORDER)
    chosen = next(k for k in ORDER if res[k]["val"]["d"] >= best_val - TIE)
    L += ["### Varianti (ogni riga da sola vs baseline)", ""] + C3.md_table([res[k] for k in ORDER]) + [""]
    L += ["**Stagioni e partite di training per variante**", "",
          "| Variante | " + " | ".join(C2.season_label(s) for s in tab_base) + " |", "|---|" + "---:|" * len(tab_base),
          "| baseline | " + " | ".join(f"{v[0]} ({v[1]})" for v in tab_base.values()) + " |"]
    for k in ORDER:
        L.append(f"| {k} | " + " | ".join(f"{v[0]} ({v[1]})" for v in tabs[k].values()) + " |")
    L += ["", "(stagioni distinte con almeno una riga di training, e numero di righe)", ""]
    L += ["**Guadagno per stagione (Δ log-loss, baseline − variante)**", "",
          "| Variante | " + " | ".join(C2.season_label(s) for s in tab_base) + " |", "|---|" + "---:|" * len(tab_base)]
    for k in ORDER:
        L.append(f"| {k} | " + " | ".join(f"{v[0]:+.4f}" for v in res[k]["by_season"].values()) + " |")
    L += ["", f"**Scelta (criterio: Δ più alto sulle validazione 2019/20-2021/22, parità entro {TIE} → la più semplice): {chosen}** "
              f"(Δ validazione {res[chosen]['val']['d']:+.5f}). Verdetto (regola A del prereg): **{C3.verdict(res[chosen], 'all')}**.", ""]
    L += C3.md_detail(res[chosen], title=f"Dettaglio della variante scelta: {res[chosen]['name']}")
    with open(os.path.join(C3.PARTS, "A.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    pd.to_pickle(dict(res={k: {x: y for x, y in v.items() if x not in ("d_vec", "ok")} for k, v in res.items()},
                      chosen=chosen, spec_names={k: spec[k][0] for k in ORDER}), os.path.join(C3.R3_DIR, "r3_A.pkl"))
    print("\n".join(L))


if __name__ == "__main__":
    main()
