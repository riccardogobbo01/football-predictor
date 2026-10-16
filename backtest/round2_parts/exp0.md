## Esperimento 0 — Audit del benchmark e della calibrazione

### 0a — Benchmark di mercato con tre metodi di rimozione del margine

Le quote medie coprono tutte le 12751 partite di test (2019/20 → oggi); per le altre fonti si usa il sottoinsieme con quote valide (colonna N). Per ogni fonte il baseline è valutato sullo STESSO sottoinsieme. Δ = log-loss(normalizzazione) − log-loss(metodo): positivo = il metodo è migliore; IC 95% bootstrap appaiato per partita (5000 ricampionamenti).

| Fonte | N | Metodo | Log-loss | RPS | Brier | Δ log-loss vs norm [IC 95%] | Baseline sullo stesso insieme |
|---|---:|---|---:|---:|---:|---|---:|
| Quote medie (raccolta pre-partita) | 12751 | normalizzazione semplice | 0.9728 | 0.1963 | 0.5784 | — | 0.9831 |
| Quote medie (raccolta pre-partita) | 12751 | power | 0.9725 | 0.1962 | 0.5781 | +0.00037 [-0.00014, +0.00087] | 0.9831 |
| Quote medie (raccolta pre-partita) | 12751 | Shin | 0.9725 | 0.1962 | 0.5782 | +0.00034 [-0.00002, +0.00069] | 0.9831 |
| Quote medie di chiusura | 12751 | normalizzazione semplice | 0.9704 | 0.1956 | 0.5768 | — | 0.9831 |
| Quote medie di chiusura | 12751 | power | 0.9701 | 0.1955 | 0.5766 | +0.00035 [-0.00016, +0.00083] | 0.9831 |
| Quote medie di chiusura | 12751 | Shin | 0.9701 | 0.1955 | 0.5766 | +0.00034 [-0.00000, +0.00068] | 0.9831 |
| Pinnacle (raccolta) | 11601 | normalizzazione semplice | 0.9712 | 0.1958 | 0.5772 | — | 0.9817 |
| Pinnacle (raccolta) | 11601 | power | 0.9710 | 0.1957 | 0.5771 | +0.00019 [-0.00019, +0.00056] | 0.9817 |
| Pinnacle (raccolta) | 11601 | Shin | 0.9710 | 0.1957 | 0.5771 | +0.00018 [-0.00007, +0.00044] | 0.9817 |
| Pinnacle (chiusura) | 11604 | normalizzazione semplice | 0.9686 | 0.1951 | 0.5756 | — | 0.9817 |
| Pinnacle (chiusura) | 11604 | power | 0.9685 | 0.1950 | 0.5755 | +0.00015 [-0.00019, +0.00049] | 0.9817 |
| Pinnacle (chiusura) | 11604 | Shin | 0.9685 | 0.1951 | 0.5755 | +0.00016 [-0.00008, +0.00040] | 0.9817 |

Shin vs power sulle quote di chiusura: Δ log-loss (power − Shin) = -0.00000 [-0.00017, +0.00017].

Metodo con la log-loss più bassa per fonte, e come cambia il divario baseline − mercato (positivo = il mercato è meglio del baseline):

- Quote medie (raccolta pre-partita): norm 0.9728 → power 0.9725 (Δ +0.0004); divario +0.0103 (norm) → +0.0107 (power)
- Quote medie di chiusura: norm 0.9704 → power 0.9701 (Δ +0.0003); divario +0.0127 (norm) → +0.0130 (power)
- Pinnacle (raccolta): norm 0.9712 → power 0.9710 (Δ +0.0002); divario +0.0106 (norm) → +0.0108 (power)
- Pinnacle (chiusura): norm 0.9686 → shin 0.9685 (Δ +0.0002); divario +0.0130 (norm) → +0.0132 (shin)

### 0b — Diagramma di affidabilità del baseline (stack + xG ridge)

10 bin per decili della probabilità prevista (stesso numero di partite per bin; con bin di ampiezza uguale i pareggi cadrebbero in 2-3 bin). Differenza = frequenza reale − previsione media (negativa = esito sovrastimato). SE = errore standard binomiale della frequenza.

**Casa (1)**

| Bin | N | Previsto medio | Frequenza reale | Differenza | SE |
|---:|---:|---:|---:|---:|---:|
| 1 | 1276 | 0.151 | 0.159 | +0.008 | 0.010 |
| 2 | 1275 | 0.240 | 0.211 | -0.029 | 0.011 |
| 3 | 1275 | 0.305 | 0.291 | -0.014 | 0.013 |
| 4 | 1275 | 0.359 | 0.334 | -0.024 | 0.013 |
| 5 | 1275 | 0.409 | 0.399 | -0.009 | 0.014 |
| 6 | 1275 | 0.458 | 0.445 | -0.013 | 0.014 |
| 7 | 1275 | 0.510 | 0.487 | -0.023 | 0.014 |
| 8 | 1275 | 0.569 | 0.562 | -0.007 | 0.014 |
| 9 | 1275 | 0.645 | 0.654 | +0.009 | 0.013 |
| 10 | 1275 | 0.762 | 0.768 | +0.006 | 0.012 |

