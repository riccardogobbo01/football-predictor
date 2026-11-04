## Round 10 — verifica di produzione dell'effetto arbitro con decadimento (s6-arbitro-decay)

Emivita 182.5 giorni (0,5 anni), k = 20. Il codice di produzione (`refeffect.compute` con emivita) ricalcola `ref_logR`; modello dei gialli come in produzione (senza livello stagionale, come nel round 10).

| Misura | Produzione | Round 10 | Differenza |
|---|---:|---:|---:|
| Δ ll totale held-out 2022/23-2025/26 | +0.00297 [+0.00007, +0.00590] | +0.00297 [+0.00007, +0.00590] | +0.0e+00 |
| Δ ll totale 2026/27 (descrittivo) | -0.00385 | -0.00385 | +0.0e+00 |
| Δ ll per squadra held-out | +0.00146 | | |
| Δ ll totale validazione | +0.00610 | | |

**Riproduzione del Δ del round 10: riprodotta.**

**Intervalli dei gialli con il livello stagionale di produzione** (frequenza reale − probabilità dichiarata, punti percentuali; s5 → s6):

| Insieme | Squadra | Totale |
|---|---:|---:|
| Tutte le stagioni | +2.2 → +2.2 | -0.3 → -0.5 |
| 2026/27 | +1.2 → +1.5 | -1.5 → -2.2 |

**Criterio (≤ 3 punti su tutte le stagioni): rispettato** (massimo 2.2 punti).

**Coerenza del serving**: stato salvato fino a quattro date di taglio e `refeffect.ratio(stato, lega, arbitro, data)` contro il rapporto del walk-forward per le partite del primo giorno dopo il taglio (61 partite): scarto massimo 8.4e-07 (arrotondamento delle somme a 4 decimali).

**Esito complessivo: riprodotto**
