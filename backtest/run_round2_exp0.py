"""Round 2 — Esperimento 0: audit del benchmark (rimozione del margine) e calibrazione del baseline."""
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
import numpy as np
import pandas as pd
from scipy.optimize import minimize

from backtest import data, round2_ctx as C
from backtest.round2_lib import Boot, devig, ll_vec, metric_vecs

PARTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "round2_parts")
os.makedirs(PARTS, exist_ok=True)
METHODS = [("norm", "normalizzazione semplice"), ("power", "power"), ("shin", "Shin")]
SOURCES = [
    ("Quote medie (raccolta pre-partita)", ["odds_h", "odds_d", "odds_a"]),
    ("Quote medie di chiusura", ["cl_h", "cl_d", "cl_a"]),
    ("Pinnacle (raccolta)", ["ps_h", "ps_d", "ps_a"]),
    ("Pinnacle (chiusura)", ["psc_h", "psc_d", "psc_a"]),
]


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def calib_line(p, z):
    """logit(P(evento)) = a + b*logit(p): b=1, a=0 se calibrato."""
    x = logit(p)

    def nll(t):
        eta = t[0] + t[1] * x
        return np.sum(np.logaddexp(0, eta) - z * eta)
    return minimize(nll, [0.0, 1.0], method="BFGS").x


