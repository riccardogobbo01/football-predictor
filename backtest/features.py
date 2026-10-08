"""
Feature walk-forward per il Poisson-stack (Step 2). Tutte calcolate SOLO con dati
precedenti alla partita:

  dc_lmu, dc_lnu    log gol attesi del Dixon-Coles sui gol (xi=0.0018, finestra 5 anni)
  sot_lmu, sot_lnu  log tiri in porta attesi di un Poisson "DC senza tau" su HST/AST
  pi_gd, pi_diff    pi-ratings (lam=0.06, gam=0.6, c=3), in sequenza per lega
  elo_diff          ClubElo casa - trasferta (backtest/elo.py)

Il costoso walk-forward del DC viene messo in cache (data/cache/core_features.pkl).
"""
import os

import numpy as np
import pandas as pd

from . import models

XI = 0.0018
FEATURE_START = "2013-07-01"          # primo rifit: dalla stagione 2013/14
CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "data", "cache", "core_features.pkl")


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
    core = pd.concat(parts).sort_index()
    return df.loc[core.index].join(core)


def build_features(df, rebuild=False, verbose=True):
    """DataFrame delle partite da FEATURE_START in poi con le feature core (senza Elo)."""
    key = (len(df), str(df.date.max().date()))
    if not rebuild and os.path.exists(CACHE_PATH):
        cached = pd.read_pickle(CACHE_PATH)
        if cached.get("key") == key:
            if verbose:
                print("  feature core lette dalla cache")
            return cached["feat"]
    feat = _build_core(df, verbose)
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    pd.to_pickle({"key": key, "feat": feat}, CACHE_PATH)
    return feat
