"""
Elo-Odds (Wunderlich & Memmert): rating Elo per campionato aggiornato dove il "risultato" non è l'esito
reale ma la probabilità implicita del mercato, S = P(1) + 0.5*P(X), dalle quote di CHIUSURA senza margine
(metodo power). Feature dello stack: eo_diff = rating casa - rating ospite PRIMA della partita.

Regole (identiche al backtest del round 2, variante 2b, K=200):
  - un sistema di rating per campionato, partite in ordine di data (ordine stabile);
  - tutti partono da 1500; squadra mai vista nel campionato = media dei 3 rating piu' bassi in quel momento
    (le squadre retrocesse restano nel dizionario, come nel backtest);
  - vantaggio casa in punti Elo = media corrente di S nel campionato (prior: 50 partite al 58%);
  - aggiornamento R_casa += K (S - E), R_ospite -= K (S - E), con E = 1/(1+10^(-(d + HFA)/400));
  - le quote della partita da prevedere non si usano MAI: il rating pre-partita si legge prima di
    aggiornarlo con le quote della stessa partita, e in produzione si usano solo partite con data < oggi.

Differenza rispetto al backtest: dove la chiusura di una partita manca ma ci sono le quote medie
pre-partita (AvgH/AvgD/AvgA, o BbAv/B365 nelle stagioni vecchie) si usano quelle (ripiego a livello di
riga); se mancano entrambe la partita non aggiorna i rating. Nello storico completo (25.538 partite) il
ripiego riguarda 4 partite 2012-2018.
"""
import numpy as np
import pandas as pd

ELO_ODDS_K = 200.0
FEATURE = "eo_diff"
ELO_START = 1500.0
HFA_PRIOR_N, HFA_PRIOR_S = 50, 0.58

SRC_NONE, SRC_CLOSING, SRC_PREMATCH = 0, 1, 2
MIN_COVERAGE_SEASON = 0.95        # quota minima di partite con quote usabili per (stagione, campionato)
MIN_COVERAGE_TOTAL = 0.99
RECENT_DAYS = 60
RECENT_MIN_MATCHES = 20
RECENT_MIN_COVERAGE = 0.5


class EloOddsError(RuntimeError):
    """Quote storiche non disponibili o troppo incomplete per costruire i rating."""


def power_devig(odds) -> np.ndarray:
    """Probabilita' senza margine col metodo power: p_i = (1/o_i)^k con k tale che sum p = 1.
    odds (n,3); righe con quote non valide -> NaN."""
    odds = np.asarray(odds, float)
    ok = np.isfinite(odds).all(1) & (odds > 1).all(1)
    out = np.full(odds.shape, np.nan)
    pi = 1.0 / odds[ok]
    lo, hi = np.full(len(pi), 0.3), np.full(len(pi), 3.0)
    for _ in range(60):
        k = (lo + hi) / 2
        up = (pi ** k[:, None]).sum(1) > 1
        lo, hi = np.where(up, k, lo), np.where(up, hi, k)
    p = pi ** ((lo + hi) / 2)[:, None]
    out[ok] = p / p.sum(1, keepdims=True)
    return out


def market_scores(df: pd.DataFrame, prematch_fallback: bool = True):
    """S = P(1) + 0.5*P(X) per partita e fonte (SRC_CLOSING / SRC_PREMATCH / SRC_NONE).
    df ha le colonne cl_h/cl_d/cl_a (chiusura) e odds_h/odds_d/odds_a (quote medie pre-partita)."""
    n = len(df)
    P = power_devig(df[["cl_h", "cl_d", "cl_a"]].to_numpy(float))
    src = np.where(np.isfinite(P).all(1), SRC_CLOSING, SRC_NONE)
    if prematch_fallback:
        need = src == SRC_NONE
        if need.any():
            P2 = power_devig(df[["odds_h", "odds_d", "odds_a"]].to_numpy(float))
            use = need & np.isfinite(P2).all(1)
            P[use] = P2[use]
            src[use] = SRC_PREMATCH
    S = np.where(src != SRC_NONE, P[:, 0] + 0.5 * P[:, 1], np.nan)
    return S, src


def _initial_rating(R: dict) -> float:
    return float(np.mean(sorted(R.values())[:3])) if len(R) >= 3 else ELO_START


def _run_league(home, away, S, K):
    """Ordine gia' stabilito. Restituisce (eo_diff pre-partita per partita, dizionario dei rating finali)."""
    R, s_sum, s_n = {}, HFA_PRIOR_S * HFA_PRIOR_N, HFA_PRIOR_N
    diff = np.empty(len(home))
    for i, (h, a) in enumerate(zip(home, away)):
        if h not in R or a not in R:
            low = _initial_rating(R)
            R.setdefault(h, low)
            R.setdefault(a, low)
        m = s_sum / s_n
        hfa = 400 * np.log10(m / (1 - m))
        d = R[h] - R[a]
        diff[i] = d
        s = S[i]
        if np.isfinite(s):
            E = 1 / (1 + 10 ** (-(d + hfa) / 400))
            R[h] += K * (s - E)
            R[a] -= K * (s - E)
            s_sum += s
            s_n += 1
    return diff, R


