"""
Modello di riferimento per le statistiche attese (tiri, corner, gialli).
Usato nel backtest fuori dal repo (test 2019/20 -> 2026/27, 12.403 partite, top-5 campionati).

Idea: per ogni statistica,
  1. un "Dixon-Coles senza tau" (Poisson con attacco/difesa per squadra, casa, decadimento
     xi=0.0018, finestra 5 anni, ridge=1.0) fittato sul conteggio della statistica:
       tiri  -> HS/AS, corner -> HC/AC, gialli -> HY/AY
     più un secondo fit "ausiliario" che aiuta la statistica:
       tiri  -> tiri in porta HST/AST (sot_lmu/sot_lnu, già in produzione)
       corner-> tiri HS/AS
       gialli-> falli HF/AF
  2. una regressione di Poisson per squadra di casa e una per l'ospite (feature standardizzate,
     alpha=1e-3), allenate su tutte le leghe insieme dalla stagione 2016/17, con le feature:
       own:    log mu/nu della statistica + log mu/nu della statistica ausiliaria
       common: dc_lmu, dc_lnu, xg_lmu, xg_lnu (DC sugli xG con ridge 2, già in produzione),
               pi_diff, |pi_diff|, gd_exp = exp(dc_lmu)-exp(dc_lnu), |gd_exp|,
               dummy di lega (E0, D1, SP1, F1; Serie A = base)
     Le feature di "stato di gara" (gd_exp, pi_diff) servono perché la favorita tira e batte
     più corner e l'avversaria commette più falli: è la parte che il metodo a medie non vede.
  3. la distribuzione del TOTALE è una Binomiale Negativa con media m = mu_casa + mu_ospite e
     varianza m + alpha*m^2; alpha stimato a momenti sul training:
       alpha = max( sum((y - m)^2 - m) / sum(m^2), 1e-4 )
     Valori trovati: tiri ~0.009, corner ~0.013, gialli ~0.0015.
"""
import numpy as np
from scipy.stats import nbinom
from sklearn.linear_model import PoissonRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline

STATS = {
    # nome: (col casa, col ospite, col ausiliaria casa, col ausiliaria ospite)
    "tiri":   ("HS", "AS", "HST", "AST"),
    "corner": ("HC", "AC", "HS",  "AS"),
    "gialli": ("HY", "AY", "HF",  "AF"),
}
LINES = {"tiri": [23.5, 25.5, 27.5], "corner": [8.5, 9.5, 10.5, 11.5], "gialli": [2.5, 3.5, 4.5, 5.5]}
STAT_XI, STAT_RIDGE = 0.0018, 1.0
COMMON = ["dc_lmu", "dc_lnu", "xg_lmu", "xg_lnu", "pi_diff", "abs_pi", "gd_exp", "abs_gd",
          "lg_E0", "lg_D1", "lg_SP1", "lg_F1"]


def own_features(stat):
    return [f"{stat}_lh", f"{stat}_la", f"{stat}_aux_lh", f"{stat}_aux_la"]


def fit_stat_model(X_train, y_home, y_away):
    """X_train: DataFrame con own_features(stat) + COMMON. Restituisce i due modelli + alpha."""
    mh = make_pipeline(StandardScaler(), PoissonRegressor(alpha=1e-3, max_iter=2000)).fit(X_train, y_home)
    ma = make_pipeline(StandardScaler(), PoissonRegressor(alpha=1e-3, max_iter=2000)).fit(X_train, y_away)
    m = mh.predict(X_train) + ma.predict(X_train)
    y = np.asarray(y_home) + np.asarray(y_away)
    alpha = max(float(((y - m) ** 2 - m).sum() / (m ** 2).sum()), 1e-4)
    return dict(home=mh, away=ma, alpha=alpha)


def stat_distribution(mu_home, mu_away, alpha, lines):
    """Media per squadra, totale, intervallo 80% e probabilità Over per ogni linea."""
    m = mu_home + mu_away
    n = 1.0 / alpha
    p = n / (n + m)
    return dict(
        home=mu_home, away=mu_away, total=m,
        lo80=nbinom.ppf(0.10, n, p), hi80=nbinom.ppf(0.90, n, p),
        over={L: 1 - nbinom.cdf(np.floor(L), n, p) for L in lines},
    )
