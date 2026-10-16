#!/usr/bin/env python3
"""
Backtest «come in produzione» dell'effetto arbitro sui gialli: usa le STESSE funzioni del training (backtest/refeffect.py,
backtest/stats_model.py con referee=True) e lo storico arbitri committato (data/referees/matches.csv), in walk-forward per
stagione (test dal 2019/20, training dal 2016/17), per entrambe le varianti del modello (with_xg e without_xg).
Riproduce il risultato del round 5 (log-loss del totale dei gialli ≈ 2.1085 con k=20, forma b).

Uso (dalla root del repo):  python -m backtest.run_referee_backtest
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import numpy as np
import pandas as pd
from scipy.stats import nbinom

from backtest import data, features, refeffect, stats_model as sm, understat
from backtest.round3_ctx import ci_block, ci_match
from config import REFEREE_K

RESULTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results_referee.md")
EXPECTED = 2.1085          # round 5, forma b, k=20, with_xg
TOL = 0.003


def nb_ll(y, m, alpha):
    n = 1.0 / alpha
    return -nbinom.logpmf(y, n, n / (n + m))


def main():
    print("Dati, xG e feature...")
    df = data.load_matches(verbose=False)
    df = understat.attach_xg(df, understat.load_xg(), strict=True)
    feat = features.build_features(df)
    feat = feat.join(features.build_xg_features(df)[["xg_lmu", "xg_lnu"]])
    feat = feat.join(features.build_stat_features(df))
    keys = refeffect.load_history_keys(df).reindex(feat.index)
    mh0, ma0 = refeffect.base_predictions(feat)                     # senza arbitro, with_xg (come nel training)
    m_tot = mh0 + ma0
    y = feat["HY"] + feat["AY"]
    R, _ = refeffect.referee_ratio(feat, y, m_tot, keys, REFEREE_K, refeffect.mbar_by_league(feat, m_tot))
    feat["ref_logR"] = np.log(R)

    test = (feat.date >= pd.Timestamp("2019-07-01")) & feat[["HY", "AY"]].notna().all(axis=1)
    lines = ["# Backtest «come in produzione» — effetto arbitro sui gialli", "",
             f"Walk-forward per stagione (training dal 2016/17, test dal 2019/20), effetto arbitro con k={REFEREE_K} come regressore (round 5, forma b). "
             f"Storico arbitri: data/referees/matches.csv (Transfermarkt 2016/17-2025/26 + football-data.org 2026/27). "
             f"Arbitro noto per {int(keys[feat.season >= 2016].notna().sum())}/{int((feat.season >= 2016).sum())} partite dal 2016/17.", ""]
    ok_all = True
    for variant, with_xg in (("with_xg", True), ("without_xg", False)):
        X0 = sm.design(feat, "gialli", with_xg)
        X1 = sm.design(feat, "gialli", with_xg, referee=True)
        has = X1.notna().all(axis=1)
        okt = has & feat["HY"].notna() & feat["AY"].notna()
        rows = []
        for s in sorted(feat.season.unique()):
            if s < refeffect.FIRST_TEST:
                continue
            tr = okt & (feat.season >= refeffect.FIRST_TRAIN) & (feat.season < s)
            te = test & has & (feat.season == s)
            if not te.any():
                continue
            m0 = sm.fit_stat_model(X0[tr], feat.HY[tr], feat.AY[tr])
            m1 = sm.fit_stat_model(X1[tr], feat.HY[tr], feat.AY[tr])
            a0, b0 = sm.predict_means(m0, X0[te])
            a1, b1 = sm.predict_means(m1, X1[te])
            yt = y[te].to_numpy()
            rows.append(pd.DataFrame({"base": nb_ll(yt, a0 + b0, m0["alpha"]), "ref": nb_ll(yt, a1 + b1, m1["alpha"]),
                                      "season": s, "week": feat.date[te].dt.strftime("%G-%V").to_numpy(),
                                      "mae0": np.abs(a0 + b0 - yt), "mae1": np.abs(a1 + b1 - yt)}, index=feat.index[te]))
        r = pd.concat(rows)
        d = (r.base - r.ref).to_numpy()
        m_, lo, hi = ci_match(d)
        _, lob, hib = ci_block(d, r.week.to_numpy())
        held = r.season.to_numpy() >= 2022
        mh, _, _ = ci_match(d[held])
        _, hl, hh = ci_block(d[held], r.week.to_numpy()[held])
        lines += [f"## Variante {variant}", "",
                  f"- {len(r)} partite di test. Log-loss del totale gialli: senza arbitro **{r.base.mean():.4f}** → con arbitro **{r.ref.mean():.4f}**.",
                  f"- Δ = {m_:+.5f}, IC 95% per partita [{lo:+.5f}, {hi:+.5f}], a blocchi per settimana [{lob:+.5f}, {hib:+.5f}]; "
                  f"held-out 2022/23→: {mh:+.5f} [{hl:+.5f}, {hh:+.5f}].",
                  f"- MAE del totale: {r.mae0.mean():.4f} → {r.mae1.mean():.4f}.",
                  "- Per stagione (Δ log-loss): " + ", ".join(f"{s}/{(s + 1) % 100:02d} {d[r.season.to_numpy() == s].mean():+.4f}" for s in sorted(r.season.unique())), ""]
        if variant == "with_xg":
            ok = abs(r.ref.mean() - EXPECTED) <= TOL and lob > 0
            ok_all &= ok
            lines += [f"**Controllo**: log-loss con arbitro {r.ref.mean():.4f} contro {EXPECTED} del round 5 (tolleranza ±{TOL}; la differenza residua "
                      f"viene dal 2026/27, dove ora l'arbitro è noto per le partite già giocate) e IC a blocchi > 0 → {'OK' if ok else 'NON SUPERATO'}.", ""]
        else:
            ok_all &= lob > 0
            lines += [f"**Controllo**: IC a blocchi del guadagno > 0 → {'OK' if lob > 0 else 'NON SUPERATO'} (variante di ripiego, non misurata nel round 5).", ""]
    text = "\n".join(lines)
    print(text)
    with open(RESULTS_PATH, "w", encoding="utf-8") as fh:
        fh.write(text)
    sys.exit(0 if ok_all else 2)


if __name__ == "__main__":
    main()
