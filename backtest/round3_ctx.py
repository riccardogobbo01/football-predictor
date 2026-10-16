"""
Round 3 — contesto condiviso: nuovo baseline (modello in produzione v6-eloodds, with_xg), confronti appaiati con
due bootstrap (per partita e a blocchi per settimana ISO), suddivisione validazione / held-out, tabelle markdown.
"""
import os

import numpy as np
import pandas as pd

from backtest import data, eloodds, round2_ctx as C2, stack
from backtest.round2_lib import metric_vecs, run_stack

R3_DIR = C2.R2_DIR
PARTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "round3_parts")
os.makedirs(PARTS, exist_ok=True)
CTX3_PATH = os.path.join(R3_DIR, "ctx3.pkl")
VALIDATION = (2019, 2020, 2021)           # stagioni di scelta dei parametri
N_BOOT = 5000
CLOSING_LL = None                          # riempito da closing_logloss()


class Ctx3:
    pass


def get_ctx3(rebuild=False):
    if not rebuild and os.path.exists(CTX3_PATH):
        return pd.read_pickle(CTX3_PATH)
    c2 = C2.get_ctx()
    feat = c2.feat.copy()
    feat[eloodds.FEATURE] = eloodds.build_features(c2.df).reindex(feat.index)     # Elo-Odds di produzione
    sp = run_stack(feat, stack.XG_FEATURES_EO, c2.ev)
    c = Ctx3()
    c.df, c.feat, c.ev, c.y, c.base_sp = c2.df, feat, c2.ev, c2.y, sp
    c.weeks = c2.ev.date.dt.strftime("%G-%V").to_numpy()
    c.is_val = c2.ev.season.isin(VALIDATION).to_numpy()
    pd.to_pickle(c, CTX3_PATH)
    return c


def closing_logloss(c):
    from backtest.round2_lib import devig, ll_vec
    return float(ll_vec(devig(c.ev[["cl_h", "cl_d", "cl_a"]].to_numpy(float), "power"), c.y).mean())


# ───────────────────────────── bootstrap ─────────────────────────────
def ci_match(d, seed=11, n_boot=N_BOOT, chunk=250):
    d = np.asarray(d, float)
    n = len(d)
    rng = np.random.default_rng(seed)
    est = np.empty(n_boot)
    for s in range(0, n_boot, chunk):
        k = min(chunk, n_boot - s)
        est[s:s + k] = d[rng.integers(0, n, size=(k, n))].mean(1)
    return float(d.mean()), float(np.percentile(est, 2.5)), float(np.percentile(est, 97.5))


def ci_block(d, blocks, seed=12, n_boot=N_BOOT):
    """Bootstrap a blocchi (settimana ISO): tutte le partite della stessa settimana restano insieme."""
    d = np.asarray(d, float)
    codes, uniq = pd.factorize(np.asarray(blocks))
    sums = np.bincount(codes, d)
    cnt = np.bincount(codes).astype(float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(uniq), size=(n_boot, len(uniq)))
    est = sums[idx].sum(1) / cnt[idx].sum(1)
    return float(d.mean()), float(np.percentile(est, 2.5)), float(np.percentile(est, 97.5))


def _delta_block(d, weeks, key, out):
    m, lo, hi = ci_match(d)
    mb, lob, hib = ci_block(d, weeks)
    out[key] = dict(d=m, lo=lo, hi=hi, lob=lob, hib=hib, n=int(len(d)))


