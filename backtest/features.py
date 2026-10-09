"""
Feature walk-forward per il Poisson-stack. Tutte calcolate SOLO con dati precedenti alla
partita:

  dc_lmu, dc_lnu    log gol attesi del Dixon-Coles sui gol (xi=0.0018, finestra 5 anni)
  sot_lmu, sot_lnu  log tiri in porta attesi di un Poisson "DC senza tau" su HST/AST
  pi_gd, pi_diff    pi-ratings (lam=0.06, gam=0.6, c=3), in sequenza per lega
  xg_lmu, xg_lnu    log xG attesi di un Poisson "DC senza tau" sugli xG Understat
                    (xi=0.003, finestra 5 anni, ridge=2; da 2016/17: gli xG partono dal 2014)
  elo_diff          ClubElo casa - trasferta (backtest/elo.py, non usato in produzione)

Il costoso walk-forward viene messo in cache (data/cache/*.pkl).
"""
import os

import numpy as np
import pandas as pd

from . import models

XI = 0.0018
FEATURE_START = "2013-07-01"          # primo rifit: dalla stagione 2013/14
XG_XI = 0.003
XG_RIDGE = 2.0                        # penalità ridge SOLO sul DC degli xG (sul DC dei gol non serve)
XG_START = "2016-07-04"               # 2 anni di xG alle spalle; stessa griglia settimanale di FEATURE_START
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "data", "cache")
CACHE_PATH = os.path.join(CACHE_DIR, "core_features.pkl")


def _xg_cache_path(ridge):
    name = "xg_features.pkl" if not ridge else f"xg_features_r{ridge:g}.pkl"
    return os.path.join(CACHE_DIR, name)


CORE_COLS = ["dc_lmu", "dc_lnu", "dc_pH", "dc_pD", "dc_pA",
             "sot_lmu", "sot_lnu", "pi_gd", "pi_diff"]


def pi_features(pi_df, c=3.0):
    eh = np.sign(pi_df.pi_hh) * (10 ** (pi_df.pi_hh.abs() / c) - 1)
    ea = np.sign(pi_df.pi_aa) * (10 ** (pi_df.pi_aa.abs() / c) - 1)
    return pd.DataFrame({"pi_gd": eh - ea,
                         "pi_diff": (pi_df.pi_hh + pi_df.pi_ha) / 2 - (pi_df.pi_ah + pi_df.pi_aa) / 2})


def _build_core(df, verbose=True):
    parts = []
    for lg, g in df.groupby("Division"):
        if verbose:
            print(f"  [{lg}] DC sui gol...", flush=True)
        wg = models.walk_forward_dc(g, XI, start=FEATURE_START)
        wg = models.add_dc_probs(wg)
        if verbose:
            print(f"  [{lg}] DC sui tiri in porta (senza tau)...", flush=True)
        ws = models.walk_forward_dc(g, XI, start=FEATURE_START, use_tau=False, gx="HST", gy="AST")
        if verbose:
            print(f"  [{lg}] pi-ratings...", flush=True)
        pi = pi_features(models.pi_ratings(g))

        f = pd.DataFrame(index=wg.index)
        f["dc_lmu"], f["dc_lnu"] = np.log(wg.mu), np.log(wg.nu)
        f["dc_pH"], f["dc_pD"], f["dc_pA"] = wg.pH, wg.pD, wg.pA
        f["sot_lmu"], f["sot_lnu"] = np.log(ws.mu.reindex(wg.index)), np.log(ws.nu.reindex(wg.index))
        f = f.join(pi)
        parts.append(f)
    return pd.concat(parts).sort_index()


def _cached(path, key, rebuild):
    if not rebuild and os.path.exists(path):
        cached = pd.read_pickle(path)
        if cached.get("key") == key:
            return cached
    return None


def build_features(df, rebuild=False, verbose=True):
    """Partite da FEATURE_START in poi con le feature core (senza Elo, senza xG)."""
    key = (len(df), str(df.date.max().date()))
    cached = _cached(CACHE_PATH, key, rebuild)
    if cached is not None:
        if verbose:
            print("  feature core lette dalla cache")
        core = cached["core"] if "core" in cached else cached["feat"][CORE_COLS]
    else:
        core = _build_core(df, verbose)
        os.makedirs(CACHE_DIR, exist_ok=True)
        pd.to_pickle({"key": key, "core": core}, CACHE_PATH)
    return df.loc[core.index].join(core)


def build_xg_features(df, ridge=XG_RIDGE, rebuild=False, verbose=True):
    """xg_lmu, xg_lnu in walk-forward (indicizzati come df). Richiede le colonne xg_h/xg_a.
    ridge: penalità ridge del fit (default XG_RIDGE, quella di produzione; 0 = senza)."""
    key = (len(df), str(df.date.max().date()), int(df.xg_h.notna().sum()), ridge)
    cache_path = _xg_cache_path(ridge)
    cached = _cached(cache_path, key, rebuild)
    if cached is not None:
        if verbose:
            print("  feature xG lette dalla cache")
        return cached["xg"]

    parts = []
    for lg, g in df.groupby("Division"):
        if verbose:
            print(f"  [{lg}] DC sugli xG (senza tau, xi={XG_XI}, ridge={ridge:g})...", flush=True)
        w = models.walk_forward_dc(g, XG_XI, start=XG_START, use_tau=False, gx="xg_h", gy="xg_a",
                                   ridge=ridge)
        parts.append(pd.DataFrame({"xg_lmu": np.log(w.mu), "xg_lnu": np.log(w.nu)}, index=w.index))
    xg = pd.concat(parts).sort_index()
    os.makedirs(CACHE_DIR, exist_ok=True)
    pd.to_pickle({"key": key, "xg": xg}, cache_path)
    return xg
