## Esperimento 1 — Porte chiuse e vantaggio casa per lega

### Date e flag "porte chiuse"

Ripresa post-lockdown 2019/20 rilevata sui dati (primo incontro dopo la pausa più lunga): Serie A 2020-06-20, Premier League 2020-06-17, Bundesliga 2020-05-16, La Liga 2020-06-11, Ligue 1 nessuna ripresa (ultima partita 2020-03-08). Flag = 1 dalla ripresa 2019/20 a fine 2019/20 e per tutta la stagione 2020/21 (come da definizione); non sono marcate le poche partite a porte chiuse prima del lockdown (Serie A 8-9 marzo 2020, Bundesliga 11 marzo) né le riaperture parziali di pubblico del 2020/21 (autunno 2020, primavera 2021), che non sono ricostruibili dai dati.

| Lega | Partite flag=1 | di cui 2019/20 | Vittorie casa flag=0 | Vittorie casa flag=1 | Gol casa−trasf. flag=0 | flag=1 |
|---|---:|---:|---:|---:|---:|---:|
| Serie A | 504 | 124 | 0.430 | 0.417 | +0.258 | +0.222 |
| Premier League | 472 | 92 | 0.449 | 0.396 | +0.315 | +0.081 |
| Bundesliga | 388 | 82 | 0.451 | 0.399 | +0.362 | +0.201 |
| La Liga | 490 | 110 | 0.465 | 0.414 | +0.407 | +0.220 |
| Ligue 1 | 380 | 0 | 0.447 | 0.374 | +0.342 | +0.034 |
| Tutte | 2234 | 408 | 0.449 | 0.402 | +0.336 | +0.156 |

Nel solo insieme di test (12751 partite) le partite con flag=1 sono 2234.

### Risultati (ogni variante da sola vs baseline)

| Variante | Log-loss | RPS | Brier | Δ log-loss vs baseline | IC 95% | Stagioni migliorate |
|---|---:|---:|---:|---:|---|---:|
| 1a — dummy nei DC (gol, tiri, xG) + nella regressione | 0.9828 | 0.1994 | 0.5853 | +0.00031 | [-0.00015, +0.00079] | 5/8 |
| 1a-i — dummy solo nei DC | 0.9829 | 0.1994 | 0.5853 | +0.00022 | [-0.00013, +0.00058] | 5/8 |
| 1a-ii — dummy solo nella regressione | 0.9827 | 0.1994 | 0.5853 | +0.00038 | [-0.00009, +0.00086] | 5/8 |
| 1b — vantaggio casa per lega (intercette di lega nella regressione) | 0.9835 | 0.1996 | 0.5857 | -0.00041 | [-0.00071, -0.00012] | 2/8 |
| 1a+1b — dummy completa + intercette di lega | 0.9832 | 0.1995 | 0.5856 | -0.00012 | [-0.00067, +0.00044] | 4/8 |

Nota: i DC sono già stimati campionato per campionato, quindi il vantaggio casa H è già separato per lega a livello di DC; la variante 1b agisce sulla regressione di stack (che mette insieme i 5 campionati), aggiungendo un'intercetta per lega a gol casa e gol trasferta.

**1a — dummy nei DC (gol, tiri, xG) + nella regressione**

| Metrica | Variante | Baseline | Δ (base − variante) | IC 95% |
|---|---:|---:|---:|---|
| Log-loss 1X2 | 0.9828 | 0.9831 | +0.00031 | [-0.00015, +0.00079] |
| RPS | 0.1994 | 0.1995 | +0.00010 | [-0.00004, +0.00026] |
| Brier | 0.5853 | 0.5855 | +0.00018 | [-0.00013, +0.00052] |

(Δ positivo = variante migliore; N = 12751; stagioni migliorate: 5/8)

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0002 | +0.0017 | +0.0003 | +0.0009 | -0.0002 | -0.0005 | +0.0001 | +0.0005 |
| N | 1725 | 1826 | 1825 | 1826 | 1752 | 1752 | 1752 | 293 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0001 | +0.0007 | +0.0005 | +0.0002 | +0.0003 |

**1a-i — dummy solo nei DC**

| Metrica | Variante | Baseline | Δ (base − variante) | IC 95% |
|---|---:|---:|---:|---|
| Log-loss 1X2 | 0.9829 | 0.9831 | +0.00022 | [-0.00013, +0.00058] |
| RPS | 0.1994 | 0.1995 | +0.00008 | [-0.00003, +0.00019] |
| Brier | 0.5853 | 0.5855 | +0.00014 | [-0.00009, +0.00039] |

(Δ positivo = variante migliore; N = 12751; stagioni migliorate: 5/8)

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0002 | +0.0010 | +0.0004 | +0.0004 | -0.0001 | -0.0001 | +0.0001 | +0.0004 |
| N | 1725 | 1826 | 1825 | 1826 | 1752 | 1752 | 1752 | 293 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0001 | +0.0004 | +0.0007 | +0.0003 | -0.0001 |

