"""Tiri: dispersione (alpha) separata per casa e ospite invece di un solo alpha per squadra — verifica in walk-forward.

Confronto, sulle stesse partite di test (2019/20 in poi), tra il modello attuale (un alpha per squadra, stimato a momenti sul training del fold)
e la variante con alpha_casa e alpha_ospite (stimati a momenti sullo stesso training, separatamente). Le medie attese non cambiano; l'alpha del
totale resta quello attuale, quindi log-loss e Over/Under del totale non cambiano. Si controllano: log-loss per squadra e del totale, log-loss
degli Over/Under (per squadra e totale), e (extra) il mercato «chi fa più tiri» della copula con ρ per lega ristimato con le nuove dispersioni.
Δ = attuale − variante (positivo = la variante migliora), IC 95% a blocchi per settimana ISO.

Da lanciare in modalità isolata:  python -I -X utf8 backtest/run_intervals_alpha.py   (scrive backtest/round6_parts/alpha_side.md e alpha_side.pkl)"""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd
from scipy.special import ndtri
from scipy.stats import nbinom

from backtest import round3_ctx as C3, round6_lib as R6, stats_v3
from backtest.run_intervals import build_feat, side_alphas, stat_intervals, summarize, TOL, NAMES, LEVELS

PARTS = os.path.join(REPO_ROOT, "backtest", "round6_parts")


def rho_by_fold(run, feat, spec, ah_aa):
    """ρ per lega per fold, PIT randomizzata dei residui di training con le dispersioni indicate ((ah, aa) per fold)."""
    rng = np.random.default_rng(17)
    out = {}
    for s, f in run.folds.items():
        i = f["idx"]
        yh, ya = feat.loc[i, spec["hc"]].to_numpy(int), feat.loc[i, spec["ac"]].to_numpy(int)
        ah, aa = ah_aa[s]
        zs = []
        for y, m, a in ((yh, f["mh"], ah), (ya, f["ma"], aa)):
            n_ = 1.0 / a
            p_ = n_ / (n_ + m)
            lo, hi = nbinom.cdf(y - 1, n_, p_), nbinom.cdf(y, n_, p_)
            zs.append(ndtri(np.clip(lo + rng.uniform(size=len(y)) * (hi - lo), 1e-9, 1 - 1e-9)))
        dv = feat.loc[i, "Division"].to_numpy()
        out[s] = {lg: float(np.corrcoef(zs[0][dv == lg], zs[1][dv == lg])[0, 1]) for lg in np.unique(dv)}
    return out


def fmt(d, key):
    r = d[key]
    return f"{r['d']:+.5f} [{r['lob']:+.5f}, {r['hib']:+.5f}]"


