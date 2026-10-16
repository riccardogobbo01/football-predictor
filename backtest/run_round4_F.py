"""Round 4 — Esperimento F: coppe, gare di ritorno (solo backtest).
Da lanciare in modalità isolata:  python -I -X utf8 backtest/run_round4_F.py"""
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

from backtest import cups_bt as CB, round3_ctx as C3
from backtest.round2_lib import ll_vec
from predictions import cups as CUPS_LIVE

DATA_DIR = os.path.join(REPO_ROOT, "data", "cache", "transfermarkt")
PARTS4 = os.path.join(REPO_ROOT, "backtest", "round4_parts")
VAL, FIRST, LAST, TIE = (2019, 2020, 2021), 2016, 2025, 0.0002
FORMS = ["F1", "F2", "F3"]
NAMES = {"F1": "F1 — g lineare (clip ±3)", "F2": "F2 — segno di g", "F3": "F3 — due pendenze (g>0, g<0)"}


def summary(d, weeks, mask):
    m = np.asarray(mask)
    if m.sum() < 5:
        return dict(n=int(m.sum()), d=np.nan, lo=np.nan, hi=np.nan, lob=np.nan, hib=np.nan)
    a, lo, hi = C3.ci_match(d[m])
    _, lob, hib = C3.ci_block(d[m], weeks[m])
    return dict(n=int(m.sum()), d=a, lo=lo, hi=hi, lob=lob, hib=hib)


