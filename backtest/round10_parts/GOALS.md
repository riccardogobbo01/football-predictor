## N1 e N2 — gol

Baseline: stack v6 di produzione senza livello di stagione. Insiemi: validazione 5377 partite, held-out 2022/23-2025/26 7082, 2026/27 447. Δ = baseline − variante (positivo = migliora).

### N1: griglia di k

| k | Δ ll 1X2 validazione | Δ ll 1X2 held-out [IC a blocchi] | Δ ll O/U 2,5 held-out [IC] | Δ RPS held-out | Δ ll 1X2 2026/27 (descrittivo) | Verdetto |
|---:|---:|---|---|---:|---:|---|
| 10 | +0.00060 | -0.00253 [-0.00483, -0.00018] | -0.00068 [-0.00275, +0.00143] | -0.00075 | -0.01307 | peggiora |
| 20 | +0.00121 | -0.00173 [-0.00372, +0.00035] | -0.00022 [-0.00206, +0.00168] | -0.00051 | -0.00935 | non distinguibile dal rumore |
| 40 | +0.00171 | -0.00101 [-0.00266, +0.00073] | +0.00023 [-0.00136, +0.00188] | -0.00028 | -0.00598 | non distinguibile dal rumore |
| 80 | +0.00197 | -0.00040 [-0.00169, +0.00095] | +0.00058 [-0.00073, +0.00195] | -0.00010 | -0.00342 | non distinguibile dal rumore |
| 160 | +0.00194 | +0.00002 [-0.00092, +0.00101] | +0.00076 [-0.00022, +0.00180] | +0.00003 | -0.00179 | non distinguibile dal rumore ← scelta |
| 320 | +0.00162 | +0.00022 [-0.00041, +0.00088] | +0.00074 [+0.00006, +0.00146] | +0.00008 | -0.00089 | non distinguibile dal rumore |

### N2: griglia di k

| k | Δ ll 1X2 validazione | Δ ll 1X2 held-out [IC a blocchi] | Δ ll O/U 2,5 held-out [IC] | Δ RPS held-out | Δ ll 1X2 2026/27 (descrittivo) | Verdetto |
|---:|---:|---|---|---:|---:|---|
| 10 | +0.00101 | -0.00110 [-0.00263, +0.00055] | -0.00024 [-0.00156, +0.00109] | -0.00036 | -0.00371 | non distinguibile dal rumore |
| 20 | +0.00115 | -0.00082 [-0.00221, +0.00069] | -0.00008 [-0.00131, +0.00116] | -0.00027 | -0.00267 | non distinguibile dal rumore |
| 40 | +0.00123 | -0.00053 [-0.00171, +0.00076] | +0.00010 [-0.00100, +0.00122] | -0.00017 | -0.00167 | non distinguibile dal rumore |
| 80 | +0.00121 | -0.00025 [-0.00118, +0.00077] | +0.00028 [-0.00065, +0.00122] | -0.00008 | -0.00092 | non distinguibile dal rumore |
| 160 | +0.00108 | -0.00004 [-0.00073, +0.00069] | +0.00039 [-0.00032, +0.00112] | -0.00001 | -0.00045 | non distinguibile dal rumore ← scelta |
| 320 | +0.00086 | +0.00007 [-0.00039, +0.00057] | +0.00040 [-0.00011, +0.00092] | +0.00002 | -0.00021 | non distinguibile dal rumore |

### Riepilogo delle configurazioni scelte in validazione

| Variante | k | Δ ll 1X2 held-out [IC] | Δ ll O/U 2,5 held-out [IC] | Δ RPS held-out | Δ O/U 1,5 | Δ O/U 3,5 | Δ BTTS | Verdetto |
|---|---:|---|---|---:|---:|---:|---:|---|
| N1 | 160 | +0.00002 [-0.00092, +0.00101] | +0.00076 [-0.00022, +0.00180] | +0.00003 | +0.00055 | +0.00133 | +0.00025 | non distinguibile dal rumore |
| N2 | 160 | -0.00004 [-0.00073, +0.00069] | +0.00039 [-0.00032, +0.00112] | -0.00001 | +0.00015 | +0.00016 | +0.00018 | non distinguibile dal rumore |

Δ ll 1X2 held-out per fase della stagione (configurazioni scelte):

| Variante | Prime 10 giornate | Resto |
|---|---:|---:|
| N1 | -0.00076 | +0.00032 |
| N2 | -0.00005 | -0.00004 |

## N2 — quante volte si sarebbe attivato

Filtro |z| > 2 per lato (z = (gol reali − previsti)/√previsti, sulle partite della stagione già giocate). «Quota attiva» = quota di partite della lega in quella stagione giocate con il filtro attivo (tra parentesi: solo dalla giornata 6, quando z non è più dominato dal caso); z finale = scarto a fine stagione; «prima attivazione» = data della prima partita con filtro attivo.

