"""Round 7, fase 2 — estensione della griglia di L3 (criteri in backtest/round7_parts/prereg_l3ext.md).
Da lanciare:  python -I -X utf8 backtest/run_round7_l3ext.py   (scrive backtest/round7_parts/L3EXT.md e il pickle con la scelta finale)"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd

from backtest import round6_lib as R6, round7_lib as L7
from backtest.run_round7 import SPEC, TIE, interval_gaps, prepare, simp_key

H0, K0 = (4, 8, 12), (5, 15, 40)
START = {"tiri": (12, 40), "sot": (8, 40), "corner": (12, 40), "falli": (4, 15), "gialli": (4, 15)}      # scelte della fase 1
EXT = {1: ((16, 24), (2, 3), (80, 160)), 2: ((32, 48), (1,), (320, 640))}                              # (H in alto, H in basso, k in alto)


def extend(Hs, Ks, dims, step):
    Hs, Ks = set(Hs), set(Ks)
    up_h, dn_h, up_k = EXT[step]
    if "Hmax" in dims:
        Hs |= set(up_h)
    if "Hmin" in dims:
        Hs |= set(dn_h)
    if "Kmax" in dims:
        Ks |= set(up_k)
    return sorted(Hs), sorted(Ks)


def border(ch, Hs, Ks, allowed):
    out = set()
    if ch[0] == max(Hs) and "Hmax" in allowed:
        out.add("Hmax")
    if ch[0] == min(Hs) and "Hmin" in allowed:
        out.add("Hmin")
    if ch[1] == max(Ks) and "Kmax" in allowed:
        out.add("Kmax")
    return out


def main():
    feat, gw, weeks, st = prepare()
    L = ["## Round 7, fase 2 — risultati dell'estensione della griglia di L3", ""]
    final = {}
    for s in L7.STATS:
        run, al, spec = st[s]["run"], st[s]["al"], SPEC[s]
        ok = (run.mh.notna() & feat[spec["hc"]].notna() & feat[spec["ac"]].notna() & (feat.season >= L7.FIRST_TEST)).to_numpy()
        rows = feat.index[ok]
        wk = weeks[ok]
        seas = feat.season.to_numpy()[ok]
        is_val = np.isin(seas, L7.VALIDATION)
        v0 = R6.evaluate(run, rows, al)
        cache = {}

        def do(c):
            if c in cache:
                return
            rh = L7.dynamic_level(feat.date, feat.Division.to_numpy(), run.mh.to_numpy(), feat[spec["hc"]].to_numpy(float), *c)
            ra = L7.dynamic_level(feat.date, feat.Division.to_numpy(), run.ma.to_numpy(), feat[spec["ac"]].to_numpy(float), *c)
            run2 = R6.Run(feat, SPEC[s], run.mh * rh, run.ma * ra, run.folds)
            v = R6.evaluate(run2, rows, al)
            cache[c] = (R6.compare(v0, v, wk, is_val), run2, v)

        def choose(cfgs):
            best = max(cache[c][0]["ll_tot_val"]["d"] for c in cfgs)
            cand = [c for c in cfgs if cache[c][0]["ll_tot_val"]["d"] >= best - TIE]
            return min(cand, key=simp_key)

        Hs, Ks = list(H0), list(K0)
        for c in [(h, k) for h in Hs for k in Ks]:
            do(c)
        ch = choose([(h, k) for h in Hs for k in Ks])
        notes = [f"Fase 1: scelta H={ch[0]}, k={ch[1]}."]
        assert ch == START[s], (s, ch, START[s])
        allowed = set()
        if ch[0] == max(H0):
            allowed.add("Hmax")
        if ch[0] == min(H0):
            allowed.add("Hmin")
        if ch[1] == max(K0):
            allowed.add("Kmax")
        step = 0
        while allowed and step < 2:
            step += 1
            Hs, Ks = extend(Hs, Ks, allowed, step)
            cfgs = [(h, k) for h in Hs for k in Ks]
            for c in cfgs:
                do(c)
            new = choose(cfgs)
            notes.append(f"Estensione {step} (dimensioni {', '.join(sorted(allowed))}): H ∈ {Hs}, k ∈ {Ks}; scelta H={new[0]}, k={new[1]}.")
            ch = new
            allowed = border(ch, Hs, Ks, allowed) if step == 1 else set()
        cfgs = [(h, k) for h in Hs for k in Ks]
        r, run2, v = cache[ch]
        ver = R6.verdict(r)
        g0, g1 = interval_gaps(feat, s, run, al, rows), interval_gaps(feat, s, run2, al, rows)
        still = border(ch, Hs, Ks, {"Hmax", "Hmin", "Kmax"})
        L += [f"### {L7.KEYS[s]}", ""] + [f"- {n}" for n in notes]
        L += [f"- Scelta finale: **H = {ch[0]}, k = {ch[1]}**" + (f" (ancora sul bordo: {', '.join(sorted(still))}; ci si ferma come da prereg)" if still else " (interna alla griglia)") + f"; verdetto: {ver}.", "",
              "| H (sett.) | k | Δ ll totale (tutte) [IC a blocchi] | Δ totale validazione | Δ totale held-out [IC a blocchi] | Δ per squadra held-out | Verdetto |", "|---:|---:|---|---:|---|---:|---|"]
        for c in sorted(cfgs):
            q = cache[c][0]
            L.append(f"| {c[0]} | {c[1]} | {q['ll_tot']['d']:+.5f} [{q['ll_tot']['lob']:+.5f}, {q['ll_tot']['hib']:+.5f}] | {q['ll_tot_val']['d']:+.5f} | {q['ll_tot_held']['d']:+.5f} [{q['ll_tot_held']['lob']:+.5f}, {q['ll_tot_held']['hib']:+.5f}] | {q['ll_team_held']['d']:+.5f} | {R6.verdict(q)}{' ← scelta' if c == ch else ''} |")
        L.append("")
        d26 = (v0["ll_tot"] - v["ll_tot"])[seas == 2026].mean()
        final[s] = dict(chosen=ch, verdict=ver, border=sorted(still), gaps=(g0, g1), d26=float(d26), res=r)
        print(s, ch, ver, flush=True)
    L += ["### Riepilogo finale (configurazioni messe in produzione)", "", "| Statistica | H | k | Δ ll totale tutte [IC] | Δ totale held-out [IC] | Δ per squadra held-out [IC] | Δ O/U totale held-out | Δ totale 2026/27 | Verdetto |", "|---|---:|---:|---|---|---|---:|---:|---|"]
    for s in L7.STATS:
        f = final[s]
        r = f["res"]
        L.append(f"| {L7.KEYS[s]} | {f['chosen'][0]} | {f['chosen'][1]} | {r['ll_tot']['d']:+.5f} [{r['ll_tot']['lob']:+.5f}, {r['ll_tot']['hib']:+.5f}] | {r['ll_tot_held']['d']:+.5f} [{r['ll_tot_held']['lob']:+.5f}, {r['ll_tot_held']['hib']:+.5f}] | "
                 f"{r['ll_team_held']['d']:+.5f} [{r['ll_team_held']['lob']:+.5f}, {r['ll_team_held']['hib']:+.5f}] | {r['ou_tot']['d']:+.5f} | {f['d26']:+.5f} | {f['verdict']} |")
    L += ["", "**Copertura degli intervalli con la configurazione finale** (frequenza reale − probabilità dichiarata; base → con livello):", "",
          "| Statistica | Squadra, tutte | Totale, tutte | Squadra, 2026/27 | Totale, 2026/27 |", "|---|---|---|---|---|"]
    for s in L7.STATS:
        g0, g1 = final[s]["gaps"]
        L.append(f"| {L7.KEYS[s]} | {g0['tutte']['team'] * 100:+.1f} → {g1['tutte']['team'] * 100:+.1f} pp | {g0['tutte']['total'] * 100:+.1f} → {g1['tutte']['total'] * 100:+.1f} pp | {g0['2026/27']['team'] * 100:+.1f} → {g1['2026/27']['team'] * 100:+.1f} pp | {g0['2026/27']['total'] * 100:+.1f} → {g1['2026/27']['total'] * 100:+.1f} pp |")
    L.append("")
    open(os.path.join(L7.P7, "L3EXT.md"), "w", encoding="utf-8").write("\n".join(L))
    pd.to_pickle({s: dict(chosen=final[s]["chosen"], verdict=final[s]["verdict"], border=final[s]["border"], d_all=final[s]["res"]["ll_tot"]["d"],
                          d_held=final[s]["res"]["ll_tot_held"]["d"], gaps=final[s]["gaps"]) for s in L7.STATS},
                 os.path.join(os.path.dirname(L7.CTX7), "l3ext.pkl"))
    print("\n".join(L))


if __name__ == "__main__":
    main()
