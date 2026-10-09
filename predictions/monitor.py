"""
Monitoraggio (Step 8): storico delle previsioni emesse in docs/history.csv e log-loss
mobile di with_xg, without_xg e mercato.

Una riga per partita (chiave: campionato, data, casa, trasferta). Finché la partita non è
stata giocata la riga viene riscritta a ogni esecuzione con l'ultima previsione (quella
emessa più vicina al calcio d'inizio); una volta giocata resta congelata e si aggiungono
i risultati. Per ogni partita si salvano le probabilità:

  p_*    del modello EMESSO (model_used: with_xg, o without_xg se è scattato il ripiego)
  pw_*   di with_xg (vuote se non utilizzabile per quella partita)
  po_*   di without_xg
  mkt_*  del mercato senza margine (metodo power): da football-data.co.uk/fixtures.csv
         al momento dell'emissione; se non c'erano, dalle quote medie del CSV dei risultati
         quando la partita si gioca (mkt_source = "csv_avg")

Salvare entrambi i modelli per ogni partita permette di confrontarli sulle STESSE partite
anche quando in produzione ne viene emesso uno solo.

La log-loss mobile usa le ultime `window` partite giocate per cui sono disponibili
contemporaneamente with_xg, without_xg e mercato (stesso insieme per tutti e tre).
"""
import io
import logging
import os
import sys

import numpy as np
import pandas as pd
import requests

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from backtest import models  # noqa: E402

log = logging.getLogger(__name__)

FIXTURES_URL = "https://www.football-data.co.uk/fixtures.csv"
HISTORY_PATH = os.path.join(REPO_ROOT, "docs", "history.csv")
WINDOW = 200
MIN_N = 30     # sotto questa soglia il riquadro mostra solo lo stato di raccolta dati

LEAGUE_CODE = {"serie_a": "I1", "premier_league": "E0", "bundesliga": "D1",
               "la_liga": "SP1", "ligue_1": "F1"}
KEY = ["league", "match_date", "home", "away"]

P3 = ["home", "draw", "away"]
COLUMNS = (["issued_on", "league", "match_date", "matchday", "home", "away", "home_dc", "away_dc",
            "model_used", "fallback_reason"]
           + [f"p_{k}" for k in P3] + [f"pw_{k}" for k in P3] + [f"po_{k}" for k in P3]
           + [f"mkt_{k}" for k in P3] + ["mkt_source", "hg", "ag", "result"])
PROB_COLS = [c for c in COLUMNS if c.split("_")[0] in ("p", "pw", "po", "mkt") and c != "mkt_source"]


def empty_history() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNS)


def load_history(path: str = HISTORY_PATH) -> pd.DataFrame:
    if not os.path.exists(path):
        return empty_history()
    h = pd.read_csv(path, dtype={"matchday": str, "home_dc": str, "away_dc": str,
                                 "fallback_reason": str, "mkt_source": str, "result": str})
    for c in COLUMNS:
        if c not in h.columns:
            h[c] = np.nan
    return h[COLUMNS]


def save_history(h: pd.DataFrame, path: str = HISTORY_PATH) -> None:
    h = h.sort_values(["match_date", "league", "home"]).reset_index(drop=True)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    h[COLUMNS].to_csv(path, index=False, float_format="%.5f")


# ── Mercato dalle fixture future ───────────────────────────────────────────────

def _market_from_odds(oh, od, oa):
    P = models.market_probs(np.asarray(oh, float), np.asarray(od, float), np.asarray(oa, float), "power")
    return P


