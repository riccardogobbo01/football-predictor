## N3 — statistiche

Baseline = produzione (modello `stats_v3` + livello stagionale di `config.LEVEL_PARAMS`). Varianti: **A1/A2** = livello di stagione (N1 / N2) al posto del livello di produzione; **B1/B2** = sopra il livello di produzione. Δ = baseline − variante (positivo = migliora), held-out 2022/23-2025/26; per i tiri k è scelto separatamente per casa e ospite.

### Falli

| Variante | k (casa, ospite) | Δ ll totale validazione | Δ totale held-out [IC a blocchi] | Δ per squadra held-out | Δ O/U totale held-out | Δ totale 2026/27 (descrittivo) | Verdetto |
|---|---|---:|---|---:|---:|---:|---|
| A1 | 80, 80 | -0.00511 | -0.00295 [-0.00496, -0.00100] | -0.00045 | -0.00224 | -0.00933 | peggiora |
| A2 | 80, 80 | -0.00689 | -0.00400 [-0.00621, -0.00178] | -0.00084 | -0.00323 | -0.01627 | peggiora |
| B1 | 320, 320 | -0.00048 | -0.00022 [-0.00063, +0.00018] | -0.00057 | -0.00006 | +0.00146 | non distinguibile dal rumore |
| B2 | 320, 320 | -0.00013 | -0.00004 [-0.00009, +0.00001] | -0.00007 | -0.00003 | +0.00085 | non distinguibile dal rumore |

### Gialli

| Variante | k (casa, ospite) | Δ ll totale validazione | Δ totale held-out [IC a blocchi] | Δ per squadra held-out | Δ O/U totale held-out | Δ totale 2026/27 (descrittivo) | Verdetto |
|---|---|---:|---|---:|---:|---:|---|
| A1 | 80, 80 | -0.00422 | -0.00444 [-0.00648, -0.00245] | -0.00172 | -0.00196 | -0.00232 | peggiora |
| A2 | 160, 160 | -0.00645 | -0.00665 [-0.00928, -0.00401] | -0.00254 | -0.00326 | -0.00388 | peggiora |
| B1 | 320, 320 | -0.00055 | -0.00049 [-0.00097, -0.00003] | -0.00061 | -0.00019 | -0.00090 | peggiora |
| B2 | 320, 320 | -0.00005 | +0.00001 [-0.00015, +0.00018] | -0.00001 | -0.00001 | +0.00000 | non distinguibile dal rumore |

### Tiri

| Variante | k (casa, ospite) | Δ ll totale validazione | Δ totale held-out [IC a blocchi] | Δ per squadra held-out | Δ O/U totale held-out | Δ totale 2026/27 (descrittivo) | Verdetto |
|---|---|---:|---|---:|---:|---:|---|
| A1 | 160, 320 | -0.00135 | +0.00015 [-0.00066, +0.00096] | +0.00015 | -0.00015 | -0.01104 | non distinguibile dal rumore |
| A2 | 320, 160 | -0.00222 | -0.00045 [-0.00154, +0.00061] | -0.00054 | -0.00051 | -0.01431 | non distinguibile dal rumore |
| B1 | 320, 320 | -0.00028 | -0.00041 [-0.00101, +0.00020] | -0.00040 | -0.00035 | +0.00525 | non distinguibile dal rumore |
| B2 | 320, 320 | -0.00020 | -0.00019 [-0.00049, +0.00008] | -0.00009 | -0.00017 | +0.00267 | non distinguibile dal rumore |
