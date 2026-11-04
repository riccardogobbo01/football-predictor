# Round 10 — livello di stagione per lega (bayesiano) per gol e statistiche (solo backtest)

**La produzione non è stata toccata.** Criteri nel prereg qui sotto (scritto prima di eseguire le analisi). Rilancio: `python -I -X utf8 backtest/run_round10.py [GOALS|STATS|REF]`.

---


**La produzione non viene toccata.** Criteri scritti PRIMA di eseguire qualsiasi analisi del round. Stesse regole dei round precedenti: validazione 2019/20-2021/22 (solo qui si scelgono i parametri), IC a blocchi per settimana ISO (5000 ricampionamenti), Δ = baseline − variante (positivo = la variante migliora), verdetto «migliora» se Δ held-out > 0 con IC a blocchi che esclude lo zero e Δ secondario ≥ 0 nell'held-out; «peggiora» se Δ held-out < 0 con IC sotto zero; altrimenti «non distinguibile dal rumore».

**Held-out e 2026/27.** Per non usare la stagione in corso nella scelta né nel giudizio principale, l'held-out del round è **2022/23-2025/26**; il **2026/27 (in corso) è riportato a parte** (tutte le leghe e Serie A) come caso di studio, mai usato per scegliere i parametri. Nessun parametro viene toccato dopo aver visto il 2026/27.

## Dati
Contesto aggiornato all'esecuzione (football-data.co.uk, Understat). Modello dei gol = stack di produzione (v6, with_xg + Elo-Odds) walk-forward per stagione (training dal 2016/17 sulle sole stagioni precedenti); modelli delle statistiche = `stats_v3` di produzione (stesso schema), come nel round 7. Il livello è stimato SOLO con partite della stessa lega e della stessa stagione con data strettamente precedente a quella della partita da prevedere (nessuna informazione dalla partita né da partite dello stesso giorno).

## N1 — livello di stagione per lega (bayesiano), gol
Per ogni lega ℓ, stagione s e lato (gol casa, gol ospite): **R = (Σy + k·m̄) / (Σμ + k·m̄)**, somme sulle partite di (ℓ, s) già giocate (date precedenti), y = gol reali del lato, μ = gol attesi v6 del lato, m̄ = Σμ / n (livello previsto medio per partita del lato nella stessa lega e stagione). Senza partite precedenti R = 1; il peso dell'osservato è n/(n + k), cioè cresce con le partite giocate; k = numero di pseudo-partite «senza scarto». Nessun riporto tra stagioni (il livello riparte da 1 a ogni stagione). R moltiplica μ e ν prima della matrice dei punteggi (stesso rho), quindi 1X2, O/U, BTTS e pareggi restano coerenti. **Griglia k ∈ {10, 20, 40, 80, 160, 320}**; scelta sulle sole validazioni: massimo Δ della log-loss 1X2; parità entro 0,0002 → k più alto.

## N2 — N1 con rilevazione di cambiamento strutturale
Come N1, ma R vale 1 finché lo scarto di stagione del lato non supera 2 errori standard: **z = (Σy − Σμ)/√Σμ** (varianza di Poisson dei gol; per lato); se |z| > 2 si usa il R di N1, altrimenti 1. Soglia fissata a 2 (non si ottimizza). k scelto in validazione con la stessa regola, separatamente da N1.
**Attivazioni**: per ogni lega e stagione dal 2019/20 si riporta la quota di partite con il filtro attivo (per lato), se è attivo a fine stagione e il giorno della prima attivazione; si evidenziano 2020/21 (porte chiuse: ci si aspetta che si attivi sul lato di casa) e il numero di coppie lega-stagione 2019/20-2025/26 con almeno un'attivazione.

## Metriche dei gol
Primaria: log-loss 1X2; secondarie: log-loss Over/Under 2,5, RPS; riportate anche la distanza tra probabilità media di pareggio prevista e frequenza dei pareggi, i gol medi previsti contro reali, O1,5/O3,5/BTTS. Insiemi: validazione, held-out (2022/23-2025/26), prime 10 giornate / resto, 2026/27 (tutte le leghe e Serie A).

