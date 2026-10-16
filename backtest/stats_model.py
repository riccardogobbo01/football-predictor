"""
Modello delle "Statistiche attese" (tiri, corner, gialli): implementazione per il repo della
specifica in backtest/stats_model_ref.py (leggere la sua docstring).

Per ogni statistica:
  1. Poisson attacco/difesa per squadra (Dixon-Coles senza tau, xi=0.0018, finestra 5 anni,
     ridge=1) sul conteggio, + uno su una statistica ausiliaria (in backtest/features.py,
     build_stat_features): tiri -> tiri in porta HST/AST (le sot_lmu/sot_lnu già usate dallo stack
     1X2), corner -> tiri HS/AS, gialli -> falli HF/AF.
  2. Due regressioni di Poisson (casa, ospite), feature standardizzate, alpha=1e-3, tutte le leghe
     insieme dal 2016/17: feature proprie + dc_lmu, dc_lnu, xg_lmu, xg_lnu, pi_diff, |pi_diff|,
     gd_exp, |gd_exp| e dummy di lega.
  3. Il totale è una Binomiale Negativa con media m = mu_casa + mu_ospite e varianza
     m + alpha*m^2 (alpha a momenti sul training).

Come lo stack 1X2 esistono due varianti: "with_xg" (come sopra) e "without_xg" (senza xg_lmu/xg_lnu),
usata quando gli xG non sono disponibili. Il serving usa solo numpy/scipy (coefficienti in JSON);
scikit-learn serve solo per allenare.
"""
import numpy as np
import pandas as pd
from scipy.stats import nbinom

from . import stack

# nome: (colonna casa, colonna ospite, ausiliaria casa, ausiliaria ospite) — come stats_model_ref.STATS
STATS = {
    "tiri":   ("HS", "AS", "HST", "AST"),
    "corner": ("HC", "AC", "HS", "AS"),
    "gialli": ("HY", "AY", "HF", "AF"),
}
PAGE_KEY = {"tiri": "shots", "corner": "corners", "gialli": "yellows"}   # chiavi in predictions.json
LINES = {"tiri": [23.5, 25.5, 27.5], "corner": [8.5, 9.5, 10.5, 11.5], "gialli": [2.5, 3.5, 4.5, 5.5]}
COMMON = ["dc_lmu", "dc_lnu", "xg_lmu", "xg_lnu", "pi_diff", "abs_pi", "gd_exp", "abs_gd",
          "lg_E0", "lg_D1", "lg_SP1", "lg_F1"]
LEAGUE_DUMMIES = {"E0": "lg_E0", "D1": "lg_D1", "SP1": "lg_SP1", "F1": "lg_F1"}   # Serie A = base
XG_COLS = ["xg_lmu", "xg_lnu"]
REG_ALPHA = 1e-3
FIRST_TRAIN_SEASON = 2016      # gli xG partono dal 2014; i fit delle statistiche dal 2016-07

# dove stanno (log mu, log nu) della statistica e di quella ausiliaria (colonne di feat)
OWN_COLS = {"tiri": ("tiri_lh", "tiri_la"), "corner": ("corner_lh", "corner_la"),
            "gialli": ("gialli_lh", "gialli_la")}
AUX_COLS = {"tiri": ("sot_lmu", "sot_lnu"), "corner": ("tiri_lh", "tiri_la"),
            "gialli": ("falli_lh", "falli_la")}


def own_features(stat):
    return [f"{stat}_lh", f"{stat}_la", f"{stat}_aux_lh", f"{stat}_aux_la"]


REFEREE_STATS = ("gialli",)     # statistiche con effetto arbitro (round 5: log R come regressore, ultima colonna)
REFEREE_COL = "ref_logR"


def feature_names(stat, with_xg=True, referee=False):
    names = own_features(stat) + [c for c in COMMON if with_xg or c not in XG_COLS]
    return names + ([REFEREE_COL] if referee and stat in REFEREE_STATS else [])


