## Fase 1 — Estensione della griglia dei GAP ratings (tiri e tiri in porta)

### Tiri

**Baseline (modello dei tiri attuale)**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.8867 | 3.5105 | 0.505 | 0.821 | 0.908 | 0.5738 | 0.0102 | -0.0096 |
| Totale | 3.1506 | 4.4924 | 0.302 | 0.818 | 0.907 | 0.6343 | 0.0152 | -0.0151 |

**Griglia 1** (η ∈ [0.05, 0.1, 0.15, 0.2] × γ ∈ [0.5, 0.75, 1.0]): scelta sulle validazione η = 0.1, γ = 1.0; l'ottimo non è al bordo di η (nessuna estensione).

| η | γ | Δ totale (tutte) [IC a blocchi] | Δ totale validazione | Δ totale held-out [IC a blocchi] | Δ per squadra (tutte) | Δ per squadra held-out | Verdetto |
|---:|---:|---|---:|---|---:|---:|---|
| 0.05 | 0.5 | +0.01477 [+0.01009, +0.01967] | +0.02047 | +0.01061 [+0.00511, +0.01730] | +0.00982 | +0.00834 | migliora (round 6) |
| 0.05 | 0.75 | +0.01834 [+0.01351, +0.02326] | +0.02531 | +0.01326 [+0.00760, +0.01996] | +0.01257 | +0.01060 | migliora |
| 0.05 | 1.0 | +0.02002 [+0.01514, +0.02490] | +0.02859 | +0.01378 [+0.00818, +0.02041] | +0.01416 | +0.01119 | migliora |
| 0.1 | 0.5 | +0.01677 [+0.01150, +0.02207] | +0.02382 | +0.01163 [+0.00556, +0.01854] | +0.01231 | +0.01053 | migliora |
| 0.1 | 0.75 | +0.01966 [+0.01428, +0.02497] | +0.02765 | +0.01384 [+0.00762, +0.02071] | +0.01425 | +0.01216 | migliora |
| 0.1 | 1.0 | +0.02073 [+0.01523, +0.02607] | +0.03039 | +0.01368 [+0.00744, +0.02065] | +0.01495 | +0.01181 | migliora ← scelta |
| 0.15 | 0.5 | +0.01391 [+0.00841, +0.01943] | +0.01958 | +0.00978 [+0.00358, +0.01660] | +0.01067 | +0.00937 | migliora |
| 0.15 | 0.75 | +0.01622 [+0.01064, +0.02169] | +0.02261 | +0.01156 [+0.00529, +0.01845] | +0.01204 | +0.01050 | migliora |
| 0.15 | 1.0 | +0.01687 [+0.01122, +0.02245] | +0.02497 | +0.01097 [+0.00454, +0.01796] | +0.01223 | +0.00961 | migliora |
| 0.2 | 0.5 | +0.01030 [+0.00488, +0.01594] | +0.01412 | +0.00752 [+0.00137, +0.01425] | +0.00843 | +0.00766 | migliora |
| 0.2 | 0.75 | +0.01215 [+0.00654, +0.01775] | +0.01657 | +0.00893 [+0.00265, +0.01576] | +0.00938 | +0.00841 | migliora |
| 0.2 | 1.0 | +0.01246 [+0.00672, +0.01826] | +0.01843 | +0.00810 [+0.00160, +0.01515] | +0.00912 | +0.00718 | migliora |

**Scelta finale sulle sole validazione: η = 0.1, γ = 1.0** — η è interno alla griglia (nessuna estensione prevista); γ = 1.0 è il limite naturale del parametro, quindi nessuna estensione ulteriore.

| Variante | Δ log-loss totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ log-loss per squadra (tutte) [IC a blocchi] | Δ per squadra held-out | Δ MAE tot. | Δ corr. tot. [IC] | Δ corr. squadra [IC] | Copertura 80% tot. (var.) | Copertura 90% tot. (var.) | ECE O/U tot. (base → var.) | Verdetto |
|---|---|---|---|---:|---:|---|---|---:|---:|---|---|
| GAP η=0.1, γ=1.0 vs baseline | +0.02073 [+0.01523, +0.02607] | +0.01368 [+0.00744, +0.02065] | +0.01495 [+0.01131, +0.01866] | +0.01181 | +0.0688 | +0.0487 [+0.0374, +0.0597] | +0.0192 [+0.0154, +0.0227] | 0.821 | 0.906 | 0.0152 → 0.0132 | migliora |

Rispetto alla configurazione del round 6 (η=0.05, γ=0.5): Δ totale +0.00596 [IC a blocchi +0.00276, +0.00891], held-out +0.00307 [-0.00065, +0.00678]; per squadra +0.00513 [+0.00293, +0.00737].

**Metriche della configurazione scelta (η=0.1, γ=1.0)**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.8717 | 3.4627 | 0.525 | 0.821 | 0.908 | 0.5667 | 0.0087 | -0.0071 |
| Totale | 3.1299 | 4.4236 | 0.351 | 0.821 | 0.906 | 0.6218 | 0.0132 | -0.0132 |

### Tiri in porta

