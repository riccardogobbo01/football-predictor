## Round 7, fase 2 — verifica di produzione del livello stagionale

Codice di produzione (`stats_v3.walk_forward_means`, `stats_v3.build_level` con il registro come lo salva il training, `predictions.levels.Levels` come lo usa il sito) sul backtest walk-forward; parametri da `config.LEVEL_PARAMS`.

| Statistica | (H, k) | Medie di base: scarto massimo vs backtest | Δ ll totale produzione (tutte) | Δ round 7 esteso | Differenza | Δ held-out produzione [IC a blocchi] | Verdetto |
|---|---|---:|---:|---:|---:|---|---|
| Tiri | 12, 80 | 0.0e+00 | +0.00325 | +0.00325 | -5.6e-10 | +0.00267 [+0.00088, +0.00459] | migliora |
| Tiri in porta | 8, 40 | 0.0e+00 | +0.00772 | +0.00772 | +2.1e-08 | +0.00666 [+0.00442, +0.00888] | migliora |
| Corner | 16, 80 | 0.0e+00 | +0.00316 | +0.00316 | +1.3e-08 | +0.00325 [+0.00170, +0.00482] | migliora |
| Falli | 3, 15 | 0.0e+00 | +0.00904 | +0.00904 | +3.9e-08 | +0.00751 [+0.00473, +0.01045] | migliora |
| Gialli | 4, 15 | 0.0e+00 | +0.00955 | +0.00955 | +2.7e-08 | +0.00982 [+0.00653, +0.01319] | migliora |

**Esito della riproduzione: riprodotto** (tolleranza sul Δ: 2e-4, dovuta all'arrotondamento del registro; medie di base identiche; scarto degli intervalli ≤ 3 punti).

**Copertura degli intervalli con il livello di produzione (frequenza reale − probabilità dichiarata, punti percentuali)**

| Statistica | Squadra, tutte | Totale, tutte | Squadra, 2026/27 | Totale, 2026/27 | Criterio ≤ 3 pp (tutte) |
|---|---:|---:|---:|---:|---|
| Tiri | -1.6 | -1.0 | -5.3 | -7.7 | ok |
| Tiri in porta | -0.1 | +0.3 | -2.5 | -3.7 | ok |
| Corner | -0.7 | -0.4 | -1.4 | -4.7 | ok |
| Falli | +0.3 | +1.0 | -3.8 | -4.0 | ok |
| Gialli | +2.3 | -0.3 | +1.9 | -0.3 | ok |

**Robustezza: riallenamento ogni 28 giorni** (le medie di base vengono da modelli rifatti ogni 28 giorni con tutte le partite precedenti, come il training settimanale di produzione, invece di un fit per stagione; il livello è ricalcolato su quelle previsioni. Δ rispetto allo stesso baseline a riallenamento periodico; alpha del baseline a un fit per stagione).

| Statistica | Δ ll totale tutte [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ per squadra held-out | Δ totale 2026/27 | Scarto intervalli squadra / totale (base → livello) | Verdetto |
|---|---|---|---:|---:|---|---|
| Tiri | +0.00253 [+0.00084, +0.00417] | +0.00217 [+0.00050, +0.00396] | +0.00097 | +0.02980 | -1.9 → -1.7 / -1.2 → -1.0 | migliora |
| Tiri in porta | +0.00530 [+0.00340, +0.00719] | +0.00538 [+0.00329, +0.00745] | +0.00268 | +0.00618 | +0.1 → -0.1 / +0.3 → +0.3 | migliora |
| Corner | +0.00245 [+0.00130, +0.00359] | +0.00267 [+0.00121, +0.00415] | +0.00110 | +0.00074 | -0.4 → -0.7 / -0.3 → -0.4 | migliora |
| Falli | +0.00795 [+0.00577, +0.01017] | +0.00691 [+0.00416, +0.00979] | +0.00195 | +0.01535 | +0.3 → +0.3 / +0.7 → +0.9 | migliora |
| Gialli | +0.00803 [+0.00563, +0.01042] | +0.00864 [+0.00545, +0.01195] | +0.00343 | +0.00421 | +2.0 → +2.3 / -0.7 → -0.3 | migliora |
