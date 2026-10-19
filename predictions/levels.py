"""
Livello stagionale delle statistiche (STATS_VERSION s5-livello, backtest/round7_parts/prereg.md e results_round7.md).

Per ogni lega, statistica e lato (casa/ospite) un moltiplicatore R sulle medie attese del modello, ricalcolato a ogni esecuzione dalle partite già
giocate: R = (Σ w·y + k·m̄) / (Σ w·μ + k·m̄), w = 0,5^(giorni / (7·H)), μ = media attesa del modello PRIMA della partita (previsione fuori campione),
m̄ = Σ w·μ / Σ w, solo partite di giorni precedenti a quello della partita da prevedere. (H, k) per statistica: config.LEVEL_PARAMS.

Le somme giornaliere fino all'ultimo allenamento stanno in models/stack.json["stats_v3"]["level"] (registro costruito da
`stats_v3.build_level` con le previsioni fuori campione per stagione). Le partite giocate dopo l'ultimo giorno del registro entrano dallo storico
(docs/history.csv): previsioni di base (prima del livello) salvate in `bm_<statistica>_h/_a` al momento dell'emissione, risultati per lato dal CSV
dei risultati. Le righe senza previsioni di base non entrano (finché il training settimanale non le include nel registro).
"""
import logging

import numpy as np
import pandas as pd

from backtest import stats_v3

log = logging.getLogger(__name__)

# colonne dei risultati per lato (football-data.co.uk) per statistica
RESULT_COLS = {"tiri": ("HS", "AS"), "sot": ("HST", "AST"), "corner": ("HC", "AC"), "falli": ("HF", "AF"), "gialli": ("HY", "AY")}


def _arr(s: str) -> np.ndarray:
    return np.array([float(x) for x in s.split(",")], float) if s else np.zeros(0)


class Levels:
    """Registro del livello (dal modello) più partite recenti (dallo storico). `multipliers` restituisce (R casa, R ospite) per partita."""

    def __init__(self, level: dict | None, extra: pd.DataFrame | None = None):
        self.params = {}
        self.data = {}              # (divisione, statistica) -> dict di array
        self.asof = {}
        if not level:
            return
        self.params = {s: tuple(v) for s, v in level["params"].items()}
        self.asof = dict(level.get("asof", {}))
        epoch = pd.Timestamp(level["epoch"])
        self.epoch = epoch
        for div, stats in level["ledger"].items():
            for stat, f in stats.items():
                self.data[(div, stat)] = {k: _arr(f[k]) for k in stats_v3.LEVEL_FIELDS}
        if extra is not None and len(extra):
            for (div, stat), g in extra.groupby(["div", "stat"]):
                a = g.assign(d=(pd.to_datetime(g["date"]) - epoch).dt.days.astype(float)).groupby("d")[["yh", "mh", "ya", "ma", "n"]].sum().reset_index()
                base = self.data.get((div, stat))
                new = {k: a[k].to_numpy(float) for k in stats_v3.LEVEL_FIELDS}
                self.data[(div, stat)] = new if base is None else {k: np.r_[base[k], new[k]] for k in stats_v3.LEVEL_FIELDS}

    @property
    def stats(self):
        return set(self.params)

    def multipliers(self, division: str, stat: str, dates) -> tuple:
        """(R casa, R ospite) per ogni data ISO delle partite da prevedere. 1,0 se non c'è storico."""
        dates = list(dates)
        d = self.data.get((division, stat))
        if d is None or stat not in self.params:
            return np.ones(len(dates)), np.ones(len(dates))
        H, k = self.params[stat]
        days = [(pd.Timestamp(x) - self.epoch).days for x in dates]
        rh = np.array([stats_v3.level_multiplier(d["d"], d["yh"], d["mh"], d["n"], t, H, k) for t in days])
        ra = np.array([stats_v3.level_multiplier(d["d"], d["ya"], d["ma"], d["n"], t, H, k) for t in days])
        return rh, ra


def extra_from_history(history: pd.DataFrame, results: pd.DataFrame, level: dict | None, max_days_apart: int = 3) -> pd.DataFrame:
    """Partite dello storico giocate dopo l'ultimo giorno del registro, con le previsioni di base salvate e i risultati per lato dal CSV:
    DataFrame (div, stat, date, yh, mh, ya, ma, n)."""
    cols = ["div", "stat", "date", "yh", "mh", "ya", "ma", "n"]
    if not level or history is None or not len(history):
        return pd.DataFrame(columns=cols)
    from predictions.monitor import LEAGUE_CODE
    asof = level.get("asof", {})
    h = history[history["result"].notna() & history["home_dc"].notna() & history["league"].isin(LEAGUE_CODE)]
    by_key = {}
    for r in results.itertuples(index=False):
        by_key.setdefault((r.Division, r.HomeTeam, r.AwayTeam), []).append(r)
    rows = []
    for _, row in h.iterrows():
        div = LEAGUE_CODE[row["league"]]
        if str(row["match_date"]) <= asof.get(div, "0000-00-00"):
            continue
        d = pd.Timestamp(row["match_date"])
        cands = [r for r in by_key.get((div, row["home_dc"], row["away_dc"]), []) if abs((r.date - d).days) <= max_days_apart]
        if not cands:
            continue
        r = min(cands, key=lambda c: abs((c.date - d).days))
        for stat, (hc, ac) in RESULT_COLS.items():
            mh, ma = row.get(f"bm_{stat}_h"), row.get(f"bm_{stat}_a")
            yh, ya = getattr(r, hc, np.nan), getattr(r, ac, np.nan)
            if pd.notna(mh) and pd.notna(ma) and np.isfinite(yh) and np.isfinite(ya):
                rows.append((div, stat, d.strftime("%Y-%m-%d"), float(yh), float(mh), float(ya), float(ma), 1.0))
    return pd.DataFrame(rows, columns=cols)


def level_pct(rh: float, ra: float, mh: float, ma: float) -> float:
    """Variazione percentuale del totale della partita dovuta al livello: (R_casa·μ_casa + R_ospite·μ_ospite)/(μ_casa + μ_ospite) − 1."""
    return float((rh * mh + ra * ma) / (mh + ma) - 1.0) if (mh + ma) > 0 else 0.0
