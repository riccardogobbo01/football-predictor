## Esperimento B — Varianti di Elo-Odds

Controllo: la ricostruzione con le funzioni del round 3 (K=200, chiusura media) coincide con `eo_diff` di produzione (differenza massima < 1e-9).

### B1 — Pinnacle di chiusura al posto della media

Nelle partite di test Pinnacle (PSCH/PSCD/PSCA) è disponibile per il 91.0%; il resto ricade sulla chiusura media (per 2025/26 metà e 2026/27 tutto). Nessun parametro libero.

**B1 — Elo-Odds su quote Pinnacle di chiusura**

| Insieme | N | Δ log-loss | IC 95% per partita | IC 95% a blocchi per settimana |
|---|---:|---:|---|---|
| tutte le stagioni | 12751 | -0.00002 | [-0.00013, +0.00009] | [-0.00012, +0.00008] |
| validazione 2019/20-2021/22 | 5376 | -0.00008 | [-0.00025, +0.00010] | [-0.00024, +0.00009] |
| held-out 2022/23→ | 7375 | +0.00002 | [-0.00012, +0.00016] | [-0.00011, +0.00015] |

Log-loss 0.9798 (baseline 0.9798); Δ RPS -0.00001; Δ Brier -0.00002.

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0001 | +0.0001 | -0.0002 | +0.0001 | +0.0000 | -0.0000 | +0.0000 | +0.0001 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0001 | -0.0000 | +0.0002 | -0.0002 | +0.0001 |

### B2 — K separato per lega

Log-loss sulle sole stagioni di validazione, per lega e K uniforme (stack completo ogni volta):

| Lega | K=100 | K=150 | K=200 | K=300 | K=400 | K scelto |
|---|---:|---:|---:|---:|---:|---:|
| Serie A | 0.9664 | 0.9654 | 0.9647 | 0.9640 | 0.9640 | **300** |
| Premier League | 0.9772 | 0.9770 | 0.9770 | 0.9774 | 0.9779 | **200** |
| Bundesliga | 0.9916 | 0.9916 | 0.9916 | 0.9921 | 0.9929 | **200** |
| La Liga | 0.9951 | 0.9955 | 0.9957 | 0.9961 | 0.9967 | **100** |
| Ligue 1 | 1.0064 | 1.0070 | 1.0074 | 1.0081 | 1.0089 | **100** |

Regola: per ogni lega il K con la log-loss di validazione più bassa; parità entro 0.0002 → il più vicino a 200.

**B2 — K per lega (Serie A 300, Premier League 200, Bundesliga 200, La Liga 100, Ligue 1 100)**

| Insieme | N | Δ log-loss | IC 95% per partita | IC 95% a blocchi per settimana |
|---|---:|---:|---|---|
| tutte le stagioni | 12751 | +0.00008 | [-0.00028, +0.00045] | [-0.00029, +0.00044] |
| validazione 2019/20-2021/22 | 5376 | +0.00055 | [-0.00004, +0.00113] | [-0.00008, +0.00120] |
| held-out 2022/23→ | 7375 | -0.00026 | [-0.00070, +0.00019] | [-0.00066, +0.00014] |

Log-loss 0.9797 (baseline 0.9798); Δ RPS +0.00002; Δ Brier +0.00003.

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0009 | +0.0010 | -0.0002 | +0.0000 | -0.0006 | +0.0001 | -0.0005 | -0.0010 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0008 | +0.0001 | +0.0001 | -0.0002 | -0.0005 |

### B3 — Rating separati casa / trasferta

