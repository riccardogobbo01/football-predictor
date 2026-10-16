## Esperimento K — Nuovi mercati derivati

### K1 — Primo tempo

12751 partite di test con punteggio al riposo (dal 2019/20). Frequenze osservate: 1X2 al riposo 0.338/0.400/0.262, Over 0.5 0.716, Over 1.5 0.357; gol medi del primo tempo casa 0.690, ospite 0.565; quota media dei gol nel primo tempo 0.446.

| Variante | Log-loss 1X2 | Log-loss Over 0.5 | Log-loss Over 1.5 | Media dei tre | ECE 1X2 | ECE O0.5 | ECE O1.5 | Scarto O0.5 | Scarto O1.5 | Scarto 1/X/2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Riferimento: medie di lega (nessuna informazione sulla partita) | 1.0843 | 0.5953 | 0.6499 | 0.7765 | 0.0128 | 0.0177 | 0.0181 | -0.0143 | -0.0149 | -0.000/+0.015/-0.015 |
| K1a — quota 1T per lega | 1.0343 | 0.5895 | 0.6422 | 0.7553 | 0.0089 | 0.0129 | 0.0111 | -0.0068 | -0.0026 | +0.004/-0.000/-0.004 |
| K1b — quote 1T casa/ospite per lega | 1.0346 | 0.5895 | 0.6423 | 0.7555 | 0.0078 | 0.0121 | 0.0118 | -0.0068 | -0.0026 | +0.005/-0.000/-0.005 |
| K1c — regressione con gol attesi totali | 1.0344 | 0.5893 | 0.6420 | 0.7552 | 0.0082 | 0.0143 | 0.0109 | -0.0101 | -0.0058 | -0.001/+0.002/-0.002 |

Scelta sulle validazione tra (a), (b), (c) (log-loss media dei tre mercati; parità entro 0.0002 → la più semplice): **K1a**.

Δ log-loss rispetto al riferimento (medie di lega) e rispetto a K1a (positivo = migliore; IC 95% a blocchi per settimana):

| Variante | Mercato | Δ vs riferimento [IC a blocchi] | Δ held-out vs riferimento [IC a blocchi] | Δ vs K1a [IC a blocchi] |
|---|---|---|---|---|
| K1a — quota 1T per lega (scelta) | 1X2 al riposo | +0.05004 [+0.04504, +0.05500] | +0.04969 [+0.04332, +0.05610] | — |
| K1a — quota 1T per lega (scelta) | Over 0.5 1T | +0.00581 [+0.00435, +0.00722] | +0.00543 [+0.00353, +0.00735] | — |
| K1a — quota 1T per lega (scelta) | Over 1.5 1T | +0.00766 [+0.00576, +0.00965] | +0.00773 [+0.00512, +0.01039] | — |
| K1a — quota 1T per lega (scelta) | media dei tre | +0.02117 [+0.01912, +0.02323] | +0.02095 [+0.01833, +0.02356] | — |
| K1b — quote 1T casa/ospite per lega | 1X2 al riposo | +0.04966 [+0.04465, +0.05463] | +0.04962 [+0.04327, +0.05604] | -0.00038 [-0.00056, -0.00020] |
| K1b — quote 1T casa/ospite per lega | Over 0.5 1T | +0.00580 [+0.00434, +0.00721] | +0.00543 [+0.00352, +0.00736] | -0.00002 [-0.00006, +0.00003] |
| K1b — quote 1T casa/ospite per lega | Over 1.5 1T | +0.00764 [+0.00574, +0.00963] | +0.00773 [+0.00512, +0.01039] | -0.00002 [-0.00008, +0.00003] |
| K1b — quote 1T casa/ospite per lega | media dei tre | +0.02103 [+0.01900, +0.02309] | +0.02093 [+0.01829, +0.02355] | -0.00014 [-0.00020, -0.00008] |
| K1c — regressione con gol attesi totali | 1X2 al riposo | +0.04989 [+0.04490, +0.05487] | +0.04990 [+0.04351, +0.05634] | -0.00015 [-0.00062, +0.00031] |
| K1c — regressione con gol attesi totali | Over 0.5 1T | +0.00604 [+0.00451, +0.00751] | +0.00567 [+0.00376, +0.00761] | +0.00022 [-0.00011, +0.00055] |
| K1c — regressione con gol attesi totali | Over 1.5 1T | +0.00789 [+0.00579, +0.01007] | +0.00819 [+0.00540, +0.01105] | +0.00023 [-0.00017, +0.00063] |
| K1c — regressione con gol attesi totali | media dei tre | +0.02127 [+0.01920, +0.02331] | +0.02125 [+0.01867, +0.02388] | +0.00010 [-0.00017, +0.00037] |

K1c: coefficiente di log(μ+ν) sulla quota del primo tempo (ultimo fold; negativo = quota minore quando ci si aspettano più gol): casa +0.077, ospite +0.021.

Quota media dei gol nel primo tempo per lega (tutte le stagioni dal 2016/17): I1 0.435, E0 0.445, D1 0.447, SP1 0.435, F1 0.443.