| Stagione | Lega | Partite | Casa: quota attiva (da g.6) | Casa: z finale | Casa: prima attivazione | Ospite: quota attiva (da g.6) | Ospite: z finale | Ospite: prima attivazione |
|---|---|---:|---|---:|---|---|---:|---|
| 2019/20 | Serie A | 380 | 0% (0%) | -1.10 | – | 21% (24%) | +2.15 | 2020-07-02 |
| 2019/20 | Premier League | 380 | 5% (6%) | -1.92 | 2020-03-08 | 0% (0%) | -1.11 | – |
| 2019/20 | Bundesliga | 306 | 0% (0%) | -1.59 | – | 25% (26%) | +2.45 | 2019-08-30 |
| 2019/20 | La Liga | 380 | 3% (3%) | -2.03 | 2020-07-19 | 58% (66%) | -2.72 | 2019-10-29 |
| 2019/20 | Ligue 1 | 279 | 0% (0%) | -0.18 | – | 46% (54%) | -1.96 | 2019-09-15 |
| 2020/21 | Serie A | 380 | 0% (0%) | -1.04 | – | 17% (19%) | +1.28 | 2020-10-31 |
| 2020/21 | Premier League | 380 | 57% (65%) | -3.51 | 2021-01-02 | 44% (38%) | +1.95 | 2020-09-19 |
| 2020/21 | Bundesliga | 306 | 2% (0%) | -0.06 | 2020-09-19 | 1% (0%) | +0.33 | 2020-09-20 |
| 2020/21 | La Liga | 380 | 30% (34%) | -1.91 | 2020-10-18 | 0% (0%) | +0.47 | – |
| 2020/21 | Ligue 1 | 380 | 19% (22%) | -2.04 | 2021-03-03 | 63% (72%) | +3.71 | 2020-12-06 |
| 2021/22 | Serie A | 380 | 1% (1%) | -1.86 | 2022-04-23 | 0% (0%) | +0.29 | – |
| 2021/22 | Premier League | 380 | 0% (0%) | -0.69 | – | 0% (0%) | +0.54 | – |
| 2021/22 | Bundesliga | 306 | 1% (1%) | +1.57 | 2022-02-27 | 0% (0%) | -0.41 | – |
| 2021/22 | La Liga | 380 | 0% (0%) | -0.51 | – | 3% (4%) | -1.50 | 2021-10-16 |
| 2021/22 | Ligue 1 | 380 | 0% (0%) | +1.32 | – | 0% (0%) | +0.51 | – |
| 2022/23 | Serie A | 380 | 40% (46%) | -2.40 | 2023-02-20 | 87% (94%) | -2.35 | 2022-08-30 |
| 2022/23 | Premier League | 380 | 4% (5%) | +0.80 | 2022-10-09 | 20% (23%) | -1.05 | 2022-10-22 |
| 2022/23 | Bundesliga | 306 | 58% (66%) | +2.67 | 2022-08-28 | 5% (3%) | -0.79 | 2022-08-06 |
| 2022/23 | La Liga | 380 | 0% (0%) | -0.47 | – | 3% (3%) | -2.04 | 2023-06-04 |
| 2022/23 | Ligue 1 | 380 | 0% (0%) | -1.04 | – | 49% (48%) | +1.07 | 2022-08-21 |
| 2023/24 | Serie A | 380 | 0% (0%) | -1.23 | – | 0% (0%) | -0.66 | – |
| 2023/24 | Premier League | 380 | 6% (6%) | +1.97 | 2024-05-06 | 32% (37%) | +2.29 | 2024-02-18 |
| 2023/24 | Bundesliga | 306 | 23% (21%) | +1.12 | 2023-08-26 | 0% (0%) | +0.07 | – |
| 2023/24 | La Liga | 380 | 3% (0%) | -0.74 | 2023-08-14 | 0% (0%) | -0.52 | – |
| 2023/24 | Ligue 1 | 306 | 25% (30%) | -1.90 | 2024-03-10 | 28% (33%) | -0.26 | 2023-11-24 |
| 2024/25 | Serie A | 380 | 23% (27%) | -2.94 | 2025-03-16 | 0% (0%) | +0.28 | – |
| 2024/25 | Premier League | 380 | 52% (56%) | -3.06 | 2024-09-15 | 0% (0%) | +0.57 | – |
| 2024/25 | Bundesliga | 306 | 0% (0%) | -1.37 | – | 9% (10%) | +1.41 | 2024-10-04 |
| 2024/25 | La Liga | 380 | 0% (0%) | -1.39 | – | 0% (0%) | -0.60 | – |
| 2024/25 | Ligue 1 | 306 | 0% (0%) | -0.83 | – | 2% (0%) | +0.61 | 2024-08-18 |
| 2025/26 | Serie A | 380 | 73% (84%) | -3.40 | 2025-10-20 | 0% (0%) | -0.96 | – |
| 2025/26 | Premier League | 380 | 0% (0%) | -1.06 | – | 0% (0%) | -1.50 | – |
| 2025/26 | Bundesliga | 306 | 0% (0%) | +1.45 | – | 5% (2%) | +1.21 | 2025-09-26 |
| 2025/26 | La Liga | 380 | 0% (0%) | +0.40 | – | 10% (11%) | -2.22 | 2026-04-24 |
| 2025/26 | Ligue 1 | 306 | 0% (0%) | -0.79 | – | 2% (2%) | -1.17 | 2025-08-29 |
| 2026/27 | Serie A | 98 | 0% (0%) | +0.83 | – | 16% (31%) | +2.37 | 2026-09-18 |
| 2026/27 | Premier League | 89 | 0% (0%) | -0.44 | – | 3% (0%) | -0.65 | 2026-08-23 |
| 2026/27 | Bundesliga | 72 | 88% (100%) | +2.64 | 2026-09-04 | 0% (0%) | -0.47 | – |
| 2026/27 | La Liga | 108 | 1% (0%) | +1.01 | 2026-08-17 | 0% (0%) | +0.42 | – |
| 2026/27 | Ligue 1 | 80 | 0% (0%) | +0.76 | – | 0% (0%) | -0.28 | – |

**Stagioni passate (2019/20-2025/26, 35 coppie lega-stagione):** attivazione in almeno una partita, lato casa 18/35, lato ospite 21/35; filtro attivo a fine stagione (|z finale| > 2), casa 8/35, ospite 8/35.