def main():
    feat = build_feat()
    spec = stats_v3.STATS3["tiri"]
    run = R6.run_model(feat, R6.SPECS["tiri"], stats_v3.design(feat, "tiri", True))
    al0, al1 = side_alphas(run, feat, spec)
    rows = feat.index[run.mh.notna() & feat[spec["hc"]].notna() & feat[spec["ac"]].notna()]
    weeks = feat.loc[rows, "date"].dt.strftime("%G-%V").to_numpy()
    is_val = feat.loc[rows, "season"].isin(C3.VALIDATION).to_numpy()
    v0, v1 = R6.evaluate(run, rows, al0), R6.evaluate(run, rows, al1)
    r = R6.compare(v0, v1, weeks, is_val)
    L = ["## Tiri: alpha separato per casa e ospite — verifica che non peggiori il modello attuale", "",
         f"{len(rows)} partite di test (dal 2019/20). Alpha medi del training (ultimo fold): attuale per squadra {al0.loc[rows, 'ah'].iloc[-1]:.4f}; "
         f"casa {al1.loc[rows, 'ah'].iloc[-1]:.4f}, ospite {al1.loc[rows, 'aa'].iloc[-1]:.4f}. L'alpha del totale non cambia ({al0.loc[rows, 'aT'].iloc[-1]:.4f}).", "",
         "Δ = attuale − alpha separato (positivo = migliora), IC 95% a blocchi per settimana ISO.", "",
         "| Metrica | Attuale | Alpha separato | Δ tutte [IC a blocchi] | Δ held-out (dal 2022/23) [IC a blocchi] |", "|---|---:|---:|---|---|"]
    ok_all = True
    for key, lab in (("ll_team", "Log-loss per squadra"), ("ll_tot", "Log-loss del totale"), ("ou_team", "Log-loss Over/Under per squadra (linee 10.5/12.5/14.5)"),
                     ("ou_tot", "Log-loss Over/Under del totale (linee 22.5/24.5/26.5)")):
        d = r[key]
        held = None
        mask = ~is_val
        dd = v0[key][mask] - v1[key][mask]
        _, lob, hib = C3.ci_block(dd, weeks[mask])
        held = f"{dd.mean():+.5f} [{lob:+.5f}, {hib:+.5f}]"
        L.append(f"| {lab} | {d['base']:.5f} | {d['var']:.5f} | {d['d']:+.5f} [{d['lob']:+.5f}, {d['hib']:+.5f}] | {held} |")
        if d["hib"] < 0 or dd.mean() < 0 and hib < 0:       # peggioramento con IC che esclude lo zero
            ok_all = False
    for key, lab in (("c80_team", "Copertura nominale 80% per squadra"), ("c80_tot", "Copertura nominale 80% del totale")):
        d = r[key]
        L.append(f"| {lab} (quantili, riferimento) | {d['base']:.4f} | {d['var']:.4f} | {d['d']:+.4f} [{d['lob']:+.4f}, {d['hib']:+.4f}] | |")
    # extra: «chi fa più tiri»
    M = spec["M"]
    f = feat.loc[rows]
    yh, ya = f[spec["hc"]].to_numpy(int), f[spec["ac"]].to_numpy(int)
    cls = np.where(yh > ya, 0, np.where(yh == ya, 1, 2))
    lls = {}
    for name, al, folds_a in (("attuale", al0, {s: (R6.moments(np.r_[feat.loc[fo["idx"], spec["hc"]].to_numpy(float), feat.loc[fo["idx"], spec["ac"]].to_numpy(float)],
                                                                np.r_[fo["mh"], fo["ma"]]),) * 2 for s, fo in run.folds.items()}),
                              ("alpha separato", al1, {s: (R6.moments(feat.loc[fo["idx"], spec["hc"]].to_numpy(float), fo["mh"]),
                                                          R6.moments(feat.loc[fo["idx"], spec["ac"]].to_numpy(float), fo["ma"])) for s, fo in run.folds.items()})):
        rho = rho_by_fold(run, feat, spec, folds_a)
        rr = np.where(np.isfinite(R6.rho_rows(run, rho, rows, True)), R6.rho_rows(run, rho, rows, True), 0.0)
        _, dif = R6.joint_dists(run.mh[rows].to_numpy(), run.ma[rows].to_numpy(), al.loc[rows, "ah"].to_numpy(), al.loc[rows, "aa"].to_numpy(), rr, M)
        P = np.column_stack([dif[:, M + 1:].sum(1), dif[:, M], dif[:, :M].sum(1)])
        lls[name] = -np.log(np.clip(P[np.arange(len(P)), cls], 1e-12, 1))
        print(name, lls[name].mean(), flush=True)
    d = lls["attuale"] - lls["alpha separato"]
    _, lob, hib = C3.ci_block(d, weeks)
    dh = d[~is_val]
    _, lobh, hibh = C3.ci_block(dh, weeks[~is_val])
    L.append(f"| Log-loss «chi fa più tiri» (copula, ρ per lega ristimato) | {lls['attuale'].mean():.5f} | {lls['alpha separato'].mean():.5f} | {d.mean():+.5f} [{lob:+.5f}, {hib:+.5f}] | {dh.mean():+.5f} [{lobh:+.5f}, {hibh:+.5f}] |")
    if hib < 0 and lob < 0:
        ok_all = False
    L += ["", "**Esito:** " + ("nessuna metrica peggiora con IC a blocchi che esclude lo zero." if ok_all else "ALCUNE METRICHE PEGGIORANO: fermarsi."), ""]
    with open(os.path.join(PARTS, "alpha_side.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    print("\n".join(L))
    if not ok_all:
        sys.exit(1)


if __name__ == "__main__":
    main()