## Caso di studio: Serie A 2026/27 (simulazione walk-forward)
Con i parametri scelti in validazione: log-loss 1X2, log-loss Over 2,5, pareggi (previsti contro reali) e gol medi, **prima (v6) e dopo (N1, N2)**, sulle partite di Serie A 2026/27 già giocate, confronto con il mercato (quote di chiusura medie senza margine: 1X2 e Over/Under 2,5) sulle stesse partite; andamento di R e di z dopo ogni giornata. Descrittivo (poche partite), nessuna scelta.

## N3 — statistiche (falli, gialli, tiri)
**Baseline = produzione**: modelli `stats_v3` + livello stagionale di `config.LEVEL_PARAMS` (round 7). **Varianti** (livello di stagione bayesiano della stessa formula di N1 per lega e lato, stesse regole di nessun riporto, applicato alle medie attese della statistica con y = valori reali, μ = medie attese):
- **A1** sostituisce il livello di produzione (R calcolato sulle medie di base); **B1** si somma al livello di produzione (R calcolato sulle medie già corrette dal livello di produzione);
- **A2 / B2**: come A1 / B1 ma attivi solo se |z| > 2, con z = (Σy − Σμ)/√Σ(μ + α·μ²) (α = dispersione del fold, per lato).
Griglia k ∈ {10, 20, 40, 80, 160, 320}, scelta per statistica e variante sulle validazioni (massimo Δ della log-loss del totale; parità entro 0,0002 → k più alto). **Tiri: separazione casa/ospite**: k_casa e k_ospite scelti separatamente (36 combinazioni) — è la «separazione casa/ospite» dei tiri; non esiste un round 9 precedente, la si definisce qui. Falli e gialli: un solo k per i due lati.
Metriche: log-loss del totale (primaria), per squadra, Over/Under del totale, copertura degli intervalli (dichiarata contro reale, per squadra e totale, tutte le stagioni e 2026/27; criterio ≤ 3 punti su tutte le stagioni).
**Effetto arbitro sui gialli con più peso sulla stagione in corso**: l'effetto R_arbitro = (Σy + k·m̄)/(Σm + k·m̄) (k = 20, come in produzione) si ricalcola con peso decrescente nel tempo sulle partite passate dell'arbitro, w = 0,5^(giorni/(365·h)) con h ∈ {0,5; 1; 2} anni; si confronta (stesso modello dei gialli, senza livello stagionale per isolare l'effetto) con la produzione (peso uniforme); h scelto in validazione con la stessa regola (parità → h più alto).


## N1 e N2 — gol

Baseline: stack v6 di produzione senza livello di stagione. Insiemi: validazione 5377 partite, held-out 2022/23-2025/26 7082, 2026/27 447. Δ = baseline − variante (positivo = migliora).

### N1: griglia di k

| k | Δ ll 1X2 validazione | Δ ll 1X2 held-out [IC a blocchi] | Δ ll O/U 2,5 held-out [IC] | Δ RPS held-out | Δ ll 1X2 2026/27 (descrittivo) | Verdetto |
|---:|---:|---|---|---:|---:|---|
| 10 | +0.00060 | -0.00253 [-0.00483, -0.00018] | -0.00068 [-0.00275, +0.00143] | -0.00075 | -0.01307 | peggiora |
| 20 | +0.00121 | -0.00173 [-0.00372, +0.00035] | -0.00022 [-0.00206, +0.00168] | -0.00051 | -0.00935 | non distinguibile dal rumore |
| 40 | +0.00171 | -0.00101 [-0.00266, +0.00073] | +0.00023 [-0.00136, +0.00188] | -0.00028 | -0.00598 | non distinguibile dal rumore |
| 80 | +0.00197 | -0.00040 [-0.00169, +0.00095] | +0.00058 [-0.00073, +0.00195] | -0.00010 | -0.00342 | non distinguibile dal rumore |
| 160 | +0.00194 | +0.00002 [-0.00092, +0.00101] | +0.00076 [-0.00022, +0.00180] | +0.00003 | -0.00179 | non distinguibile dal rumore ← scelta |
| 320 | +0.00162 | +0.00022 [-0.00041, +0.00088] | +0.00074 [+0.00006, +0.00146] | +0.00008 | -0.00089 | non distinguibile dal rumore |

### N2: griglia di k

| k | Δ ll 1X2 validazione | Δ ll 1X2 held-out [IC a blocchi] | Δ ll O/U 2,5 held-out [IC] | Δ RPS held-out | Δ ll 1X2 2026/27 (descrittivo) | Verdetto |
|---:|---:|---|---|---:|---:|---|
| 10 | +0.00101 | -0.00110 [-0.00263, +0.00055] | -0.00024 [-0.00156, +0.00109] | -0.00036 | -0.00371 | non distinguibile dal rumore |
| 20 | +0.00115 | -0.00082 [-0.00221, +0.00069] | -0.00008 [-0.00131, +0.00116] | -0.00027 | -0.00267 | non distinguibile dal rumore |
| 40 | +0.00123 | -0.00053 [-0.00171, +0.00076] | +0.00010 [-0.00100, +0.00122] | -0.00017 | -0.00167 | non distinguibile dal rumore |
| 80 | +0.00121 | -0.00025 [-0.00118, +0.00077] | +0.00028 [-0.00065, +0.00122] | -0.00008 | -0.00092 | non distinguibile dal rumore |
| 160 | +0.00108 | -0.00004 [-0.00073, +0.00069] | +0.00039 [-0.00032, +0.00112] | -0.00001 | -0.00045 | non distinguibile dal rumore ← scelta |
| 320 | +0.00086 | +0.00007 [-0.00039, +0.00057] | +0.00040 [-0.00011, +0.00092] | +0.00002 | -0.00021 | non distinguibile dal rumore |

### Riepilogo delle configurazioni scelte in validazione

| Variante | k | Δ ll 1X2 held-out [IC] | Δ ll O/U 2,5 held-out [IC] | Δ RPS held-out | Δ O/U 1,5 | Δ O/U 3,5 | Δ BTTS | Verdetto |
|---|---:|---|---|---:|---:|---:|---:|---|
| N1 | 160 | +0.00002 [-0.00092, +0.00101] | +0.00076 [-0.00022, +0.00180] | +0.00003 | +0.00055 | +0.00133 | +0.00025 | non distinguibile dal rumore |
| N2 | 160 | -0.00004 [-0.00073, +0.00069] | +0.00039 [-0.00032, +0.00112] | -0.00001 | +0.00015 | +0.00016 | +0.00018 | non distinguibile dal rumore |

Δ ll 1X2 held-out per fase della stagione (configurazioni scelte):

| Variante | Prime 10 giornate | Resto |
|---|---:|---:|
| N1 | -0.00076 | +0.00032 |
| N2 | -0.00005 | -0.00004 |

## N2 — quante volte si sarebbe attivato

Filtro |z| > 2 per lato (z = (gol reali − previsti)/√previsti, sulle partite della stagione già giocate). «Quota attiva» = quota di partite della lega in quella stagione giocate con il filtro attivo (tra parentesi: solo dalla giornata 6, quando z non è più dominato dal caso); z finale = scarto a fine stagione; «prima attivazione» = data della prima partita con filtro attivo.

| Stagione | Lega | Partite | Casa: quota attiva (da g.6) | Casa: z finale | Casa: prima attivazione | Ospite: quota attiva (da g.6) | Ospite: z finale | Ospite: prima attivazione |
|---|---|---:|---|---:|---|---|---:|---|
| 2019/20 | Serie A | 380 | 0% (0%) | -1.10 | – | 21% (24%) | +2.15 | 2020-07-02 |
| 2019/20 | Premier League | 380 | 5% (6%) | -1.92 | 2020-03-08 | 0% (0%) | -1.11 | – |
| 2019/20 | Bundesliga | 306 | 0% (0%) | -1.59 | – | 25% (26%) | +2.45 | 2019-08-30 |
| 2019/20 | La Liga | 380 | 3% (3%) | -2.03 | 2020-07-19 | 58% (66%) | -2.72 | 2019-10-29 |
| 2019/20 | Ligue 1 | 279 | 0% (0%) | -0.18 | – | 46% (54%) | -1.96 | 2019-09-15 |
| 2020/21 | Serie A | 380 | 0% (0%) | -1.04 | – | 17% (19%) | +1.28 | 2020-10-31 |
| 2020/21 | Premier League | 380 | 57% (65%) | -3.51 | 2021-01-02 | 44% (38%) | +1.95 | 2020-09-19 |
| 2020/21 | Bundesliga | 306 | 2% (0%) | -0.06 | 2020-09-19 | 1% (0%) | +0.33 | 2020-09-20 |
| 2020/21 | La Liga | 380 | 30% (34%) | -1.91 | 2020-10-18 | 0% (0%) | +0.47 | – |
| 2020/21 | Ligue 1 | 380 | 19% (22%) | -2.04 | 2021-03-03 | 63% (72%) | +3.71 | 2020-12-06 |
| 2021/22 | Serie A | 380 | 1% (1%) | -1.86 | 2022-04-23 | 0% (0%) | +0.29 | – |
| 2021/22 | Premier League | 380 | 0% (0%) | -0.69 | – | 0% (0%) | +0.54 | – |
| 2021/22 | Bundesliga | 306 | 1% (1%) | +1.57 | 2022-02-27 | 0% (0%) | -0.41 | – |
| 2021/22 | La Liga | 380 | 0% (0%) | -0.51 | – | 3% (4%) | -1.50 | 2021-10-16 |
| 2021/22 | Ligue 1 | 380 | 0% (0%) | +1.32 | – | 0% (0%) | +0.51 | – |
| 2022/23 | Serie A | 380 | 40% (46%) | -2.40 | 2023-02-20 | 87% (94%) | -2.35 | 2022-08-30 |
| 2022/23 | Premier League | 380 | 4% (5%) | +0.80 | 2022-10-09 | 20% (23%) | -1.05 | 2022-10-22 |
| 2022/23 | Bundesliga | 306 | 58% (66%) | +2.67 | 2022-08-28 | 5% (3%) | -0.79 | 2022-08-06 |
| 2022/23 | La Liga | 380 | 0% (0%) | -0.47 | – | 3% (3%) | -2.04 | 2023-06-04 |
| 2022/23 | Ligue 1 | 380 | 0% (0%) | -1.04 | – | 49% (48%) | +1.07 | 2022-08-21 |
| 2023/24 | Serie A | 380 | 0% (0%) | -1.23 | – | 0% (0%) | -0.66 | – |
| 2023/24 | Premier League | 380 | 6% (6%) | +1.97 | 2024-05-06 | 32% (37%) | +2.29 | 2024-02-18 |
| 2023/24 | Bundesliga | 306 | 23% (21%) | +1.12 | 2023-08-26 | 0% (0%) | +0.07 | – |
| 2023/24 | La Liga | 380 | 3% (0%) | -0.74 | 2023-08-14 | 0% (0%) | -0.52 | – |
| 2023/24 | Ligue 1 | 306 | 25% (30%) | -1.90 | 2024-03-10 | 28% (33%) | -0.26 | 2023-11-24 |
| 2024/25 | Serie A | 380 | 23% (27%) | -2.94 | 2025-03-16 | 0% (0%) | +0.28 | – |
| 2024/25 | Premier League | 380 | 52% (56%) | -3.06 | 2024-09-15 | 0% (0%) | +0.57 | – |
| 2024/25 | Bundesliga | 306 | 0% (0%) | -1.37 | – | 9% (10%) | +1.41 | 2024-10-04 |
| 2024/25 | La Liga | 380 | 0% (0%) | -1.39 | – | 0% (0%) | -0.60 | – |
| 2024/25 | Ligue 1 | 306 | 0% (0%) | -0.83 | – | 2% (0%) | +0.61 | 2024-08-18 |
| 2025/26 | Serie A | 380 | 73% (84%) | -3.40 | 2025-10-20 | 0% (0%) | -0.96 | – |
| 2025/26 | Premier League | 380 | 0% (0%) | -1.06 | – | 0% (0%) | -1.50 | – |
| 2025/26 | Bundesliga | 306 | 0% (0%) | +1.45 | – | 5% (2%) | +1.21 | 2025-09-26 |
| 2025/26 | La Liga | 380 | 0% (0%) | +0.40 | – | 10% (11%) | -2.22 | 2026-04-24 |
| 2025/26 | Ligue 1 | 306 | 0% (0%) | -0.79 | – | 2% (2%) | -1.17 | 2025-08-29 |
| 2026/27 | Serie A | 98 | 0% (0%) | +0.83 | – | 16% (31%) | +2.37 | 2026-09-18 |
| 2026/27 | Premier League | 89 | 0% (0%) | -0.44 | – | 3% (0%) | -0.65 | 2026-08-23 |
| 2026/27 | Bundesliga | 72 | 88% (100%) | +2.64 | 2026-09-04 | 0% (0%) | -0.47 | – |
| 2026/27 | La Liga | 108 | 1% (0%) | +1.01 | 2026-08-17 | 0% (0%) | +0.42 | – |
| 2026/27 | Ligue 1 | 80 | 0% (0%) | +0.76 | – | 0% (0%) | -0.28 | – |

**Stagioni passate (2019/20-2025/26, 35 coppie lega-stagione):** attivazione in almeno una partita, lato casa 18/35, lato ospite 21/35; filtro attivo a fine stagione (|z finale| > 2), casa 8/35, ospite 8/35.


## Caso di studio: Serie A 2026/27 (98 partite giocate)

Simulazione walk-forward con parametri scelti in validazione (N1: k=160, N2: k=160). Il 2026/27 non entra in nessuna scelta.

| Modello | Log-loss 1X2 | Log-loss Over 2,5 | Pareggi previsti | Over 2,5 previsto | Gol previsti a partita | 1 previsto | 2 previsto |
|---|---:|---:|---:|---:|---:|---:|---:|
| v6 (baseline) | 0.8868 | 0.6731 | 24.4% | 52.3% | 2.78 | 43.2% | 32.3% |
| N1 (k=160) | 0.8896 | 0.6721 | 24.2% | 53.3% | 2.83 | 42.3% | 33.5% |
| N2 (k=160) | 0.8886 | 0.6723 | 24.3% | 52.7% | 2.80 | 42.9% | 32.8% |
| Mercato (chiusura media, senza margine; 98 partite 1X2, 98 Over/Under) | 0.8835 | 0.6725 | – | 52.9% | – | – | – |
| **Reale** | | | **16.3%** | **60.2%** | **3.15** | **48.0%** | **35.7%** |

**Sensibilità a k, Serie A 2026/27 (descrittiva: la scelta di k resta quella della validazione)**

| Variante | Log-loss 1X2 | Log-loss Over 2,5 | Pareggi previsti | Over 2,5 previsto | Gol previsti a partita |
|---|---:|---:|---:|---:|---:|
| N1, k=10 | 0.9021 | 0.6755 | 24.0% | 54.8% | 2.89 |
| N1, k=20 | 0.8987 | 0.6741 | 24.0% | 54.6% | 2.89 |
| N1, k=40 | 0.8951 | 0.6729 | 24.0% | 54.3% | 2.87 |
| N1, k=80 | 0.8919 | 0.6722 | 24.1% | 53.8% | 2.85 |
| N1, k=160 | 0.8896 | 0.6721 | 24.2% | 53.3% | 2.83 |
| N1, k=320 | 0.8882 | 0.6723 | 24.3% | 52.9% | 2.81 |
| N2, k=10 | 0.8927 | 0.6716 | 24.2% | 53.3% | 2.83 |
| N2, k=20 | 0.8919 | 0.6716 | 24.2% | 53.2% | 2.82 |
| N2, k=40 | 0.8909 | 0.6718 | 24.2% | 53.1% | 2.82 |
| N2, k=80 | 0.8897 | 0.6720 | 24.3% | 52.9% | 2.81 |
| N2, k=160 | 0.8886 | 0.6723 | 24.3% | 52.7% | 2.80 |
| N2, k=320 | 0.8878 | 0.6725 | 24.4% | 52.5% | 2.79 |
| Oracolo a posteriori (R casa 1.07, R ospite 1.21: non utilizzabile) | 0.8821 | 0.6640 | 22.5% | 60.6% | 3.15 |

Andamento di R e z della Serie A 2026/27 (N1, k=160) all'inizio di ogni giornata (valori usati per prevedere le partite di quella giornata):

| Giornata | Partite già giocate | R casa | R ospite | z casa | z ospite | Filtro N2 attivo (casa / ospite) |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 0 | 1.000 | 1.000 | +0.00 | +0.00 | no / no |
| 2 | 10 | 0.988 | 0.997 | -0.76 | -0.18 | no / no |
| 3 | 20 | 0.974 | 1.006 | -1.30 | +0.27 | no / no |
| 4 | 30 | 0.978 | 1.030 | -0.92 | +1.15 | no / no |
| 5 | 40 | 0.993 | 1.058 | -0.28 | +2.00 | no / sì |
| 6 | 50 | 0.994 | 1.040 | -0.21 | +1.31 | no / no |
| 7 | 60 | 1.002 | 1.023 | +0.08 | +0.71 | no / no |
| 8 | 70 | 1.006 | 1.043 | +0.20 | +1.31 | no / no |
| 9 | 80 | 1.007 | 1.057 | +0.25 | +1.69 | no / no |
| 10 | 90 | 1.021 | 1.083 | +0.67 | +2.45 | no / sì |

**Tutte le leghe, 2026/27** (parametri scelti in validazione):

| Lega | Partite | Gol reali | Gol previsti v6 | N1 | N2 | Δ ll 1X2 v6 − N1 | Δ ll 1X2 v6 − N2 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Serie A | 98 | 3.15 | 2.78 | 2.83 | 2.80 | -0.00282 | -0.00181 |
| Premier League | 89 | 2.72 | 2.86 | 2.86 | 2.86 | -0.00255 | +0.00039 |
| Bundesliga | 72 | 3.50 | 3.16 | 3.26 | 3.26 | -0.00113 | -0.00073 |
| La Liga | 108 | 3.01 | 2.84 | 2.89 | 2.84 | -0.00035 | -0.00007 |
| Ligue 1 | 80 | 3.05 | 2.98 | 2.97 | 2.98 | -0.00221 | +0.00000 |


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


## N3 — effetto arbitro dei gialli con peso sulla stagione in corso

Controllo: il ricalcolo con peso uniforme riproduce `ref_logR` di produzione (scarto massimo 0.0e+00). Pesi decrescenti w = 0,5^(giorni/(365·h)) sulle partite passate dell'arbitro; k = 20. Modello dei gialli senza livello stagionale (per isolare l'effetto). Δ = produzione − variante.