B3a: la feature `eo_ha` = R_casa(squadra di casa) − R_trasf(ospite) sostituisce `eo_diff`. Griglia (6 configurazioni), scelta sulle validazione (parità entro 0.0002 → la più semplice, nell'ordine in tabella).

| Variante | Log-loss | Δ tutte (IC per partita) | Δ tutte (IC a blocchi) | Δ validazione | Δ held-out (IC a blocchi) | Stagioni migliorate |
|---|---:|---|---|---:|---|---:|
| B3a — rating casa/trasferta K=200, γ=0.0 | 0.9806 | -0.00081 [-0.00170, +0.00003] | [-0.00173, +0.00012] | +0.00161 | -0.00257 [-0.00351, -0.00165] | 2/8 |
| B3a — rating casa/trasferta K=300, γ=0.0 | 0.9803 | -0.00053 [-0.00139, +0.00026] | [-0.00140, +0.00034] | +0.00148 | -0.00199 [-0.00288, -0.00111] | 2/8 |
| B3a — rating casa/trasferta K=400, γ=0.0 | 0.9806 | -0.00082 [-0.00172, +0.00004] | [-0.00176, +0.00013] | +0.00080 | -0.00199 [-0.00302, -0.00097] | 1/8 |
| B3a — rating casa/trasferta K=200, γ=0.5 | 0.9795 | +0.00028 [-0.00035, +0.00089] | [-0.00041, +0.00097] | +0.00182 | -0.00084 [-0.00143, -0.00025] | 2/8 |
| B3a — rating casa/trasferta K=300, γ=0.5 | 0.9792 | +0.00061 [-0.00006, +0.00127] | [-0.00011, +0.00132] | +0.00203 | -0.00042 [-0.00106, +0.00023] | 4/8 |
| B3a — rating casa/trasferta K=400, γ=0.5 | 0.9794 | +0.00042 [-0.00038, +0.00120] | [-0.00040, +0.00123] | +0.00168 | -0.00050 [-0.00132, +0.00035] | 4/8 |

Scelta: **K=300, γ=0.5** (Δ validazione +0.00203).

**B3a — rating casa/trasferta (K=300, γ=0.5) al posto di eo_diff**

| Insieme | N | Δ log-loss | IC 95% per partita | IC 95% a blocchi per settimana |
|---|---:|---:|---|---|
| tutte le stagioni | 12751 | +0.00061 | [-0.00006, +0.00127] | [-0.00011, +0.00132] |
| validazione 2019/20-2021/22 | 5376 | +0.00203 | [+0.00070, +0.00330] | [+0.00069, +0.00337] |
| held-out 2022/23→ | 7375 | -0.00042 | [-0.00110, +0.00027] | [-0.00106, +0.00023] |

Log-loss 0.9792 (baseline 0.9798); Δ RPS +0.00018; Δ Brier +0.00035.

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0011 | +0.0050 | -0.0000 | -0.0009 | +0.0003 | -0.0009 | +0.0006 | -0.0050 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0007 | +0.0009 | -0.0003 | -0.0001 | +0.0018 |

**B3b — eo_ha AGGIUNTO a eo_diff (stessi parametri di B3a)**

| Insieme | N | Δ log-loss | IC 95% per partita | IC 95% a blocchi per settimana |
|---|---:|---:|---|---|
| tutte le stagioni | 12751 | +0.00009 | [-0.00024, +0.00040] | [-0.00024, +0.00041] |
| validazione 2019/20-2021/22 | 5376 | +0.00037 | [-0.00015, +0.00090] | [-0.00022, +0.00094] |
| held-out 2022/23→ | 7375 | -0.00011 | [-0.00052, +0.00028] | [-0.00049, +0.00028] |

Log-loss 0.9797 (baseline 0.9798); Δ RPS +0.00002; Δ Brier +0.00004.

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0004 | +0.0014 | +0.0001 | -0.0006 | +0.0004 | -0.0005 | +0.0006 | -0.0024 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0001 | -0.0001 | -0.0002 | +0.0000 | +0.0006 |

### Riepilogo B (ogni variante da sola vs baseline)

| Variante | Log-loss | Δ tutte (IC per partita) | Δ tutte (IC a blocchi) | Δ validazione | Δ held-out (IC a blocchi) | Stagioni migliorate |
|---|---:|---|---|---:|---|---:|
| B1 — Elo-Odds su quote Pinnacle di chiusura | 0.9798 | -0.00002 [-0.00013, +0.00009] | [-0.00012, +0.00008] | -0.00008 | +0.00002 [-0.00011, +0.00015] | 5/8 |
| B2 — K per lega {'I1': 300, 'E0': 200, 'D1': 200, 'SP1': 100, 'F1': 100} | 0.9797 | +0.00008 [-0.00028, +0.00045] | [-0.00029, +0.00044] | +0.00055 | -0.00026 [-0.00066, +0.00014] | 4/8 |
| B3a — rating casa/trasferta K=300, γ=0.5 | 0.9792 | +0.00061 [-0.00006, +0.00127] | [-0.00011, +0.00132] | +0.00203 | -0.00042 [-0.00106, +0.00023] | 4/8 |
| B3b — eo_diff + rating casa/trasferta (K=300, γ=0.5) | 0.9797 | +0.00009 [-0.00024, +0.00040] | [-0.00024, +0.00041] | +0.00037 | -0.00011 [-0.00049, +0.00028] | 4/8 |

Verdetti (regola: Δ held-out > 0 con IC a blocchi che esclude lo zero): B1: **non distinguibile dal rumore**; B2: **non distinguibile dal rumore**; B3a: **non distinguibile dal rumore**; B3b: **non distinguibile dal rumore**.