Totale: previsto medio 0.4407, frequenza reale 0.4311, differenza -0.0096 (IC 95% ±0.0086). Retta di ricalibrazione logit(freq) = -0.038 + 1.035·logit(p) (1 = calibrato).

**Pareggio (X)**

| Bin | N | Previsto medio | Frequenza reale | Differenza | SE |
|---:|---:|---:|---:|---:|---:|
| 1 | 1276 | 0.147 | 0.143 | -0.004 | 0.010 |
| 2 | 1275 | 0.196 | 0.204 | +0.008 | 0.011 |
| 3 | 1275 | 0.220 | 0.218 | -0.002 | 0.012 |
| 4 | 1275 | 0.235 | 0.233 | -0.002 | 0.012 |
| 5 | 1275 | 0.245 | 0.247 | +0.002 | 0.012 |
| 6 | 1275 | 0.254 | 0.300 | +0.046 | 0.013 |
| 7 | 1275 | 0.261 | 0.307 | +0.046 | 0.013 |
| 8 | 1275 | 0.269 | 0.262 | -0.007 | 0.012 |
| 9 | 1275 | 0.277 | 0.294 | +0.017 | 0.013 |
| 10 | 1275 | 0.294 | 0.317 | +0.023 | 0.013 |

Totale: previsto medio 0.2398, frequenza reale 0.2525, differenza +0.0127 (IC 95% ±0.0075). Retta di ricalibrazione logit(freq) = +0.262 + 1.170·logit(p) (1 = calibrato).

**Trasferta (2)**

| Bin | N | Previsto medio | Frequenza reale | Differenza | SE |
|---:|---:|---:|---:|---:|---:|
| 1 | 1276 | 0.083 | 0.086 | +0.003 | 0.008 |
| 2 | 1275 | 0.144 | 0.125 | -0.019 | 0.009 |
| 3 | 1275 | 0.191 | 0.182 | -0.009 | 0.011 |
| 4 | 1275 | 0.233 | 0.236 | +0.003 | 0.012 |
| 5 | 1275 | 0.274 | 0.262 | -0.012 | 0.012 |
| 6 | 1275 | 0.319 | 0.318 | -0.000 | 0.013 |
| 7 | 1275 | 0.369 | 0.366 | -0.002 | 0.013 |
| 8 | 1275 | 0.428 | 0.435 | +0.006 | 0.014 |
| 9 | 1275 | 0.509 | 0.504 | -0.005 | 0.014 |
| 10 | 1275 | 0.644 | 0.649 | +0.005 | 0.013 |

Totale: previsto medio 0.3195, frequenza reale 0.3164, differenza -0.0031 (IC 95% ±0.0081). Retta di ricalibrazione logit(freq) = -0.000 + 1.025·logit(p) (1 = calibrato).

**Pareggio per stagione, lega e livello di gol attesi** (frequenza reale − previsto medio):

| Segmento | N | Previsto X | Reale X | Differenza |
|---|---:|---:|---:|---:|
| 2019/20 | 1725 | 0.237 | 0.243 | +0.007 |
| 2020/21 | 1826 | 0.242 | 0.255 | +0.013 |
| 2021/22 | 1825 | 0.244 | 0.259 | +0.015 |
| 2022/23 | 1826 | 0.241 | 0.243 | +0.002 |
| 2023/24 | 1752 | 0.237 | 0.264 | +0.027 |
| 2024/25 | 1752 | 0.236 | 0.249 | +0.014 |
| 2025/26 | 1752 | 0.242 | 0.255 | +0.013 |
| 2026/27 | 293 | 0.243 | 0.253 | +0.009 |
| Serie A | 2717 | 0.238 | 0.262 | +0.023 |
| Premier League | 2719 | 0.235 | 0.238 | +0.003 |
| Bundesliga | 2187 | 0.226 | 0.246 | +0.020 |
| La Liga | 2737 | 0.251 | 0.267 | +0.016 |
| Ligue 1 | 2391 | 0.246 | 0.247 | +0.001 |
| gol attesi totali bassi (terzile 1) | 4250 | 0.274 | 0.299 | +0.025 |
| gol attesi totali medi (terzile 2) | 4250 | 0.245 | 0.255 | +0.009 |
| gol attesi totali alti (terzile 3) | 4251 | 0.200 | 0.204 | +0.004 |