**Baseline (modello I dei tiri in porta, senza GAP)**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.1777 | 1.7803 | 0.447 | 0.870 | 0.940 | 0.5910 | 0.0133 | +0.0116 |
| Totale | 2.5436 | 2.4949 | 0.271 | 0.851 | 0.928 | 0.6313 | 0.0186 | +0.0186 |

**Griglia 1** (η ∈ [0.05, 0.1, 0.15, 0.2] × γ ∈ [0.5, 0.75, 1.0]): scelta sulle validazione η = 0.05, γ = 1.0; l'ottimo non è al bordo di η (nessuna estensione).

| η | γ | Δ totale (tutte) [IC a blocchi] | Δ totale validazione | Δ totale held-out [IC a blocchi] | Δ per squadra (tutte) | Δ per squadra held-out | Verdetto |
|---:|---:|---|---:|---|---:|---:|---|
| 0.05 | 0.5 | +0.00523 [+0.00343, +0.00706] | +0.00411 | +0.00605 [+0.00374, +0.00832] | +0.00314 | +0.00368 | migliora (round 6) |
| 0.05 | 0.75 | +0.00649 [+0.00472, +0.00831] | +0.00522 | +0.00741 [+0.00511, +0.00969] | +0.00398 | +0.00467 | migliora |
| 0.05 | 1.0 | +0.00679 [+0.00494, +0.00868] | +0.00570 | +0.00759 [+0.00518, +0.00997] | +0.00445 | +0.00499 | migliora ← scelta |
| 0.1 | 0.5 | +0.00270 [+0.00064, +0.00482] | +0.00151 | +0.00358 [+0.00096, +0.00615] | +0.00254 | +0.00318 | migliora |
| 0.1 | 0.75 | +0.00318 [+0.00115, +0.00528] | +0.00189 | +0.00412 [+0.00152, +0.00668] | +0.00288 | +0.00363 | migliora |
| 0.1 | 1.0 | +0.00300 [+0.00096, +0.00509] | +0.00181 | +0.00387 [+0.00126, +0.00649] | +0.00296 | +0.00357 | migliora |
| 0.15 | 0.5 | +0.00006 [-0.00216, +0.00235] | -0.00098 | +0.00082 [-0.00199, +0.00358] | +0.00134 | +0.00188 | non distinguibile dal rumore |
| 0.15 | 0.75 | +0.00014 [-0.00200, +0.00240] | -0.00089 | +0.00090 [-0.00186, +0.00363] | +0.00137 | +0.00195 | non distinguibile dal rumore |
| 0.15 | 1.0 | -0.00019 [-0.00231, +0.00198] | -0.00114 | +0.00050 [-0.00221, +0.00318] | +0.00126 | +0.00167 | non distinguibile dal rumore |
| 0.2 | 0.5 | -0.00201 [-0.00433, +0.00032] | -0.00290 | -0.00136 [-0.00426, +0.00148] | +0.00028 | +0.00068 | non distinguibile dal rumore |
| 0.2 | 0.75 | -0.00215 [-0.00437, +0.00015] | -0.00300 | -0.00152 [-0.00429, +0.00118] | +0.00016 | +0.00053 | non distinguibile dal rumore |
| 0.2 | 1.0 | -0.00256 [-0.00474, -0.00038] | -0.00333 | -0.00201 [-0.00473, +0.00067] | -0.00007 | +0.00017 | non distinguibile dal rumore |

**Scelta finale sulle sole validazione: η = 0.05, γ = 1.0** — η = 0.05 è interno all'unione delle griglie (round 6: 0.02 e 0.05; fase 1: da 0.05 a 0.20) e il guadagno scende per η più alti; γ = 1.0 è il limite naturale del parametro, quindi nessuna estensione.

| Variante | Δ log-loss totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ log-loss per squadra (tutte) [IC a blocchi] | Δ per squadra held-out | Δ MAE tot. | Δ corr. tot. [IC] | Δ corr. squadra [IC] | Copertura 80% tot. (var.) | Copertura 90% tot. (var.) | ECE O/U tot. (base → var.) | Verdetto |
|---|---|---|---|---:|---:|---|---|---:|---:|---|---|
| GAP η=0.05, γ=1.0 vs baseline | +0.00679 [+0.00494, +0.00868] | +0.00759 [+0.00518, +0.00997] | +0.00445 [+0.00335, +0.00562] | +0.00499 | +0.0203 | +0.0187 [+0.0136, +0.0244] | +0.0072 [+0.0053, +0.0091] | 0.853 | 0.930 | 0.0186 → 0.0113 | migliora |

Rispetto alla configurazione del round 6 (η=0.05, γ=0.5): Δ totale +0.00156 [IC a blocchi +0.00050, +0.00262], held-out +0.00154 [+0.00009, +0.00293]; per squadra +0.00131 [+0.00065, +0.00198].

**Metriche della configurazione scelta (η=0.05, γ=1.0)**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.1733 | 1.7703 | 0.454 | 0.871 | 0.940 | 0.5884 | 0.0088 | +0.0072 |
| Totale | 2.5368 | 2.4746 | 0.290 | 0.853 | 0.930 | 0.6274 | 0.0113 | +0.0113 |