def main():
    games = pd.read_csv(os.path.join(DATA_DIR, "games.csv.gz"), parse_dates=["date"],
                        usecols=["game_id", "competition_id", "season", "round", "date", "home_club_id", "away_club_id",
                                 "home_club_goals", "away_club_goals", "home_club_name", "away_club_name"])
    app = pd.read_csv(os.path.join(DATA_DIR, "appearances.csv.gz"), usecols=["game_id", "minutes_played"])
    mmax = app.groupby("game_id").minutes_played.max()
    elo = CB.build_elo(games)
    c = CB.cup_table(games, elo, mmax)

    L = ["## Esperimento F — Coppe: gare di ritorno", ""]
    # ── plausibilità dell'Elo ricostruito ─────────────────────────────────────
    R = elo.attrs["final_ratings"]
    names = {}
    for r in games.dropna(subset=["home_club_id"]).drop_duplicates("home_club_id", keep="last").itertuples():
        names[int(r.home_club_id)] = r.home_club_name
    last_season = games.groupby("home_club_id").season.max()
    with open(os.path.join(REPO_ROOT, "data", "cache", "clubelo_cups.json"), encoding="utf-8") as fh:
        live = json.load(fh)["ranking"]
    pairs = []
    for cid, nm in names.items():
        if not isinstance(nm, str) or last_season.get(cid, 0) < 2025 or cid not in R:
            continue
        best = max(((CUPS_LIVE.name_similarity(nm, v["name"]), v["elo"], v["name"]) for v in live.values()), default=(0, 0, ""))
        if best[0] >= 0.9:
            pairs.append((R[cid], best[1], nm, best[2]))
    a = np.array([(x[0], x[1]) for x in pairs])
    L += ["### Plausibilità dell'Elo ricostruito", "",
          f"Confronto tra il mio Elo a fine dati (2026-09) e il ranking attuale di clubelo.com ({len(live)} club): {len(pairs)} club con "
          f"abbinamento di nome sicuro (somiglianza ≥ 0.9) e partite nel 2025/26 o dopo. Correlazione di Pearson "
          f"{pearsonr(a[:, 0], a[:, 1])[0]:.3f}, di Spearman {spearmanr(a[:, 0], a[:, 1])[0]:.3f}; pendenza ClubElo/mio Elo "
          f"{np.polyfit(a[:, 0], a[:, 1], 1)[0]:.2f}. Le scale non coincidono: i coefficienti si stimano comunque dai dati.", ""]
    top = sorted(pairs, key=lambda x: -x[0])[:6]
    L += ["Primi 6 club per Elo ricostruito (mio / ClubElo): " + "; ".join(f"{x[2]} {x[0]:.0f} / {x[3]} {x[1]:.0f}" for x in top) + ".", ""]

    # ── descrizione del campione ──────────────────────────────────────────────
    test = c[(c.season >= FIRST) & (c.season <= LAST)]
    ret = test[test.is_return]
    L += ["### Campione", "",
          f"Partite delle fasi principali di CL/EL/UCOL 2012/13-2025/26 con punteggio e Elo: {len(c)} (finali escluse). "
          f"Nel test 2016/17-2025/26: **{len(test)} partite**, di cui **{len(ret)} gare di ritorno** (validazione 2019/20-2021/22: "
          f"{int(ret.season.isin(VAL).sum())}; held-out 2022/23-2025/26: {int((~ret.season.isin(VAL)).sum())}), "
          f"{int(test.is_first_leg.sum())} andate, {int(test.is_single_ko.sum())} gare uniche a eliminazione diretta, "
          f"{int(test.is_group.sum())} partite dei gironi.", "",
          f"Partite ai supplementari riconosciute (minuti > 95): {int(test.et_ok.sum())} nel test, di cui {int((test.et_ok & test.is_return).sum())} "
          f"gare di ritorno e {int((test.et_ok & test.is_single_ko).sum())} gare uniche; la classe 1X2 dei 90' è ricostruita con la regola scritta "
          f"prima ed escluse dal training dei gol. Partite senza minuti nel dataset (supplementari non controllabili): "
          f"{int((~test.has_minutes).sum())} nel test, di cui {int((~ret.has_minutes).sum())} tra le gare di ritorno.", ""]

    # ── walk-forward ──────────────────────────────────────────────────────────
    P0 = CB.walk_forward(c, "base", FIRST, LAST)
    ok = np.isfinite(P0).all(1)
    y = c.y.to_numpy()
    weeks = c.date.dt.strftime("%G-%V").to_numpy()
    isret = c.is_return.to_numpy()
    val = c.season.isin(VAL).to_numpy()
    ll0 = ll_vec(P0[ok], y[ok]).mean()
    L += [f"Log-loss 1X2 del baseline (modello Elo riallenato in walk-forward, Elo ricostruito) su tutte le {int(ok.sum())} partite del test: "
          f"**{ll0:.4f}**; sulle sole gare di ritorno: {ll_vec(P0[ok & isret], y[ok & isret]).mean():.4f}. "
          "Non è confrontabile col 0.965 di `cups_model.json` (Elo diverso, insieme di partite diverso).", ""]
    res, Pf = {}, {}
    for f in FORMS:
        P = CB.walk_forward(c, f, FIRST, LAST)
        Pf[f] = P
        d = np.zeros(len(c))
        d[ok] = ll_vec(P0[ok], y[ok]) - ll_vec(P[ok], y[ok])
        res[f] = dict(name=NAMES[f], all=summary(d, weeks, ok), ret=summary(d, weeks, ok & isret),
                      ret_val=summary(d, weeks, ok & isret & val), ret_held=summary(d, weeks, ok & isret & ~val),
                      val=summary(d, weeks, ok & val), held=summary(d, weeks, ok & ~val),
                      ll=ll_vec(P[ok], y[ok]).mean(), d=d)
        print(f, res[f]["ret"]["d"], flush=True)

    def row(r):
        a_, b, v, h = r["all"], r["ret"], r["ret_val"], r["ret_held"]
        return (f"| {r['name']} | {r['ll']:.4f} | {a_['d']:+.5f} [{a_['lob']:+.5f}, {a_['hib']:+.5f}] | {b['d']:+.5f} [{b['lo']:+.5f}, {b['hi']:+.5f}] | "
                f"[{b['lob']:+.5f}, {b['hib']:+.5f}] | {v['d']:+.5f} | {h['d']:+.5f} [{h['lob']:+.5f}, {h['hib']:+.5f}] |")
    L += ["### Varianti (ogni forma da sola vs baseline)", "",
          "Δ = log-loss(baseline) − log-loss(variante). «Tutte» = tutte le partite del test (la variante cambia solo le gare di ritorno, "
          "il resto varia di poco per il riallenamento); «ritorni» = solo gare di ritorno.", "",
          "| Forma | Log-loss (tutte) | Δ tutte [IC a blocchi] | Δ ritorni [IC per partita] | IC a blocchi ritorni | Δ ritorni validazione | Δ ritorni held-out [IC a blocchi] |",
          "|---|---:|---|---|---|---:|---|"] + [row(res[f]) for f in FORMS] + [""]
    best = max(res[f]["val"]["d"] for f in FORMS)
    chosen = next(f for f in FORMS if res[f]["val"]["d"] >= best - TIE)
    best_r = max(res[f]["ret_val"]["d"] for f in FORMS)
    sel_ret = next(f for f in FORMS if res[f]["ret_val"]["d"] >= best_r - TIE)
    r = res[chosen]
    h = r["ret_held"]
    verdict = "migliora" if (h["d"] > 0 and h["lob"] > 0) else ("peggiora" if (h["d"] < 0 and h["hib"] < 0) else "non distinguibile dal rumore")
    L += [f"Scelta sulle validazione (Δ su tutte le partite di validazione, parità entro {TIE} → la più semplice): **{r['name']}** "
          f"(Δ validazione {r['val']['d']:+.5f}); scegliendo sul Δ delle sole gare di ritorno in validazione sarebbe {NAMES[sel_ret]}. "
          f"Verdetto (Δ sulle gare di ritorno held-out, IC a blocchi): **{verdict}**.", "",
          f"Dettaglio della variante scelta, gare di ritorno: n = {r['ret']['n']} (validazione {r['ret_val']['n']}, held-out {h['n']}); "
          f"Δ {r['ret']['d']:+.5f} [IC per partita {r['ret']['lo']:+.5f}, {r['ret']['hi']:+.5f}; IC a blocchi {r['ret']['lob']:+.5f}, {r['ret']['hib']:+.5f}]. "
          "Con così poche gare di ritorno gli intervalli sono larghi.", ""]
    Xl = CB.design(c, chosen)
    trm = (c.season <= LAST).to_numpy() & c.usable_goals.to_numpy()
    w = 0.5 ** ((LAST - c.season.to_numpy()[trm]) / CB.HALF_LIFE_SEASONS)
    mh, ma, rho = CB._fit(Xl[trm], c.home_club_goals.to_numpy()[trm], c.away_club_goals.to_numpy()[trm], w)
    cols = {"F1": ["elo_diff", "g"], "F2": ["elo_diff", "segno(g)"], "F3": ["elo_diff", "g+", "g−"]}[chosen]
    L += ["Coefficienti (log-gol attesi) del fit su tutte le stagioni fino al 2025/26, per illustrazione: casa " +
          ", ".join(f"{n} {v:+.3f}" for n, v in zip(cols, mh.coef_)) + "; ospite " + ", ".join(f"{n} {v:+.3f}" for n, v in zip(cols, ma.coef_)) +
          f"; rho {rho:+.3f}.", ""]
    dd = r["d"]
    seas = list(range(FIRST, LAST + 1))
    L += ["| Stagione | " + " | ".join(f"{s}/{(s + 1) % 100:02d}" for s in seas) + " |", "|---|" + "---:|" * len(seas),
          "| Gare di ritorno | " + " | ".join(str(int(((c.season == s) & ok & isret).sum())) for s in seas) + " |",
          "| Δ log-loss sui ritorni | " + " | ".join((f"{dd[((c.season == s) & ok & isret).to_numpy()].mean():+.3f}"
                                                   if ((c.season == s) & ok & isret).any() else "—") for s in seas) + " |", ""]
    with open(os.path.join(PARTS4, "F.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    strip = lambda x: {k: v for k, v in x.items() if k != "d"}
    pd.to_pickle(dict(res={k: strip(v) for k, v in res.items()}, chosen=chosen, ll0=float(ll0), verdict=verdict,
                      n_ret=len(ret), n_test=len(test)), os.path.join(C3.R3_DIR, "r4_F.pkl"))
    print("\n".join(L))


if __name__ == "__main__":
    main()
