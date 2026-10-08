#!/usr/bin/env python3
"""
Allena il Poisson-stack e salva coefficienti, scaler e rho in models/stack.json
(JSON, niente pickle). Il file contiene DUE modelli:

  without_xg  6 feature (dc_lmu, dc_lnu, sot_lmu, sot_lnu, pi_gd, pi_diff), dal 2013/14
  with_xg     le stesse + xg_lmu, xg_lnu (DC sugli xG Understat), dal 2016/17

In produzione si usa with_xg; without_xg è il ripiego automatico (Understat non risponde
o mancano gli xG di una squadra) — vedi predictions/stack_predictor.py.

Costruisce lo storico delle feature in walk-forward (ognuna calcolata solo con dati
precedenti alla partita) per i 5 campionati, poi stima le due regressioni di Poisson e
rho su tutto lo storico disponibile. Se Understat non risponde l'allenamento FALLISCE
(exit 1) senza toccare models/stack.json: meglio un modello vecchio che uno monco.
Pensato per girare una volta a settimana (.github/workflows/train.yml).

Richiede scikit-learn (solo per l'allenamento: il serving usa solo numpy).

Uso:
  python scripts/train_stack.py
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

import numpy as np

from backtest import data, features, stack, understat

OUT_PATH = os.path.join(REPO_ROOT, "models", "stack.json")

# nome -> (feature, prima stagione di training o None)
MODELS = {
    "without_xg": (stack.PRODUCTION_FEATURES, None),
    "with_xg": (stack.XG_FEATURES, stack.XG_FIRST_TRAIN_SEASON),
}


def train_one(name, cols, min_season, feat):
    X = feat[cols]
    ok = X.notna().all(axis=1) & np.isfinite(X).all(axis=1)
    if min_season is not None:
        ok &= feat.season >= min_season
    X, hg, ag = X[ok], feat.hg[ok], feat.ag[ok]
    print(f"  [{name}] {len(X)} partite di training ({feat.date[ok].min().date()} → "
          f"{feat.date[ok].max().date()})", flush=True)

    model = stack.fit_stack(X, hg, ag)
    d = stack.stack_to_dict(model, cols, meta={
        "n_train": int(len(X)),
        "first_match": str(feat.date[ok].min().date()),
        "last_match": str(feat.date[ok].max().date()),
    })

    # Il serving (solo numpy) deve dare gli stessi gol attesi di scikit-learn
    sample = X.iloc[:: max(len(X) // 500, 1)]
    mu_js, nu_js, _ = stack.predict_from_dict(d, sample.to_numpy())
    if not (np.allclose(model["home"].predict(sample), mu_js)
            and np.allclose(model["away"].predict(sample), nu_js)):
        raise SystemExit(f"ERRORE: il modello {name} serializzato non coincide con scikit-learn")

    print(f"  [{name}] rho={d['rho']:.4f}", flush=True)
    for side in ("home", "away"):
        print(f"    {side}: " + ", ".join(f"{f}={c:+.3f}" for f, c in zip(cols, d[side]["coef"])))
    return d


def main():
    t0 = time.time()
    print("Download/lettura dati football-data.co.uk...", flush=True)
    df = data.load_matches()

    print("Download/lettura xG Understat...", flush=True)
    try:
        xg_raw = understat.load_xg()
        df = understat.attach_xg(df, xg_raw, strict=True)
    except understat.UnderstatError as e:
        print(f"ERRORE: xG Understat non disponibili o abbinamento insufficiente:\n{e}", file=sys.stderr)
        sys.exit(1)

    print("Feature walk-forward (può richiedere diversi minuti)...", flush=True)
    feat = features.build_features(df)
    feat = feat.join(features.build_xg_features(df)[["xg_lmu", "xg_lnu"]])

    print("Stima degli stack...", flush=True)
    out = {
        "version": 2,
        "models": {name: train_one(name, cols, min_season, feat)
                   for name, (cols, min_season) in MODELS.items()},
        "meta": {
            "trained_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "leagues": sorted(feat.Division.unique().tolist()),
            "note": ("Poisson-stack, feature in walk-forward (DC xi=0.0018, xG xi=0.003, finestra 5 anni). "
                     "In produzione with_xg; without_xg e' il ripiego."),
        },
    }

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
        fh.write("\n")
    print(f"Salvato {OUT_PATH} — {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
