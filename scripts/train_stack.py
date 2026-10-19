#!/usr/bin/env python3
"""
Allena il Poisson-stack e salva coefficienti, scaler e rho in models/stack.json
(JSON, niente pickle). Il file contiene DUE modelli:

  without_xg  7 feature (dc_lmu, dc_lnu, sot_lmu, sot_lnu, pi_gd, pi_diff, eo_diff), dal 2013/14
  with_xg     le stesse + xg_lmu, xg_lnu (DC sugli xG Understat con ridge=2), dal 2016/17

eo_diff e' il rating Elo-Odds (backtest/eloodds.py, K=200): Elo per campionato aggiornato con le
probabilita' implicite delle quote di CHIUSURA di football-data.co.uk (senza margine, metodo power).

In produzione si usa with_xg; without_xg è il ripiego automatico (Understat non risponde
o mancano gli xG di una squadra) — vedi predictions/stack_predictor.py.

Salva anche "stats_v3" (backtest/stats_v3.py, versione s3-gap): per tiri, tiri in porta, corner, gialli e falli i due Poisson
(casa, ospite), gli alpha della Binomiale Negativa (totale e per squadra) in due varianti (with_xg / without_xg) come lo stack 1X2;
tiri e tiri in porta usano i GAP ratings (backtest/gap.py), la copula gaussiana (rho) per i mercati «chi ne fa di più», e la quota
dei gol nel primo tempo per lega. Il modello dei gialli ha in più l'effetto arbitro (backtest/refeffect.py, round 5): il training
ricalcola con le sole partite passate l'effetto di ogni arbitro e lo salva in "referees" (somme per arbitro, usate dal serving).
Lo storico degli arbitri viene da data/referees/matches.csv e da docs/history.csv (nessuna chiamata di rete).

Costruisce lo storico delle feature in walk-forward (ognuna calcolata solo con dati
precedenti alla partita) per i 5 campionati, poi stima le due regressioni di Poisson e
rho su tutto lo storico disponibile. Se Understat non risponde l'allenamento FALLISCE
(exit 1) senza toccare models/stack.json: meglio un modello vecchio che uno monco. Lo stesso vale se le quote
storiche (chiusura) di football-data.co.uk non si scaricano o sono troppo incomplete (Elo-Odds).
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

from backtest import data, eloodds, features, refeffect, stack, stats_v3, understat
from config import GAP_PARAMS, LEVEL_PARAMS, REFEREE_K, STATS_VERSION

OUT_PATH = os.path.join(REPO_ROOT, "models", "stack.json")

# nome -> (feature, prima stagione di training o None)
MODELS = {
    "without_xg": (stack.PRODUCTION_FEATURES_EO, None),
    "with_xg": (stack.XG_FEATURES_EO, stack.XG_FIRST_TRAIN_SEASON),
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


def train_stats_v3(feat, priors):
    """Modelli delle statistiche attese s3-gap (backtest/stats_v3.py): {variante: {statistica: dict JSON}}, ρ della copula, quota del
    primo tempo e parametri dei GAP ratings."""
    models = {}
    copula = {}
    for variant, with_xg in (("with_xg", True), ("without_xg", False)):
        models[variant] = {}
        for stat in stats_v3.ORDER:
            d, mh, ma, ok = stats_v3.train_stat(feat, stat, with_xg)
            spec = stats_v3.STATS3[stat]
            print(f"  [stats {variant}/{stat}] {d['meta']['n_train']} partite, alpha NB totale={d['alpha']:.4f}, per squadra={d['alpha_team']:.4f}"
                  + (f" (casa {d['alpha_home']:.4f}, ospite {d['alpha_away']:.4f})" if 'alpha_home' in d else ""), flush=True)
            models[variant][stat] = d
            if with_xg and stat in stats_v3.COPULA_PER_LEAGUE:
                per_league = stats_v3.COPULA_PER_LEAGUE[stat]
                rho = stats_v3.estimate_rho(feat[spec["hc"]][ok].to_numpy(), feat[spec["ac"]][ok].to_numpy(), mh, ma, stats_v3.team_alphas(d),
                                            division=feat.Division[ok].to_numpy() if per_league else None)
                copula[stat] = {"per_league": per_league, "rho": rho, "M": spec["M"]}
                print(f"  [copula {stat}] rho = {rho}", flush=True)
    level = stats_v3.build_level(feat, LEVEL_PARAMS)
    print(f"  [livello] registro fino al {', '.join(f'{k} {v}' for k, v in level['asof'].items())}; parametri (H, k): "
          + ", ".join(f"{s} {tuple(v)}" for s, v in level["params"].items()), flush=True)
    fh = stats_v3.train_first_half(feat)
    print(f"  [primo tempo] quota dei gol per lega: {', '.join(f'{k} {v:.3f}' for k, v in fh['share'].items())} ({fh['n']} partite)", flush=True)
    return {"version": 3, "gap": {"params": {k: list(v) for k, v in GAP_PARAMS.items()}, "priors": priors},
            "models": models, "copula": copula, "first_half": fh, "level": level}


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

    print("Controllo quote di chiusura (Elo-Odds)...", flush=True)
    try:
        odds_cov = eloodds.check_training_coverage(df)
    except eloodds.EloOddsError as e:
        print(f"ERRORE: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"  {odds_cov['closing']} partite con quote di chiusura, {odds_cov['prematch_fallback']} con ripiego "
          f"pre-partita, {odds_cov['none']} senza quote (su {odds_cov['matches']})", flush=True)

    print("Feature walk-forward (può richiedere diversi minuti)...", flush=True)
    feat = features.build_features(df)
    feat = feat.join(eloodds.build_features(df))
    feat = feat.join(features.build_xg_features(df)[["xg_lmu", "xg_lnu"]])
    feat = feat.join(features.build_stat_features(df))

    print("Effetto arbitro sui gialli...", flush=True)
    try:
        keys = refeffect.load_history_keys(df).reindex(feat.index)
    except refeffect.RefereeDataError as e:
        print(f"ERRORE: {e}", file=sys.stderr)
        sys.exit(1)
    cur = data.current_season()
    cur_rows = (feat.season == cur)
    print(f"  arbitro noto per {int(keys.notna().sum())} partite (dal 2016/17: {int(keys[feat.season >= 2016].notna().sum())}/"
          f"{int((feat.season >= 2016).sum())}); stagione corrente: {int(keys[cur_rows].notna().sum())}/{int(cur_rows.sum())}", flush=True)
    chk = refeffect.check_premier_league(df, keys.reindex(df.index))
    if chk["agree"] is not None:
        print(f"  coerenza con la colonna Referee di football-data.co.uk (Premier League, cognome): {chk['agree']:.1%} su {chk['n']} partite", flush=True)
        if chk["agree"] < 0.95:
            print("ERRORE: abbinamento degli arbitri incoerente con football-data.co.uk (< 95%)", file=sys.stderr)
            sys.exit(1)
    if keys[feat.season >= 2016].notna().mean() < 0.9:
        print("ERRORE: storico degli arbitri troppo incompleto (< 90% delle partite dal 2016/17)", file=sys.stderr)
        sys.exit(1)
    feat["ref_logR"], ref_state = refeffect.compute(feat, keys, REFEREE_K)
    print(f"  {ref_state['n_referees']} arbitri con storico, k={REFEREE_K}", flush=True)
    priors = stats_v3.gap_priors(df)
    feat = feat.join(stats_v3.gap_features(df, priors))
    mhf, maf = stats_v3.base_predictions(feat, "falli")
    feat["ref_logR_f"], ref_state_f = refeffect.compute_stat(feat, keys, mhf, maf, feat["HF"] + feat["AF"], REFEREE_K)
    print(f"  falli: {ref_state_f['n_referees']} arbitri con storico", flush=True)

    print("Stima degli stack...", flush=True)
    out = {
        "referees": ref_state,
        "referees_fouls": ref_state_f,
        "stats_v3": train_stats_v3(feat, priors),
        "version": 2,
        "models": {name: train_one(name, cols, min_season, feat)
                   for name, (cols, min_season) in MODELS.items()},
        "meta": {
            "trained_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "leagues": sorted(feat.Division.unique().tolist()),
            "xg_ridge": features.XG_RIDGE,
            "elo_odds": {"k": eloodds.ELO_ODDS_K, "odds_rows": odds_cov},
            "stats_version": STATS_VERSION,
            "note": ("Poisson-stack, feature in walk-forward (DC xi=0.0018, xG xi=0.003 con ridge sul solo "
                     "DC degli xG, finestra 5 anni, Elo-Odds K=200 sulle quote di chiusura). "
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
