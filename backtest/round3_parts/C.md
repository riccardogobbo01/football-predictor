## Esperimento C — Ordered logit di ricalibrazione sopra il baseline v6

Rifit settimanale sul passato (finestra espansiva), burn-in di 600 partite con identità (645 partite di test). Input: x1 = log(λ casa/λ ospite), x2 = λ casa + λ ospite del modello baseline; output: 1X2.

| Variante | Log-loss | Δ tutte (IC per partita) | Δ tutte (IC a blocchi) | Δ validazione | Δ held-out (IC a blocchi) | Stagioni migliorate |
|---|---:|---|---|---:|---|---:|
| Ordered logit semplice (4 parametri) | 0.9797 | +0.00012 [-0.00113, +0.00143] | [-0.00125, +0.00147] | +0.00046 | -0.00013 [-0.00184, +0.00154] | 4/8 |
| Ordered logit flessibile (banda del pareggio dipende da gol attesi) | 0.9791 | +0.00073 [-0.00034, +0.00186] | [-0.00043, +0.00187] | +0.00114 | +0.00043 [-0.00100, +0.00185] | 4/8 |

Scelta sulle validazione (parità entro 0.0002 → il semplice): **Ordered logit flessibile (banda del pareggio dipende da gol attesi)** (Δ validazione +0.00114). Verdetto: **non distinguibile dal rumore**.

**Ordered logit flessibile (banda del pareggio dipende da gol attesi)**

| Insieme | N | Δ log-loss | IC 95% per partita | IC 95% a blocchi per settimana |
|---|---:|---:|---|---|
| tutte le stagioni | 12751 | +0.00073 | [-0.00034, +0.00186] | [-0.00043, +0.00187] |
| validazione 2019/20-2021/22 | 5376 | +0.00114 | [-0.00083, +0.00312] | [-0.00071, +0.00298] |
| held-out 2022/23→ | 7375 | +0.00043 | [-0.00082, +0.00170] | [-0.00100, +0.00185] |

Log-loss 0.9791 (baseline 0.9798); Δ RPS +0.00011; Δ Brier +0.00037.

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0009 | +0.0058 | -0.0016 | -0.0031 | +0.0022 | +0.0026 | -0.0002 | +0.0024 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0041 | -0.0004 | -0.0004 | -0.0007 | +0.0009 |

Pareggio: previsto medio 0.2400 → 0.2514 dopo la ricalibrazione (reale 0.2525). Parametri dell'ultimo rifit: 1.476, 0.118, 0.079, 0.203, -0.258, 0.091.

La ricalibrazione non «migliora» secondo la regola scritta prima: non è stata applicata alla matrice dei punteggi (come richiesto, solo se migliora).