| h (anni) | Δ ll totale validazione | Δ totale held-out [IC a blocchi] | Δ per squadra held-out | Δ totale 2026/27 (descrittivo) | Verdetto |
|---:|---:|---|---:|---:|---|
| 0.5 | +0.00610 | +0.00297 [+0.00007, +0.00590] | +0.00146 | -0.00385 | migliora ← scelta |
| 1.0 | +0.00460 | +0.00370 [+0.00164, +0.00579] | +0.00180 | -0.00114 | migliora |
| 2.0 | +0.00281 | +0.00315 [+0.00190, +0.00446] | +0.00153 | +0.00090 | migliora |


## Tabella riassuntiva

| Esperimento | Configurazione (validazione) | Δ held-out 2022/23-2025/26 [IC a blocchi] | Verdetto |
|---|---|---|---|
| N1 — livello di stagione bayesiano, gol | k = 160 | log-loss 1X2 +0,00002 [−0,00092, +0,00101]; Over/Under 2,5 +0,00076 [−0,00022, +0,00180] | non distinguibile dal rumore |
| N2 — N1 con filtro a 2 errori standard | k = 160 | log-loss 1X2 −0,00004 [−0,00073, +0,00069]; Over/Under 2,5 +0,00039 [−0,00032, +0,00112] | non distinguibile dal rumore |
| N3 falli — livello di stagione al posto di quello di produzione (A1/A2) | k = 80 | −0,00295 [−0,00496, −0,00100] / −0,00400 [−0,00621, −0,00178] | peggiora |
| N3 falli — sopra quello di produzione (B1/B2) | k = 320 | −0,00022 [−0,00063, +0,00018] / −0,00004 [−0,00009, +0,00001] | non distinguibile dal rumore |
| N3 gialli — A1/A2 | k = 80 / 160 | −0,00444 [−0,00648, −0,00245] / −0,00665 [−0,00928, −0,00401] | peggiora |
| N3 gialli — B1/B2 | k = 320 | −0,00049 [−0,00097, −0,00003] / +0,00001 [−0,00015, +0,00018] | peggiora / rumore |
| N3 tiri (k separati casa/ospite) — A1/A2/B1/B2 | (160, 320) / (320, 160) / (320, 320) / (320, 320) | +0,00015 / −0,00045 / −0,00041 / −0,00019, tutti con IC che include lo zero | non distinguibile dal rumore |
| N3 gialli — effetto arbitro con peso sulla stagione in corso | h = 0,5 anni (tutti gli h migliorano) | +0,00297 [+0,00007, +0,00590] (h = 1: +0,00370 [+0,00164, +0,00579]; h = 2: +0,00315 [+0,00190, +0,00446]) | migliora (modesto) |