**1a-ii — dummy solo nella regressione**

| Metrica | Variante | Baseline | Δ (base − variante) | IC 95% |
|---|---:|---:|---:|---|
| Log-loss 1X2 | 0.9827 | 0.9831 | +0.00038 | [-0.00009, +0.00086] |
| RPS | 0.1994 | 0.1995 | +0.00011 | [-0.00004, +0.00027] |
| Brier | 0.5853 | 0.5855 | +0.00021 | [-0.00012, +0.00054] |

(Δ positivo = variante migliore; N = 12751; stagioni migliorate: 5/8)

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0000 | +0.0026 | +0.0002 | +0.0009 | -0.0004 | -0.0008 | +0.0001 | +0.0004 |
| N | 1725 | 1826 | 1825 | 1826 | 1752 | 1752 | 1752 | 293 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0003 | +0.0011 | -0.0002 | +0.0001 | +0.0012 |

**1b — vantaggio casa per lega (intercette di lega nella regressione)**

| Metrica | Variante | Baseline | Δ (base − variante) | IC 95% |
|---|---:|---:|---:|---|
| Log-loss 1X2 | 0.9835 | 0.9831 | -0.00041 | [-0.00071, -0.00012] |
| RPS | 0.1996 | 0.1995 | -0.00012 | [-0.00021, -0.00004] |
| Brier | 0.5857 | 0.5855 | -0.00026 | [-0.00046, -0.00006] |

(Δ positivo = variante migliore; N = 12751; stagioni migliorate: 2/8)

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0000 | -0.0018 | +0.0003 | -0.0003 | -0.0005 | -0.0007 | +0.0001 | -0.0002 |
| N | 1725 | 1826 | 1825 | 1826 | 1752 | 1752 | 1752 | 293 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0004 | -0.0006 | -0.0012 | -0.0001 | -0.0008 |

**1a+1b — dummy completa + intercette di lega**

| Metrica | Variante | Baseline | Δ (base − variante) | IC 95% |
|---|---:|---:|---:|---|
| Log-loss 1X2 | 0.9832 | 0.9831 | -0.00012 | [-0.00067, +0.00044] |
| RPS | 0.1995 | 0.1995 | -0.00003 | [-0.00020, +0.00015] |
| Brier | 0.5856 | 0.5855 | -0.00009 | [-0.00046, +0.00030] |

(Δ positivo = variante migliore; N = 12751; stagioni migliorate: 4/8)

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0003 | -0.0002 | +0.0007 | +0.0006 | -0.0006 | -0.0013 | +0.0002 | +0.0003 |
| N | 1725 | 1826 | 1825 | 1826 | 1752 | 1752 | 1752 | 293 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0003 | +0.0002 | -0.0008 | +0.0000 | -0.0005 |

### Effetto per sottoinsieme (variante 1a completa)

| Sottoinsieme | N | Δ log-loss (base − variante) | IC 95% |
|---|---:|---:|---|
| partite a porte chiuse (flag=1) | 2234 | +0.00126 | [-0.00074, +0.00328] |
| partite con pubblico (flag=0) | 10517 | +0.00010 | [-0.00028, +0.00049] |
| dalla stagione 2021/22 (H storico ancora contaminato) | 9200 | +0.00012 | [-0.00031, +0.00055] |

### Vantaggio casa stimato dal DC sui gol (media dei rifit settimanali)

H = parametro di vantaggio casa (log), delta = variazione stimata a porte chiuse; baseline = H del modello attuale, stimato su tutte le partite.

| Lega | Periodo | H con dummy (solo pubblico) | delta (porte chiuse) |
|---|---|---:|---:|
| Serie A | 2019/20-2020/21 | 0.119 | +0.113 |
| Serie A | 2021/22 | 0.120 | +0.055 |
| Serie A | 2023/24 | 0.163 | +0.096 |
| Premier League | 2019/20-2020/21 | 0.216 | -0.062 |
| Premier League | 2021/22 | 0.176 | -0.087 |
| Premier League | 2023/24 | 0.221 | -0.180 |
| Bundesliga | 2019/20-2020/21 | 0.193 | -0.100 |
| Bundesliga | 2021/22 | 0.245 | -0.061 |
| Bundesliga | 2023/24 | 0.293 | -0.088 |
| La Liga | 2019/20-2020/21 | 0.321 | -0.158 |
| La Liga | 2021/22 | 0.288 | -0.084 |
| La Liga | 2023/24 | 0.284 | -0.068 |
| Ligue 1 | 2019/20-2020/21 | 0.276 | -0.101 |
| Ligue 1 | 2021/22 | 0.224 | -0.122 |
| Ligue 1 | 2023/24 | 0.188 | -0.108 |