class EloOddsState:
    """Rating Elo-Odds di un campionato dopo l'ultima partita del suo storico."""

    def __init__(self, ratings: dict):
        self.R = dict(ratings)

    @classmethod
    def from_matches(cls, g: pd.DataFrame, K: float = ELO_ODDS_K, prematch_fallback: bool = True):
        """g: partite GIA' GIOCATE di UN campionato (tutto lo storico disponibile prima di oggi)."""
        g = g.sort_values("date", kind="stable")
        S, _ = market_scores(g, prematch_fallback)
        _, R = _run_league(g.HomeTeam.to_numpy(), g.AwayTeam.to_numpy(), S, K)
        return cls(R)

    def rating(self, team):
        return self.R.get(team)

    def diff(self, homes, aways) -> np.ndarray:
        """eo_diff per le coppie (casa, ospite); una squadra sconosciuta vale la media dei 3 rating piu' bassi."""
        low = _initial_rating(self.R)
        return np.array([self.R.get(h, low) - self.R.get(a, low) for h, a in zip(homes, aways)])


def build_features(df: pd.DataFrame, K: float = ELO_ODDS_K, prematch_fallback: bool = True) -> pd.Series:
    """eo_diff pre-partita per ogni partita di df (indice di df), tutti i campionati. Usato dal training e dal backtest."""
    out = pd.Series(np.nan, index=df.index, name=FEATURE)
    for lg, g in df.groupby("Division"):
        g = g.sort_values("date", kind="stable")
        S, _ = market_scores(g, prematch_fallback)
        diff, _ = _run_league(g.HomeTeam.to_numpy(), g.AwayTeam.to_numpy(), S, K)
        out.loc[g.index] = diff
    return out


# ───────────────────────── copertura delle quote ─────────────────────────
def source_counts(df: pd.DataFrame) -> dict:
    _, src = market_scores(df)
    return {"n": int(len(df)), "closing": int((src == SRC_CLOSING).sum()),
            "prematch_fallback": int((src == SRC_PREMATCH).sum()), "none": int((src == SRC_NONE).sum())}


def recent_coverage(df: pd.DataFrame, today, days: int = RECENT_DAYS) -> dict:
    """Copertura delle quote nelle partite giocate negli ultimi `days` giorni (quelle che pesano di piu' nei rating)."""
    today = pd.Timestamp(today).normalize()
    r = df[(df.date < today) & (df.date >= today - pd.Timedelta(days=days))]
    c = source_counts(r)
    usable = c["closing"] + c["prematch_fallback"]
    c["days"] = days
    c["ok"] = c["n"] < RECENT_MIN_MATCHES or usable / c["n"] >= RECENT_MIN_COVERAGE
    return c


def check_training_coverage(df: pd.DataFrame, today=None, first_season: int = 2012, current: int = None):
    """Solleva EloOddsError se le quote storiche non sono utilizzabili: file di stagione mancanti o troppo
    poche partite con quote. Il training NON deve procedere (e non deve sovrascrivere models/stack.json)."""
    from backtest import data
    today = pd.Timestamp(today if today is not None else pd.Timestamp.utcnow().tz_localize(None)).normalize()
    cur = data.current_season() if current is None else current
    _, src = market_scores(df)
    d = df.assign(_usable=(src != SRC_NONE))
    problems = []
    have = d.groupby(["season", "Division"]).agg(n=("_usable", "size"), u=("_usable", "mean"))
    for s in range(first_season, cur + 1):
        for lg in data.LEAGUES:
            if (s, lg) not in have.index:
                if s < cur or today.month not in (7, 8):          # la stagione corrente puo' non essere ancora iniziata
                    problems.append(f"file {data.season_code(s)}/{lg} non disponibile")
                continue
            n, u = have.loc[(s, lg), "n"], have.loc[(s, lg), "u"]
            if u < MIN_COVERAGE_SEASON:
                problems.append(f"{data.season_code(s)}/{lg}: quote usabili solo per {u:.0%} delle {int(n)} partite")
    total = float(d._usable.mean())
    if total < MIN_COVERAGE_TOTAL:
        problems.append(f"quote usabili solo per {total:.1%} delle {len(d)} partite")
    rc = recent_coverage(df, today)
    if not rc["ok"]:
        problems.append(f"ultimi {rc['days']} giorni: quote per {rc['closing'] + rc['prematch_fallback']} partite su {rc['n']}")
    if problems:
        raise EloOddsError("quote storiche per Elo-Odds non utilizzabili:\n  - " + "\n  - ".join(problems))
    return {"matches": int(len(d)), **source_counts(df)}
