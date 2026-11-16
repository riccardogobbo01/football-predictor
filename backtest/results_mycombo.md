# MyCombo — validazione walk-forward (stagioni 2022/23-2025/26)

Protocollo scritto prima dell'esecuzione: `backtest/mycombo_parts/prereg.md` (qui sotto, in fondo). Scarto = frequenza reale − probabilità prevista, in punti percentuali, IC 95 % a blocchi per settimana ISO.

## Esito della regola di arresto (5 punti): **SUPERATA**

Scarto complessivo +0.2 pp; fasce con almeno 300 combo: 1/3-0,375 (quota 2,67-3,0) +0.1; 0,375-0,417 (2,4-2,67) +0.1; 0,417-0,458 (2,18-2,4) +1.8.
Nessun sottogruppo (≥ 300 combo) con scarto > 3 punti e IC che esclude zero.


**21243 combo proposte su 7081 partite** (3.00 per partita; numero di giocate: 3: 16264, 4: 4768, 5: 211).

## Sintesi

- **La regola di arresto non scatta**: la probabilità congiunta delle combo proposte è calibrata. Nelle stagioni 2022/23-2025/26 (7.081 partite, 21.243 combo, tutte fuori campione) la probabilità prevista media è 36.7% e la frequenza reale 36.9% (scarto +0.2 punti, IC a blocchi [-0.6; +1.0]). Nessuna fascia di probabilità con almeno 300 combo oltre 2 punti; la fascia più alta (quota equa 2,0-2,18, solo 286 combo) è a +3,7 punti con IC [−1,9; +9,2].
- **Le correlazioni contano molto e il modello le coglie**: calcolando la combo «come se le giocate fossero indipendenti» la probabilità sarebbe 25.7%, contro il 36.9% reale. Il rapporto tra probabilità congiunta e prodotto delle singole è mediamente 1,45; la calibrazione tiene in tutte le fasce di questo rapporto (anche oltre 1,5).
- **Cosa NON era già stimato**: nel repository esisteva solo la copula tra casa e ospite della stessa statistica (tiri, corner, gialli). Le dipendenze tra statistiche diverse e tra gol e statistiche sono state stimate qui sui residui fuori campione: tiri-tiri in porta ≈ +0,6, tiri-corner ≈ +0,44, gol-tiri in porta della stessa squadra ≈ +0,46, falli-gialli ≈ +0,31; l'effetto «stato di gara» tra squadre (gol di una squadra contro tiri o corner dell'altra) è piccolo (|r| ≤ 0,10).
- **Limiti**: (1) le singole giocate sul totale gol sono leggermente ottimiste (Over: −1,2 punti, IC [−2,2; −0,2]); (2) corner e gialli restano «indicativi» (definizione delle quote e conteggio dei rossi variano da bookmaker); (3) nella stagione 2026/27, solo 447 partite finora, La Liga (+7,4) e Bundesliga (+5,1) mostrano scarti oltre 5 punti con IC che esclude zero: è un campione corto e non fa parte del criterio, ma viene seguito dal registro a carta; (4) il test usa la regola di selezione dell'algoritmo, quindi misura anche l'effetto della selezione (nessuna distorsione visibile); (5) non c'è nessuna quota di bookmaker: la calibrazione non dice nulla sul valore rispetto a Sisal.

## 1. Calibrazione della probabilità congiunta

| Insieme | N combo | % prevista | % reale | scarto (pp) [IC blocchi] | % «come se indipendenti» |
|---|---|---|---|---|---|
| Tutte le combo | 21243 | 36.7 | 36.9 | +0.2 [-0.6; +1.0] | 25.7 |

**Per fascia di probabilità prevista (quota equa):**

