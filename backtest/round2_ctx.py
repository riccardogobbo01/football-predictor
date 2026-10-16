"""
Round 2 — contesto condiviso (dati, baseline in cache), registro delle varianti e confronto appaiato.
"""
import os

import numpy as np
import pandas as pd

from backtest import data, stack
from backtest.round2_lib import (CACHE, baseline_frame, eval_set, load_all, metric_vecs, run_stack)

R2_DIR = os.path.join(CACHE, "round2")
CTX_PATH = os.path.join(R2_DIR, "ctx.pkl")
REG_PATH = os.path.join(R2_DIR, "registry.pkl")
os.makedirs(R2_DIR, exist_ok=True)


class Ctx:
    pass


def get_ctx(rebuild=False):
    """df completo, frame di feature del baseline, insieme di valutazione `ev` e previsioni baseline."""
    if not rebuild and os.path.exists(CTX_PATH):
        return pd.read_pickle(CTX_PATH)
    df = load_all(verbose=False)
    feat = baseline_frame(df)
    ev = eval_set(feat)
    sp = run_stack(feat, stack.XG_FEATURES, ev)
    c = Ctx()
    c.df, c.feat, c.ev, c.base_sp = df, feat, ev, sp
    c.y = ev.res.to_numpy()
    pd.to_pickle(c, CTX_PATH)
    return c


def reg_load():
    return pd.read_pickle(REG_PATH) if os.path.exists(REG_PATH) else {}


def reg_save(name, sp, meta=None):
    """sp: DataFrame con pH,pD,pA (e opz. mu,nu) indicizzato come ev."""
    r = reg_load()
    r[name] = dict(sp=sp, meta=meta or {})
    pd.to_pickle(r, REG_PATH)


def season_label(s):
    return f"{s}/{(s + 1) % 100:02d}"


def compare(P_var, P_base, ev, boot, name=""):
    """Metriche della variante e delta (base - variante: positivo = variante migliore) con IC 95%
    bootstrap appaiato per partita, per stagione e per lega. Righe con NaN escluse da entrambe."""
    y = ev.res.to_numpy()
    ok = np.isfinite(P_var).all(1) & np.isfinite(P_base).all(1)
    lv, rv, bv = metric_vecs(P_var[ok], y[ok])
    lb, rb, bb = metric_vecs(P_base[ok], y[ok])
    out = dict(name=name, n=int(ok.sum()), ll=lv.mean(), rps=rv.mean(), brier=bv.mean(),
               ll_base=lb.mean(), rps_base=rb.mean(), brier_base=bb.mean())
    for k, (a, b) in dict(ll=(lb, lv), rps=(rb, rv), brier=(bb, bv)).items():
        m, lo, hi = boot.ci(a - b)
        out[f"d_{k}"], out[f"lo_{k}"], out[f"hi_{k}"] = m, lo, hi
    d = lb - lv
    seas = ev.season.to_numpy()[ok]
    lg = ev.Division.to_numpy()[ok]
    out["by_season"] = {int(s): (float(d[seas == s].mean()), int((seas == s).sum())) for s in np.unique(seas)}
    out["by_league"] = {l: (float(d[lg == l].mean()), int((lg == l).sum())) for l in data.LEAGUES}
    out["seasons_better"] = (sum(v[0] > 0 for v in out["by_season"].values()), len(out["by_season"]))
    return out


# ───────────────────────────── formattazione markdown ─────────────────────────
def md_variant(res, title=None, extra_note=None):
    """Sezione markdown per una variante: metriche, delta con IC, per stagione, per lega."""
    L = []
    if title:
        L += [f"**{title}**", ""]
    if extra_note:
        L += [extra_note, ""]
    L += ["| Metrica | Variante | Baseline | Δ (base − variante) | IC 95% |", "|---|---:|---:|---:|---|"]
    for k, lab in (("ll", "Log-loss 1X2"), ("rps", "RPS"), ("brier", "Brier")):
        L.append(f"| {lab} | {res[k]:.4f} | {res[k + '_base']:.4f} | {res['d_' + k]:+.5f} | "
                 f"[{res['lo_' + k]:+.5f}, {res['hi_' + k]:+.5f}] |")
    L += ["", f"(Δ positivo = variante migliore; N = {res['n']}; stagioni migliorate: "
              f"{res['seasons_better'][0]}/{res['seasons_better'][1]})", ""]
    L += ["| Stagione | " + " | ".join(season_label(s) for s in res["by_season"]) + " |",
          "|---|" + "---:|" * len(res["by_season"]),
          "| Δ log-loss | " + " | ".join(f"{v[0]:+.4f}" for v in res["by_season"].values()) + " |",
          "| N | " + " | ".join(str(v[1]) for v in res["by_season"].values()) + " |", ""]
    L += ["| Lega | " + " | ".join(data.LEAGUE_NAMES[l] for l in res["by_league"]) + " |",
          "|---|" + "---:|" * len(res["by_league"]),
          "| Δ log-loss | " + " | ".join(f"{v[0]:+.4f}" for v in res["by_league"].values()) + " |", ""]
    return L


def md_summary_rows(results):
    """Righe per la tabella riassuntiva di un esperimento."""
    L = ["| Variante | Log-loss | RPS | Brier | Δ log-loss vs baseline | IC 95% | Stagioni migliorate |",
         "|---|---:|---:|---:|---:|---|---:|"]
    for r in results:
        L.append(f"| {r['name']} | {r['ll']:.4f} | {r['rps']:.4f} | {r['brier']:.4f} | {r['d_ll']:+.5f} | "
                 f"[{r['lo_ll']:+.5f}, {r['hi_ll']:+.5f}] | {r['seasons_better'][0]}/{r['seasons_better'][1]} |")
    return L