## Commento

1. **N1 e N2 non migliorano e non vanno messi in produzione.** Il k scelto in validazione è 160 (guadagno in validazione +0,0019 per N1, +0,0011 per N2), ma l'held-out lo azzera: +0,00002 per N1, −0,00004 per N2, con IC larghi intorno allo zero. Con k piccolo (adattamento rapido, 10-20 pseudo-partite) il livello di stagione **peggiora** nettamente la log-loss 1X2 (k = 10: −0,0025 [−0,0048, −0,0002]), e nelle prime 10 giornate N1 perde −0,0008 mentre nel resto guadagna +0,0003: la stima di inizio stagione è soprattutto rumore. In altre parole il livello di una lega nel corso di una stagione si muove poco rispetto a quanto fa la differenza tra partite, e non c'è un k che permetta di adattarsi in fretta senza pagare nelle stagioni normali.
2. **Quante volte N2 si sarebbe attivato.** Su 35 coppie lega-stagione (2019/20-2025/26) il filtro |z| > 2 si attiva in almeno una partita nel 51% dei casi sul lato casa (18/35) e nel 60% sul lato ospite (21/35) e a fine stagione è attivo in 8/35 per lato: non è un evento raro, perché il livello di gol di una lega varia da una stagione all'altra più di quanto spieghi il solo errore di Poisson (z = scarto/√previsti ignora il rumore del modello). Nel 2020/21 a porte chiuse il filtro rileva il calo dei gol in casa della Premier League (z finale −3,51, attivo dal 2/1/2021 e sul 57% delle partite), il lato ospite della Ligue 1 (+3,71, dal 6/12/2020), e a tratti La Liga in casa (−1,91, attivo sul 30% delle partite dal 18/10/2020); in Serie A e Bundesliga non si attiva (casa −1,04 e −0,06). Altri casi: Serie A 2022/23 (entrambi i lati), Bundesliga 2022/23 in casa (+2,67 dall'agosto 2022), Premier 2024/25 in casa (−3,06), Serie A 2025/26 in casa (−3,40). Nel 2026/27 si attiva la Bundesliga in casa (z +2,64, dal 4/9/2026: 88% delle partite) e la Serie A sul lato ospite (+2,37, dal 18/9/2026: 16% delle partite); la Serie A in casa non è anomala (+0,83). Tuttavia, nei cambiamenti passati, scattare e correggere non ha dato un guadagno misurabile (N2 held-out ≈ 0).
3. **Caso di studio: Serie A 2026/27 (98 partite, nessun parametro scelto qui).** Gol reali 3,15 contro 2,78 previsti dal modello attuale; pareggi reali 16,3% contro 24,4%; vittorie in casa 48,0% (previste 43,2%) e in trasferta 35,7% (32,3%); Over 2,5 reale 60,2% (previsto 52,3%). Log-loss 1X2: modello 0,8868, mercato 0,8835, N1 0,8896, N2 0,8886; Over 2,5: modello 0,6731, mercato 0,6725, N1 0,6721, N2 0,6723. Il mercato ha mancato come il modello: i suoi prezzi di chiusura implicano Over 2,5 al 52,9% (reale 60,2%), e sul 1X2 il modello è a 0,0033 dal mercato. Il livello bayesiano con il k validato (160) sposta i gol previsti da 2,78 a 2,83 (N1) o 2,80 (N2): quasi nulla, perché il peso di un campione di 98 partite contro 160 pseudo-partite è piccolo; con k più basso i gol previsti salgono fino a 2,89 ma la log-loss 1X2 della Serie A **peggiora** (k = 10: 0,9021) perché il livello in più viene dal lato ospite (+21% a posteriori) mentre gli esiti hanno premiato le squadre in casa. Anche con il livello «oracolo» (R casa 1,07, R ospite 1,21 calcolati a posteriori sulle stesse 98 partite, non utilizzabile) i pareggi previsti scendono solo al 22,5% e la log-loss 1X2 migliora di appena 0,005 (0,8821); quella dell'Over 2,5 di 0,009 (0,6640). Il 16,3% di pareggi è circa 1,9 errori standard sotto il 24,4% previsto (errore standard 4,3 punti con 98 partite): i dati della stagione in corso sono ancora troppo pochi per distinguere un cambio di regime da una serie fortunata. Andamento di N1: R ospite sale da 1,000 a 1,083 e R casa da 0,974-0,988 a 1,021 in dieci giornate.
4. **N3: le statistiche non hanno bisogno di un livello di stagione in più.** Sostituire il livello multi-stagionale di produzione con quello di stagione peggiora falli e gialli in modo netto (falli −0,0030, gialli −0,0044 con N1; di più con il filtro), e sommarlo a quello di produzione non porta nulla (il k scelto è il massimo della griglia, cioè «nessuna correzione»; gialli B1 −0,0005 con IC che esclude lo zero). Per i tiri, con k diversi per casa e ospite (160 e 320 per A1), nessuna variante migliora: Δ held-out tra −0,0005 e +0,0002 con IC che includono lo zero. La separazione casa/ospite del livello dei tiri non aggiunge informazione rispetto al livello di produzione, che già ha moltiplicatori distinti per i due lati. (Round 9: vedi sotto.)
5. **Effetto arbitro con più peso sulla stagione in corso: migliora, ma poco.** Con pesi decrescenti nel tempo sulle partite passate dell'arbitro la log-loss del totale dei gialli migliora in tutte e tre le scelte (h = 0,5, 1, 2 anni): in validazione +0,0061, +0,0046, +0,0028; sull'held-out +0,0030, +0,0037, +0,0032, con IC a blocchi che esclude lo zero. È circa un terzo dell'effetto totale dell'arbitro (+0,0104 nel round 5-7). La regola di scelta in validazione dà h = 0,5; sull'held-out h = 1 è leggermente meglio, ma non lo si usa per scegliere. Sul 2026/27 (descrittivo, 447 partite) h = 0,5 e h = 1 sono a −0,0039 e −0,0011 e h = 2 a +0,0009: nulla di statisticamente leggibile. Proposta: candidato a un cambio di produzione con h = 1 anno (stabile in tutte le finestre) o con il valore validato h = 0,5, a tua scelta; non l'ho implementato.
6. **Dati e limiti.** Understat non era raggiungibile durante l'esecuzione: il contesto dei dati usa la cache degli xG (aggiornata al 25/10) per le partite successive, quindi le previsioni del modello 1X2 per le partite giocate tra il 26/10 e il 1/11 usano forze xG meno aggiornate (effetto atteso piccolo). Il 2026/27 non entra in nessuna scelta: validazione 2019/20-2021/22 e held-out 2022/23-2025/26 sono separati dalla stagione in corso.

## Round 9 (livello casa/ospite dei tiri)
Un round 9 separato **non è stato eseguito**: nel commento del round 8 avevo solo suggerito di provare un livello dei tiri con parametri propri per casa e ospite (perché i tiri degli ospiti in Serie A 2026/27 sono +18% sul previsto), ma nessuna richiesta lo ha avviato. Nel round 10 ho incluso la parte che ti serve per N3 (k separati per casa e ospite del livello di stagione dei tiri, 36 combinazioni scelte in validazione): non migliora (vedi tabella). Il livello multi-stagionale di produzione per i tiri ha già moltiplicatori distinti per casa e ospite ma gli stessi (H, k) per i due lati; una variante con (H, k) diversi per lato nel livello di produzione resta da fare come round a sé, se vuoi.

---

## Decisione e messa in produzione (s6-arbitro-decay)

Decisioni: nessuna correzione del livello dei gol (N1/N2/N3 non vanno in produzione, round 9 non necessario); in produzione l'effetto arbitro dei gialli con decadimento h = 0,5 anni (emivita 182,5 giorni, scelta di validazione); falli invariati. `STATS_VERSION = "s6-arbitro-decay"`, `MODEL_VERSION` invariata.


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
