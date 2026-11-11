"""Monitoraggio «a carta» di tre anomalie trovate nel backtest (round 11, V5-V6). SOLO resoconto: nessuna influenza sul modello né sulle previsioni.

Le regole sono fissate l'11/11/2026 e non si cambiano: si contano solo le partite giocate da quella data (PAPER_START). Le probabilità sono quelle
implicite nelle quote MEDIE PRE-PARTITA di football-data.co.uk (AvgH/D/A, raccolte giorni prima), senza margine (metodo power); il rendimento teorico
è quello di puntare 1 unità alla quota media su ogni partita che soddisfa la regola.

  (a) Serie A, ospite con probabilità implicita >= 45 %           -> si punta sulla vittoria dell'ospite
  (b) La Liga, favorita in casa con probabilità implicita >= 60 %  -> si punta sulla vittoria in casa
  (c) pareggi tra squadre equilibrate, |p_casa - p_ospite| <= 10 punti (5 campionati) -> si punta sul pareggio

Con poche partite l'esito è dominato dal caso: sotto MIN_N partite si mostrano solo i conteggi, senza intervalli. Gli intervalli (95 %) sono a blocchi per settimana ISO."""
import numpy as np
import pandas as pd

from backtest import eloodds

PAPER_START = "2026-11-11"
MIN_N = 30
N_BOOT = 3000
RULES = {
    "a": {"label": "(a) Serie A, ospite con probabilità >= 45 %", "leagues": ("I1",), "outcome": 2, "kind": "ge", "thr": 0.45,
          "ref": "backtest 2019/20-2026/27: eccesso +7,0 pt, ROI +9,3 %; 2013/14-2018/19: +3,1 pt, ROI +2,5 %"},
    "b": {"label": "(b) La Liga, favorita in casa con probabilità >= 60 %", "leagues": ("SP1",), "outcome": 0, "kind": "ge", "thr": 0.60,
          "ref": "backtest 2019/20-2026/27: eccesso +5,0 pt, ROI +5,2 %; 2013/14-2018/19: +0,5 pt, ROI −1,4 %"},
    "c": {"label": "(c) Pareggio tra squadre equilibrate (|p casa − p ospite| <= 10 pt), 5 campionati", "leagues": ("I1", "E0", "D1", "SP1", "F1"), "outcome": 1,
          "kind": "balanced", "thr": 0.10,
          "ref": "backtest 2019/20-2026/27: eccesso +2,3 pt, ROI +2,1 %; 2013/14-2018/19: +1,6 pt, ROI −0,5 %"},
}


def _block_ci(num, den, weeks, seed):
    """Σnum/Σden con IC 95 % a blocchi per settimana (ricampionamento delle settimane)."""
    num, den = np.asarray(num, float), np.asarray(den, float)
    wk, inv = np.unique(np.asarray(weeks), return_inverse=True)
    sn, sd = np.bincount(inv, num), np.bincount(inv, den)
    rng = np.random.default_rng(seed)
    b = rng.integers(0, len(wk), size=(N_BOOT, len(wk)))
    d = sd[b].sum(1)
    est = np.where(d > 0, sn[b].sum(1) / np.where(d > 0, d, 1), np.nan)
    est = est[np.isfinite(est)]
    return float(sn.sum() / sd.sum()), float(np.percentile(est, 2.5)), float(np.percentile(est, 97.5))


def select(matches: pd.DataFrame, rule: dict, start=PAPER_START):
    """Partite giocate da `start` che soddisfano la regola, con quote medie pre-partita valide. Restituisce (sottoinsieme, p_esito senza margine)."""
    m = matches[matches["Division"].isin(rule["leagues"]) & (matches["date"] >= pd.Timestamp(start)) & matches["res"].isin([0, 1, 2])]
    odds = m[["odds_h", "odds_d", "odds_a"]].to_numpy(float)
    ok = np.isfinite(odds).all(1) & (odds > 1).all(1)
    m, odds = m[ok], odds[ok]
    if not len(m):
        return m, np.empty(0)
    p = eloodds.power_devig(odds)
    if rule["kind"] == "ge":
        sel = p[:, rule["outcome"]] >= rule["thr"]
    else:
        sel = np.abs(p[:, 0] - p[:, 2]) <= rule["thr"]
    return m[sel], p[sel, rule["outcome"]]


def compute(matches: pd.DataFrame, start=PAPER_START) -> dict:
    """Per ciascuna regola: N, probabilità implicita media, frequenza reale, eccesso, rendimento teorico a quota media (IC a blocchi se N >= MIN_N)."""
    out = {"start": str(start), "min_n": MIN_N, "rules": {}}
    for key, r in RULES.items():
        m, p = select(matches, r, start)
        o = r["outcome"]
        res = {"label": r["label"], "ref": r["ref"], "n": int(len(m)), "ci": False}
        if len(m):
            win = (m["res"].to_numpy() == o).astype(float)
            odds = m[["odds_h", "odds_d", "odds_a"]].to_numpy(float)[:, o]
            weeks = m["date"].dt.strftime("%G-%V").to_numpy()
            profit = odds * win - 1
            res.update(implied=float(p.mean()), real=float(win.mean()), wins=int(win.sum()), excess=float(win.mean() - p.mean()),
                       roi=float(profit.mean()), profit=float(profit.sum()), last_date=str(m["date"].max().date()))
            if len(m) >= MIN_N:
                res["ci"] = True
                res["excess_ci"] = _block_ci(win - p, np.ones(len(m)), weeks, 1)
                res["roi_ci"] = _block_ci(profit, np.ones(len(m)), weeks, 2)
        out["rules"][key] = res
    return out
