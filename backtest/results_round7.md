# Round 7 — diagnosi e correzione del livello stagionale (solo backtest)

**La produzione non è stata toccata.** Criteri nel prereg qui sotto, scritto prima di eseguire le analisi; dati fino al 12/10/2026 (ultimo giorno presente nei CSV di football-data.co.uk al momento dell'esecuzione). Rilancio: `python -I -X utf8 backtest/run_round7.py`, poi `backtest/run_round7_extra.py`.

---


**Nulla della produzione è stato toccato.** Questa sezione è stata scritta PRIMA di eseguire qualsiasi analisi del round (le uniche informazioni note al momento della scrittura sono quelle del contesto: 65 partite registrate dal 9 ottobre con 2,98 gol previsti contro 3,63 reali, Serie A del 16-18/10 a 3,9 gol contro 2,85 previsti, intervalli dei tiri 2026/27 circa 8 punti sotto il nominale nel round 6).

## Dati e insieme di valutazione
- Dati aggiornati al momento dell'esecuzione (football-data.co.uk, Understat), stesse feature di produzione (core, xG, Elo-Odds, statistiche, GAP, effetto arbitro). Cache nuova del round 7, separata da quelle dei round precedenti (che restano valide per i loro risultati).
- **Modello dei gol (v6)**: stack di produzione with_xg + Elo-Odds (`stack.XG_FEATURES_EO`), walk-forward per stagione con training dal 2016/17 sulle sole stagioni precedenti (come `round6_lib.v6_goals`), rho del fit; previsioni fuori campione dal 2019/20, in campione per il 2016/17-2018/19 (usate SOLO come storico per stimare il livello, mai valutate).
- **Modelli delle statistiche (s4-intervalli)**: tiri, tiri in porta, corner, falli, gialli (con arbitro) come in produzione (`stats_v3`, variante with_xg, alpha per fold; alpha separato casa/ospite sui tiri). Totali.
- Validazione 2019/20-2021/22 (scelta dei parametri); held-out dal 2022/23 (compreso il 2026/27 in corso). IC a blocchi per settimana ISO (3000 ricampionamenti per le medie e i rapporti; bootstrap dei Δ come nel round 6).
- **Prime giornate**: giornata di una partita = massimo tra le partite già giocate in campionato nella stagione da casa e ospite, più uno. «Prime 8 giornate» (diagnosi 2) e «prime 10 giornate» (esperimenti) = giornata ≤ 8 e ≤ 10; «resto» = le altre.

## Diagnosi
1. **Livello 2026/27**: su tutte le partite del 2026/27 già giocate dei 5 campionati, media prevista, media reale, rapporto reale/previsto (Σ reali / Σ previsti) con IC a blocchi, per lega e complessivo, per gol casa, gol ospite, gol totali e per i totali di tiri, tiri in porta, corner, falli, gialli. Convenzione: scarto = reale − previsto.
2. **Inizio stagione**: stessa misura (rapporto reale/previsto dei gol totali e dei totali delle statistiche) per le prime 8 giornate di ogni stagione 2019/20-2026/27 e per il resto di ciascuna stagione, per capire se lo scarto di inizio stagione è normale o il 2026/27 è anomalo. Il 2026/27 è «anomalo» se il suo rapporto sta fuori dall'intervallo dei rapporti delle sette stagioni precedenti (minimo-massimo) e il suo IC a blocchi non include il rapporto medio delle precedenti.
3. **Calibrazione 2026/27**: probabilità media prevista contro frequenza osservata per Over 1,5, 2,5, 3,5 e BTTS (IC a blocchi della differenza).

## Esperimenti (uno alla volta, poi combinazione dei positivi)
Metrica primaria dei gol: **log-loss 1X2**; secondarie: log-loss Over/Under 2,5, RPS; riportate anche O1,5/O3,5/BTTS. Δ = baseline − variante (positivo = la variante migliora). Valutazione separata per «prime 10 giornate», «resto» e solo 2026/27 (descrittiva).

**L1 — livello dinamico di lega per i gol.** Per lega e per lato (gol casa, gol ospite) un moltiplicatore pre-partita R = (Σ w·y + k·m̄)/(Σ w·μ + k·m̄) sulle partite PRECEDENTI (data strettamente minore) della stessa lega, w = 0,5^(giorni / (7·H)), μ = gol attesi v6 della partita, y = gol reali, m̄ = media pesata di μ (k = pseudo-partite con rapporto 1: shrinkage verso 1). Il moltiplicatore si applica a μ e ν prima della matrice dei punteggi (stesso rho), così 1X2, O/U e BTTS restano coerenti. Griglia: **H ∈ {4, 8, 12} settimane × k ∈ {5, 15, 40}** (9 configurazioni). Scelta: la configurazione con Δ log-loss 1X2 più alto sulle sole validazioni; parità entro 0,0002 → la più semplice (k più alto, poi H più alto). Il livello viene calcolato in continuo sull'intera storia (anche il 2016/17-2018/19 in campione serve da avvio); nessun azzeramento tra stagioni (il decadimento in giorni abbassa da solo il peso dell'estate).

**L2 — decadimento più veloce del solo livello medio nei Dixon-Coles.** I rating delle squadre restano quelli di produzione (decadimento xi = 0,0018/giorno); il solo livello medio di lega (intercetta, per lato) si stima con decadimento più veloce *a rating fissati*: lo scostamento log R (stessa formula di L1, ma calcolata sulle previsioni DC `dc_lmu`, `dc_lnu`, griglia H, k identica) si somma a `dc_lmu` e `dc_lnu` PRIMA di allenare lo stack (che viene rifatto per ogni fold con le feature corrette). È una approssimazione per costruzione di «intercetta con decadimento separato» (non si rifitta il DC con due decadimenti). Scelta in validazione con la stessa regola di L1 sulla log-loss 1X2 dello stack finale.

**L3 — livello dinamico per tiri, tiri in porta, corner, falli, gialli.** Stessa formula di L1, per lega e per lato (casa/ospite), applicata alla media della Binomiale Negativa di ciascun lato (le dispersioni restano quelle del fold). Griglia (H, k) uguale; scelta **per statistica** sulla log-loss del totale in validazione, stessa regola di parità. Metriche: log-loss del totale e per squadra, log-loss Over/Under del totale, copertura degli intervalli come nel rapporto `results_intervals.md` (probabilità dichiarata contro frequenza reale, per squadra e totale, tutte le stagioni e solo 2026/27).