| Fascia | N | % prevista | % reale | scarto (pp) [IC] | % indipendenti |
|---|---|---|---|---|---|
| 1/3-0,375 (quota 2,67-3,0) | 14768 | 35.0 | 35.1 | +0.1 [-0.8; +0.9] | 24.8 |
| 0,375-0,417 (2,4-2,67) | 4747 | 39.2 | 39.2 | +0.1 [-1.5; +1.6] | 27.2 |
| 0,417-0,458 (2,18-2,4) | 1442 | 43.3 | 45.1 | +1.8 [-0.9; +4.4] | 29.3 |
| 0,458-0,5 (2,0-2,18) | 286 | 47.0 | 50.7 | +3.7 [-1.9; +9.2] | 32.2 |

**Per numero di giocate:**

| Combo | N | % prevista | % reale | scarto (pp) [IC] | % indipendenti |
|---|---|---|---|---|---|
| 3 giocate | 16264 | 36.9 | 37.1 | +0.1 [-0.7; +1.0] | 25.1 |
| 4 giocate | 4768 | 35.9 | 36.3 | +0.4 [-1.0; +1.8] | 27.7 |
| 5 giocate | 211 | 36.0 | 37.4 | +1.4 [-4.8; +7.5] | 29.8 |

**Per stagione:**

| Stagione | N | % prevista | % reale | scarto (pp) [IC] | % indipendenti |
|---|---|---|---|---|---|
| 2022/23 | 5478 | 36.6 | 37.2 | +0.6 [-0.7; +2.0] | 25.6 |
| 2023/24 | 5256 | 36.6 | 37.3 | +0.6 [-1.2; +2.4] | 25.7 |
| 2024/25 | 5253 | 36.7 | 36.3 | -0.4 [-2.3; +1.3] | 25.8 |
| 2025/26 | 5256 | 36.7 | 36.8 | +0.1 [-1.3; +1.5] | 25.8 |

**Per lega:**

| Lega | N | % prevista | % reale | scarto (pp) [IC] | % indipendenti |
|---|---|---|---|---|---|
| Serie A | 4560 | 36.4 | 35.2 | -1.1 [-2.5; +0.3] | 25.5 |
| Premier League | 4560 | 36.9 | 37.4 | +0.5 [-1.4; +2.2] | 25.8 |
| Bundesliga | 3669 | 37.0 | 39.0 | +2.0 [+0.0; +4.0] | 25.9 |
| La Liga | 4560 | 36.5 | 36.9 | +0.4 [-0.9; +1.7] | 25.7 |
| Ligue 1 | 3894 | 36.7 | 36.3 | -0.4 [-2.0; +1.3] | 25.7 |

**Per tipo di giocate:**

| Combo | N | % prevista | % reale | scarto (pp) [IC] | % indipendenti |
|---|---|---|---|---|---|
| senza statistiche (solo gol e primo tempo) | 6488 | 38.1 | 38.7 | +0.5 [-0.9; +1.9] | 23.6 |
| con almeno una statistica (tiri, tiri in porta, corner, gialli) | 14755 | 36.0 | 36.1 | +0.1 [-0.8; +1.0] | 26.7 |
| con corner (indicativi) | 713 | 35.2 | 36.2 | +1.0 [-2.7; +4.5] | 28.0 |
| con gialli | 1332 | 35.6 | 36.7 | +1.2 [-1.2; +3.7] | 29.4 |

**Per quanto contano le correlazioni (rapporto tra probabilità congiunta e prodotto delle singole):**

| Rapporto | N | % prevista | % reale | scarto (pp) [IC] | % indipendenti |
|---|---|---|---|---|---|
| p congiunta / p indipendenti in (0.8, 1.0] | 7 | 34.0 | 28.6 | -5.4 [-34.3; +23.5] | 36.7 |
| p congiunta / p indipendenti in (1.0, 1.25] | 2587 | 36.1 | 36.6 | +0.5 [-1.5; +2.7] | 30.4 |
| p congiunta / p indipendenti in (1.25, 1.5] | 12394 | 36.4 | 36.7 | +0.3 [-0.6; +1.3] | 26.5 |
| p congiunta / p indipendenti in (1.5, 100.0] | 6255 | 37.4 | 37.3 | -0.1 [-1.4; +1.2] | 22.2 |

