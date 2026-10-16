"""Round 5 — analisi aggiuntiva (NON prevista dal prereg) sul segnale dei corner e sulla coerenza dell'abbinamento.
Da lanciare in modalità isolata:  python -I -X utf8 backtest/run_round5_H2.py"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import data, features, referees as RF, round3_ctx as C3, round5_lib as R5

PARTS5 = os.path.join(REPO_ROOT, "backtest", "round5_parts")
K, FORM = 20, "b"                  # configurazione scelta per G


def main():
    c = C3.get_ctx3()
    df = c.df
    feat = c.feat.join(features.build_stat_features(df))
    refs = RF.map_referees(df).reindex(feat.index)
    keys_tm = refs.ref
    fd = RF.fd_referee_e0(df).reindex(feat.index)
    L = ["### Analisi aggiuntiva (NON prevista dal prereg): da dove viene il segnale sui corner?", ""]

    # (1) accordo sul solo cognome
    e0 = feat[(feat.Division == "E0") & (feat.season >= 2014)]
    both = keys_tm.reindex(e0.index).notna() & fd.reindex(e0.index).notna()
    sur = [RF.normalize(a).split()[-1] == RF.normalize(b).split()[-1] for a, b in zip(keys_tm[e0.index][both], fd[e0.index][both])]
    L += [f"Premier League: accordo sul solo cognome tra Transfermarkt e football-data = {np.mean(sur):.1%} su {int(both.sum())} partite "
          "(le differenze rimaste a livello di iniziale sono nomi diversi della stessa persona, es. «Bobby» / «R Madley»).", ""]

    # (2) Stage 0 e insieme di valutazione, come in G
    st, st_c = R5.Stage0(feat, "gialli"), R5.Stage0(feat, "corner")
    complete = feat[["HY", "AY", "HC", "AC", "HF", "AF"]].notna().all(axis=1)
    test = (feat.date >= pd.Timestamp("2019-07-01")) & complete & st.mh.notna() & st_c.mh.notna()
    ev = feat[test]
    weeks = ev.date.dt.strftime("%G-%V").to_numpy()
    is_val = ev.season.isin(C3.VALIDATION).to_numpy()

    def delta(stobj, keys, mask):
        base = R5.vectors(stobj, pd.DataFrame({"mh": stobj.mh, "ma": stobj.ma, "alpha": stobj.alpha}), test)
        pred, _ = R5.with_referee(stobj, keys, K, FORM)
        var = R5.vectors(stobj, pred, test)
        d = base["nb"] - var["nb"]
        m = mask.to_numpy()
        a, lo, hi = C3.ci_match(d[m])
        _, lob, hib = C3.ci_block(d[m], weeks[m])
        return a, lob, hib, int(m.sum())

    # (3) per lega, corner e gialli, con gli arbitri di Transfermarkt
    L += ["**Δ log-loss del totale per lega (arbitri da Transfermarkt, forma b, k=20; IC a blocchi)**", "",
          "| Lega | Gialli | Corner |", "|---|---|---|"]
    for lg in data.LEAGUES:
        mk = (ev.Division == lg)
        g = delta(st, keys_tm, mk)
        h = delta(st_c, keys_tm, mk)
        L.append(f"| {data.LEAGUE_NAMES[lg]} | {g[0]:+.5f} [{g[1]:+.5f}, {g[2]:+.5f}] | {h[0]:+.5f} [{h[1]:+.5f}, {h[2]:+.5f}] |")
    # (4) Premier League: arbitri da football-data (fonte indipendente) contro Transfermarkt
    keys_fd = fd.map(RF.normalize)
    mk = (ev.Division == "E0")
    L += ["", "**Premier League, stessa procedura con le due fonti dell'arbitro** (football-data = fonte indipendente dall'abbinamento Transfermarkt)", "",
          "| Fonte | Gialli | Corner |", "|---|---|---|"]
    for lab, keys in (("Transfermarkt", keys_tm), ("football-data (colonna Referee)", keys_fd)):
        g = delta(st, keys, mk)
        h = delta(st_c, keys, mk)
        L.append(f"| {lab} | {g[0]:+.5f} [{g[1]:+.5f}, {g[2]:+.5f}] | {h[0]:+.5f} [{h[1]:+.5f}, {h[2]:+.5f}] |")
    L.append("")
    with open(os.path.join(PARTS5, "H2.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