Per K2 e K3 l'insieme di valutazione è quello dei campionati: 12751 partite dal 2019/20.

### K2 — «Chi fa più» e handicap ±1,5 dai modelli congiunti

**corner**: ρ unica (ultimo fold -0.195).

| Mercato | Log-loss copula | Log-loss indipendenza | Δ [IC a blocchi] | Δ held-out [IC a blocchi] | ECE copula / indip. | Scarto medio copula (casa/pari/ospite) | Frequenze osservate |
|---|---:|---:|---|---|---|---|---|
| Chi ha più corner (casa / pari / ospite) | 0.8713 | 0.8724 | +0.00114 [+0.00038, +0.00194] | +0.00032 [-0.00068, +0.00129] | 0.0043 / 0.0118 | -0.011/+0.000/+0.011 | 0.535/0.094/0.370 |
| Handicap Casa −1,5 (casa vince di almeno 2 corner) | 0.6381 | 0.6393 | +0.00123 [+0.00071, +0.00174] | +0.00084 [+0.00019, +0.00150] | 0.0141 / 0.0238 | -0.0102 (indip. -0.0127) | frequenza 0.439 |
| Handicap Ospite −1,5 (ospite vince di almeno 2 corner) | 0.5531 | 0.5539 | +0.00080 [-0.00006, +0.00168] | +0.00003 [-0.00103, +0.00113] | 0.0116 / 0.0191 | +0.0079 (indip. -0.0087) | frequenza 0.286 |

**gialli**: ρ unica (ultimo fold +0.171).

| Mercato | Log-loss copula | Log-loss indipendenza | Δ [IC a blocchi] | Δ held-out [IC a blocchi] | ECE copula / indip. | Scarto medio copula (casa/pari/ospite) | Frequenze osservate |
|---|---:|---:|---|---|---|---|---|
| Chi ha più gialli (casa / pari / ospite) | 1.0564 | 1.0601 | +0.00367 [+0.00255, +0.00473] | +0.00374 [+0.00230, +0.00524] | 0.0112 / 0.0222 | +0.009/-0.015/+0.006 | 0.330/0.240/0.430 |

### K3 — Falli per squadra e totali

**Baseline semplice: metodo «a medie» sui falli**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.6992 | 2.8971 | 0.370 | 0.846 | 0.924 | 0.5936 | 0.0054 | +0.0042 |
| Totale | 3.0924 | 4.2700 | 0.416 | 0.834 | 0.921 | 0.6110 | 0.0063 | +0.0040 |

**K3a — modello dei falli (struttura degli altri, senza arbitro)**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.6918 | 2.8709 | 0.389 | 0.846 | 0.925 | 0.5892 | 0.0085 | +0.0067 |
| Totale | 3.0853 | 4.2313 | 0.432 | 0.839 | 0.923 | 0.6082 | 0.0126 | +0.0077 |

**K3b — modello dei falli con effetto arbitro**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.6842 | 2.8487 | 0.405 | 0.844 | 0.923 | 0.5851 | 0.0071 | +0.0047 |
| Totale | 3.0711 | 4.1673 | 0.458 | 0.838 | 0.920 | 0.6001 | 0.0102 | +0.0049 |

Δ = baseline − variante (positivo = variante migliore); IC 95% a blocchi per settimana.

| Variante | Δ log-loss totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ log-loss per squadra (tutte) [IC a blocchi] | Δ per squadra held-out | Δ MAE tot. | Δ corr. tot. [IC] | Δ corr. squadra [IC] | Copertura 80% tot. (var.) | Copertura 90% tot. (var.) | ECE O/U tot. (base → var.) | Verdetto |
|---|---|---|---|---:|---:|---|---|---:|---:|---|---|
| K3a vs baseline a medie | +0.00711 [+0.00177, +0.01212] | +0.00801 [+0.00188, +0.01381] | +0.00734 [+0.00396, +0.01056] | +0.00954 | +0.0387 | +0.0168 [+0.0076, +0.0263] | +0.0187 [+0.0118, +0.0253] | 0.839 | 0.923 | 0.0063 → 0.0126 | migliora |
| K3b (con arbitro) vs K3a | +0.01424 [+0.01051, +0.01793] | +0.01187 [+0.00747, +0.01628] | +0.00761 [+0.00554, +0.00966] | +0.00633 | +0.0640 | +0.0250 [+0.0191, +0.0315] | +0.0158 [+0.0117, +0.0199] | 0.838 | 0.920 | 0.0126 → 0.0102 | migliora |
| K3b vs baseline a medie | +0.02134 [+0.01494, +0.02741] | +0.01988 [+0.01296, +0.02645] | +0.01495 [+0.01108, +0.01871] | +0.01586 | +0.1027 | +0.0418 [+0.0310, +0.0528] | +0.0345 [+0.0269, +0.0418] | 0.838 | 0.920 | 0.0063 → 0.0102 | migliora |