Rapporto medio probabilità congiunta / prodotto delle singole: 1.45 (mediana 1.41). Frequenza reale: 36.9 %; prevista dal modello: 36.7 %; prevista «come se fossero indipendenti»: 25.7 %.

## 2. Calibrazione delle singole giocate del catalogo (tutte le partite, non solo le giocate proposte; solo giocate «positive»: Over, esiti, Gol)

| Famiglia | N giocate | % prevista | % reale | scarto (pp) [IC] |
|---|---|---|---|---|
| btts | 7081 | 54.0 | 54.6 | +0.6 [-0.6; +1.8] |
| corner_t | 21243 | 47.3 | 46.9 | -0.4 [-1.5; +0.7] |
| gialli_t | 21243 | 47.1 | 47.1 | +0.0 [-1.0; +1.0] |
| gtot | 21243 | 55.1 | 53.9 | -1.2 [-2.2; -0.2] |
| htou | 14162 | 53.7 | 53.7 | -0.1 [-1.0; +0.9] |
| htres | 21243 | 33.3 | 33.3 | -0.0 [-0.0; +0.0] |
| res | 21243 | 33.3 | 33.3 | -0.0 [-0.0; +0.0] |
| sot_c | 21243 | 47.0 | 46.9 | -0.1 [-1.2; +1.0] |
| sot_o | 21243 | 46.9 | 46.2 | -0.7 [-1.7; +0.4] |
| tiri_c | 21243 | 47.3 | 47.7 | +0.4 [-0.7; +1.5] |
| tiri_o | 21243 | 47.0 | 46.8 | -0.2 [-1.2; +0.8] |

**Per fascia di probabilità della singola giocata:**

| Fascia | N | % prevista | % reale | scarto (pp) [IC] |
|---|---|---|---|---|
| (-0.001, 0.2] | 7095 | 15.1 | 14.2 | -0.9 [-1.9; +0.1] |
| (0.2, 0.35] | 48469 | 28.7 | 27.9 | -0.8 [-1.2; -0.4] |
| (0.35, 0.5] | 74527 | 42.2 | 42.2 | -0.0 [-0.5; +0.4] |
| (0.5, 0.65] | 56031 | 56.7 | 56.7 | -0.0 [-0.6; +0.6] |
| (0.65, 0.8] | 23226 | 71.3 | 71.6 | +0.3 [-0.4; +1.0] |
| (0.8, 1.0] | 3082 | 83.6 | 83.5 | -0.1 [-1.5; +1.4] |

## Stagione 2026/27 in corso (descrittiva, mai usata per scegliere nulla)

447 partite, 1341 combo.

| Insieme | N | % prevista | % reale | scarto (pp) [IC] | % indipendenti |
|---|---|---|---|---|---|
| 2026/27 (tutte le leghe) | 1341 | 36.7 | 38.4 | +1.7 [-1.8; +4.8] | 25.8 |
| Serie A | 294 | 36.5 | 37.8 | +1.3 [-6.1; +8.2] | 25.9 |
| Premier League | 267 | 36.9 | 32.6 | -4.3 [-10.6; +1.3] | 26.0 |
| Bundesliga | 216 | 37.0 | 42.1 | +5.1 [+1.8; +8.0] | 25.7 |
| La Liga | 324 | 36.7 | 44.1 | +7.4 [+3.6; +11.7] | 25.9 |
| Ligue 1 | 240 | 36.6 | 34.6 | -2.1 [-8.4; +4.4] | 25.5 |

## 3. Matrice di correlazione dei punteggi normali (tutte le stagioni 2019/20-2026/27 fuori campione)

