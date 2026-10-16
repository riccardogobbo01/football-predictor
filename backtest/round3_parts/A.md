## Esperimento A — Lunghezza del training dello stack

### Quante stagioni di training ha lo stack in ogni stagione di test (baseline)

Stack allenato dal 2016/17 sulle sole stagioni precedenti alla stagione di test (gli xG partono dal 2014/15 e il DC xG richiede 2 anni di storia: prima feature xG nell'estate 2016).

| Stagione di test | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Stagioni di training | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| Partite di training | 5478 | 7203 | 9029 | 10855 | 12681 | 14433 | 16185 | 17937 |

### Varianti (ogni riga da sola vs baseline)

| Variante | Log-loss | Δ tutte (IC per partita) | Δ tutte (IC a blocchi) | Δ validazione | Δ held-out (IC a blocchi) | Stagioni migliorate |
|---|---:|---|---|---:|---|---:|
| A1 — xG con 12 mesi di riscaldamento, training dal 2015/16 | 0.9796 | +0.00016 [-0.00009, +0.00041] | [-0.00008, +0.00041] | +0.00006 | +0.00023 [-0.00000, +0.00046] | 6/8 |
| A2 — xG con 6 mesi di riscaldamento, training dal 2014/15 | 0.9798 | +0.00001 [-0.00025, +0.00027] | [-0.00025, +0.00027] | -0.00035 | +0.00028 [+0.00003, +0.00053] | 5/8 |
| A3 — training dal 2013/14 con xG mancante gestito (imputazione + indicatore) | 0.9798 | -0.00004 [-0.00050, +0.00043] | [-0.00049, +0.00045] | -0.00072 | +0.00046 [-0.00011, +0.00104] | 4/8 |
| A4 — xG a 6 mesi + training dal 2013/14 con xG mancante gestito | 0.9800 | -0.00015 [-0.00061, +0.00031] | [-0.00061, +0.00033] | -0.00101 | +0.00048 [-0.00006, +0.00102] | 4/8 |

**Stagioni e partite di training per variante**

| Variante | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 3 (5478) | 4 (7203) | 5 (9029) | 6 (10855) | 7 (12681) | 8 (14433) | 9 (16185) | 10 (17937) |
| A1 | 4 (7304) | 5 (9029) | 6 (10855) | 7 (12681) | 8 (14507) | 9 (16259) | 10 (18011) | 11 (19763) |
| A2 | 5 (8090) | 6 (9815) | 7 (11641) | 8 (13467) | 9 (15293) | 10 (17045) | 11 (18797) | 12 (20549) |
| A3 | 6 (10956) | 7 (12681) | 8 (14507) | 9 (16333) | 10 (18159) | 11 (19911) | 12 (21663) | 13 (23415) |
| A4 | 6 (10956) | 7 (12681) | 8 (14507) | 9 (16333) | 10 (18159) | 11 (19911) | 12 (21663) | 13 (23415) |

(stagioni distinte con almeno una riga di training, e numero di righe)

**Guadagno per stagione (Δ log-loss, baseline − variante)**

| Variante | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A1 | +0.0002 | -0.0004 | +0.0005 | +0.0004 | +0.0002 | -0.0001 | +0.0003 | +0.0015 |
| A2 | -0.0004 | -0.0011 | +0.0005 | +0.0003 | +0.0004 | -0.0001 | +0.0003 | +0.0017 |
| A3 | -0.0006 | -0.0011 | -0.0005 | +0.0008 | +0.0006 | -0.0004 | +0.0008 | +0.0009 |
| A4 | -0.0010 | -0.0020 | -0.0000 | +0.0008 | +0.0006 | -0.0005 | +0.0007 | +0.0022 |

**Scelta (criterio: Δ più alto sulle validazione 2019/20-2021/22, parità entro 0.0002 → la più semplice): A1** (Δ validazione +0.00006). Verdetto (regola A del prereg): **non distinguibile dal rumore**.

**Dettaglio della variante scelta: A1 — xG con 12 mesi di riscaldamento, training dal 2015/16**

| Insieme | N | Δ log-loss | IC 95% per partita | IC 95% a blocchi per settimana |
|---|---:|---:|---|---|
| tutte le stagioni | 12751 | +0.00016 | [-0.00009, +0.00041] | [-0.00008, +0.00041] |
| validazione 2019/20-2021/22 | 5376 | +0.00006 | [-0.00043, +0.00055] | [-0.00043, +0.00054] |
| held-out 2022/23→ | 7375 | +0.00023 | [-0.00000, +0.00046] | [-0.00000, +0.00046] |

Log-loss 0.9796 (baseline 0.9798); Δ RPS +0.00005; Δ Brier +0.00012.

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0002 | -0.0004 | +0.0005 | +0.0004 | +0.0002 | -0.0001 | +0.0003 | +0.0015 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0006 | +0.0001 | +0.0001 | -0.0001 | +0.0001 |
