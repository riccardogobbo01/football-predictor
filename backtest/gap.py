"""
GAP ratings (Wheatcroft) per una statistica di conteggio (tiri, tiri in porta): quattro rating per squadra (attacco e difesa in
casa e in trasferta) aggiornati partita dopo partita. Versione di produzione di quanto valutato nel round 6 (backtest/round6_lib.py).

  previsione casa     = max(mu_casa + A_casa[i] + D_trasf[j], 0.5)
  previsione ospite   = max(mu_trasf + A_trasf[j] + D_casa[i], 0.5)
  errore e = osservato - previsto; A_casa[i] += eta*e_c, D_trasf[j] += eta*e_c, A_trasf[j] += eta*e_o, D_casa[i] += eta*e_o,
  e una frazione gamma degli stessi aggiornamenti sui rating dell'altro campo.
mu = media di lega del campo, con prior di `PRIOR_N` partite pari alla media della statistica prima del 2014 (costante: si salva nel
modello). Rating per campionato, nessun azzeramento tra le stagioni, squadre nuove a 0. Le previsioni sono quelle PRIMA di ogni
partita: nessuna informazione sulla partita stessa.
"""
import numpy as np
import pandas as pd

PRIOR_N = 20
PRIOR_CUTOFF = pd.Timestamp("2014-01-01")
MIN_PRED = 0.5


def priors(df: pd.DataFrame, hc: str, ac: str) -> list:
    """Media (casa, ospite) della statistica nelle partite precedenti al 2014 (tutti i campionati)."""
    old = df[df.date < PRIOR_CUTOFF]
    return [float(old[hc].mean()), float(old[ac].mean())]


class GapState:
    def __init__(self):
        self.AH, self.DH, self.AA, self.DA = {}, {}, {}, {}
        self.sh = self.sa = 0.0
        self.n = 0


def _predict(st: GapState, h, a, prior):
    mu_h = (st.sh + PRIOR_N * prior[0]) / (st.n + PRIOR_N)
    mu_a = (st.sa + PRIOR_N * prior[1]) / (st.n + PRIOR_N)
    ph = max(mu_h + st.AH.get(h, 0.0) + st.DA.get(a, 0.0), MIN_PRED)
    pa = max(mu_a + st.AA.get(a, 0.0) + st.DH.get(h, 0.0), MIN_PRED)
    return ph, pa


def _update(st: GapState, h, a, xh, xa, ph, pa, eta, gamma):
    eh, ea = xh - ph, xa - pa
    st.AH[h] = st.AH.get(h, 0.0) + eta * eh
    st.DA[a] = st.DA.get(a, 0.0) + eta * eh
    st.AA[a] = st.AA.get(a, 0.0) + eta * ea
    st.DH[h] = st.DH.get(h, 0.0) + eta * ea
    if gamma:
        st.AA[h] = st.AA.get(h, 0.0) + gamma * eta * eh
        st.DH[a] = st.DH.get(a, 0.0) + gamma * eta * eh
        st.AH[a] = st.AH.get(a, 0.0) + gamma * eta * ea
        st.DA[h] = st.DA.get(h, 0.0) + gamma * eta * ea
    st.sh += xh
    st.sa += xa
    st.n += 1


def run_league(g: pd.DataFrame, hc: str, ac: str, eta: float, gamma: float, prior: list):
    """g: partite GIOCATE di UN campionato. Restituisce (previsioni pre-partita come DataFrame gap_h/gap_a con l'indice di g, stato finale)."""
    g = g.sort_values("date", kind="stable")
    st = GapState()
    oh, oa = [], []
    for h, a, xh, xa in zip(g.HomeTeam.to_numpy(), g.AwayTeam.to_numpy(), g[hc].to_numpy(float), g[ac].to_numpy(float)):
        ph, pa = _predict(st, h, a, prior)
        oh.append(ph)
        oa.append(pa)
        if np.isfinite(xh) and np.isfinite(xa):
            _update(st, h, a, xh, xa, ph, pa, eta, gamma)
    return pd.DataFrame({"gap_h": oh, "gap_a": oa}, index=g.index), st


def pre_match(df: pd.DataFrame, hc: str, ac: str, eta: float, gamma: float, prior: list) -> pd.DataFrame:
    """Previsioni pre-partita per tutte le righe di df (tutti i campionati), indicizzate come df."""
    parts = [run_league(g, hc, ac, eta, gamma, prior)[0] for _, g in df.groupby("Division")]
    return pd.concat(parts).reindex(df.index)


def predict(st: GapState, homes, aways, prior) -> tuple:
    """Previsioni (casa, ospite) per partite future dallo stato dopo l'ultima partita giocata."""
    out = [_predict(st, h, a, prior) for h, a in zip(homes, aways)]
    return np.array([o[0] for o in out]), np.array([o[1] for o in out])