|  | gol_c | gol_o | tiri_c | tiri_o | sot_c | sot_o | corner_c | corner_o | gialli_c | gialli_o | falli_c | falli_o |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gol_c | +1.00 | +0.02 | +0.13 | +0.03 | +0.46 | +0.02 | -0.10 | +0.05 | -0.04 | +0.01 | -0.00 | -0.04 |
| gol_o | +0.02 | +1.00 | +0.06 | +0.18 | +0.02 | +0.47 | +0.06 | -0.06 | +0.05 | +0.01 | -0.03 | +0.01 |
| tiri_c | +0.13 | +0.06 | +1.00 | -0.21 | +0.58 | -0.07 | +0.44 | -0.22 | -0.05 | +0.02 | -0.07 | -0.06 |
| tiri_o | +0.03 | +0.18 | -0.21 | +1.00 | -0.08 | +0.60 | -0.19 | +0.44 | +0.04 | -0.06 | -0.04 | -0.06 |
| sot_c | +0.46 | +0.02 | +0.58 | -0.08 | +1.00 | -0.04 | +0.20 | -0.08 | -0.04 | +0.02 | -0.04 | -0.06 |
| sot_o | +0.02 | +0.47 | -0.07 | +0.60 | -0.04 | +1.00 | -0.07 | +0.20 | +0.03 | -0.04 | -0.04 | -0.04 |
| corner_c | -0.10 | +0.06 | +0.44 | -0.19 | +0.20 | -0.07 | +1.00 | -0.20 | -0.01 | +0.00 | -0.06 | -0.06 |
| corner_o | +0.05 | -0.06 | -0.22 | +0.44 | -0.08 | +0.20 | -0.20 | +1.00 | +0.01 | -0.04 | -0.05 | -0.06 |
| gialli_c | -0.04 | +0.05 | -0.05 | +0.04 | -0.04 | +0.03 | -0.01 | +0.01 | +1.00 | +0.16 | +0.31 | +0.07 |
| gialli_o | +0.01 | +0.01 | +0.02 | -0.06 | +0.02 | -0.04 | +0.00 | -0.04 | +0.16 | +1.00 | +0.06 | +0.32 |
| falli_c | -0.00 | -0.03 | -0.07 | -0.04 | -0.04 | -0.04 | -0.06 | -0.05 | +0.31 | +0.06 | +1.00 | +0.06 |
| falli_o | -0.04 | +0.01 | -0.06 | -0.06 | -0.06 | -0.04 | -0.06 | -0.06 | +0.07 | +0.32 | +0.06 | +1.00 |

Stimata su 12905 partite. Confronto con la copula casa-ospite già in produzione (rho): tiri −0,16/−0,24 per lega (matrice: -0.21), corner −0,20 (-0.20), gialli +0,17 (+0.16).

---

# Protocollo (prereg)

# MyCombo — protocollo di validazione (scritto prima di eseguire il backtest)

**Obiettivo.** Verificare, prima di pubblicare qualsiasi cosa, che la probabilità congiunta delle combo proposte dall'algoritmo sia calibrata: stesse combo che il sito proporrebbe, calcolate fuori campione, confrontate con ciò che è successo davvero. **Regola di arresto: se la calibrazione è fuori di oltre 5 punti percentuali, non si pubblica.**