def main():
    c = C.get_ctx()
    ev, y = c.ev, c.y
    Pb = c.base_sp[["pH", "pD", "pA"]].to_numpy()
    out = ["## Esperimento 0 — Audit del benchmark e della calibrazione", ""]

    # ── 0a ────────────────────────────────────────────────────────────────────
    out += ["### 0a — Benchmark di mercato con tre metodi di rimozione del margine", "",
            f"Le quote medie coprono tutte le {len(ev)} partite di test (2019/20 → oggi); per le altre fonti si usa il "
            "sottoinsieme con quote valide (colonna N). Per ogni fonte il baseline è valutato sullo STESSO "
            "sottoinsieme. Δ = log-loss(normalizzazione) − log-loss(metodo): positivo = il metodo è migliore; "
            "IC 95% bootstrap appaiato per partita (5000 ricampionamenti).", "",
            "| Fonte | N | Metodo | Log-loss | RPS | Brier | Δ log-loss vs norm [IC 95%] | Baseline sullo stesso insieme |",
            "|---|---:|---|---:|---:|---:|---|---:|"]
    res0a = {}
    for src, cols in SOURCES:
        o = ev[cols].to_numpy(float)
        ok = np.isfinite(o).all(1) & (o > 1).all(1)
        yb = y[ok]
        base_ll = ll_vec(Pb[ok], yb).mean()
        P = {m: devig(o[ok], m) for m, _ in METHODS}
        lv = {m: ll_vec(P[m], yb) for m in P}
        for m, label in METHODS:
            ll, rps, br = metric_vecs(P[m], yb)
            if m == "norm":
                dtxt = "—"
            else:
                mean, lo, hi = Boot(int(ok.sum())).ci(lv["norm"] - lv[m])
                dtxt = f"{mean:+.5f} [{lo:+.5f}, {hi:+.5f}]"
            res0a[(src, m)] = dict(ll=ll.mean(), rps=rps.mean(), br=br.mean(), n=int(ok.sum()), base=base_ll)
            out.append(f"| {src} | {ok.sum()} | {label} | {ll.mean():.4f} | {rps.mean():.4f} | {br.mean():.4f} | "
                       f"{dtxt} | {base_ll:.4f} |")
    out.append("")
    o = ev[["cl_h", "cl_d", "cl_a"]].to_numpy(float)
    a, b = ll_vec(devig(o, "power"), y), ll_vec(devig(o, "shin"), y)
    m_, lo_, hi_ = Boot(len(y)).ci(a - b)
    out += [f"Shin vs power sulle quote di chiusura: Δ log-loss (power − Shin) = {m_:+.5f} [{lo_:+.5f}, {hi_:+.5f}].", ""]
    best = {src: min(("norm", "power", "shin"), key=lambda m: res0a[(src, m)]["ll"]) for src, _ in SOURCES}
    out += ["Metodo con la log-loss più bassa per fonte, e come cambia il divario baseline − mercato "
            "(positivo = il mercato è meglio del baseline):", ""]
    for src, _ in SOURCES:
        r_n, r_b = res0a[(src, "norm")], res0a[(src, best[src])]
        out.append(f"- {src}: norm {r_n['ll']:.4f} → {best[src]} {r_b['ll']:.4f} (Δ {r_n['ll'] - r_b['ll']:+.4f}); "
                   f"divario {r_n['base'] - r_n['ll']:+.4f} (norm) → {r_b['base'] - r_b['ll']:+.4f} ({best[src]})")
    out.append("")
    pd.to_pickle(dict(res0a=res0a, best=best), os.path.join(C.R2_DIR, "exp0a.pkl"))

    # ── 0b ────────────────────────────────────────────────────────────────────
    out += ["### 0b — Diagramma di affidabilità del baseline (stack + xG ridge)", "",
            "10 bin per decili della probabilità prevista (stesso numero di partite per bin; con bin di "
            "ampiezza uguale i pareggi cadrebbero in 2-3 bin). Differenza = frequenza reale − previsione media "
            "(negativa = esito sovrastimato). SE = errore standard binomiale della frequenza.", ""]
    names = ["Casa (1)", "Pareggio (X)", "Trasferta (2)"]
    chart = {}
    for k in range(3):
        p = Pb[:, k]
        z = (y == k).astype(float)
        bins = np.array_split(np.argsort(p, kind="stable"), 10)
        out += [f"**{names[k]}**", "", "| Bin | N | Previsto medio | Frequenza reale | Differenza | SE |",
                "|---:|---:|---:|---:|---:|---:|"]
        pts = []
        for i, ix in enumerate(bins):
            pm, fr = p[ix].mean(), z[ix].mean()
            se = np.sqrt(fr * (1 - fr) / len(ix))
            pts.append((pm, fr, se))
            out.append(f"| {i + 1} | {len(ix)} | {pm:.3f} | {fr:.3f} | {fr - pm:+.3f} | {se:.3f} |")
        chart[names[k]] = pts
        a_, b_ = calib_line(p, z)
        bias = z.mean() - p.mean()
        se_b = z.std(ddof=1) / np.sqrt(len(z))
        out += ["", f"Totale: previsto medio {p.mean():.4f}, frequenza reale {z.mean():.4f}, "
                    f"differenza {bias:+.4f} (IC 95% ±{1.96 * se_b:.4f}). Retta di ricalibrazione "
                    f"logit(freq) = {a_:+.3f} + {b_:.3f}·logit(p) (1 = calibrato).", ""]
    out += ["**Pareggio per stagione, lega e livello di gol attesi** (frequenza reale − previsto medio):", "",
            "| Segmento | N | Previsto X | Reale X | Differenza |", "|---|---:|---:|---:|---:|"]
    zD = (y == 1).astype(float)

    def row(label, m):
        out.append(f"| {label} | {m.sum()} | {Pb[m, 1].mean():.3f} | {zD[m].mean():.3f} | {zD[m].mean() - Pb[m, 1].mean():+.3f} |")
    for s in sorted(ev.season.unique()):
        row(C.season_label(s), (ev.season == s).to_numpy())
    for l in data.LEAGUES:
        row(data.LEAGUE_NAMES[l], (ev.Division == l).to_numpy())
    tot = (c.base_sp.mu + c.base_sp.nu).to_numpy()
    qs = np.quantile(tot, [0, 1 / 3, 2 / 3, 1])
    for i, lab in enumerate(["gol attesi totali bassi (terzile 1)", "gol attesi totali medi (terzile 2)",
                             "gol attesi totali alti (terzile 3)"]):
        m = (tot >= qs[i]) & ((tot <= qs[i + 1]) if i == 2 else (tot < qs[i + 1]))
        row(lab, m)
    out.append("")
    pd.to_pickle(chart, os.path.join(C.R2_DIR, "exp0b_chart.pkl"))
    with open(os.path.join(PARTS, "exp0.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))
    print("\n".join(out))


if __name__ == "__main__":
    main()