def fixtures_market(url: str = FIXTURES_URL, session=None) -> pd.DataFrame:
    """Quote delle prossime partite (football-data.co.uk/fixtures.csv) come probabilità senza
    margine. Colonne: Division, date, HomeTeam, AwayTeam, mkt_home/draw/away. Vuoto se non disponibile."""
    cols = ["Division", "date", "HomeTeam", "AwayTeam"] + [f"mkt_{k}" for k in P3]
    try:
        resp = (session or requests).get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        fx = pd.read_csv(io.StringIO(resp.content.decode("utf-8-sig", errors="replace")),
                         on_bad_lines="skip")
    except Exception as e:   # servizio esterno: la mancanza di quote non deve fermare nulla
        log.warning("fixtures.csv non disponibile (%s): nessuna quota di mercato all'emissione", e)
        return pd.DataFrame(columns=cols)

    fx = fx[fx["Div"].isin(LEAGUE_CODE.values())].copy()
    for trio in (("AvgH", "AvgD", "AvgA"), ("B365H", "B365D", "B365A")):
        if all(c in fx.columns for c in trio):
            o = fx[list(trio)].apply(pd.to_numeric, errors="coerce")
            if o.notna().all(axis=1).any():
                break
    else:
        return pd.DataFrame(columns=cols)
    ok = o.notna().all(axis=1) & (o > 1).all(axis=1)
    fx, o = fx[ok], o[ok]
    if fx.empty:
        return pd.DataFrame(columns=cols)
    P = _market_from_odds(o.iloc[:, 0], o.iloc[:, 1], o.iloc[:, 2])
    out = pd.DataFrame({"Division": fx["Div"].values,
                        "date": pd.to_datetime(fx["Date"], dayfirst=True, format="mixed", errors="coerce").values,
                        "HomeTeam": fx["HomeTeam"].astype(str).str.strip().values,
                        "AwayTeam": fx["AwayTeam"].astype(str).str.strip().values,
                        "mkt_home": P[:, 0], "mkt_draw": P[:, 1], "mkt_away": P[:, 2]})
    return out.dropna(subset=["date"])


def attach_fixture_market(rows: list[dict], fx: pd.DataFrame) -> None:
    """Riempie mkt_* nelle righe nuove con le quote di fixtures.csv (chiave: lega, squadre CSV,
    data entro ±1 giorno)."""
    if fx.empty:
        return
    for r in rows:
        if not r["home_dc"] or not r["away_dc"]:
            continue
        d = pd.Timestamp(r["match_date"])
        hit = fx[(fx.Division == LEAGUE_CODE[r["league"]]) & (fx.HomeTeam == r["home_dc"])
                 & (fx.AwayTeam == r["away_dc"]) & ((fx.date - d).abs() <= pd.Timedelta(days=1))]
        if len(hit):
            h = hit.iloc[0]
            r["mkt_home"], r["mkt_draw"], r["mkt_away"] = h.mkt_home, h.mkt_draw, h.mkt_away
            r["mkt_source"] = "fixtures"


# ── Aggiornamento dello storico ────────────────────────────────────────────────

def make_row(league, fix, pred, probs, issued_on) -> dict:
    """Riga di storico per una partita. pred = previsione emessa (stack_predictor.predict_pairs),
    probs = {"with_xg": (h,d,a)|None, "without_xg": (h,d,a)} (stack_predictor.probs_by_model)."""
    row = {c: np.nan for c in COLUMNS}
    row.update(issued_on=issued_on, league=league, match_date=fix["date"], matchday=str(fix["matchday"]),
               home=fix["home"], away=fix["away"], home_dc=fix.get("home_dc"), away_dc=fix.get("away_dc"),
               model_used=pred["model"], fallback_reason=pred["fallback_reason"] or np.nan,
               p_home=pred["prob_home"], p_draw=pred["prob_draw"], p_away=pred["prob_away"])
    for tag, name in (("pw", "with_xg"), ("po", "without_xg")):
        if probs.get(name) is not None:
            row[f"{tag}_home"], row[f"{tag}_draw"], row[f"{tag}_away"] = probs[name]
    return row


def upsert(history: pd.DataFrame, new_rows: list[dict], today) -> pd.DataFrame:
    """Aggiunge le partite nuove e riscrive quelle non ancora giocate (match_date >= oggi) con
    l'ultima previsione. Le righe già con risultato non si toccano. Se la nuova riga non ha
    quote di mercato si tiene quella già salvata."""
    today = pd.Timestamp(today).strftime("%Y-%m-%d")
    h = history.copy()
    idx = {tuple(r): i for i, r in enumerate(h[KEY].itertuples(index=False, name=None))}
    add = []
    for r in new_rows:
        k = (r["league"], r["match_date"], r["home"], r["away"])
        if k not in idx:
            add.append(r)
            continue
        i = idx[k]
        if pd.notna(h.at[i, "result"]) or str(h.at[i, "match_date"]) < today:
            continue
        old_mkt = {c: h.at[i, c] for c in ("mkt_home", "mkt_draw", "mkt_away", "mkt_source")}
        for c in COLUMNS:
            if c in r:
                h.at[i, c] = r[c]
        if pd.isna(r.get("mkt_home")) and pd.notna(old_mkt["mkt_home"]):
            for c, v in old_mkt.items():
                h.at[i, c] = v
    if add:
        h = pd.concat([h, pd.DataFrame(add, columns=COLUMNS)], ignore_index=True)
    return h