## Cosa si valida
Il codice di produzione `predictions/mycombo.py` (simulazione di 20.000 scenari per partita, generazione delle combo) applicato a ogni partita di test con i soli dati disponibili prima della partita:
- **Gol**: matrice di Dixon-Coles dello stack v6 (walk-forward per stagione, come in tutti i round).
- **Statistiche** (tiri, tiri in porta, corner, gialli, falli): modelli `stats_v3` walk-forward per stagione, con il livello stagionale di produzione (`config.LEVEL_PARAMS`) e l'effetto arbitro sui gialli (già nei modelli); dispersione per squadra stimata sul training del fold.
- **Primo tempo**: quota dei gol del primo tempo per lega, stimata sulle sole stagioni precedenti.
- **Dipendenze**: nel repository esiste solo la copula tra casa e ospite della stessa statistica. Le dipendenze **tra statistiche diverse e tra gol e statistiche («stato di gara») non erano stimate**: si stimano qui. Matrice di correlazione 12×12 dei punteggi normali (PIT randomizzata) dei residui delle previsioni fuori campione delle 12 variabili (gol, tiri, tiri in porta, corner, gialli, falli × casa/ospite); per la stagione di test s si usano le sole stagioni 2019/20…s−1.
- **Giocate ammesse**: 1X2, doppia chance, Over/Under gol 1,5/2,5/3,5, gol/no gol, 1X2 e Over 0,5/1,5 del primo tempo, Over/Under tiri e tiri in porta per squadra, Over/Under gialli totali, Over/Under corner totali. Linee delle statistiche intorno alla media attesa (tre linee x,5 per lato).
- **Algoritmo** (fissato, nessun parametro viene scelto sui risultati): 12.000 combo candidate per partita (2.000 da 3, 4.000 da 4 e 6.000 da 5 giocate; famiglie diverse, una sola giocata per famiglia, giocate più probabili campionate più spesso); quota equa = 1/probabilità congiunta tra 2,0 e 3,0 (probabilità tra 1/3 e 1/2); giocate ridondanti escluse (se la meno probabile implica l'altra in almeno il 97 % degli scenari); punteggio = |ln(p congiunta / prodotto delle p singole)| / (giocate − 1), cioè quanto contano le correlazioni; fino a 3 combo per partita: prima la migliore per ciascun numero di giocate (3, 4, 5) quando esiste, poi le migliori restanti; due combo della stessa partita condividono al più una giocata. (Prima versione dell'algoritmo, abbandonata prima di vedere qualunque calibrazione: proponeva solo combo da 3 giocate.)

## Insiemi
Test: **2022/23, 2023/24, 2024/25, 2025/26** (tutte le partite dei 5 campionati con dati completi). 2026/27 (in corso) a parte, descrittivo. Nessun parametro dell'algoritmo è stato scelto guardando queste stagioni.

## Misure
1. **Calibrazione della probabilità congiunta**: probabilità prevista media contro frequenza reale di vincita delle combo proposte, complessiva e per fascia di probabilità prevista (1/3-0,375, 0,375-0,417, 0,417-0,458, 0,458-0,5), per numero di giocate (3, 4, 5), per stagione, per lega, per presenza di corner/gialli (indicativi). Scarto = frequenza reale − prevista, con IC 95 % a blocchi per settimana ISO (le combo della stessa partita e della stessa settimana non sono indipendenti).
2. **Confronto con «come se fossero indipendenti»**: frequenza reale contro il prodotto delle probabilità singole (per mostrare quanto contano le correlazioni e se il modello le coglie).
3. **Calibrazione delle singole giocate** (tutte le giocate del catalogo, non solo quelle proposte), per famiglia (risultato, totale gol, gol/no gol, primo tempo, tiri, tiri in porta, corner, gialli) e per fascia di probabilità: serve a trovare l'origine di un'eventuale scalibratura.
4. **Esito sui singoli segmenti**: per ogni combo la frequenza con cui ogni giocata, a sé, si è verificata (diagnostica).

## Criterio di arresto
Si guarda la calibrazione sulle combo proposte nel test 2022/23-2025/26:
- **ARRESTO** se lo scarto complessivo (reale − previsto) supera 5 punti in valore assoluto, oppure se qualunque fascia di probabilità prevista con almeno 300 combo supera 5 punti in valore assoluto.
- Se lo scarto complessivo è entro 5 punti ma l'IC di una fascia o di un sottogruppo con almeno 300 combo è chiaramente scostato (scarto > 3 punti con IC che esclude zero) lo si riporta nel resoconto e nella nota delle combo, senza arresto.
- In caso di arresto non si pubblica: si riporta l'origine (famiglia di giocate, numero di giocate, correlazioni) e si propongono le correzioni a parte, da validare di nuovo con lo stesso protocollo.
