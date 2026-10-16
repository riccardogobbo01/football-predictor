### Analisi aggiuntive (NON previste dal prereg)

Stesso insieme di valutazione dei campionati (12751 partite).

**Baseline dei gialli (modello attuale con effetto arbitro): metriche per squadra e totale**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 1.6618 | 1.0639 | 0.282 | 0.932 | 0.978 | 0.6259 | 0.0111 | -0.0093 |
| Totale | 2.1082 | 1.6171 | 0.316 | 0.870 | 0.934 | 0.5822 | 0.0073 | -0.0015 |

**Tiri in porta: modello con GAP ratings (η=0.05, γ=0.5, scelto in validazione per J4)**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.1746 | 1.7739 | 0.452 | 0.872 | 0.941 | 0.5891 | 0.0103 | +0.0088 |
| Totale | 2.5384 | 2.4799 | 0.286 | 0.854 | 0.929 | 0.6285 | 0.0141 | +0.0141 |

Tiri in porta, GAP vs baseline semplice «tiri previsti × quota in porta» (Δ positivo = GAP migliore):

| Variante | Δ log-loss totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ log-loss per squadra (tutte) [IC a blocchi] | Δ per squadra held-out | Δ MAE tot. | Δ corr. tot. [IC] | Δ corr. squadra [IC] | Copertura 80% tot. (var.) | Copertura 90% tot. (var.) | ECE O/U tot. (base → var.) | Verdetto |
|---|---|---|---|---:|---:|---|---|---:|---:|---|---|
| Tiri in porta — J4 GAP vs baseline semplice | +0.00260 [-0.00141, +0.00640] | +0.00005 [-0.00422, +0.00458] | +0.00654 [+0.00429, +0.00871] | +0.00494 | -0.0041 | +0.0081 [-0.0032, +0.0194] | +0.0121 [+0.0083, +0.0158] | 0.854 | 0.929 | 0.0069 → 0.0141 | non distinguibile dal rumore |
