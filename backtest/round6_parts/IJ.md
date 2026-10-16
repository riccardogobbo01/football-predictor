## Esperimenti I e J — tiri in porta (nuovo modello) e miglioramenti di tiri, tiri in porta e corner

Insieme di valutazione: 12751 partite di campionato dal 2019/20 (stesso insieme per tutte le statistiche e varianti). Validazione 5377 partite, held-out 7374.

Controllo: la matrice delle feature del baseline dei tiri coincide con `stats_model.design` di produzione.

### I — Modello dei tiri in porta per squadra (HST/AST)

**Baseline semplice: tiri previsti × quota in porta storica**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.1811 | 1.7773 | 0.440 | 0.873 | 0.941 | 0.5929 | 0.0056 | -0.0049 |
| Totale | 2.5410 | 2.4758 | 0.278 | 0.854 | 0.931 | 0.6300 | 0.0069 | -0.0065 |

**Nuovo modello dei tiri in porta (struttura degli altri modelli)**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.1777 | 1.7803 | 0.447 | 0.870 | 0.940 | 0.5910 | 0.0133 | +0.0116 |
| Totale | 2.5436 | 2.4949 | 0.271 | 0.851 | 0.928 | 0.6313 | 0.0186 | +0.0186 |

Δ del nuovo modello rispetto al baseline semplice (positivo = nuovo modello migliore):

| Variante | Δ log-loss totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ log-loss per squadra (tutte) [IC a blocchi] | Δ per squadra held-out | Δ MAE tot. | Δ corr. tot. [IC] | Δ corr. squadra [IC] | Copertura 80% tot. (var.) | Copertura 90% tot. (var.) | ECE O/U tot. (base → var.) | Verdetto |
|---|---|---|---|---:|---:|---|---|---:|---:|---|---|
| I — modello dei tiri in porta vs baseline semplice | -0.00264 [-0.00700, +0.00152] | -0.00600 [-0.01022, -0.00164] | +0.00340 [+0.00101, +0.00563] | +0.00126 | -0.0191 | -0.0067 [-0.0191, +0.0059] | +0.0068 [+0.0026, +0.0110] | 0.851 | 0.928 | 0.0069 → 0.0186 | peggiora |

### J — tiri: modello dei tiri attuale come baseline

**Baseline**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.8867 | 3.5105 | 0.505 | 0.821 | 0.908 | 0.5738 | 0.0102 | -0.0096 |
| Totale | 3.1506 | 4.4924 | 0.302 | 0.818 | 0.907 | 0.6343 | 0.0152 | -0.0151 |

Δ = baseline − variante (positivo = variante migliore); IC 95% a blocchi per settimana.

