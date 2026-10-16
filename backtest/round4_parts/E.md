## Esperimento E — Limite massimo della formazione titolare (campionati)

> **Questo è un test «a formazione nota».** Le feature usano gli 11 effettivamente schierati nella partita da prevedere, informazione che si conosce circa un'ora prima del calcio d'inizio: non c'è quando le previsioni si pubblicano. Il guadagno qui sotto è quindi un **limite massimo** di quanto potrebbe valere conoscere la formazione, non un guadagno ottenibile in produzione. La versione realistica è la «formazione prevista» (in fondo, solo se la condizione scritta prima è soddisfatta).

### Copertura

Partite di campionato abbinate a una partita del dataset Transfermarkt e con formazione completa per entrambe le squadre (esattamente 11 titolari) e almeno 3 partite di storico con minuti (N=5 / N=10). Le altre hanno differenze = 0 e indicatore `lu_miss` = 1 (stesso trattamento in training e in test).

| Stagione | Partite di test | Abbinate | Complete (N=5) | Complete (N=10) |
|---|---:|---:|---:|---:|
| 2019/20 | 1725 | 100.0% | 100.0% | 100.0% |
| 2020/21 | 1826 | 100.0% | 99.9% | 99.9% |
| 2021/22 | 1825 | 100.0% | 99.8% | 99.8% |
| 2022/23 | 1826 | 100.0% | 99.7% | 99.7% |
| 2023/24 | 1752 | 100.0% | 99.8% | 99.8% |
| 2024/25 | 1752 | 100.0% | 99.9% | 99.9% |
| 2025/26 | 1752 | 100.0% | 99.7% | 99.7% |
| 2026/27 | 293 | 0.0% | 0.0% | 0.0% |

Totale partite di test con formazione completa: N=5 97.5%, N=10 97.5%. Tutta la stagione 2026/27 manca nel dataset (ultimo aggiornamento 2026-09-05, valutazioni fino al 2026-06-12); anche il training dello stack dal 2016/17 al 2025/26 ha copertura completa (≥ 98% per stagione).

### Griglia di 6 configurazioni (ogni riga da sola vs baseline v6)

| Variante | Log-loss | Δ tutte (IC per partita) | Δ tutte (IC a blocchi) | Δ validazione | Δ held-out (IC a blocchi) | Stagioni migliorate |
|---|---:|---|---|---:|---|---:|
| E — N=5, quota minuti | 0.9794 | +0.00043 [-0.00027, +0.00115] | [-0.00038, +0.00124] | +0.00022 | +0.00058 [-0.00054, +0.00163] | 6/8 |
| E — N=5, valore | 0.9794 | +0.00045 [-0.00049, +0.00140] | [-0.00058, +0.00144] | +0.00153 | -0.00034 [-0.00168, +0.00097] | 3/8 |
| E — N=5, quota minuti + valore | 0.9788 | +0.00097 [-0.00012, +0.00203] | [-0.00023, +0.00212] | +0.00161 | +0.00050 [-0.00103, +0.00204] | 5/8 |
| E — N=10, quota minuti | 0.9791 | +0.00072 [+0.00008, +0.00138] | [-0.00002, +0.00144] | +0.00054 | +0.00086 [-0.00027, +0.00190] | 6/8 |
| E — N=10, valore | 0.9796 | +0.00025 [-0.00080, +0.00130] | [-0.00092, +0.00139] | +0.00115 | -0.00040 [-0.00181, +0.00100] | 4/8 |
| E — N=10, quota minuti + valore | 0.9789 | +0.00095 [-0.00020, +0.00208] | [-0.00031, +0.00221] | +0.00146 | +0.00058 [-0.00101, +0.00211] | 4/8 |

Scelta sulle validazione (parità entro 0.0002 → la più semplice): **E — N=5, valore** (Δ validazione +0.00153). Verdetto: **non distinguibile dal rumore**.

**E — N=5, valore**

| Insieme | N | Δ log-loss | IC 95% per partita | IC 95% a blocchi per settimana |
|---|---:|---:|---|---|
| tutte le stagioni | 12751 | +0.00045 | [-0.00049, +0.00140] | [-0.00058, +0.00144] |
| validazione 2019/20-2021/22 | 5376 | +0.00153 | [+0.00006, +0.00303] | [-0.00001, +0.00307] |
| held-out 2022/23→ | 7375 | -0.00034 | [-0.00157, +0.00082] | [-0.00168, +0.00097] |

Log-loss 0.9794 (baseline 0.9798); Δ RPS +0.00017; Δ Brier +0.00038.

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0004 | +0.0021 | +0.0029 | -0.0003 | -0.0014 | +0.0025 | -0.0004 | -0.0115 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0008 | +0.0017 | +0.0010 | +0.0004 | -0.0018 |

**Guadagno su partite con formazione completa e sulle altre (variante scelta)**

| Insieme | N | Δ log-loss | IC 95% a blocchi |
|---|---:|---:|---|
| formazione completa | 12437 | +0.00071 | [-0.00021, +0.00161] |
| formazione mancante (indicatore = 1) | 314 | -0.00977 | [-0.02611, +0.00849] |

### Formazione prevista

Condizione scritta prima: Δ held-out ≥ +0.002 con IC a blocchi che esclude lo zero. Configurazione scelta: Δ held-out -0.00034, IC a blocchi [-0.00168, +0.00097] → condizione **NON soddisfatta**.

Non si fa la versione «formazione prevista», come stabilito.