**Verdetto** (come nei round precedenti): «migliora» se Δ held-out > 0 con IC a blocchi che esclude lo zero e Δ secondario (O/U 2,5 per i gol; per squadra per le statistiche) ≥ 0 nell'held-out; «peggiora» se Δ held-out < 0 con IC sotto zero; altrimenti «non distinguibile dal rumore». Per la sola descrizione si riporta anche il 2026/27.

**Combinazione.** Si combinano le varianti con verdetto «migliora»: per i gol L1, L2 e L1 applicato sopra L2 (con (H, k) di L1 riscelti in validazione sull'uscita di L2); per le statistiche L3 sulle statistiche con verdetto «migliora». La combinazione si valuta con le stesse metriche e regole.

## Verifica delle definizioni dei dati
Confronto, per alcune partite del 2026/27, dei tiri in porta e dei falli di football-data.co.uk con quelli di theScore (e di una terza fonte se disponibile), annotando le differenze di definizione. Non entra nei modelli.

## Proposta per il pannello
Se una correzione del livello migliora, una riga di contesto per lega del tipo «Ritmo stagionale Premier: +12% gol» mostrata solo quando il moltiplicatore corrente si discosta da 1 di almeno una soglia fissata dai dati (proposta, non implementata).


## Diagnosi

### 1. Livello del 2026/27 (previsione walk-forward del modello di produzione; 293 partite giocate nei 5 campionati, dati fino al 2026-10-11)

Rapporto = Σ reali / Σ previsti; IC 95% a blocchi per settimana ISO. Un rapporto > 1 vuol dire che il modello ha previsto meno di quanto è successo.

**Gol**

| Lega | N | Casa prev. | Casa reale | Rapporto casa [IC] | Ospite prev. | Ospite reale | Rapporto ospite [IC] | Totale prev. | Totale reale | Rapporto totale [IC] |
|---|---:|---:|---:|---|---:|---:|---|---:|---:|---|
| Serie A | 58 | 1.53 | 1.52 | 0.994 [0.869, 1.098] | 1.22 | 1.33 | 1.088 [0.863, 1.331] | 2.75 | 2.84 | 1.036 [0.909, 1.152] |
| Premier League | 59 | 1.57 | 1.58 | 1.003 [0.760, 1.224] | 1.27 | 1.34 | 1.051 [0.758, 1.357] | 2.85 | 2.92 | 1.024 [0.890, 1.165] |
| Bundesliga | 45 | 1.71 | 2.36 | 1.377 [1.274, 1.498] | 1.43 | 1.47 | 1.022 [0.826, 1.251] | 3.15 | 3.82 | 1.215 [1.165, 1.267] |
| La Liga | 77 | 1.56 | 1.74 | 1.113 [0.938, 1.264] | 1.24 | 1.31 | 1.059 [0.946, 1.151] | 2.80 | 3.05 | 1.089 [1.000, 1.148] |
| Ligue 1 | 54 | 1.62 | 1.67 | 1.026 [0.816, 1.229] | 1.35 | 1.24 | 0.917 [0.635, 1.274] | 2.98 | 2.91 | 0.976 [0.794, 1.107] |
| **Tutte** | 293 | 1.59 | 1.74 | 1.096 [0.983, 1.192] | 1.29 | 1.33 | 1.029 [0.911, 1.163] | 2.89 | 3.08 | 1.066 [0.996, 1.118] |

**Statistiche (totali per partita: previsto → reale, rapporto [IC])**

| Lega | N | Tiri | Tiri in porta | Corner | Falli | Gialli |
|---|---:|---:|---:|---:|---:|---:|
| Serie A | 58 | 25.4 → 28.9 (1.140 [1.109, 1.163]) | 8.8 → 9.6 (1.085 [1.003, 1.191]) | 9.6 → 9.4 (0.984 [0.934, 1.025]) | 24.9 → 22.4 (0.898 [0.861, 0.941]) | 4.0 → 3.4 (0.839 [0.752, 0.915]) |
| Premier League | 59 | 26.1 → 27.6 (1.061 [1.018, 1.107]) | 8.7 → 8.9 (1.026 [0.963, 1.095]) | 10.1 → 9.3 (0.927 [0.830, 1.022]) | 21.6 → 23.2 (1.074 [1.004, 1.144]) | 3.8 → 3.9 (1.022 [0.923, 1.116]) |
| Bundesliga | 45 | 27.9 → 31.5 (1.128 [1.091, 1.165]) | 10.1 → 11.0 (1.098 [1.056, 1.141]) | 9.8 → 10.8 (1.102 [1.006, 1.205]) | 21.1 → 22.6 (1.071 [1.025, 1.121]) | 3.7 → 3.4 (0.935 [0.766, 1.127]) |
| La Liga | 77 | 24.7 → 26.6 (1.078 [0.994, 1.140]) | 8.6 → 9.4 (1.090 [1.037, 1.124]) | 9.5 → 9.8 (1.030 [0.929, 1.156]) | 25.0 → 24.8 (0.991 [0.951, 1.042]) | 4.5 → 4.2 (0.933 [0.835, 1.087]) |
| Ligue 1 | 54 | 26.0 → 27.6 (1.060 [0.985, 1.136]) | 9.0 → 9.6 (1.057 [0.964, 1.155]) | 9.6 → 9.6 (1.008 [0.957, 1.046]) | 23.9 → 23.8 (0.997 [0.953, 1.041]) | 3.7 → 3.2 (0.882 [0.769, 1.002]) |
| **Tutte** | 293 | 25.8 → 28.2 (1.092 [1.055, 1.123]) | 9.0 → 9.6 (1.072 [1.034, 1.092]) | 9.7 → 9.8 (1.007 [0.963, 1.049]) | 23.5 → 23.5 (0.999 [0.987, 1.016]) | 4.0 → 3.7 (0.923 [0.876, 0.986]) |

### 2. Inizio di stagione: prime 8 giornate contro il resto, dal 2019/20

Rapporto reale/previsto dei gol totali (e, sotto, delle statistiche) per le prime 8 giornate di ciascuna stagione (giornata ≤ 8) e per il resto della stessa stagione (2026/27: ancora nessuna partita dopo la giornata 8, salvo dove indicato).

| Stagione | N prime 8 | Rapporto gol, prime 8 [IC] | N resto | Rapporto gol, resto [IC] | Gol previsti / reali, prime 8 |
|---|---:|---|---:|---|---|
| 2019/20 | 391 | 0.951 [0.916, 0.986] | 1334 | 0.966 [0.935, 0.995] | 2.87 / 2.72 |
| 2020/21 | 383 | 1.040 [0.977, 1.099] | 1443 | 0.979 [0.947, 1.011] | 2.83 / 2.95 |
| 2021/22 | 389 | 0.996 [0.941, 1.044] | 1437 | 0.996 [0.962, 1.030] | 2.82 / 2.81 |
| 2022/23 | 390 | 0.995 [0.936, 1.069] | 1436 | 0.970 [0.945, 0.997] | 2.84 / 2.83 |
| 2023/24 | 382 | 1.043 [0.999, 1.092] | 1370 | 0.991 [0.956, 1.024] | 2.84 / 2.97 |
| 2024/25 | 384 | 1.002 [0.943, 1.057] | 1368 | 0.953 [0.920, 0.986] | 2.90 / 2.91 |
| 2025/26 | 384 | 0.965 [0.931, 0.996] | 1368 | 0.963 [0.935, 0.991] | 2.85 / 2.75 |
| 2026/27 | 293 | 1.066 [0.996, 1.118] | 0 | — | 2.89 / 3.08 |

Rapporto gol delle prime 8 giornate nelle sette stagioni precedenti: min 0.951, media 0.999, max 1.043; 2026/27: 1.066 [0.996, 1.118]. Secondo la regola del prereg il 2026/27 è **nella norma** per i gol.

**Statistiche, rapporto reale/previsto dei totali nelle prime 8 giornate**

| Stagione | Tiri | Tiri in porta | Corner | Falli | Gialli |
|---|---:|---:|---:|---:|---:|
| 2019/20 | 0.987 [0.967, 1.005] | 1.000 [0.961, 1.039] | 1.048 [1.017, 1.083] | 1.013 [0.998, 1.030] | 1.060 [1.005, 1.122] |
| 2020/21 | 0.955 [0.929, 0.977] | 0.982 [0.947, 1.008] | 0.955 [0.913, 0.985] | 1.048 [1.033, 1.065] | 0.996 [0.956, 1.048] |
| 2021/22 | 1.012 [0.992, 1.027] | 0.958 [0.936, 0.983] | 1.020 [1.002, 1.042] | 0.984 [0.953, 1.007] | 1.105 [1.050, 1.154] |
| 2022/23 | 1.018 [0.998, 1.041] | 1.007 [0.968, 1.056] | 0.994 [0.973, 1.020] | 0.995 [0.977, 1.017] | 1.074 [1.025, 1.132] |
| 2023/24 | 1.033 [1.007, 1.061] | 1.014 [0.968, 1.064] | 0.995 [0.958, 1.035] | 1.005 [0.991, 1.017] | 1.065 [1.008, 1.129] |
| 2024/25 | 0.997 [0.968, 1.021] | 0.997 [0.973, 1.023] | 1.015 [0.997, 1.034] | 0.983 [0.968, 0.999] | 1.047 [0.978, 1.103] |
| 2025/26 | 1.003 [0.985, 1.023] | 0.946 [0.904, 0.980] | 0.994 [0.946, 1.043] | 1.044 [1.030, 1.055] | 0.989 [0.944, 1.030] |
| 2026/27 | 1.092 [1.055, 1.123] | 1.072 [1.034, 1.092] | 1.007 [0.963, 1.049] | 0.999 [0.987, 1.016] | 0.923 [0.876, 0.986] |

### 3. Calibrazione dei mercati dei gol nel 2026/27

| Mercato | N | Probabilità media prevista | Frequenza osservata | Scarto (previsto − osservato) [IC a blocchi] |
|---|---:|---:|---:|---|
| Over 1,5 | 293 | 0.780 | 0.795 | -0.016 [-0.047, +0.014] |
| Over 2,5 | 293 | 0.544 | 0.604 | -0.060 [-0.105, -0.016] |
| Over 3,5 | 293 | 0.328 | 0.382 | -0.055 [-0.098, -0.008] |
| BTTS | 293 | 0.541 | 0.584 | -0.043 [-0.084, +0.014] |

Per lega (Over 2,5): Serie A previsto 0.515, osservato 0.552; Premier League previsto 0.539, osservato 0.559; Bundesliga previsto 0.598, osservato 0.778; La Liga previsto 0.524, osservato 0.571; Ligue 1 previsto 0.567, osservato 0.611.


### Weekend 16-18/10 (partite non ancora nei CSV di football-data.co.uk)

Risultati finali da theScore; previsioni = quelle pubblicate dal sito prima del weekend (commit `dd8bd91`, modello di produzione con i dati fino al 12/10). Stesse partite per lega (le partite del 19/10 non sono incluse).

| Lega | N | Gol previsti (media) | Gol reali (media) | Rapporto | Over 2,5 previsto | Over 2,5 reale |
|---|---:|---:|---:|---:|---:|---:|
| Serie A | 8 | 2.85 | 3.50 | 1.23 | 0.54 | 0.75 |
| Premier League | 9 | 2.99 | 2.44 | 0.82 | 0.57 | 0.33 |
| Bundesliga | 9 | 3.20 | 3.00 | 0.94 | 0.61 | 0.56 |
| La Liga | 9 | 2.98 | 3.00 | 1.01 | 0.57 | 0.44 |
| Ligue 1 | 9 | 2.99 | 3.89 | 1.30 | 0.57 | 0.78 |
| **Tutte** | 44 | 3.01 | 3.16 | 1.05 | 0.57 | 0.57 |

Con 44 partite l'errore standard della media dei gol è circa 0,25 per partita: lo scarto complessivo (+0,15) è dentro il rumore; le differenze per lega (8-9 partite ciascuna, errore standard circa 0,6) non sono interpretabili.

### Moltiplicatori correnti L3 (configurazioni scelte in validazione) dopo l'ultima partita giocata

Rapporto di livello per lega e lato (casa / ospite) applicato alle medie previste.

| Statistica | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---|---|---|---|---|
| Tiri (H=12, k=40) | 1.05 / 1.05 | 1.02 / 1.03 | 1.06 / 1.04 | 1.04 / 1.03 | 1.03 / 1.03 |
| Tiri in porta (H=8, k=40) | 0.98 / 1.06 | 1.00 / 1.03 | 1.07 / 1.01 | 1.06 / 1.03 | 1.04 / 1.00 |
| Corner (H=12, k=40) | 0.97 / 0.95 | 0.95 / 0.99 | 1.06 / 1.01 | 1.01 / 1.02 | 0.99 / 1.03 |
| Falli (H=4, k=15) | 0.98 / 0.88 | 1.03 / 1.07 | 1.02 / 1.05 | 1.00 / 0.99 | 0.98 / 1.01 |
| Gialli (H=4, k=15) | 1.02 / 0.82 | 1.00 / 1.06 | 0.97 / 0.92 | 0.97 / 0.97 | 1.03 / 0.89 |


## Esperimenti sui gol

Baseline (modello v6 di produzione): log-loss 1X2 0.97981, log-loss O/U 2,5 0.67418, RPS 0.19845 su 12752 partite di test (dal 2019/20). Prime 10 giornate: 3668 partite; resto: 9084; 2026/27: 293.

### L1 — livello dinamico di lega per i gol

Griglia H (emivita, settimane) × k (pseudo-partite). Scelta sulle validazioni: **H = 12, k = 40**.

| Configurazione | Δ ll 1X2 tutte [IC] | Δ validazione | Δ held-out [IC] | Δ ll O/U 2,5 held-out [IC] | Δ RPS held-out [IC] | Δ ll 1X2 prime 10 | Δ ll 1X2 resto | Δ ll 1X2 2026/27 | Verdetto |
|---|---|---:|---|---|---|---:|---:|---:|---|
| H=4 sett., k=5 | -0.00224 [-0.00408, -0.00034] | -0.00079 | -0.00329 [-0.00571, -0.00084] | -0.00053 [-0.00283, +0.00181] | -0.00109 [-0.00183, -0.00037] | -0.00526 | -0.00102 | -0.01398 | peggiora |
| H=4 sett., k=15 | -0.00087 [-0.00238, +0.00067] | +0.00035 | -0.00175 [-0.00369, +0.00021] | +0.00037 [-0.00150, +0.00228] | -0.00060 [-0.00119, -0.00002] | -0.00278 | -0.00009 | -0.00886 | non distinguibile dal rumore |
| H=4 sett., k=40 | +0.00024 [-0.00082, +0.00129] | +0.00114 | -0.00041 [-0.00175, +0.00095] | +0.00098 [-0.00032, +0.00228] | -0.00017 [-0.00057, +0.00024] | -0.00090 | +0.00070 | -0.00450 | non distinguibile dal rumore |
| H=8 sett., k=5 | -0.00058 [-0.00205, +0.00091] | +0.00119 | -0.00186 [-0.00360, -0.00012] | +0.00022 [-0.00177, +0.00224] | -0.00060 [-0.00114, -0.00007] | -0.00283 | +0.00033 | -0.00841 | peggiora |
| H=8 sett., k=15 | -0.00012 [-0.00143, +0.00120] | +0.00150 | -0.00131 [-0.00285, +0.00023] | +0.00056 [-0.00121, +0.00235] | -0.00043 [-0.00090, +0.00005] | -0.00201 | +0.00064 | -0.00659 | non distinguibile dal rumore |
| H=8 sett., k=40 | +0.00042 [-0.00061, +0.00147] | +0.00179 | -0.00058 [-0.00177, +0.00063] | +0.00094 [-0.00045, +0.00234] | -0.00019 [-0.00057, +0.00018] | -0.00101 | +0.00100 | -0.00421 | non distinguibile dal rumore |
| H=12 sett., k=5 | +0.00005 [-0.00123, +0.00136] | +0.00181 | -0.00124 [-0.00264, +0.00017] | +0.00047 [-0.00125, +0.00227] | -0.00040 [-0.00085, +0.00003] | -0.00204 | +0.00089 | -0.00582 | non distinguibile dal rumore |
| H=12 sett., k=15 | +0.00026 [-0.00091, +0.00147] | +0.00193 | -0.00096 [-0.00224, +0.00034] | +0.00066 [-0.00094, +0.00232] | -0.00031 [-0.00072, +0.00009] | -0.00163 | +0.00102 | -0.00498 | non distinguibile dal rumore |
| H=12 sett., k=40 | +0.00056 [-0.00042, +0.00158] | +0.00204 | -0.00051 [-0.00158, +0.00057] | +0.00090 [-0.00044, +0.00230] | -0.00017 [-0.00051, +0.00017] | -0.00100 | +0.00120 | -0.00362 | non distinguibile dal rumore |

### L2 — livello medio dei Dixon-Coles con decadimento più veloce

Scelta sulle validazioni: **H = 12, k = 40**.

| Configurazione | Δ ll 1X2 tutte [IC] | Δ validazione | Δ held-out [IC] | Δ ll O/U 2,5 held-out [IC] | Δ RPS held-out [IC] | Δ ll 1X2 prime 10 | Δ ll 1X2 resto | Δ ll 1X2 2026/27 | Verdetto |
|---|---|---:|---|---|---|---:|---:|---:|---|
| H=4 sett., k=5 | -0.00026 [-0.00046, -0.00007] | -0.00066 | +0.00003 [-0.00016, +0.00022] | +0.00033 [+0.00001, +0.00066] | -0.00000 [-0.00005, +0.00005] | -0.00019 | -0.00029 | -0.00027 | non distinguibile dal rumore |
| H=4 sett., k=15 | -0.00022 [-0.00038, -0.00006] | -0.00054 | +0.00002 [-0.00014, +0.00018] | +0.00026 [-0.00002, +0.00055] | -0.00000 [-0.00004, +0.00004] | -0.00016 | -0.00024 | -0.00013 | non distinguibile dal rumore |
| H=4 sett., k=40 | -0.00014 [-0.00026, -0.00002] | -0.00034 | +0.00001 [-0.00011, +0.00013] | +0.00017 [-0.00004, +0.00038] | -0.00000 [-0.00003, +0.00003] | -0.00010 | -0.00015 | +0.00001 | non distinguibile dal rumore |
| H=8 sett., k=5 | -0.00022 [-0.00038, -0.00006] | -0.00054 | +0.00001 [-0.00017, +0.00018] | +0.00028 [-0.00000, +0.00057] | -0.00000 [-0.00005, +0.00004] | -0.00012 | -0.00026 | +0.00004 | non distinguibile dal rumore |
| H=8 sett., k=15 | -0.00019 [-0.00034, -0.00005] | -0.00047 | +0.00001 [-0.00015, +0.00016] | +0.00025 [-0.00001, +0.00051] | -0.00000 [-0.00004, +0.00004] | -0.00011 | -0.00022 | +0.00005 | non distinguibile dal rumore |
| H=8 sett., k=40 | -0.00014 [-0.00026, -0.00003] | -0.00035 | +0.00000 [-0.00013, +0.00013] | +0.00019 [-0.00002, +0.00040] | -0.00000 [-0.00004, +0.00003] | -0.00008 | -0.00017 | +0.00010 | non distinguibile dal rumore |
| H=12 sett., k=5 | -0.00018 [-0.00033, -0.00004] | -0.00044 | +0.00000 [-0.00016, +0.00016] | +0.00024 [-0.00001, +0.00050] | -0.00001 [-0.00005, +0.00004] | -0.00010 | -0.00021 | +0.00019 | non distinguibile dal rumore |
| H=12 sett., k=15 | -0.00017 [-0.00030, -0.00003] | -0.00040 | +0.00001 [-0.00015, +0.00015] | +0.00022 [-0.00001, +0.00046] | -0.00000 [-0.00004, +0.00004] | -0.00010 | -0.00019 | +0.00019 | non distinguibile dal rumore |
| H=12 sett., k=40 | -0.00014 [-0.00025, -0.00002] | -0.00032 | +0.00000 [-0.00013, +0.00013] | +0.00019 [-0.00002, +0.00039] | -0.00000 [-0.00004, +0.00003] | -0.00008 | -0.00016 | +0.00021 | non distinguibile dal rumore |

### Riepilogo gol (configurazioni scelte in validazione)

| Variante | Configurazione | Δ ll 1X2 tutte [IC] | Δ held-out [IC] | Δ ll O/U 2,5 held-out [IC] | Δ RPS held-out | Δ prime 10 | Δ resto | Δ 2026/27 | Verdetto |
|---|---|---|---|---|---:|---:|---:|---:|---|
| L1 livello dinamico | H=12, k=40 | +0.00056 [-0.00042, +0.00158] | -0.00051 [-0.00158, +0.00057] | +0.00090 [-0.00044, +0.00230] | -0.00017 | -0.00100 | +0.00120 | -0.00362 | non distinguibile dal rumore |
| L2 decadimento veloce del livello DC | H=12, k=40 | -0.00014 [-0.00025, -0.00002] | +0.00000 [-0.00013, +0.00013] | +0.00019 [-0.00002, +0.00039] | -0.00000 | -0.00008 | -0.00016 | +0.00021 | non distinguibile dal rumore |

### Effetto sul livello del 2026/27

| Variante | Gol totali previsti (media 2026/27) | Gol reali | Over 2,5 previsto | Over 2,5 reale | Over 3,5 previsto | Over 3,5 reale | BTTS previsto | BTTS reale |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 2.89 | 3.08 | 0.544 | 0.604 | 0.328 | 0.382 | 0.541 | 0.584 |
| L1 (H=12, k=40) | 2.87 | 3.08 | 0.539 | 0.604 | 0.324 | 0.382 | 0.536 | 0.584 |
| L2 (H=12, k=40) | 2.88 | 3.08 | 0.544 | 0.604 | 0.327 | 0.382 | 0.541 | 0.584 |

### Moltiplicatore corrente di lega (L1, configurazione scelta) dopo l'ultima partita giocata

| Lega | Gol casa | Gol ospite | Gol totali (stima) |
|---|---:|---:|---:|
| Serie A | 0.948 | 1.011 | 0.976 (-2%) |
| Premier League | 0.984 | 0.996 | 0.989 (-1%) |
| Bundesliga | 1.138 | 1.029 | 1.089 (+9%) |
| La Liga | 1.056 | 0.988 | 1.026 (+3%) |
| Ligue 1 | 0.991 | 0.966 | 0.980 (-2%) |


## Esperimenti sulle statistiche (L3)

Livello dinamico per lega e lato sulle medie delle statistiche (stessa formula di L1), (H, k) scelto per statistica sulla log-loss del totale in validazione. Δ = baseline − variante (positivo = la variante migliora).

### Tiri

| H (sett.) | k | Δ ll totale (tutte) [IC a blocchi] | Δ totale validazione | Δ totale held-out [IC a blocchi] | Δ per squadra held-out | Verdetto |
|---:|---:|---|---:|---|---:|---|
| 4 | 5 | +0.00098 [-0.00238, +0.00440] | +0.00207 | +0.00020 [-0.00355, +0.00424] | -0.00163 | non distinguibile dal rumore |
| 4 | 15 | +0.00238 [-0.00047, +0.00523] | +0.00357 | +0.00152 [-0.00158, +0.00492] | -0.00004 | non distinguibile dal rumore |
| 4 | 40 | +0.00305 [+0.00098, +0.00514] | +0.00425 | +0.00218 [+0.00001, +0.00464] | +0.00108 | migliora |
| 8 | 5 | +0.00254 [-0.00063, +0.00556] | +0.00323 | +0.00203 [-0.00120, +0.00560] | +0.00012 | non distinguibile dal rumore |
| 8 | 15 | +0.00298 [+0.00015, +0.00567] | +0.00378 | +0.00240 [-0.00049, +0.00561] | +0.00063 | non distinguibile dal rumore |
| 8 | 40 | +0.00332 [+0.00105, +0.00547] | +0.00420 | +0.00267 [+0.00039, +0.00520] | +0.00119 | migliora |
| 12 | 5 | +0.00291 [+0.00005, +0.00564] | +0.00356 | +0.00243 [-0.00046, +0.00549] | +0.00066 | non distinguibile dal rumore |
| 12 | 15 | +0.00312 [+0.00044, +0.00566] | +0.00383 | +0.00260 [-0.00008, +0.00543] | +0.00091 | non distinguibile dal rumore |
| 12 | 40 | +0.00332 [+0.00107, +0.00547] | +0.00411 | +0.00275 [+0.00047, +0.00514] | +0.00123 | migliora ← scelta |

### Tiri in porta

| H (sett.) | k | Δ ll totale (tutte) [IC a blocchi] | Δ totale validazione | Δ totale held-out [IC a blocchi] | Δ per squadra held-out | Verdetto |
|---:|---:|---|---:|---|---:|---|
| 4 | 5 | +0.00598 [+0.00282, +0.00924] | +0.00805 | +0.00447 [+0.00099, +0.00797] | +0.00093 | migliora |
| 4 | 15 | +0.00715 [+0.00451, +0.00986] | +0.00917 | +0.00567 [+0.00284, +0.00852] | +0.00234 | migliora |
| 4 | 40 | +0.00706 [+0.00513, +0.00906] | +0.00885 | +0.00576 [+0.00376, +0.00774] | +0.00302 | migliora |
| 8 | 5 | +0.00729 [+0.00422, +0.01038] | +0.00877 | +0.00621 [+0.00303, +0.00933] | +0.00266 | migliora |
| 8 | 15 | +0.00770 [+0.00491, +0.01051] | +0.00921 | +0.00661 [+0.00378, +0.00942] | +0.00313 | migliora |
| 8 | 40 | +0.00772 [+0.00547, +0.01000] | +0.00916 | +0.00666 [+0.00442, +0.00888] | +0.00347 | migliora ← scelta |
| 12 | 5 | +0.00744 [+0.00448, +0.01043] | +0.00865 | +0.00656 [+0.00348, +0.00953] | +0.00314 | migliora |
| 12 | 15 | +0.00766 [+0.00489, +0.01044] | +0.00887 | +0.00677 [+0.00391, +0.00950] | +0.00337 | migliora |
| 12 | 40 | +0.00771 [+0.00534, +0.01010] | +0.00890 | +0.00684 [+0.00444, +0.00916] | +0.00359 | migliora |

### Corner

| H (sett.) | k | Δ ll totale (tutte) [IC a blocchi] | Δ totale validazione | Δ totale held-out [IC a blocchi] | Δ per squadra held-out | Verdetto |
|---:|---:|---|---:|---|---:|---|
| 4 | 5 | -0.00027 [-0.00283, +0.00230] | +0.00000 | -0.00047 [-0.00374, +0.00282] | -0.00298 | non distinguibile dal rumore |
| 4 | 15 | +0.00140 [-0.00072, +0.00348] | +0.00171 | +0.00117 [-0.00146, +0.00382] | -0.00119 | non distinguibile dal rumore |
| 4 | 40 | +0.00242 [+0.00095, +0.00388] | +0.00276 | +0.00218 [+0.00035, +0.00404] | +0.00026 | migliora |
| 8 | 5 | +0.00189 [-0.00023, +0.00400] | +0.00189 | +0.00189 [-0.00080, +0.00453] | -0.00049 | non distinguibile dal rumore |
| 8 | 15 | +0.00243 [+0.00055, +0.00433] | +0.00250 | +0.00239 [-0.00003, +0.00479] | +0.00012 | non distinguibile dal rumore |
| 8 | 40 | +0.00294 [+0.00143, +0.00446] | +0.00309 | +0.00283 [+0.00092, +0.00476] | +0.00083 | migliora |
| 12 | 5 | +0.00257 [+0.00065, +0.00446] | +0.00244 | +0.00266 [+0.00027, +0.00508] | +0.00044 | migliora |
| 12 | 15 | +0.00283 [+0.00106, +0.00459] | +0.00274 | +0.00289 [+0.00069, +0.00514] | +0.00074 | migliora |
| 12 | 40 | +0.00312 [+0.00162, +0.00462] | +0.00309 | +0.00314 [+0.00126, +0.00503] | +0.00115 | migliora ← scelta |

### Falli

| H (sett.) | k | Δ ll totale (tutte) [IC a blocchi] | Δ totale validazione | Δ totale held-out [IC a blocchi] | Δ per squadra held-out | Verdetto |
|---:|---:|---|---:|---|---:|---|
| 4 | 5 | +0.00821 [+0.00539, +0.01097] | +0.01014 | +0.00680 [+0.00329, +0.01052] | +0.00123 | migliora |
| 4 | 15 | +0.00900 [+0.00675, +0.01122] | +0.01092 | +0.00761 [+0.00478, +0.01061] | +0.00253 | migliora ← scelta |
| 4 | 40 | +0.00827 [+0.00669, +0.00984] | +0.00998 | +0.00703 [+0.00506, +0.00912] | +0.00304 | migliora |
| 8 | 5 | +0.00760 [+0.00514, +0.01002] | +0.00917 | +0.00645 [+0.00328, +0.00978] | +0.00215 | migliora |
| 8 | 15 | +0.00795 [+0.00580, +0.01010] | +0.00951 | +0.00681 [+0.00401, +0.00975] | +0.00262 | migliora |
| 8 | 40 | +0.00781 [+0.00612, +0.00951] | +0.00930 | +0.00673 [+0.00454, +0.00904] | +0.00297 | migliora |
| 12 | 5 | +0.00665 [+0.00443, +0.00891] | +0.00806 | +0.00563 [+0.00280, +0.00866] | +0.00214 | migliora |
| 12 | 15 | +0.00685 [+0.00480, +0.00894] | +0.00824 | +0.00584 [+0.00328, +0.00864] | +0.00239 | migliora |
| 12 | 40 | +0.00688 [+0.00516, +0.00862] | +0.00821 | +0.00591 [+0.00375, +0.00826] | +0.00265 | migliora |

### Gialli

| H (sett.) | k | Δ ll totale (tutte) [IC a blocchi] | Δ totale validazione | Δ totale held-out [IC a blocchi] | Δ per squadra held-out | Verdetto |
|---:|---:|---|---:|---|---:|---|
| 4 | 5 | +0.00852 [+0.00542, +0.01160] | +0.00808 | +0.00883 [+0.00491, +0.01291] | +0.00297 | migliora |
| 4 | 15 | +0.00955 [+0.00699, +0.01210] | +0.00918 | +0.00982 [+0.00653, +0.01319] | +0.00409 | migliora ← scelta |
| 4 | 40 | +0.00897 [+0.00710, +0.01083] | +0.00875 | +0.00914 [+0.00678, +0.01159] | +0.00429 | migliora |
| 8 | 5 | +0.00831 [+0.00547, +0.01115] | +0.00748 | +0.00892 [+0.00545, +0.01246] | +0.00380 | migliora |
| 8 | 15 | +0.00869 [+0.00611, +0.01126] | +0.00789 | +0.00928 [+0.00615, +0.01247] | +0.00419 | migliora |
| 8 | 40 | +0.00858 [+0.00653, +0.01065] | +0.00787 | +0.00909 [+0.00658, +0.01161] | +0.00436 | migliora |
| 12 | 5 | +0.00748 [+0.00480, +0.01021] | +0.00612 | +0.00846 [+0.00523, +0.01168] | +0.00385 | migliora |
| 12 | 15 | +0.00767 [+0.00519, +0.01020] | +0.00635 | +0.00863 [+0.00563, +0.01163] | +0.00403 | migliora |
| 12 | 40 | +0.00767 [+0.00556, +0.00982] | +0.00645 | +0.00856 [+0.00603, +0.01111] | +0.00415 | migliora |

### Riepilogo L3 (configurazioni scelte in validazione)

| Statistica | Configurazione | Δ ll totale tutte [IC] | Δ totale held-out [IC] | Δ per squadra held-out [IC] | Δ O/U totale held-out | Δ ll totale 2026/27 | Verdetto |
|---|---|---|---|---|---:|---:|---|
| Tiri | H=12, k=40 | +0.00332 [+0.00107, +0.00547] | +0.00275 [+0.00047, +0.00514] | +0.00123 [-0.00016, +0.00269] | +0.00134 | +0.03909 | migliora |
| Tiri in porta | H=8, k=40 | +0.00772 [+0.00547, +0.01000] | +0.00666 [+0.00442, +0.00888] | +0.00347 [+0.00213, +0.00477] | +0.00419 | +0.00582 | migliora |
| Corner | H=12, k=40 | +0.00312 [+0.00162, +0.00462] | +0.00314 [+0.00126, +0.00503] | +0.00115 [-0.00013, +0.00245] | +0.00167 | +0.00008 | migliora |
| Falli | H=4, k=15 | +0.00900 [+0.00675, +0.01122] | +0.00761 [+0.00478, +0.01061] | +0.00253 [+0.00076, +0.00434] | +0.00576 | +0.01542 | migliora |
| Gialli | H=4, k=15 | +0.00955 [+0.00699, +0.01210] | +0.00982 [+0.00653, +0.01319] | +0.00409 [+0.00235, +0.00595] | +0.00526 | +0.00456 | migliora |

### Copertura degli intervalli (frequenza reale − probabilità dichiarata)

| Statistica | Scarto intervallo squadra, tutte (base → L3) | Scarto intervallo totale, tutte (base → L3) | Scarto squadra 2026/27 (base → L3) | Scarto totale 2026/27 (base → L3) |
|---|---|---|---|---|
| Tiri | -1.9 → -1.7 pp | -1.2 → -1.0 pp | -7.6 → -4.7 pp | -8.8 → -6.3 pp |
| Tiri in porta | +0.1 → -0.1 pp | +0.2 → +0.3 pp | -1.5 → -2.5 pp | -4.3 → -3.7 pp |
| Corner | -0.4 → -0.8 pp | -0.3 → -0.4 pp | -1.3 → -1.5 pp | -3.8 → -4.6 pp |
| Falli | +0.2 → +0.3 pp | +0.7 → +0.9 pp | -4.1 → -4.2 pp | -3.5 → -4.6 pp |
| Gialli | +1.9 → +2.3 pp | -0.8 → -0.3 pp | +3.2 → +1.9 pp | +0.7 → -0.3 pp |


## Verifica delle definizioni: football-data.co.uk contro theScore

Confronto sulle 10 partite di Serie A del 10-12/10/2026 presenti in entrambe le fonti (theScore dalla pagina «Team Comparison» di ogni partita; football-data.co.uk dal CSV 2026/27). La riga «Shots (on goal)» di theScore è il numero dei **tiri in porta**; i tiri totali non compaiono nella pagina.

| Partita | Tiri in porta (theScore = fd) | Falli | Corner | Gialli | Rossi |
|---|---|---|---|---|---|
| Torino-Udinese | 4-1 = 4-1 | 4-10 = 4-10 | 4-3 = 4-3 | 0-1 = 0-1 | 0-0 = 0-0 |
| Sassuolo-Milan | 4-6 = 4-6 | 13-11 = 13-11 | 3-5 = 3-5 | **2-4 contro 1-4** | 0-0 = 0-0 |
| Napoli-Frosinone | 8-1 = 8-1 | 8-12 = 8-12 | 6-4 = 6-4 | 2-0 = 2-0 | 0-0 = 0-0 |
| Lecce-Bologna | 5-5 = 5-5 | 17-8 = 17-8 | 10-3 = 10-3 | 3-2 = 3-2 | 0-0 = 0-0 |
| Lazio-Monza | 7-6 = 7-6 | 10-9 = 10-9 | 7-6 = 7-6 | 3-1 = 3-1 | 0-1 = 0-1 |
| Inter-Parma | 6-2 = 6-2 | 13-9 = 13-9 | 3-1 = 3-1 | 0-0 = 0-0 | 0-0 = 0-0 |
| Genoa-Fiorentina | 4-3 = 4-3 | 11-10 = 11-10 | 3-4 = 3-4 | 5-3 = 5-3 | 0-0 = 0-0 |
| Como-Roma | 4-2 = 4-2 | 9-9 = 9-9 | 6-2 = 6-2 | 2-3 = 2-3 | 0-1 = 0-1 |
| Cagliari-Juventus | 2-10 = 2-10 | 8-8 = 8-8 | 1-9 = 1-9 | 2-1 = 2-1 | 0-0 = 0-0 |
| Atalanta-Venezia | 11-4 = 11-4 | 14-6 = 14-6 | 8-7 = 8-7 | 0-2 = 0-2 | 1-0 = 1-0 |

**Esito.** Tiri in porta, falli, corner e rossi coincidono in tutte le 10 partite (le definizioni sono le stesse). I gialli coincidono in 9 su 10: in Sassuolo-Milan theScore ha 2 gialli per il Sassuolo, football-data.co.uk 1 (non si può dire quale sia giusto da qui).

**Il caso Milan, 3 falli.** In Milan-Atalanta (18/10, 3-2) theScore riporta **3 falli del Milan contro 10 dell'Atalanta**, 6-4 tiri in porta, 2-2 corner. Nelle altre 17 partite del 10-18/10 sulle quali ho letto la pagina il minimo di falli di una squadra è 4 (Torino) e la media è 9,7 falli per squadra; 3 è quindi un valore anomalo ma non impossibile. La partita non è ancora nel CSV di football-data.co.uk (aggiornato con ritardo: l'ultima data presente è l'11-12/10), quindi non posso ancora dire se le due fonti coincidano; **da ricontrollare appena il CSV si aggiorna**. Nel round 7 i falli del 2026/27 usati dai modelli sono quelli di football-data.co.uk fino al 12/10 e non includono quella partita.

**Arbitri.** Per le 8 partite di Serie A del 16-18/10 lette su theScore (Sacchi, Guida, Abisso, Chiffi, Massa, Marchetti, Di Bello, Doveri) l'arbitro coincide con la designazione AIA della 7ª giornata pubblicata il 14/10.


## Tabella riassuntiva

| Esperimento | Configurazione (validazione) | Δ held-out [IC a blocchi] | Verdetto | Effetto sul 2026/27 |
|---|---|---|---|---|
| L1 — livello dinamico di lega, gol | H=12 sett., k=40 | log-loss 1X2 −0,00051 [−0,00158, +0,00057]; O/U 2,5 +0,00090 [−0,00044, +0,00230] | non distinguibile dal rumore | log-loss 1X2 −0,0036 (peggiora); gol previsti 2,87 (baseline 2,89; reali 3,08) |
| L2 — decadimento veloce del livello DC | H=12 sett., k=40 | +0,00000 [−0,00013, +0,00013] | non distinguibile dal rumore | +0,0002; gol previsti 2,88 |
| L1 sopra L2 | non eseguita | — | nessuna delle due migliora | — |
| L3 tiri | H=12, k=40 | log-loss totale +0,00275 [+0,00047, +0,00514] | migliora | totale +0,0391; scarto intervallo squadra −7,6 → −4,7 pp |
| L3 tiri in porta | H=8, k=40 | +0,00666 [+0,00442, +0,00888] | migliora | totale +0,0058 |
| L3 corner | H=12, k=40 | +0,00314 [+0,00126, +0,00503] | migliora | totale +0,0001 |
| L3 falli | H=4, k=15 | +0,00761 [+0,00478, +0,01061] | migliora | totale +0,0154 |
| L3 gialli | H=4, k=15 | +0,00982 [+0,00653, +0,01319] | migliora | totale +0,0046 |

## Commento

1. **Il livello dei gol del 2026/27 non è, finora, un problema misurabile del modello.** Sulle 293 partite di campionato giocate fino al 12/10 (tutte nei CSV) i gol reali sono 3,08 contro 2,89 previsti, +6,6% (IC a blocchi 95% [−0,4%, +11,8%]): al limite della significatività. Il grosso viene dalla Bundesliga (rapporto 1,215 [1,165, 1,267]; gol in casa +38%); Serie A, Premier e Ligue 1 sono a ±4%, La Liga +9% (IC [0,0%, +14,8%]). Per le prime 8 giornate le sette stagioni precedenti stanno tra 0,951 e 1,043 (media 0,999): il 2026/27 (1,066) è fuori dal minimo-massimo ma il suo IC include la media, quindi per la regola del prereg è «nella norma». Over 2,5 è sotto-previsto di 6,0 punti [−10,5, −1,6] e Over 3,5 di 5,5 [−9,8, −0,8]: sono gli unici due scarti con IC a blocchi che esclude lo zero (BTTS −4,3 [−8,4, +1,4] no, Over 1,5 −1,6 no), e vanno letti con 293 partite e cinque leghe.
2. **Il confronto del weekend e le «65 partite».** Le 65 partite registrate dal 9/10 contengono 18 partite di Champions League (4,33 gol a partita, modello Elo delle coppe) e 47 di campionato (3,36); il blocco dei gol attesi 2,98 e reali 3,63 mescola quindi i due modelli. Sul weekend 16-18/10 (44 partite dei cinque campionati, risultati da theScore, previsioni emesse prima) i gol sono 3,16 contro 3,01 previsti (+5%) e la frequenza di Over 2,5 è 0,57 contro 0,57. La Serie A (8 partite) è a 3,50 contro 2,85 (e Ligue 1 3,89 contro 2,99), ma la Premier è a 2,44 contro 2,99: con 8-9 partite per lega l'errore standard della media è circa 0,6 gol, quindi queste differenze non sono interpretabili. Non c'è una prova di una sottostima sistematica in tutte le leghe.
3. **L1 e L2 non migliorano e non vanno messi in produzione.** Nessuna delle 9 configurazioni di L1 ha un guadagno con IC a blocchi che esclude lo zero sull'held-out; due peggiorano (emivita corta e shrinkage debole). Sul solo 2026/27 L1 peggiora sempre la log-loss (−0,004 con la configurazione scelta): il moltiplicatore, a questo punto della stagione, porta ancora la memoria di una stagione 2025/26 con rapporto 0,96-0,97, e il suo valore corrente è 0,98 per la Serie A e 1,09 per la Bundesliga, non il +10-20% che sarebbe servito. L2 è neutro (differenze di 1e-4). Il livello medio dei gol non mostra prime giornate sistematicamente sottostimate: in sette stagioni il rapporto delle prime 8 giornate oscilla intorno a 1,00.
4. **Per le statistiche L3 migliora in tutte e cinque** (Δ log-loss del totale in held-out con IC a blocchi che esclude lo zero e per squadra ≥ 0). I guadagni sono piccoli sui tiri e sui corner (+0,003) e più netti su tiri in porta, falli e gialli (+0,007/+0,010); sui tiri del 2026/27 il guadagno è +0,039, che accorcia lo scarto di copertura degli intervalli da −7,6 a −4,7 punti per squadra (e da −8,8 a −6,3 sul totale): il livello dei tiri 2026/27 è effettivamente più alto del previsto (rapporto 1,092 [1,055, 1,123]) e i gialli più bassi (0,923 [0,876, 0,986]). Sugli altri intervalli la correzione cambia di poco il 2026/27 e non peggiora la copertura storica oltre 0,4 punti.
5. **Attenzione al bordo della griglia.** Per tiri, tiri in porta e corner la scelta cade sul bordo di k (40, il massimo) e per tiri e corner anche su H=12 (il massimo); per falli e gialli su H=4 (il minimo). Il guadagno è piatto lungo la griglia (vedi le tabelle per statistica) e per prereg non si estende; se si decide di metterla in produzione conviene fissare la configurazione di validazione e non cercare oltre.
6. **Definizioni dei dati.** I tiri in porta, i falli, i corner e i rossi di football-data.co.uk coincidono con theScore in tutte le 10 partite di Serie A del 10-12/10 (i gialli in 9 su 10: Sassuolo-Milan 2 contro 1). Il 3 falli del Milan in Milan-Atalanta (18/10) è su theScore, ma la partita non è ancora nel CSV: valore anomalo (minimo altrove 4, media 9,7) da ricontrollare quando football-data.co.uk si aggiorna. Il fatto che la tabella dei falli di football-data.co.uk coincida in tutte le altre partite esclude una differenza di definizione sistematica.
7. **Limite dei dati.** I CSV di football-data.co.uk si fermano al 12/10: i 44 risultati del 16-18/10 non sono nei modelli di questo round (solo nella tabella del weekend). Rilanciare `python -I -X utf8 backtest/run_round7.py` quando il CSV si aggiorna per includerli (il lavoro è ripetibile).

## Proposta per il pannello

- **Gol: nessuna correzione e nessuna riga «ritmo stagionale».** Dato che L1 non migliora, mostrare un +x% corretto sarebbe una correzione non validata. Se si vuole una nota di contesto puramente descrittiva (non un'etichetta del modello): in «Contesto» una riga per la lega della partita, ad es. «Bundesliga 2026/27: 3,8 gol a partita (media 2019-25: 3,2)», mostrata solo quando lo scarto tra la media della stagione in corso e quella delle stagioni precedenti supera, ad esempio, il 15% e le partite giocate sono almeno 40.
- **Statistiche, se L3 va in produzione:** nella sezione di ciascuna statistica una riga «Livello stagionale Serie A: tiri +5% (casa e ospite)», mostrata solo quando almeno uno dei due moltiplicatori della lega si discosta da 1 per più del 5%. Ai valori attuali comparirebbe per i tiri (Serie A +5%, Bundesliga +6%), per i gialli ospite (Serie A −18%, Ligue 1 −11%, Bundesliga −8%) e per i falli ospite della Serie A (−12%); i valori sono nella tabella dei moltiplicatori correnti. La riga è una spiegazione della correzione già applicata ai valori attesi, non un'aggiunta ulteriore.