def compare3(P_var, c, name="", P_base=None):
    """Metriche e delta (baseline − variante) con IC per partita e a blocchi, su tutte / validazione / held-out;
    per stagione e per lega. Righe con NaN escluse da entrambi."""
    P_base = c.base_sp[["pH", "pD", "pA"]].to_numpy() if P_base is None else P_base
    y, ev = c.y, c.ev
    ok = np.isfinite(P_var).all(1) & np.isfinite(P_base).all(1)
    lv, rv, bv = metric_vecs(P_var[ok], y[ok])
    lb, rb, bb = metric_vecs(P_base[ok], y[ok])
    out = dict(name=name, n=int(ok.sum()), ll=lv.mean(), rps=rv.mean(), brier=bv.mean(),
               ll_base=lb.mean(), rps_base=rb.mean(), brier_base=bb.mean())
    d = lb - lv
    wk, val = c.weeks[ok], c.is_val[ok]
    _delta_block(d, wk, "all", out)
    _delta_block(d[val], wk[val], "val", out)
    _delta_block(d[~val], wk[~val], "held", out)
    out["d_rps"] = float((rb - rv).mean())
    out["d_brier"] = float((bb - bv).mean())
    seas, lg = ev.season.to_numpy()[ok], ev.Division.to_numpy()[ok]
    out["by_season"] = {int(s): (float(d[seas == s].mean()), int((seas == s).sum())) for s in np.unique(seas)}
    out["by_league"] = {l: (float(d[lg == l].mean()), int((lg == l).sum())) for l in data.LEAGUES}
    out["seasons_better"] = (sum(v[0] > 0 for v in out["by_season"].values()), len(out["by_season"]))
    out["d_vec"] = d
    out["ok"] = ok
    return out


# ───────────────────────────── markdown ─────────────────────────────
def _f(r, k, a="d"):
    x = r[k]
    return f"{x['d']:+.5f}"


def md_table(results, closing_ll=None, base_ll=None):
    L = ["| Variante | Log-loss | Δ tutte (IC per partita) | Δ tutte (IC a blocchi) | Δ validazione | Δ held-out (IC a blocchi) | Stagioni migliorate |",
         "|---|---:|---|---|---:|---|---:|"]
    for r in results:
        a, v, h = r["all"], r["val"], r["held"]
        L.append(f"| {r['name']} | {r['ll']:.4f} | {a['d']:+.5f} [{a['lo']:+.5f}, {a['hi']:+.5f}] | "
                 f"[{a['lob']:+.5f}, {a['hib']:+.5f}] | {v['d']:+.5f} | {h['d']:+.5f} [{h['lob']:+.5f}, {h['hib']:+.5f}] | "
                 f"{r['seasons_better'][0]}/{r['seasons_better'][1]} |")
    return L


def md_detail(r, title=None):
    L = [f"**{title or r['name']}**", "",
         "| Insieme | N | Δ log-loss | IC 95% per partita | IC 95% a blocchi per settimana |", "|---|---:|---:|---|---|"]
    for key, lab in (("all", "tutte le stagioni"), ("val", "validazione 2019/20-2021/22"), ("held", "held-out 2022/23→")):
        x = r[key]
        L.append(f"| {lab} | {x['n']} | {x['d']:+.5f} | [{x['lo']:+.5f}, {x['hi']:+.5f}] | [{x['lob']:+.5f}, {x['hib']:+.5f}] |")
    L += ["", f"Log-loss {r['ll']:.4f} (baseline {r['ll_base']:.4f}); Δ RPS {r['d_rps']:+.5f}; Δ Brier {r['d_brier']:+.5f}.", "",
          "| Stagione | " + " | ".join(C2.season_label(s) for s in r["by_season"]) + " |",
          "|---|" + "---:|" * len(r["by_season"]),
          "| Δ log-loss | " + " | ".join(f"{v[0]:+.4f}" for v in r["by_season"].values()) + " |", "",
          "| Lega | " + " | ".join(data.LEAGUE_NAMES[l] for l in r["by_league"]) + " |",
          "|---|" + "---:|" * len(r["by_league"]),
          "| Δ log-loss | " + " | ".join(f"{v[0]:+.4f}" for v in r["by_league"].values()) + " |", ""]
    return L


def verdict(r, kind="held"):
    """'migliora' / 'non distinguibile dal rumore' / 'peggiora' secondo la regola scritta nel prereg."""
    if kind == "held":
        x = r["held"]
        if x["d"] > 0 and x["lob"] > 0:
            return "migliora"
        if x["d"] < 0 and x["hib"] < 0:
            return "peggiora"
        return "non distinguibile dal rumore"
    a, h = r["all"], r["held"]            # regola A: Δ su tutte con IC a blocchi > 0 e held-out non peggiore di -0.0005
    if a["d"] > 0 and a["lob"] > 0 and h["d"] >= -0.0005:
        return "migliora"
    if a["d"] < 0 and a["hib"] < 0:
        return "peggiora"
    return "non distinguibile dal rumore"