def common_frame(feat) -> pd.DataFrame:
    """Feature comuni a tutte le statistiche (stato di gara, rating, lega)."""
    out = pd.DataFrame(index=feat.index)
    out["dc_lmu"], out["dc_lnu"] = feat["dc_lmu"], feat["dc_lnu"]
    out["xg_lmu"], out["xg_lnu"] = feat["xg_lmu"], feat["xg_lnu"]
    out["pi_diff"] = feat["pi_diff"]
    out["abs_pi"] = feat["pi_diff"].abs()
    gd = np.exp(feat["dc_lmu"]) - np.exp(feat["dc_lnu"])
    out["gd_exp"], out["abs_gd"] = gd, gd.abs()
    for div, col in LEAGUE_DUMMIES.items():
        out[col] = (feat["Division"] == div).astype(float)
    return out


def design(feat, stat, with_xg=True, referee=False) -> pd.DataFrame:
    """Matrice delle feature (nell'ordine di feature_names) per una statistica. referee=True aggiunge, per le statistiche in
    REFEREE_STATS, la colonna ref_logR (log dell'effetto arbitro, backtest/refeffect.py) che deve essere in feat."""
    own, aux = OWN_COLS[stat], AUX_COLS[stat]
    X = pd.DataFrame({f"{stat}_lh": feat[own[0]], f"{stat}_la": feat[own[1]],
                      f"{stat}_aux_lh": feat[aux[0]], f"{stat}_aux_la": feat[aux[1]]}, index=feat.index)
    X = X.join(common_frame(feat))
    if referee and stat in REFEREE_STATS:
        X[REFEREE_COL] = feat[REFEREE_COL]
    return X[feature_names(stat, with_xg, referee)]


def fit_stat_model(X_train, y_home, y_away):
    """Due Poisson (casa, ospite) + alpha della Binomiale Negativa a momenti."""
    from sklearn.linear_model import PoissonRegressor
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    mh = make_pipeline(StandardScaler(), PoissonRegressor(alpha=REG_ALPHA, max_iter=2000)).fit(X_train, y_home)
    ma = make_pipeline(StandardScaler(), PoissonRegressor(alpha=REG_ALPHA, max_iter=2000)).fit(X_train, y_away)
    m = mh.predict(X_train) + ma.predict(X_train)
    y = np.asarray(y_home) + np.asarray(y_away)
    alpha = max(float(((y - m) ** 2 - m).sum() / (m ** 2).sum()), 1e-4)
    return dict(home=mh, away=ma, alpha=alpha)


def predict_means(model, X):
    return model["home"].predict(X), model["away"].predict(X)


# ── serializzazione JSON (solo numpy in produzione) ────────────────────────────────
def model_to_dict(model, features, meta=None):
    return {"features": list(features), "alpha": float(model["alpha"]),
            "home": stack._side_to_dict(model["home"]), "away": stack._side_to_dict(model["away"]),
            "meta": meta or {}}


def means_from_dict(d, X):
    X = np.asarray(X, float)
    return stack._side_predict(d["home"], X), stack._side_predict(d["away"], X)


# ── distribuzione del totale ─────────────────────────────────────────────────────
def stat_distribution(mu_home, mu_away, alpha, lines):
    """Media per squadra, totale, intervallo 80% e probabilità Over per ogni linea (NB sul totale)."""
    mu_home, mu_away = np.asarray(mu_home, float), np.asarray(mu_away, float)
    m = mu_home + mu_away
    n = 1.0 / alpha
    p = n / (n + m)
    return dict(
        home=mu_home, away=mu_away, total=m,
        lo80=nbinom.ppf(0.10, n, p), hi80=nbinom.ppf(0.90, n, p),
        over={L: 1 - nbinom.cdf(np.floor(L), n, p) for L in lines},
    )


def page_stats(stat, mu_home, mu_away, alpha):
    """Righe per la pagina (una per partita): valori per squadra, totale, intervallo 80% e Over/Under."""
    d = stat_distribution(mu_home, mu_away, alpha, LINES[stat])
    rows = []
    for i in range(len(d["total"])):
        rows.append({"home": round(float(d["home"][i]), 1), "away": round(float(d["away"][i]), 1),
                     "total": round(float(d["total"][i]), 1),
                     "lo80": int(d["lo80"][i]), "hi80": int(d["hi80"][i]),
                     "over": {f"{L:g}": round(float(d["over"][L][i]), 4) for L in LINES[stat]}})
    return rows
