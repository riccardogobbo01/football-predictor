#!/usr/bin/env python3
"""
Allena il Poisson-stack (senza Elo) e salva coefficienti, scaler e rho in
models/stack.json (JSON, niente pickle).

Costruisce lo storico delle feature in walk-forward (DC sui gol, DC sui tiri in porta,
pi-ratings; ognuna calcolata solo con dati precedenti alla partita) per i 5 campionati
dalla stagione 2013/14 a oggi, poi stima le due regressioni di Poisson e rho su tutto lo
storico disponibile. Pensato per girare una volta a settimana (.github/workflows/train.yml).

Richiede scikit-learn (solo per l'allenamento: il serving usa solo numpy).

Uso:
  python scripts/train_stack.py
"""
import json
import os
import sys
import time
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import numpy as np

from backtest import data, features, stack

OUT_PATH = os.path.join(REPO_ROOT, "models", "stack.json")
FEATS = stack.PRODUCTION_FEATURES


def main():
    t0 = time.time()
    print("Download/lettura dati football-data.co.uk...", flush=True)
    df = data.load_matches()

    print("Feature walk-forward (può richiedere diversi minuti)...", flush=True)
    feat = features.build_features(df)

    X = feat[FEATS]
    ok = X.notna().all(axis=1) & np.isfinite(X).all(axis=1)
    X, hg, ag = X[ok], feat.hg[ok], feat.ag[ok]
    print(f"  {len(X)} partite di training ({feat.date[ok].min().date()} → "
          f"{feat.date[ok].max().date()}), {len(feat) - len(X)} scartate", flush=True)

    print("Stima dello stack...", flush=True)
    model = stack.fit_stack(X, hg, ag)
    d = stack.stack_to_dict(model, FEATS, meta={
        "trained_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "n_train": int(len(X)),
        "first_match": str(feat.date[ok].min().date()),
        "last_match": str(feat.date[ok].max().date()),
        "leagues": sorted(feat.Division.unique().tolist()),
        "note": "Poisson-stack senza Elo; feature in walk-forward, ξ=0.0018, finestra 5 anni",
    })

    # Il serving (solo numpy) deve dare gli stessi gol attesi di scikit-learn
    sample = X.iloc[:: max(len(X) // 500, 1)]
    mu_sk, nu_sk = model["home"].predict(sample), model["away"].predict(sample)
    mu_js, nu_js, rho = stack.predict_from_dict(d, sample.to_numpy())
    if not (np.allclose(mu_sk, mu_js) and np.allclose(nu_sk, nu_js)):
        raise SystemExit("ERRORE: il modello serializzato non coincide con quello di scikit-learn")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=2)
        fh.write("\n")
    print(f"Salvato {OUT_PATH} — rho={d['rho']:.4f} — {time.time() - t0:.0f}s", flush=True)
    for side in ("home", "away"):
        print(f"  {side}: " + ", ".join(f"{f}={c:+.3f}" for f, c in zip(FEATS, d[side]["coef"])))


if __name__ == "__main__":
    main()