def fill_results(history: pd.DataFrame, results: pd.DataFrame, today, max_days_apart: int = 3) -> pd.DataFrame:
    """Per le partite già giocate senza risultato cerca hg/ag nei CSV dei risultati
    (colonne Division, date, HomeTeam, AwayTeam, hg, ag, odds_h/d/a) e, se mancano, riempie anche
    il mercato con le quote medie del CSV."""
    h = history.copy()
    today = pd.Timestamp(today)
    results = results.dropna(subset=["hg", "ag"])
    by_key = {}
    for r in results.itertuples(index=False):
        by_key.setdefault((r.Division, r.HomeTeam, r.AwayTeam), []).append(r)

    n_new = 0
    for i, row in h.iterrows():
        if pd.notna(row["result"]) or pd.Timestamp(row["match_date"]) > today:
            continue
        if not isinstance(row["home_dc"], str) or not isinstance(row["away_dc"], str):
            continue
        d = pd.Timestamp(row["match_date"])
        cands = [r for r in by_key.get((LEAGUE_CODE[row["league"]], row["home_dc"], row["away_dc"]), [])
                 if abs((r.date - d).days) <= max_days_apart]
        if not cands:
            continue
        r = min(cands, key=lambda c: abs((c.date - d).days))
        h.at[i, "hg"], h.at[i, "ag"] = int(r.hg), int(r.ag)
        h.at[i, "result"] = "H" if r.hg > r.ag else ("D" if r.hg == r.ag else "A")
        n_new += 1
        if pd.isna(row["mkt_home"]):
            o = np.array([r.odds_h, r.odds_d, r.odds_a], float)
            if np.isfinite(o).all() and (o > 1).all():
                P = _market_from_odds(o[:1], o[1:2], o[2:])[0]
                h.at[i, "mkt_home"], h.at[i, "mkt_draw"], h.at[i, "mkt_away"] = P
                h.at[i, "mkt_source"] = "csv_avg"
    if n_new:
        log.info("Storico: %d risultati nuovi", n_new)
    return h


# ── Log-loss mobile ────────────────────────────────────────────────────────────

def rolling_logloss(history: pd.DataFrame, window: int = WINDOW, min_n: int = MIN_N) -> dict:
    """Log-loss delle ultime `window` partite giocate con with_xg, without_xg e mercato disponibili."""
    h = history
    played = h[h["result"].isin(["H", "D", "A"])]
    out = {"window": window, "min_n": min_n, "tracked": int(len(h)), "with_result": int(len(played)),
           "n": 0, "status": "in_raccolta", "since": None, "until": None}
    need = [f"{t}_{k}" for t in ("pw", "po", "mkt") for k in P3]
    full = played.dropna(subset=need).sort_values(["match_date", "league", "home"]).tail(window)
    out["n"] = int(len(full))
    if len(full) < min_n:
        return out

    y = full["result"].map({"H": 0, "D": 1, "A": 2}).to_numpy()
    out["since"], out["until"] = str(full.match_date.iloc[0]), str(full.match_date.iloc[-1])
    out["status"] = "ok"
    for name, tag in (("with_xg", "pw"), ("without_xg", "po"), ("market", "mkt")):
        P = full[[f"{tag}_{k}" for k in P3]].to_numpy(float)
        P = np.clip(P, 1e-12, 1)
        P = P / P.sum(1, keepdims=True)
        out[name] = float(-np.log(P[np.arange(len(y)), y]).mean())
    out["delta_with_xg_vs_market"] = out["with_xg"] - out["market"]
    out["delta_without_xg_vs_market"] = out["without_xg"] - out["market"]
    out["delta_with_xg_vs_without_xg"] = out["with_xg"] - out["without_xg"]
    return out
