"""Round 5 — G (arbitro nel modello dei gialli) e H (corner, controllo). Solo backtest.
Da lanciare in modalità isolata:  python -I -X utf8 backtest/run_round5_G.py"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import data, features, referees as RF, round2_ctx as C2, round3_ctx as C3, round5_lib as R5, stats_model as sm

PARTS5 = os.path.join(REPO_ROOT, "backtest", "round5_parts")
os.makedirs(PARTS5, exist_ok=True)
KS = [5, 10, 20, 40, 80]
GRID = [(f, k) for f in ("a", "b") for k in KS]          # ordine di semplicità: a prima di b, k crescente
TIE = 0.0002


def fmt_metrics(res, title):
    rows = [("Log-loss del totale (NB)", "nb", 4), ("Log-loss Over/Under (media 4 linee)", "ou", 4), ("MAE del totale", "mae", 4),
            ("Copertura intervallo 80% (obiettivo 0.80)", "cover", 4)]
    L = [f"**{title}**", "", "| Metrica | Baseline | Variante | Δ | IC per partita | IC a blocchi |", "|---|---:|---:|---:|---|---|"]
    for lab, k, nd in rows:
        r = res[k]
        L.append(f"| {lab} | {r['base']:.{nd}f} | {r['var']:.{nd}f} | {r['d']:+.5f} | [{r['lo']:+.5f}, {r['hi']:+.5f}] | [{r['lob']:+.5f}, {r['hib']:+.5f}] |")
    for lab, k in (("Correlazione per squadra", "corr_team"), ("Correlazione del totale", "corr_total")):
        r = res[k]
        L.append(f"| {lab} | {r['base']:.4f} | {r['var']:.4f} | {r['d']:+.5f} | — | [{r['lob']:+.5f}, {r['hib']:+.5f}] |")
    L += ["", "Log-loss Over/Under per linea (Δ = baseline − variante, IC a blocchi): " + "; ".join(
        f"{k[2:]}: {res[k]['base']:.4f} → {res[k]['var']:.4f} (Δ {res[k]['d']:+.5f} [{res[k]['lob']:+.5f}, {res[k]['hib']:+.5f}])"
        for k in res if k.startswith("ou") and k != "ou") + ".", "",
          f"Log-loss del totale per periodo: validazione Δ {res['nb_val']['d']:+.5f} [{res['nb_val']['lob']:+.5f}, {res['nb_val']['hib']:+.5f}] "
          f"(n={res['nb_val']['n']}); held-out Δ {res['nb_held']['d']:+.5f} [{res['nb_held']['lob']:+.5f}, {res['nb_held']['hib']:+.5f}] (n={res['nb_held']['n']}).", ""]
    return L


def verdict(res):
    h = res["nb_held"]
    return "migliora" if (h["d"] > 0 and h["lob"] > 0) else ("peggiora" if (h["d"] < 0 and h["hib"] < 0) else "non distinguibile dal rumore")


def main():
    c = C3.get_ctx3()
    df = c.df
    feat = c.feat.join(features.build_stat_features(df))
    refs = RF.map_referees(df).reindex(feat.index)
    keys = refs.ref
    L = ["## Esperimento G — Arbitro nel modello dei cartellini gialli", ""]

    # ── copertura e coerenza dell'abbinamento ────────────────────────────────
    d2 = feat.assign(ref=keys, matched=refs.matched)
    cov = d2[d2.season >= 2014].groupby(["season", "Division"]).apply(lambda g: g.ref.notna().mean()).unstack()
    L += ["### Abbinamento e copertura", "",
          "Quota di partite di campionato con arbitro (abbinate a una partita Transfermarkt con arbitro indicato):", "",
          "| Stagione | " + " | ".join(data.LEAGUE_NAMES[l] for l in data.LEAGUES) + " |", "|---|" + "---:|" * 5]
    for s in cov.index:
        L.append(f"| {C2.season_label(s)} | " + " | ".join(f"{cov.loc[s, l]:.1%}" for l in data.LEAGUES) + " |")
    n_tot = int((d2.season >= 2016).sum())
    L += ["", f"Dal 2016/17 (inizio dello storico dei modelli): {int(d2[d2.season >= 2016].ref.notna().sum())}/{n_tot} partite con arbitro. "
              "La stagione 2026/27 non è nel dataset: arbitro sconosciuto → effetto zero.", ""]
    dist = d2[d2.season >= 2016].groupby("Division").ref.agg(["nunique", lambda s: s.value_counts().median()])
    L += ["Arbitri distinti (dal 2016/17) e partite mediane per arbitro:", "", "| Lega | Arbitri distinti | Partite mediane per arbitro |", "|---|---:|---:|"]
    for lg in data.LEAGUES:
        L.append(f"| {data.LEAGUE_NAMES[lg]} | {int(dist.loc[lg].iloc[0])} | {dist.loc[lg].iloc[1]:.0f} |")
    L += ["", f"Totale arbitri distinti: {d2[d2.season >= 2016].groupby('Division').ref.nunique().sum()} (chiave = lega + nome).", ""]
    fd = RF.fd_referee_e0(df).reindex(feat.index)
    e0 = d2[(d2.Division == "E0") & (d2.season >= 2014)]
    agree = np.array([RF.same_referee(a, b) for a, b in zip(e0.ref, fd.reindex(e0.index))])
    both = e0.ref.notna() & fd.reindex(e0.index).notna()
    L += [f"**Controllo di coerenza con football-data (colonna `Referee`, solo Premier League)**: su {int(both.sum())} partite 2014/15-2026/27 con arbitro in entrambe "
          f"le fonti, stesso arbitro (stesso cognome e stessa iniziale) nel **{agree[both.to_numpy()].mean():.1%}** dei casi. "
          "Per le altre leghe football-data non ha l'arbitro: il controllo non è possibile.", ""]
    bad = e0[both & ~pd.Series(agree, index=e0.index)]
    if len(bad):
        ex = [(r.HomeTeam, r.AwayTeam, str(r.season), r.ref, fd.get(i)) for i, r in bad.head(5).iterrows()]
        L += ["Esempi di disaccordo: " + "; ".join(f"{h}-{a} {s}: TM «{t}» / FD «{f}»" for h, a, s, t, f in ex) + ".", ""]

    # ── stadio 0 e insieme di valutazione ─────────────────────────────────────
    st = R5.Stage0(feat, "gialli")
    st_c = R5.Stage0(feat, "corner")
    complete = feat[["HY", "AY", "HC", "AC", "HF", "AF"]].notna().all(axis=1)
    test = (feat.date >= pd.Timestamp("2019-07-01")) & complete & st.mh.notna() & st_c.mh.notna()
    ev = feat[test]
    weeks = ev.date.dt.strftime("%G-%V").to_numpy()
    is_val = ev.season.isin(C3.VALIDATION).to_numpy()
    base_pred = pd.DataFrame({"mh": st.mh, "ma": st.ma, "alpha": st.alpha})
    vb = R5.vectors(st, base_pred, test)
    L += ["### Baseline e insieme di valutazione", "",
          f"{len(ev)} partite di test (dal 2019/20) con gialli, falli e corner disponibili; stesso insieme per baseline e varianti. Baseline gialli: "
          f"log-loss del totale {vb['nb'].mean():.4f}, correlazione per squadra {R5.corr_team(vb):.3f}, MAE {vb['mae'].mean():.3f}, "
          f"copertura 80% {vb['cover'].mean():.3f}; media dei gialli per partita {(ev.HY + ev.AY).mean():.2f}.", ""]

    # ── griglia ───────────────────────────────────────────────────────────────
    res, preds = {}, {}
    for form, k in GRID:
        pred, R = R5.with_referee(st, keys, k, form)
        vv = R5.vectors(st, pred, test)
        res[(form, k)] = R5.compare5(vb, vv, weeks, is_val)
        preds[(form, k)] = (pred, R)
        print(form, k, f"{res[(form, k)]['nb']['d']:+.5f}", flush=True)
    best = max(res[g]["nb_val"]["d"] for g in GRID)
    chosen = next(g for g in GRID if res[g]["nb_val"]["d"] >= best - TIE)
    L += ["### Griglia: effetto arbitro sui gialli (10 configurazioni, ogni riga da sola vs baseline)", "",
          "Δ = log-loss del totale (baseline − variante); forma a = moltiplicativa, b = regressore appreso; k = partite equivalenti di shrinkage.", "",
          "| Forma | k | Log-loss totale | Δ tutte [IC a blocchi] | Δ validazione | Δ held-out [IC a blocchi] | Δ log-loss Over/Under | Δ corr. per squadra |",
          "|---|---:|---:|---|---:|---|---:|---:|"]
    for g in GRID:
        r = res[g]
        L.append(f"| {g[0]} | {g[1]} | {r['nb']['var']:.4f} | {r['nb']['d']:+.5f} [{r['nb']['lob']:+.5f}, {r['nb']['hib']:+.5f}] | "
                 f"{r['nb_val']['d']:+.5f} | {r['nb_held']['d']:+.5f} [{r['nb_held']['lob']:+.5f}, {r['nb_held']['hib']:+.5f}] | "
                 f"{r['ou']['d']:+.5f} | {r['corr_team']['d']:+.5f} |")
    r = res[chosen]
    L += ["", f"**Scelta sulle validazione** (log-loss del totale; parità entro {TIE} → la più semplice): **forma {chosen[0]}, k = {chosen[1]}** "
              f"(Δ validazione {r['nb_val']['d']:+.5f}). Verdetto: **{verdict(r)}**.", ""]
    L += fmt_metrics(r, f"G1 — effetto arbitro sui gialli, forma {chosen[0]}, k={chosen[1]} (variante scelta)")
    R = preds[chosen][1]
    te_idx = ev.index
    n_known = float((keys.reindex(te_idx).notna()).mean())
    L += [f"Nei dati di test l'arbitro è noto per il {n_known:.1%} delle partite; |log R| mediano {np.median(np.abs(np.log(R.reindex(te_idx)))):.3f} "
          f"(R tra {R.reindex(te_idx).quantile(0.05):.2f} e {R.reindex(te_idx).quantile(0.95):.2f} tra il 5° e il 95° percentile).", ""]
    # per stagione e lega
    d_nb = vb["nb"] - R5.vectors(st, preds[chosen][0], test)["nb"]
    L += ["| Stagione | " + " | ".join(C2.season_label(s) for s in sorted(ev.season.unique())) + " |",
          "|---|" + "---:|" * len(ev.season.unique()),
          "| Δ log-loss totale | " + " | ".join(f"{d_nb[(ev.season == s).to_numpy()].mean():+.4f}" for s in sorted(ev.season.unique())) + " |", "",
          "| Lega | " + " | ".join(data.LEAGUE_NAMES[l] for l in data.LEAGUES) + " |", "|---|" + "---:|" * 5,
          "| Δ log-loss totale | " + " | ".join(f"{d_nb[(ev.Division == l).to_numpy()].mean():+.4f}" for l in data.LEAGUES) + " |", ""]

    # ── G2: falli ─────────────────────────────────────────────────────────────
    mf = np.exp(feat.falli_lh) + np.exp(feat.falli_la)
    yf = feat.HF + feat.AF
    mbar_f = R5.mbar_by_league(feat, mf)
    Rf = R5.referee_ratio(feat, yf, mf, keys, chosen[1], mbar_f)
    pred2, _ = R5.with_referee(st, keys, chosen[1], "b", extra=[np.log(Rf)])
    v2 = R5.vectors(st, pred2, test)
    res2 = R5.compare5(vb, v2, weeks, is_val)
    g1b = R5.compare5(R5.vectors(st, preds[("b", chosen[1])][0], test), v2, weeks, is_val)
    L += ["### G2 — in più l'effetto arbitro sui falli (forma b, stesso k)", "",
          "Regressore aggiuntivo log R_f: rapporto tra falli osservati e attesi (modello Poisson attacco/difesa sui falli) nelle partite passate dell'arbitro. "
          "Il modello non ha un modello dei rossi: la variante «rossi» non è applicabile.", ""]
    L += fmt_metrics(res2, f"G2 vs baseline (k={chosen[1]})")
    L += [f"G2 rispetto a G1 (forma b, k={chosen[1]}): Δ log-loss totale {g1b['nb']['d']:+.5f}, IC a blocchi [{g1b['nb']['lob']:+.5f}, {g1b['nb']['hib']:+.5f}].", ""]

    # ── placebo ───────────────────────────────────────────────────────────────
    kp = R5.permute_keys(feat, keys)
    predp, _ = R5.with_referee(st, kp, chosen[1], chosen[0])
    resp = R5.compare5(vb, R5.vectors(st, predp, test), weeks, is_val)
    L += ["### Placebo", "",
          f"Arbitri permutati a caso tra le partite dello stesso campionato e stagione, stessa configurazione (forma {chosen[0]}, k={chosen[1]}): "
          f"Δ log-loss del totale {resp['nb']['d']:+.5f}, IC a blocchi [{resp['nb']['lob']:+.5f}, {resp['nb']['hib']:+.5f}] "
          f"(con gli arbitri veri: {r['nb']['d']:+.5f}).", ""]

    # ── H: corner ─────────────────────────────────────────────────────────────
    vbc = R5.vectors(st_c, pd.DataFrame({"mh": st_c.mh, "ma": st_c.ma, "alpha": st_c.alpha}), test)
    predc, Rc = R5.with_referee(st_c, keys, chosen[1], chosen[0])
    resc = R5.compare5(vbc, R5.vectors(st_c, predc, test), weeks, is_val)
    flag = resc["nb"]["lob"] > 0 or resc["nb"]["hib"] < 0
    L += ["## Esperimento H — Corner, controllo", "",
          f"Stessa procedura applicata ai corner con la configurazione scelta per G (forma {chosen[0]}, k={chosen[1]}), senza scelta di parametri. "
          f"Baseline corner: log-loss del totale {vbc['nb'].mean():.4f}.", ""]
    L += fmt_metrics(resc, "H — effetto arbitro sui corner")
    L += [f"Esito del controllo: Δ log-loss del totale {resc['nb']['d']:+.5f}, IC a blocchi su tutte le stagioni [{resc['nb']['lob']:+.5f}, {resc['nb']['hib']:+.5f}] → "
          + ("**distinguibile da zero**: possibile problema di abbinamento (o effetto reale dell'arbitro), da indagare." if flag else
             "**non distinguibile da zero**, come atteso: nessun segnale di problemi nell'abbinamento."), ""]

    with open(os.path.join(PARTS5, "G.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    pd.to_pickle(dict(res=res, chosen=chosen, g2=res2, g1b=g1b, placebo=resp, corner=resc, n_ev=len(ev),
                      base=dict(nb=float(vb["nb"].mean()), corr=R5.corr_team(vb), mae=float(vb["mae"].mean()), cover=float(vb["cover"].mean())),
                      base_c=float(vbc["nb"].mean()), flag=bool(flag), verdict=verdict(res[chosen])),
                 os.path.join(C3.R3_DIR, "r5_G.pkl"))
    print("\n".join(L))


if __name__ == "__main__":
    main()
