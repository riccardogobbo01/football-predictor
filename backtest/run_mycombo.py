"""MyCombo — validazione walk-forward PRIMA della pubblicazione (stagioni 2022/23-2025/26; 2026/27 in corso descrittivo). Protocollo in backtest/mycombo_parts/prereg.md.
Per ogni partita di test: parametri del modello come in produzione, fuori campione (gol: stack walk-forward; statistiche: stats_v3 con livello stagionale e arbitro; quota del primo tempo
e matrice di correlazione stimate SOLO sulle stagioni precedenti), simulazione di 20.000 scenari, combo proposte dall'algoritmo di produzione, esito reale di ogni giocata.

Da lanciare (modalita' isolata, una stagione per volta; ogni passo e' in cache):
  python -I -X utf8 backtest/run_mycombo.py PREP            # parametri, residui e matrici di correlazione
  python -I -X utf8 backtest/run_mycombo.py SEASON 2022 [limite_partite]
  python -I -X utf8 backtest/run_mycombo.py REPORT          # tabelle e models/mycombo_corr.json"""
import json
import os
import pickle
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd
from scipy.special import ndtri
from scipy.stats import nbinom

from backtest import models, stats_v3
from backtest.run_round7 import prepare
from backtest.run_round7_prod import level_run
from config import LEVEL_PARAMS
from predictions import mycombo as MC

PD = os.path.join(REPO_ROOT, "backtest", "mycombo_parts")
CACHE = os.path.join(PD, "_cache")
os.makedirs(CACHE, exist_ok=True)
TEST_SEASONS = (2022, 2023, 2024, 2025)
CUR = 2026
ACT = {"tiri": ("HS", "AS"), "sot": ("HST", "AST"), "corner": ("HC", "AC"), "gialli": ("HY", "AY"), "falli": ("HF", "AF")}
LG_NAME = {"I1": "Serie A", "E0": "Premier League", "D1": "Bundesliga", "SP1": "La Liga", "F1": "Ligue 1"}


# ───────────────────────────── preparazione ─────────────────────────────
def build_universe():
    feat, gw, weeks, st = prepare()
    params = {k: LEVEL_PARAMS[k] for k in stats_v3.ORDER}
    level = stats_v3.build_level(feat, params, means={t: (st[t]["run"].mh, st[t]["run"].ma) for t in stats_v3.ORDER})
    n = len(feat)
    ok = (feat.season >= 2019).to_numpy() & gw.mu.notna().to_numpy() & feat.hg.notna().to_numpy() & feat.HTHG.notna().to_numpy() & feat.HTAG.notna().to_numpy()
    U = {"mu": gw.mu.to_numpy(float), "nu": gw.nu.to_numpy(float), "rho": gw.rho.to_numpy(float), "stats": {}, "act": {}}
    for s in stats_v3.ORDER:
        run, al = st[s]["run"], st[s]["al"]
        hc, ac = ACT[s]
        has = (run.mh.notna() & feat[hc].notna() & feat[ac].notna() & (feat.season >= 2019)).to_numpy()
        mh2, ma2 = level_run(feat, s, run.mh, run.ma, level, has)
        U["stats"][s] = (mh2.to_numpy(float), ma2.to_numpy(float), al["ah"].to_numpy(float), al["aa"].to_numpy(float))
        U["act"][s] = (feat[hc].to_numpy(float), feat[ac].to_numpy(float))
        ok &= has & np.isfinite(U["stats"][s][2]) & np.isfinite(U["stats"][s][3])
    U["hg"], U["ag"] = feat.hg.to_numpy(float), feat.ag.to_numpy(float)
    U["hth"], U["ath"] = feat.HTHG.to_numpy(float), feat.HTAG.to_numpy(float)
    U["season"], U["lg"] = feat.season.to_numpy(), feat.Division.to_numpy()
    U["week"] = weeks
    U["date"] = feat.date.dt.strftime("%Y-%m-%d").to_numpy()
    U["home"], U["away"] = feat.HomeTeam.to_numpy(), feat.AwayTeam.to_numpy()
    U["ok"] = ok
    # quota dei gol del primo tempo per lega e stagione di test (solo stagioni precedenti)
    f = feat[(feat.season >= 2016) & feat.HTHG.notna() & feat.HTAG.notna() & feat.hg.notna()]
    U["share"] = {}
    for s in list(TEST_SEASONS) + [CUR]:
        g = f[f.season < s]
        U["share"][s] = {lg: float((x.HTHG + x.HTAG).sum() / (x.hg + x.ag).sum()) for lg, x in g.groupby("Division")}
    # punteggi normali (PIT randomizzata) delle 12 variabili, per le righe valide
    rng = np.random.default_rng(2024)
    idx = np.where(ok)[0]
    M = models.score_matrix(U["mu"][idx], U["nu"][idx], U["rho"][idx], MC.G)
    Z = np.full((n, 12), np.nan)
    for col, (g, axis) in enumerate(((U["hg"], 2), (U["ag"], 1))):
        F = np.cumsum(M.sum(axis), axis=1)
        gi = g[idx].astype(int)
        lo = np.where(gi > 0, F[np.arange(len(idx)), np.maximum(gi - 1, 0)], 0.0)
        hi = F[np.arange(len(idx)), np.minimum(gi, MC.G)]
        Z[idx, col] = ndtri(np.clip(lo + rng.random(len(idx)) * (hi - lo), 1e-9, 1 - 1e-9))
    for j, s in enumerate(MC.STATS):
        mh, ma, ah, aa = U["stats"][s]
        yh, ya = U["act"][s]
        for side, m, a, y, col in (("c", mh, ah, yh, 2 + 2 * j), ("o", ma, aa, ya, 3 + 2 * j)):
            nn = 1.0 / a[idx]
            pp = nn / (nn + m[idx])
            yi = y[idx].astype(int)
            lo, hi = nbinom.cdf(yi - 1, nn, pp), nbinom.cdf(yi, nn, pp)
            Z[idx, col] = ndtri(np.clip(lo + rng.random(len(idx)) * (hi - lo), 1e-9, 1 - 1e-9))
    U["Z"] = Z
    return U


