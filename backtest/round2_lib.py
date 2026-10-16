"""
Round 2 di esperimenti (solo backtest, nessuna modifica alla produzione).

Infrastruttura comune: caricamento dati + quote extra (O/U, Pinnacle), baseline (stack con xG ridge,
training dal 2016/17), valutazione appaiata (bootstrap per partita), delta per stagione e per lega.
"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import numpy as np
import pandas as pd

from backtest import data, models, features, stack, understat

TEST_START = "2019-07-01"
FIRST_TEST_SEASON = 2019
MIN_TRAIN_SEASON = stack.XG_FIRST_TRAIN_SEASON      # 2016
CACHE = data.CACHE_DIR
N_BOOT = 5000

# colonne quote extra: nome interno -> colonna football-data
EXTRA_COLS = {
    "ps_h": "PSH", "ps_d": "PSD", "ps_a": "PSA",                 # Pinnacle, quote a raccolta
    "psc_h": "PSCH", "psc_d": "PSCD", "psc_a": "PSCA",           # Pinnacle, chiusura
    "avgc_h": "AvgCH", "avgc_d": "AvgCD", "avgc_a": "AvgCA",     # media di mercato, chiusura
    "ou_avgc_o": "AvgC>2.5", "ou_avgc_u": "AvgC<2.5",
    "ou_psc_o": "PC>2.5", "ou_psc_u": "PC<2.5",
    "ou_avg_o": "Avg>2.5", "ou_avg_u": "Avg<2.5",
    "ou_bb_o": "BbAv>2.5", "ou_bb_u": "BbAv<2.5",
}


def _extra_one(season, league):
    path = os.path.join(CACHE, f"{data.season_code(season)}_{league}.csv")
    if not os.path.exists(path):
        return None
    raw = pd.read_csv(path, encoding="latin-1", on_bad_lines="skip", low_memory=False)
    raw = raw.dropna(subset=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"])
    out = pd.DataFrame({"Division": league, "season": season,
                        "HomeTeam": raw["HomeTeam"].astype(str).str.strip(),
                        "AwayTeam": raw["AwayTeam"].astype(str).str.strip()})
    for k, c in EXTRA_COLS.items():
        out[k] = pd.to_numeric(raw[c], errors="coerce") if c in raw.columns else np.nan
    return out


def load_all(verbose=True):
    """df con tutte le colonne del backtest + xG Understat + quote extra (O/U, Pinnacle)."""
    df = data.load_matches(verbose=verbose)
    df = understat.attach_xg(df, understat.load_xg(), strict=True)
    parts = [p for s in range(data.FIRST_SEASON, data.current_season() + 1)
             for lg in data.LEAGUES if (p := _extra_one(s, lg)) is not None]
    extra = pd.concat(parts, ignore_index=True)
    extra = extra.drop_duplicates(["Division", "season", "HomeTeam", "AwayTeam"])
    n0 = len(df)
    df = df.reset_index().merge(extra, on=["Division", "season", "HomeTeam", "AwayTeam"],
                                how="left").set_index("index")
    df.index.name = None
    assert len(df) == n0
    return df


def baseline_frame(df, rebuild=False):
    """Feature del baseline (core + xG con ridge=2) indicizzate come df."""
    feat = features.build_features(df, rebuild=rebuild, verbose=False)
    xg_r = features.build_xg_features(df, ridge=features.XG_RIDGE, rebuild=rebuild, verbose=False)
    feat = feat.assign(xg_lmu=xg_r.xg_lmu, xg_lnu=xg_r.xg_lnu)
    # colonne extra (O/U, Pinnacle) dal df completo
    extra_cols = [c for c in df.columns if c not in feat.columns]
    return feat.join(df.loc[feat.index, extra_cols])


def eval_set(feat):
    """Partite di test con quote medie valide (stesso insieme del backtest ufficiale)."""
    test = feat[feat.date >= pd.Timestamp(TEST_START)]
    o = test[["odds_h", "odds_d", "odds_a"]].to_numpy(float)
    ok = np.isfinite(o).all(1) & (o > 1).all(1)
    return test[ok]


def run_stack(frame, cols, ev, extra_cols=None):
    """Stack walk-forward (stagione per stagione, training dal 2016/17) -> DataFrame pH,pD,pA,mu,nu su ev."""
    sp = stack.walk_forward_stack(frame, cols, FIRST_TEST_SEASON, MIN_TRAIN_SEASON)
    return sp.reindex(ev.index)


# ─────────────────────────── statistiche appaiate ─────────────────────────────
class Boot:
    """Bootstrap appaiato per partita: indici di ricampionamento fissi (stessi per tutti i confronti)."""
    def __init__(self, n, n_boot=N_BOOT, seed=7, chunk=250):
        self.n, self.n_boot, self.seed, self.chunk = n, n_boot, seed, chunk

    def ci(self, d):
        d = np.asarray(d, float)
        n = len(d)
        rng = np.random.default_rng(self.seed)
        est = np.empty(self.n_boot)
        for s in range(0, self.n_boot, self.chunk):
            k = min(self.chunk, self.n_boot - s)
            idx = rng.integers(0, n, size=(k, n))
            est[s:s + k] = d[idx].mean(1)
        return float(d.mean()), float(np.percentile(est, 2.5)), float(np.percentile(est, 97.5))


def ll_vec(P, y):
    P = np.clip(P, 1e-12, 1)
    P = P / P.sum(1, keepdims=True)
    return -np.log(P[np.arange(len(y)), y])


def metric_vecs(P, y):
    """log-loss, RPS, Brier per partita."""
    P = np.clip(P, 1e-12, 1)
    P = P / P.sum(1, keepdims=True)
    Y = np.eye(3)[y]
    ll = -np.log(P[np.arange(len(y)), y])
    br = ((P - Y) ** 2).sum(1)
    cP, cY = np.cumsum(P, 1)[:, :2], np.cumsum(Y, 1)[:, :2]
    rps = ((cP - cY) ** 2).sum(1) / 2
    return ll, rps, br


# ─────────────────────────── rimozione del margine ────────────────────────────
def devig(odds, method="power"):
    """Probabilità senza margine per un mercato a k esiti (k=2 O/U, k=3 1X2).
    odds: array (n, k). method: 'norm' (normalizzazione semplice), 'power', 'shin'.
    Righe con quote non valide -> NaN."""
    odds = np.asarray(odds, float)
    ok = np.isfinite(odds).all(1) & (odds > 1).all(1)
    out = np.full(odds.shape, np.nan)
    pi = 1.0 / odds[ok]
    B = pi.sum(1, keepdims=True)
    if method == "norm":
        out[ok] = pi / B
    elif method == "power":
        # p_i = pi_i ** k con k tale che sum p = 1 (k >= 1 quando il margine e' positivo)
        lo = np.full(len(pi), 0.3); hi = np.full(len(pi), 3.0)
        for _ in range(60):
            k = (lo + hi) / 2
            s = (pi ** k[:, None]).sum(1)
            up = s > 1
            lo = np.where(up, k, lo); hi = np.where(up, hi, k)
        p = pi ** ((lo + hi) / 2)[:, None]
        out[ok] = p / p.sum(1, keepdims=True)
    elif method == "shin":
        # Shin (1992/1993), versione di Strumbelj (2014): z = quota di scommettitori informati
        lo = np.zeros(len(pi)); hi = np.full(len(pi), 0.6)
        def psum(z):
            z = z[:, None]
            p = (np.sqrt(z ** 2 + 4 * (1 - z) * pi ** 2 / B) - z) / (2 * (1 - z))
            return p, p.sum(1)
        for _ in range(60):
            z = (lo + hi) / 2
            _, s = psum(z)
            up = s > 1                      # la somma decresce con z
            lo = np.where(up, z, lo); hi = np.where(up, hi, z)
        p, _ = psum((lo + hi) / 2)
        out[ok] = p / p.sum(1, keepdims=True)
    else:
        raise ValueError(method)
    return out