| Variante | Δ log-loss totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ log-loss per squadra (tutte) [IC a blocchi] | Δ per squadra held-out | Δ MAE tot. | Δ corr. tot. [IC] | Δ corr. squadra [IC] | Copertura 80% tot. (var.) | Copertura 90% tot. (var.) | ECE O/U tot. (base → var.) | Verdetto |
|---|---|---|---|---:|---:|---|---|---:|---:|---|---|
| J1 — + eo_diff e gol attesi v6 | -0.00300 [-0.00530, -0.00071] | +0.00223 [-0.00005, +0.00456] | -0.00031 [-0.00197, +0.00134] | +0.00423 | -0.0121 | -0.0053 [-0.0103, -0.0005] | -0.0001 [-0.0025, +0.0022] | 0.818 | 0.907 | 0.0152 → 0.0139 | non distinguibile dal rumore |
| J2a — alpha per lega | +0.00021 [-0.00058, +0.00100] | -0.00113 [-0.00218, -0.00003] | -0.00029 [-0.00060, +0.00001] | -0.00049 | +0.0000 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0.818 | 0.906 | 0.0152 → 0.0151 | peggiora |
| J2b — alpha per squadra con shrinkage (30) | -0.00131 [-0.00250, -0.00011] | -0.00221 [-0.00373, -0.00069] | -0.00299 [-0.00409, -0.00191] | -0.00280 | +0.0000 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0.819 | 0.906 | 0.0152 → 0.0151 | peggiora |
| J4 — GAP η=0.02, γ=0.0 | -0.00453 [-0.00888, +0.00029] | -0.00020 [-0.00532, +0.00658] | -0.00505 [-0.00807, -0.00166] | -0.00335 | -0.0273 | -0.0155 [-0.0238, -0.0066] | -0.0091 [-0.0124, -0.0060] | 0.817 | 0.910 | 0.0152 → 0.0162 | non distinguibile dal rumore |
| J4 — GAP η=0.05, γ=0.0 | +0.00617 [+0.00167, +0.01099] | +0.00446 [-0.00092, +0.01108] | +0.00307 [+0.00005, +0.00635] | +0.00245 | +0.0094 | +0.0107 [+0.0016, +0.0202] | +0.0017 [-0.0017, +0.0047] | 0.819 | 0.909 | 0.0152 → 0.0127 | non distinguibile dal rumore |
| J4 — GAP η=0.02, γ=0.5 | +0.00236 [-0.00184, +0.00687] | +0.00458 [-0.00042, +0.01097] | -0.00056 [-0.00352, +0.00271] | +0.00030 | +0.0050 | +0.0039 [-0.0040, +0.0125] | -0.0025 [-0.0056, +0.0004] | 0.818 | 0.907 | 0.0152 → 0.0151 | non distinguibile dal rumore |
| J4 — GAP η=0.05, γ=0.5 (scelta in validazione) | +0.01477 [+0.01009, +0.01967] | +0.01061 [+0.00511, +0.01730] | +0.00982 [+0.00671, +0.01312] | +0.00834 | +0.0489 | +0.0338 [+0.0245, +0.0434] | +0.0115 [+0.0081, +0.0144] | 0.819 | 0.907 | 0.0152 → 0.0131 | migliora |
| J3 — copula gaussiana, ρ unica | -0.00033 [-0.00096, +0.00029] | -0.00010 [-0.00080, +0.00062] | +0.00000 [+0.00000, +0.00000] | +0.00000 | +0.0002 | -0.0000 [-0.0001, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0.819 | 0.908 | 0.0152 → 0.0213 | non distinguibile dal rumore |
| J3 — copula gaussiana, ρ per lega (scelta in validazione) | -0.00002 [-0.00101, +0.00094] | -0.00102 [-0.00218, +0.00017] | +0.00000 [+0.00000, +0.00000] | +0.00000 | +0.0002 | -0.0000 [-0.0001, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0.819 | 0.907 | 0.0152 → 0.0206 | non distinguibile dal rumore |

**J3, «chi ha più tiri»** (esito casa / pari / ospite) con ρ per lega: log-loss 0.7232 contro 0.7251 con l'indipendenza (ρ = 0): Δ +0.00185, IC a blocchi [+0.00091, +0.00280], held-out +0.00147 [+0.00021, +0.00274]. Probabilità medie previste casa/pari/ospite 0.584/0.050/0.366, frequenze osservate 0.592/0.049/0.359.

ρ stimata (ultimo fold): D1 -0.189, E0 -0.248, F1 -0.213, I1 -0.129, SP1 -0.208.

### J — sot: modello I dei tiri in porta come baseline

**Baseline**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.1777 | 1.7803 | 0.447 | 0.870 | 0.940 | 0.5910 | 0.0133 | +0.0116 |
| Totale | 2.5436 | 2.4949 | 0.271 | 0.851 | 0.928 | 0.6313 | 0.0186 | +0.0186 |

Δ = baseline − variante (positivo = variante migliore); IC 95% a blocchi per settimana.

| Variante | Δ log-loss totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ log-loss per squadra (tutte) [IC a blocchi] | Δ per squadra held-out | Δ MAE tot. | Δ corr. tot. [IC] | Δ corr. squadra [IC] | Copertura 80% tot. (var.) | Copertura 90% tot. (var.) | ECE O/U tot. (base → var.) | Verdetto |
|---|---|---|---|---:|---:|---|---|---:|---:|---|---|
| J1 — + eo_diff e gol attesi v6 | +0.00126 [-0.00006, +0.00263] | +0.00077 [-0.00111, +0.00255] | +0.00327 [+0.00216, +0.00441] | +0.00390 | +0.0103 | +0.0015 [-0.0015, +0.0046] | +0.0056 [+0.0035, +0.0077] | 0.850 | 0.927 | 0.0186 → 0.0080 | non distinguibile dal rumore |
| J2a — alpha per lega | +0.00011 [-0.00023, +0.00045] | +0.00004 [-0.00039, +0.00048] | -0.00007 [-0.00031, +0.00017] | -0.00019 | +0.0000 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0.850 | 0.927 | 0.0186 → 0.0183 | non distinguibile dal rumore |
| J2b — alpha per squadra con shrinkage (30) | -0.00084 [-0.00160, -0.00008] | -0.00052 [-0.00152, +0.00050] | -0.00158 [-0.00234, -0.00077] | -0.00173 | +0.0000 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0.852 | 0.929 | 0.0186 → 0.0177 | non distinguibile dal rumore |
| J4 — GAP η=0.02, γ=0.0 | -0.00213 [-0.00386, -0.00045] | -0.00157 [-0.00385, +0.00079] | -0.00111 [-0.00200, -0.00023] | -0.00104 | -0.0077 | -0.0042 [-0.0090, +0.0008] | -0.0014 [-0.0028, +0.0000] | 0.852 | 0.927 | 0.0186 → 0.0231 | non distinguibile dal rumore |
| J4 — GAP η=0.05, γ=0.0 | +0.00186 [-0.00000, +0.00369] | +0.00254 [+0.00021, +0.00488] | +0.00113 [+0.00016, +0.00209] | +0.00137 | +0.0047 | +0.0054 [+0.0001, +0.0111] | +0.0018 [+0.0002, +0.0036] | 0.852 | 0.928 | 0.0186 → 0.0181 | migliora |
| J4 — GAP η=0.02, γ=0.5 | +0.00202 [+0.00045, +0.00357] | +0.00285 [+0.00077, +0.00510] | +0.00087 [+0.00002, +0.00169] | +0.00115 | +0.0049 | +0.0067 [+0.0024, +0.0116] | +0.0017 [+0.0003, +0.0031] | 0.852 | 0.928 | 0.0186 → 0.0185 | migliora |
| J4 — GAP η=0.05, γ=0.5 (scelta in validazione) | +0.00523 [+0.00343, +0.00706] | +0.00605 [+0.00374, +0.00832] | +0.00314 [+0.00217, +0.00416] | +0.00368 | +0.0150 | +0.0148 [+0.0096, +0.0205] | +0.0052 [+0.0035, +0.0069] | 0.854 | 0.929 | 0.0186 → 0.0141 | migliora |
| J3 — copula gaussiana, ρ unica | +0.00031 [+0.00008, +0.00056] | +0.00026 [-0.00005, +0.00056] | +0.00000 [+0.00000, +0.00000] | +0.00000 | +0.0024 | -0.0000 [-0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0.851 | 0.927 | 0.0186 → 0.0147 | non distinguibile dal rumore |
| J3 — copula gaussiana, ρ per lega (scelta in validazione) | +0.00055 [+0.00010, +0.00102] | +0.00045 [-0.00012, +0.00102] | +0.00000 [+0.00000, +0.00000] | +0.00000 | +0.0024 | -0.0000 [-0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0.851 | 0.928 | 0.0186 → 0.0147 | non distinguibile dal rumore |

**J3, «chi ha più sot»** (esito casa / pari / ospite) con ρ per lega: log-loss 0.8506 contro 0.8507 con l'indipendenza (ρ = 0): Δ +0.00009, IC a blocchi [-0.00017, +0.00036], held-out -0.00011 [-0.00045, +0.00023]. Probabilità medie previste casa/pari/ospite 0.526/0.109/0.365, frequenze osservate 0.531/0.112/0.357.

ρ stimata (ultimo fold): D1 -0.068, E0 -0.071, F1 -0.044, I1 +0.011, SP1 +0.009.

### J — corner: modello dei corner attuale come baseline

**Baseline**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.3299 | 2.0909 | 0.360 | 0.858 | 0.933 | 0.5995 | 0.0098 | +0.0093 |
| Totale | 2.6157 | 2.6820 | 0.154 | 0.841 | 0.921 | 0.6472 | 0.0174 | +0.0174 |

Δ = baseline − variante (positivo = variante migliore); IC 95% a blocchi per settimana.

| Variante | Δ log-loss totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ log-loss per squadra (tutte) [IC a blocchi] | Δ per squadra held-out | Δ MAE tot. | Δ corr. tot. [IC] | Δ corr. squadra [IC] | Copertura 80% tot. (var.) | Copertura 90% tot. (var.) | ECE O/U tot. (base → var.) | Verdetto |
|---|---|---|---|---:|---:|---|---|---:|---:|---|---|
| J1 — + eo_diff e gol attesi v6 | -0.00056 [-0.00116, +0.00005] | +0.00023 [-0.00047, +0.00092] | +0.00024 [-0.00039, +0.00088] | +0.00094 | +0.0007 | -0.0048 [-0.0076, -0.0020] | +0.0002 [-0.0013, +0.0018] | 0.841 | 0.920 | 0.0174 → 0.0128 | non distinguibile dal rumore |
| J2a — alpha per lega | +0.00004 [-0.00041, +0.00048] | +0.00027 [-0.00025, +0.00081] | -0.00002 [-0.00021, +0.00016] | -0.00004 | +0.0000 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0.841 | 0.920 | 0.0174 → 0.0173 | non distinguibile dal rumore |
| J2b — alpha per squadra con shrinkage (30) | -0.00050 [-0.00117, +0.00018] | -0.00037 [-0.00118, +0.00048] | -0.00245 [-0.00334, -0.00152] | -0.00189 | +0.0000 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0.842 | 0.921 | 0.0174 → 0.0171 | non distinguibile dal rumore |
| J4 — GAP η=0.02, γ=0.0 | -0.00131 [-0.00279, +0.00025] | -0.00117 [-0.00323, +0.00109] | -0.00070 [-0.00159, +0.00025] | -0.00099 | -0.0036 | -0.0102 [-0.0174, -0.0029] | -0.0032 [-0.0051, -0.0013] | 0.841 | 0.922 | 0.0174 → 0.0177 | non distinguibile dal rumore |
| J4 — GAP η=0.05, γ=0.0 | -0.00077 [-0.00217, +0.00073] | -0.00111 [-0.00305, +0.00109] | +0.00025 [-0.00065, +0.00119] | +0.00002 | -0.0039 | -0.0060 [-0.0127, +0.0009] | -0.0008 [-0.0027, +0.0011] | 0.841 | 0.921 | 0.0174 → 0.0194 | non distinguibile dal rumore |
| J4 — GAP η=0.02, γ=0.5 | +0.00070 [-0.00072, +0.00223] | +0.00112 [-0.00085, +0.00334] | +0.00022 [-0.00066, +0.00115] | +0.00003 | +0.0028 | -0.0000 [-0.0068, +0.0070] | -0.0012 [-0.0031, +0.0006] | 0.842 | 0.922 | 0.0174 → 0.0149 | non distinguibile dal rumore |
| J4 — GAP η=0.05, γ=0.5 (scelta in validazione) | +0.00082 [-0.00058, +0.00234] | +0.00050 [-0.00148, +0.00269] | +0.00119 [+0.00023, +0.00219] | +0.00139 | +0.0011 | +0.0020 [-0.0045, +0.0091] | +0.0014 [-0.0006, +0.0032] | 0.841 | 0.921 | 0.0174 → 0.0174 | non distinguibile dal rumore |
| J3 — copula gaussiana, ρ unica (scelta in validazione) | +0.00021 [-0.00032, +0.00075] | -0.00019 [-0.00091, +0.00056] | +0.00000 [+0.00000, +0.00000] | +0.00000 | +0.0027 | +0.0000 [-0.0001, +0.0001] | +0.0000 [+0.0000, +0.0000] | 0.842 | 0.921 | 0.0174 → 0.0101 | non distinguibile dal rumore |
| J3 — copula gaussiana, ρ per lega | +0.00017 [-0.00044, +0.00077] | -0.00005 [-0.00082, +0.00074] | +0.00000 [+0.00000, +0.00000] | +0.00000 | +0.0027 | +0.0000 [-0.0001, +0.0001] | +0.0000 [+0.0000, +0.0000] | 0.842 | 0.921 | 0.0174 → 0.0104 | non distinguibile dal rumore |

**J3, «chi ha più corner»** (esito casa / pari / ospite) con ρ unica: log-loss 0.8713 contro 0.8724 con l'indipendenza (ρ = 0): Δ +0.00114, IC a blocchi [+0.00038, +0.00194], held-out +0.00032 [-0.00068, +0.00129]. Probabilità medie previste casa/pari/ospite 0.524/0.094/0.381, frequenze osservate 0.535/0.094/0.370.

ρ stimata (ultimo fold): -0.195.