def get_universe(rebuild=False):
    fp = os.path.join(CACHE, "universe.pkl")
    if os.path.exists(fp) and not rebuild:
        return pickle.load(open(fp, "rb"))
    U = build_universe()
    pickle.dump(U, open(fp, "wb"))
    return U


def corr_matrix(U, upto_season):
    """Correlazione dei punteggi normali sulle stagioni 2019/20 … upto_season − 1 (fuori campione)."""
    m = U["ok"] & (U["season"] < upto_season)
    return np.corrcoef(U["Z"][m].T), int(m.sum())


# ───────────────────────────── una stagione ─────────────────────────────
def run_season(U, season, limit=None):
    t0 = time.time()
    C, n_train = corr_matrix(U, season)
    cc = MC.prepare_corr(C)
    rows = np.where(U["ok"] & (U["season"] == season))[0]
    if limit:
        rows = rows[:: max(len(rows) // limit, 1)][:limit]
    combos, legs = [], []
    for k, i in enumerate(rows):
        p = {"mu": U["mu"][i], "nu": U["nu"][i], "rho": U["rho"][i], "share": U["share"][season].get(U["lg"][i], 0.44),
             "stats": {s: tuple(float(x[i]) for x in U["stats"][s]) for s in MC.STATS}}
        act = {"hg": U["hg"][i], "ag": U["ag"][i], "hth": U["hth"][i], "ath": U["ath"][i]}
        for s in MC.STATS:
            act[f"{s}_c"], act[f"{s}_o"] = U["act"][s][0][i], U["act"][s][1][i]
        sim = MC.simulate(p, cc, seed=int(i))
        specs = MC.catalog(p)
        gen = MC.generate(sim, specs, seed=int(i))
        hits = [bool(MC.eval_spec(sp, act)) for sp in specs]
        meta = (int(i), season, U["lg"][i], U["week"][i], U["date"][i], U["home"][i], U["away"][i])
        for j, sp in enumerate(specs):
            legs.append(meta[:4] + (MC.family(sp), MC.label(sp), float(gen["p_legs"][j]), hits[j]))
        for c in gen["combos"]:
            lh = [hits[j] for j in c["legs"]]
            combos.append(meta + (c["k"], [MC.label(specs[j]) for j in c["legs"]], [MC.family(specs[j]) for j in c["legs"]], c["p"], c["fair"], c["p_indep"], c["score"], lh, all(lh)))
        if (k + 1) % 200 == 0:
            print(f"  {season}: {k + 1}/{len(rows)} partite, {len(combos)} combo ({time.time() - t0:.0f}s)", flush=True)
    cols_c = ["row", "season", "lg", "week", "date", "home", "away", "k", "labels", "fams", "p", "fair", "p_indep", "score", "leg_hits", "hit"]
    cols_l = ["row", "season", "lg", "week", "fam", "label", "p", "hit"]
    out = {"combos": pd.DataFrame(combos, columns=cols_c), "legs": pd.DataFrame(legs, columns=cols_l), "n_train": n_train, "n_matches": len(rows), "secs": time.time() - t0}
    return out


# ───────────────────────────── main ─────────────────────────────
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "PREP"
    if mode == "PREP":
        U = get_universe(rebuild=True)
        print("righe valide:", int(U["ok"].sum()), "stagioni:", {int(s): int((U["ok"] & (U["season"] == s)).sum()) for s in np.unique(U["season"][U["ok"]])})
    elif mode == "SEASON":
        season = int(sys.argv[2])
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
        U = get_universe()
        r = run_season(U, season, limit)
        fp = os.path.join(CACHE, f"season_{season}{'_test' if limit else ''}.pkl")
        pickle.dump(r, open(fp, "wb"))
        print(f"{season}: {r['n_matches']} partite, {len(r['combos'])} combo, {r['secs']:.0f}s -> {os.path.basename(fp)}")
