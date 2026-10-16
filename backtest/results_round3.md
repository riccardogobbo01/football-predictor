# Round 3 — esperimenti sul modello dei campionati (solo backtest)

**Nulla della produzione è stato toccato.** Codice in `backtest/round3_*.py`, `backtest/run_round3_*.py`, `backtest/eloodds`-derivati solo in lettura, `backtest/transfermarkt.py` e `backtest/transfermarkt_aliases.py`. Stesse regole del round 2: stesse 12.751 partite per tutte le varianti, bootstrap appaiato con 5000 ricampionamenti, IC 95% percentile sia per partita sia a blocchi per settimana ISO.

---
## Criteri fissati PRIMA di calcolare i risultati

Questa sezione è stata scritta prima di eseguire qualsiasi variante del round 3 (il file `backtest/round3_parts/prereg.md` precede, per data di modifica, tutti i file di risultati). Cosa è stato guardato prima: solo la copertura e i nomi dei dati Transfermarkt (nessun esito di partita, nessuna log-loss).

**Baseline**: modello in produzione v6-eloodds, variante `with_xg`: stack Poisson con `XG_FEATURES + eo_diff` (Elo-Odds K=200, ripiego su quote pre-partita come in produzione), allenato stagione per stagione dal 2016/17, test dal 2019/20 al 2026-10-12 (12.751 partite con quote medie valide, le stesse del round 2).

**Divisione delle stagioni**
- Stagioni di **validazione**: 2019/20, 2020/21, 2021/22 (5.376 partite). Qui, e solo qui, si scelgono i parametri.
- Stagioni **fuori campione** (held-out): 2022/23 → 2026/27 (7.375 partite). Nessun parametro è scelto guardandole.
- Si riportano Δ log-loss sulle validazione, sulle held-out e su tutte (quest'ultimo numero include le stagioni usate per scegliere ed è quindi più ottimistico; serve per confronto col round 2).

**Regola di scelta dei parametri (uguale per tutti gli esperimenti)**: tra le configurazioni della griglia dichiarata sotto si sceglie quella con il Δ log-loss vs baseline più alto sulle sole stagioni di validazione; a parità entro 0.0002 vince la più semplice (meno parametri / più vicina al default). Le griglie sono quelle scritte qui: nessuna estensione dopo aver visto i risultati.

**Intervalli di confidenza**: bootstrap appaiato (5000 ricampionamenti, IC 95% percentile) sia per partita sia a blocchi per settimana ISO (tutte le leghe della stessa settimana restano insieme). Δ = log-loss(baseline) − log-loss(variante), positivo = variante migliore.

**Verdetto «migliora»**: Δ sulle held-out > 0 con IC 95% a blocchi per settimana che esclude lo zero. Per A (lunghezza del training) il bersaglio sono le prime stagioni di test: verdetto sul Δ su tutte le stagioni con IC a blocchi che esclude lo zero e senza peggioramento sulle held-out (Δ held-out ≥ −0.0005). Un Δ positivo con IC che include lo zero è «non distinguibile dal rumore».

**A — Lunghezza del training**
- Si riporta il numero di stagioni (e di partite) di training dello stack per ogni stagione di test.
- Griglia, ogni riga da sola vs baseline: **A1** xG con 12 mesi di riscaldamento (feature xG dal 2015-08-03) e stack allenato dal 2015/16; **A2** xG con 6 mesi di riscaldamento (dal 2015-02-02) e stack allenato dal 2014/15 sulle sole righe con xG; **A3** xG come baseline (24 mesi) e stack allenato dal 2013/14 con feature xG mancante gestita esplicitamente (xg_lmu, xg_lnu = dc_lmu, dc_lnu dove mancano, più un indicatore `xg_miss`); **A4** come A3 ma con xG a 6 mesi di riscaldamento. DC gol, tiri e Elo-Odds hanno già feature dal 2013/14; il DC xG usa le stesse impostazioni del baseline (xi=0.003, ridge 2, finestra 5 anni).
- Scelta: la variante con Δ più alto sulle validazione.

**B — Varianti di Elo-Odds** (una alla volta vs baseline; K=200 e le altre regole invariate dove non specificato)
- **B1** quote Pinnacle di chiusura (PSCH/PSCD/PSCA) al posto della media; dove Pinnacle manca (metà 2025/26, 2026/27) ripiego sulla chiusura media e poi sulle quote pre-partita. Nessun parametro libero.
- **B2** K separato per lega: griglia K ∈ {100, 150, 200, 300, 400}; si fa girare lo stack con K uguale per tutte le leghe per ogni valore della griglia e per ogni lega si sceglie il K con la log-loss di validazione più bassa su quella lega; poi un'unica corsa con i K scelti.
- **B3** rating separati casa/trasferta: ogni squadra ha un rating in casa e uno in trasferta; la feature è rating_casa(squadra di casa) − rating_trasferta(ospite); aggiornamento di entrambi con lo stesso errore S − E; il rating dell'altro campo si aggiorna con una frazione γ dell'errore. Griglia K ∈ {200, 300, 400} × γ ∈ {0, 0.5} (6 configurazioni), scelta sulle validazione. Due forme: **B3a** la feature sostituisce eo_diff; **B3b** si aggiunge a eo_diff (con i parametri scelti per B3a).

**C — Ordered logit di ricalibrazione** sopra il baseline: rifit settimanale sul passato, finestra espansiva, burn-in di 600 partite (identità), input x1 = log(λc/λo), x2 = λc + λo. Griglia: ordered logit semplice (4 parametri) e flessibile (banda del pareggio dipendente da x2 e x1², 6 parametri). Scelta sulle validazione. Solo se «migliora» (verdetto sopra) si applica alla matrice dei punteggi riscalando ogni cella per P_nuova/P_vecchia del suo esito e si controllano Over/Under, BTTS e punteggio consigliato.

**D — Valore della rosa Transfermarkt** (dataset dcaribou/transfermarkt-datasets, tabelle `player_valuations`, `clubs`, aggiornate al 2026-09-05)
- Valore di una squadra a una data di riferimento D = somma, sui giocatori con almeno una valutazione nella finestra, dell'ultima valutazione ≤ D, assegnata al club indicato in quella riga. Abbinamento dei nomi con tabella esplicita (`backtest/transfermarkt_aliases.py`), verificata per copertura.
- Una squadra è «non affidabile» se ha meno di 12 giocatori valutati (tipico delle neopromosse: la seconda divisione non è nel dataset). Per le non affidabili il valore è imputato con il minimo tra i club affidabili della stessa lega e stagione (regola fissa, non ottimizzata).
- Feature per partita: **F1** `tm_diff` = log(V_casa / media di lega) − log(V_ospite / media di lega), cioè log(V_casa/V_ospite); **F2** F1 più `tm_chg_diff` = variazione della posizione relativa (log valore relativo alla media di lega) rispetto alla stagione precedente, casa − ospite (0 se una delle due stagioni è «non affidabile»).
- Griglia (8 configurazioni): data D ∈ {1 luglio, 1 agosto} × finestra di valutazione ∈ {240, 365} giorni × {F1, F2}. Scelta sulle validazione.
- Si riporta il guadagno separatamente su tre sottoinsiemi che non si sovrappongono: (1) partite con almeno una neopromossa (squadra assente dallo stesso campionato nella stagione precedente); (2) restanti partite delle prime 8 giornate (entrambe le squadre con meno di 8 partite giocate nella stagione); (3) tutto il resto.
- Dati live non considerati (solo backtest).


## Esperimento A — Lunghezza del training dello stack

### Quante stagioni di training ha lo stack in ogni stagione di test (baseline)

Stack allenato dal 2016/17 sulle sole stagioni precedenti alla stagione di test (gli xG partono dal 2014/15 e il DC xG richiede 2 anni di storia: prima feature xG nell'estate 2016).

| Stagione di test | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Stagioni di training | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| Partite di training | 5478 | 7203 | 9029 | 10855 | 12681 | 14433 | 16185 | 17937 |

### Varianti (ogni riga da sola vs baseline)

| Variante | Log-loss | Δ tutte (IC per partita) | Δ tutte (IC a blocchi) | Δ validazione | Δ held-out (IC a blocchi) | Stagioni migliorate |
|---|---:|---|---|---:|---|---:|
| A1 — xG con 12 mesi di riscaldamento, training dal 2015/16 | 0.9796 | +0.00016 [-0.00009, +0.00041] | [-0.00008, +0.00041] | +0.00006 | +0.00023 [-0.00000, +0.00046] | 6/8 |
| A2 — xG con 6 mesi di riscaldamento, training dal 2014/15 | 0.9798 | +0.00001 [-0.00025, +0.00027] | [-0.00025, +0.00027] | -0.00035 | +0.00028 [+0.00003, +0.00053] | 5/8 |
| A3 — training dal 2013/14 con xG mancante gestito (imputazione + indicatore) | 0.9798 | -0.00004 [-0.00050, +0.00043] | [-0.00049, +0.00045] | -0.00072 | +0.00046 [-0.00011, +0.00104] | 4/8 |
| A4 — xG a 6 mesi + training dal 2013/14 con xG mancante gestito | 0.9800 | -0.00015 [-0.00061, +0.00031] | [-0.00061, +0.00033] | -0.00101 | +0.00048 [-0.00006, +0.00102] | 4/8 |

**Stagioni e partite di training per variante**

| Variante | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 3 (5478) | 4 (7203) | 5 (9029) | 6 (10855) | 7 (12681) | 8 (14433) | 9 (16185) | 10 (17937) |
| A1 | 4 (7304) | 5 (9029) | 6 (10855) | 7 (12681) | 8 (14507) | 9 (16259) | 10 (18011) | 11 (19763) |
| A2 | 5 (8090) | 6 (9815) | 7 (11641) | 8 (13467) | 9 (15293) | 10 (17045) | 11 (18797) | 12 (20549) |
| A3 | 6 (10956) | 7 (12681) | 8 (14507) | 9 (16333) | 10 (18159) | 11 (19911) | 12 (21663) | 13 (23415) |
| A4 | 6 (10956) | 7 (12681) | 8 (14507) | 9 (16333) | 10 (18159) | 11 (19911) | 12 (21663) | 13 (23415) |

(stagioni distinte con almeno una riga di training, e numero di righe)

**Guadagno per stagione (Δ log-loss, baseline − variante)**

| Variante | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A1 | +0.0002 | -0.0004 | +0.0005 | +0.0004 | +0.0002 | -0.0001 | +0.0003 | +0.0015 |
| A2 | -0.0004 | -0.0011 | +0.0005 | +0.0003 | +0.0004 | -0.0001 | +0.0003 | +0.0017 |
| A3 | -0.0006 | -0.0011 | -0.0005 | +0.0008 | +0.0006 | -0.0004 | +0.0008 | +0.0009 |
| A4 | -0.0010 | -0.0020 | -0.0000 | +0.0008 | +0.0006 | -0.0005 | +0.0007 | +0.0022 |

**Scelta (criterio: Δ più alto sulle validazione 2019/20-2021/22, parità entro 0.0002 → la più semplice): A1** (Δ validazione +0.00006). Verdetto (regola A del prereg): **non distinguibile dal rumore**.

**Dettaglio della variante scelta: A1 — xG con 12 mesi di riscaldamento, training dal 2015/16**

| Insieme | N | Δ log-loss | IC 95% per partita | IC 95% a blocchi per settimana |
|---|---:|---:|---|---|
| tutte le stagioni | 12751 | +0.00016 | [-0.00009, +0.00041] | [-0.00008, +0.00041] |
| validazione 2019/20-2021/22 | 5376 | +0.00006 | [-0.00043, +0.00055] | [-0.00043, +0.00054] |
| held-out 2022/23→ | 7375 | +0.00023 | [-0.00000, +0.00046] | [-0.00000, +0.00046] |

Log-loss 0.9796 (baseline 0.9798); Δ RPS +0.00005; Δ Brier +0.00012.

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0002 | -0.0004 | +0.0005 | +0.0004 | +0.0002 | -0.0001 | +0.0003 | +0.0015 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0006 | +0.0001 | +0.0001 | -0.0001 | +0.0001 |


## Esperimento B — Varianti di Elo-Odds

Controllo: la ricostruzione con le funzioni del round 3 (K=200, chiusura media) coincide con `eo_diff` di produzione (differenza massima < 1e-9).

### B1 — Pinnacle di chiusura al posto della media

Nelle partite di test Pinnacle (PSCH/PSCD/PSCA) è disponibile per il 91.0%; il resto ricade sulla chiusura media (per 2025/26 metà e 2026/27 tutto). Nessun parametro libero.

**B1 — Elo-Odds su quote Pinnacle di chiusura**

| Insieme | N | Δ log-loss | IC 95% per partita | IC 95% a blocchi per settimana |
|---|---:|---:|---|---|
| tutte le stagioni | 12751 | -0.00002 | [-0.00013, +0.00009] | [-0.00012, +0.00008] |
| validazione 2019/20-2021/22 | 5376 | -0.00008 | [-0.00025, +0.00010] | [-0.00024, +0.00009] |
| held-out 2022/23→ | 7375 | +0.00002 | [-0.00012, +0.00016] | [-0.00011, +0.00015] |

Log-loss 0.9798 (baseline 0.9798); Δ RPS -0.00001; Δ Brier -0.00002.

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0001 | +0.0001 | -0.0002 | +0.0001 | +0.0000 | -0.0000 | +0.0000 | +0.0001 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0001 | -0.0000 | +0.0002 | -0.0002 | +0.0001 |

### B2 — K separato per lega

Log-loss sulle sole stagioni di validazione, per lega e K uniforme (stack completo ogni volta):

| Lega | K=100 | K=150 | K=200 | K=300 | K=400 | K scelto |
|---|---:|---:|---:|---:|---:|---:|
| Serie A | 0.9664 | 0.9654 | 0.9647 | 0.9640 | 0.9640 | **300** |
| Premier League | 0.9772 | 0.9770 | 0.9770 | 0.9774 | 0.9779 | **200** |
| Bundesliga | 0.9916 | 0.9916 | 0.9916 | 0.9921 | 0.9929 | **200** |
| La Liga | 0.9951 | 0.9955 | 0.9957 | 0.9961 | 0.9967 | **100** |
| Ligue 1 | 1.0064 | 1.0070 | 1.0074 | 1.0081 | 1.0089 | **100** |

Regola: per ogni lega il K con la log-loss di validazione più bassa; parità entro 0.0002 → il più vicino a 200.

**B2 — K per lega (Serie A 300, Premier League 200, Bundesliga 200, La Liga 100, Ligue 1 100)**

| Insieme | N | Δ log-loss | IC 95% per partita | IC 95% a blocchi per settimana |
|---|---:|---:|---|---|
| tutte le stagioni | 12751 | +0.00008 | [-0.00028, +0.00045] | [-0.00029, +0.00044] |
| validazione 2019/20-2021/22 | 5376 | +0.00055 | [-0.00004, +0.00113] | [-0.00008, +0.00120] |
| held-out 2022/23→ | 7375 | -0.00026 | [-0.00070, +0.00019] | [-0.00066, +0.00014] |

Log-loss 0.9797 (baseline 0.9798); Δ RPS +0.00002; Δ Brier +0.00003.

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0009 | +0.0010 | -0.0002 | +0.0000 | -0.0006 | +0.0001 | -0.0005 | -0.0010 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0008 | +0.0001 | +0.0001 | -0.0002 | -0.0005 |

### B3 — Rating separati casa / trasferta

B3a: la feature `eo_ha` = R_casa(squadra di casa) − R_trasf(ospite) sostituisce `eo_diff`. Griglia (6 configurazioni), scelta sulle validazione (parità entro 0.0002 → la più semplice, nell'ordine in tabella).

| Variante | Log-loss | Δ tutte (IC per partita) | Δ tutte (IC a blocchi) | Δ validazione | Δ held-out (IC a blocchi) | Stagioni migliorate |
|---|---:|---|---|---:|---|---:|
| B3a — rating casa/trasferta K=200, γ=0.0 | 0.9806 | -0.00081 [-0.00170, +0.00003] | [-0.00173, +0.00012] | +0.00161 | -0.00257 [-0.00351, -0.00165] | 2/8 |
| B3a — rating casa/trasferta K=300, γ=0.0 | 0.9803 | -0.00053 [-0.00139, +0.00026] | [-0.00140, +0.00034] | +0.00148 | -0.00199 [-0.00288, -0.00111] | 2/8 |
| B3a — rating casa/trasferta K=400, γ=0.0 | 0.9806 | -0.00082 [-0.00172, +0.00004] | [-0.00176, +0.00013] | +0.00080 | -0.00199 [-0.00302, -0.00097] | 1/8 |
| B3a — rating casa/trasferta K=200, γ=0.5 | 0.9795 | +0.00028 [-0.00035, +0.00089] | [-0.00041, +0.00097] | +0.00182 | -0.00084 [-0.00143, -0.00025] | 2/8 |
| B3a — rating casa/trasferta K=300, γ=0.5 | 0.9792 | +0.00061 [-0.00006, +0.00127] | [-0.00011, +0.00132] | +0.00203 | -0.00042 [-0.00106, +0.00023] | 4/8 |
| B3a — rating casa/trasferta K=400, γ=0.5 | 0.9794 | +0.00042 [-0.00038, +0.00120] | [-0.00040, +0.00123] | +0.00168 | -0.00050 [-0.00132, +0.00035] | 4/8 |

Scelta: **K=300, γ=0.5** (Δ validazione +0.00203).

**B3a — rating casa/trasferta (K=300, γ=0.5) al posto di eo_diff**

| Insieme | N | Δ log-loss | IC 95% per partita | IC 95% a blocchi per settimana |
|---|---:|---:|---|---|
| tutte le stagioni | 12751 | +0.00061 | [-0.00006, +0.00127] | [-0.00011, +0.00132] |
| validazione 2019/20-2021/22 | 5376 | +0.00203 | [+0.00070, +0.00330] | [+0.00069, +0.00337] |
| held-out 2022/23→ | 7375 | -0.00042 | [-0.00110, +0.00027] | [-0.00106, +0.00023] |

Log-loss 0.9792 (baseline 0.9798); Δ RPS +0.00018; Δ Brier +0.00035.

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0011 | +0.0050 | -0.0000 | -0.0009 | +0.0003 | -0.0009 | +0.0006 | -0.0050 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0007 | +0.0009 | -0.0003 | -0.0001 | +0.0018 |

**B3b — eo_ha AGGIUNTO a eo_diff (stessi parametri di B3a)**

| Insieme | N | Δ log-loss | IC 95% per partita | IC 95% a blocchi per settimana |
|---|---:|---:|---|---|
| tutte le stagioni | 12751 | +0.00009 | [-0.00024, +0.00040] | [-0.00024, +0.00041] |
| validazione 2019/20-2021/22 | 5376 | +0.00037 | [-0.00015, +0.00090] | [-0.00022, +0.00094] |
| held-out 2022/23→ | 7375 | -0.00011 | [-0.00052, +0.00028] | [-0.00049, +0.00028] |

Log-loss 0.9797 (baseline 0.9798); Δ RPS +0.00002; Δ Brier +0.00004.

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0004 | +0.0014 | +0.0001 | -0.0006 | +0.0004 | -0.0005 | +0.0006 | -0.0024 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0001 | -0.0001 | -0.0002 | +0.0000 | +0.0006 |

### Riepilogo B (ogni variante da sola vs baseline)

| Variante | Log-loss | Δ tutte (IC per partita) | Δ tutte (IC a blocchi) | Δ validazione | Δ held-out (IC a blocchi) | Stagioni migliorate |
|---|---:|---|---|---:|---|---:|
| B1 — Elo-Odds su quote Pinnacle di chiusura | 0.9798 | -0.00002 [-0.00013, +0.00009] | [-0.00012, +0.00008] | -0.00008 | +0.00002 [-0.00011, +0.00015] | 5/8 |
| B2 — K per lega {'I1': 300, 'E0': 200, 'D1': 200, 'SP1': 100, 'F1': 100} | 0.9797 | +0.00008 [-0.00028, +0.00045] | [-0.00029, +0.00044] | +0.00055 | -0.00026 [-0.00066, +0.00014] | 4/8 |
| B3a — rating casa/trasferta K=300, γ=0.5 | 0.9792 | +0.00061 [-0.00006, +0.00127] | [-0.00011, +0.00132] | +0.00203 | -0.00042 [-0.00106, +0.00023] | 4/8 |
| B3b — eo_diff + rating casa/trasferta (K=300, γ=0.5) | 0.9797 | +0.00009 [-0.00024, +0.00040] | [-0.00024, +0.00041] | +0.00037 | -0.00011 [-0.00049, +0.00028] | 4/8 |

Verdetti (regola: Δ held-out > 0 con IC a blocchi che esclude lo zero): B1: **non distinguibile dal rumore**; B2: **non distinguibile dal rumore**; B3a: **non distinguibile dal rumore**; B3b: **non distinguibile dal rumore**.


## Esperimento C — Ordered logit di ricalibrazione sopra il baseline v6

Rifit settimanale sul passato (finestra espansiva), burn-in di 600 partite con identità (645 partite di test). Input: x1 = log(λ casa/λ ospite), x2 = λ casa + λ ospite del modello baseline; output: 1X2.

| Variante | Log-loss | Δ tutte (IC per partita) | Δ tutte (IC a blocchi) | Δ validazione | Δ held-out (IC a blocchi) | Stagioni migliorate |
|---|---:|---|---|---:|---|---:|
| Ordered logit semplice (4 parametri) | 0.9797 | +0.00012 [-0.00113, +0.00143] | [-0.00125, +0.00147] | +0.00046 | -0.00013 [-0.00184, +0.00154] | 4/8 |
| Ordered logit flessibile (banda del pareggio dipende da gol attesi) | 0.9791 | +0.00073 [-0.00034, +0.00186] | [-0.00043, +0.00187] | +0.00114 | +0.00043 [-0.00100, +0.00185] | 4/8 |

Scelta sulle validazione (parità entro 0.0002 → il semplice): **Ordered logit flessibile (banda del pareggio dipende da gol attesi)** (Δ validazione +0.00114). Verdetto: **non distinguibile dal rumore**.

**Ordered logit flessibile (banda del pareggio dipende da gol attesi)**

| Insieme | N | Δ log-loss | IC 95% per partita | IC 95% a blocchi per settimana |
|---|---:|---:|---|---|
| tutte le stagioni | 12751 | +0.00073 | [-0.00034, +0.00186] | [-0.00043, +0.00187] |
| validazione 2019/20-2021/22 | 5376 | +0.00114 | [-0.00083, +0.00312] | [-0.00071, +0.00298] |
| held-out 2022/23→ | 7375 | +0.00043 | [-0.00082, +0.00170] | [-0.00100, +0.00185] |

Log-loss 0.9791 (baseline 0.9798); Δ RPS +0.00011; Δ Brier +0.00037.

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0009 | +0.0058 | -0.0016 | -0.0031 | +0.0022 | +0.0026 | -0.0002 | +0.0024 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0041 | -0.0004 | -0.0004 | -0.0007 | +0.0009 |

Pareggio: previsto medio 0.2400 → 0.2514 dopo la ricalibrazione (reale 0.2525). Parametri dell'ultimo rifit: 1.476, 0.118, 0.079, 0.203, -0.258, 0.091.

La ricalibrazione non «migliora» secondo la regola scritta prima: non è stata applicata alla matrice dei punteggi (come richiesto, solo se migliora).


## Esperimento D — Valore della rosa Transfermarkt

Dati: dataset dcaribou/transfermarkt-datasets (file `player_valuations.csv.gz`, `clubs.csv.gz`, `players.csv.gz`, `competitions.csv.gz`, scaricati il 2026-10-16 dal bucket pubblico del progetto, ultima modifica 2026-09-05; ultima valutazione nei dati: 2026-06-12). Abbinamento nomi: tabella esplicita `backtest/transfermarkt_aliases.py` (176 squadre dei 5 campionati dal 2012/13; controllo di copertura superato: nessuna squadra senza alias).

### Copertura e affidabilità dei valori (data 1 agosto, finestra 365 giorni)

Club-stagione 2019/20 → oggi: 776; non affidabili (< 12 giocatori valutati): 12.

| Lega | club-stagione non affidabili (2019/20 →) |
|---|---|
| Serie A | Cremonese 2025/26 (11), Frosinone 2026/27 (3) |
| Premier League | Coventry 2026/27 (9), Hull 2026/27 (11) |
| Bundesliga | Elversberg 2026/27 (4), Paderborn 2026/27 (2), Schalke 04 2026/27 (4) |
| La Liga | La Coruna 2026/27 (1), Malaga 2026/27 (1), Santander 2026/27 (2) |
| Ligue 1 | Le Mans 2026/27 (2), Troyes 2026/27 (3) |

Giocatori valutati per club (mediana tra club affidabili): 35; valore mediano di una rosa: 202 M€.

### Griglia di 8 configurazioni (ogni riga da sola vs baseline v6)

| Variante | Log-loss | Δ tutte (IC per partita) | Δ tutte (IC a blocchi) | Δ validazione | Δ held-out (IC a blocchi) | Stagioni migliorate |
|---|---:|---|---|---:|---|---:|
| D — data jul, finestra 240 g, F1 | 0.9798 | +0.00004 [-0.00013, +0.00022] | [-0.00013, +0.00021] | +0.00018 | -0.00006 [-0.00030, +0.00016] | 5/8 |
| D — data jul, finestra 240 g, F2 | 0.9799 | -0.00005 [-0.00031, +0.00021] | [-0.00030, +0.00021] | +0.00012 | -0.00017 [-0.00043, +0.00009] | 4/8 |
| D — data jul, finestra 365 g, F1 | 0.9798 | +0.00004 [-0.00013, +0.00021] | [-0.00013, +0.00021] | +0.00018 | -0.00007 [-0.00030, +0.00016] | 5/8 |
| D — data jul, finestra 365 g, F2 | 0.9799 | -0.00005 [-0.00031, +0.00020] | [-0.00031, +0.00020] | +0.00012 | -0.00018 [-0.00044, +0.00008] | 4/8 |
| D — data aug, finestra 240 g, F1 | 0.9798 | +0.00005 [-0.00015, +0.00026] | [-0.00014, +0.00025] | +0.00023 | -0.00007 [-0.00034, +0.00018] | 5/8 |
| D — data aug, finestra 240 g, F2 | 0.9798 | +0.00000 [-0.00022, +0.00024] | [-0.00022, +0.00023] | +0.00019 | -0.00013 [-0.00043, +0.00016] | 3/8 |
| D — data aug, finestra 365 g, F1 | 0.9798 | +0.00005 [-0.00015, +0.00025] | [-0.00014, +0.00024] | +0.00022 | -0.00008 [-0.00034, +0.00017] | 5/8 |
| D — data aug, finestra 365 g, F2 | 0.9798 | -0.00001 [-0.00023, +0.00022] | [-0.00023, +0.00022] | +0.00018 | -0.00015 [-0.00045, +0.00014] | 4/8 |

Scelta sulle validazione (parità entro 0.0002 → la più semplice): **D — data jul, finestra 240 g, F1** (Δ validazione +0.00018). Verdetto: **non distinguibile dal rumore**.

**D — data jul, finestra 240 g, F1**

| Insieme | N | Δ log-loss | IC 95% per partita | IC 95% a blocchi per settimana |
|---|---:|---:|---|---|
| tutte le stagioni | 12751 | +0.00004 | [-0.00013, +0.00022] | [-0.00013, +0.00021] |
| validazione 2019/20-2021/22 | 5376 | +0.00018 | [-0.00006, +0.00041] | [-0.00007, +0.00042] |
| held-out 2022/23→ | 7375 | -0.00006 | [-0.00031, +0.00018] | [-0.00030, +0.00016] |

Log-loss 0.9798 (baseline 0.9798); Δ RPS +0.00002; Δ Brier +0.00003.

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0001 | +0.0002 | +0.0003 | -0.0003 | -0.0001 | +0.0001 | -0.0000 | +0.0002 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0000 | -0.0000 | +0.0000 | +0.0003 | -0.0001 |

### Guadagno per sottoinsieme (variante scelta)

Insiemi disgiunti: (1) partite con almeno una neopromossa (squadra assente dallo stesso campionato nella stagione precedente); (2) restanti partite in cui entrambe le squadre hanno giocato meno di 8 partite nella stagione (prime 8 giornate); (3) resto.

| Sottoinsieme | N | Δ log-loss | IC 95% per partita | IC 95% a blocchi | Δ held-out |
|---|---:|---:|---|---|---:|
| neopromosse (almeno una squadra) | 3410 | -0.00016 | [-0.00065, +0.00032] | [-0.00067, +0.00034] | -0.00030 |
| restanti prime 8 giornate | 2195 | +0.00049 | [+0.00021, +0.00077] | [+0.00028, +0.00070] | +0.00038 |
| resto | 7146 | -0.00000 | [-0.00018, +0.00019] | [-0.00019, +0.00019] | -0.00009 |


## Tabella riassuntiva

Baseline = modello in produzione v6-eloodds (with_xg): log-loss **0.9798** su 12751 partite 2019/20 → 2026-10-12. Quote di chiusura senza margine (power) = **0.9701**; divario baseline − chiusura = 0.0097. Δ = baseline − variante (positivo = variante migliore). Validazione = 2019/20-2021/22 (dove si scelgono i parametri), held-out = 2022/23 → oggi. Per D è riportata la sola configurazione scelta sulle validazione (le altre 7 sono nella sezione D).

| Variante | Log-loss | Δ tutte [IC per partita] | IC a blocchi | Δ validazione | Δ held-out [IC a blocchi] | Stagioni migliorate | Distanza dalla chiusura | Divario recuperato |
|---|---:|---|---|---:|---|---:|---:|---:|
| *Quote di chiusura (power)* | 0.9701 | — | — | — | — | — | 0.0000 | 100% |
| **Baseline v6-eloodds** | 0.9798 | — | — | — | — | — | +0.0097 | 0% |
| A1 — xG con 12 mesi di riscaldamento, training dal 2015/16 | 0.9796 | +0.00016 [-0.00009, +0.00041] | [-0.00008, +0.00041] | +0.00006 | +0.00023 [-0.00000, +0.00046] | 6/8 | +0.0096 | 1.6% |
| A2 — xG con 6 mesi di riscaldamento, training dal 2014/15 | 0.9798 | +0.00001 [-0.00025, +0.00027] | [-0.00025, +0.00027] | -0.00035 | +0.00028 [+0.00003, +0.00053] | 5/8 | +0.0097 | 0.1% |
| A3 — training dal 2013/14 con xG mancante gestito (imputazione + indicatore) | 0.9798 | -0.00004 [-0.00050, +0.00043] | [-0.00049, +0.00045] | -0.00072 | +0.00046 [-0.00011, +0.00104] | 4/8 | +0.0098 | -0.4% |
| A4 — xG a 6 mesi + training dal 2013/14 con xG mancante gestito | 0.9800 | -0.00015 [-0.00061, +0.00031] | [-0.00061, +0.00033] | -0.00101 | +0.00048 [-0.00006, +0.00102] | 4/8 | +0.0099 | -1.5% |
| B1 — Elo-Odds su quote Pinnacle di chiusura | 0.9798 | -0.00002 [-0.00013, +0.00009] | [-0.00012, +0.00008] | -0.00008 | +0.00002 [-0.00011, +0.00015] | 5/8 | +0.0097 | -0.2% |
| B2 — K per lega {'I1': 300, 'E0': 200, 'D1': 200, 'SP1': 100, 'F1': 100} | 0.9797 | +0.00008 [-0.00028, +0.00045] | [-0.00029, +0.00044] | +0.00055 | -0.00026 [-0.00066, +0.00014] | 4/8 | +0.0096 | 0.8% |
| B3a — rating casa/trasferta K=300, γ=0.5 | 0.9792 | +0.00061 [-0.00006, +0.00127] | [-0.00011, +0.00132] | +0.00203 | -0.00042 [-0.00106, +0.00023] | 4/8 | +0.0091 | 6.3% |
| B3b — eo_diff + rating casa/trasferta (K=300, γ=0.5) | 0.9797 | +0.00009 [-0.00024, +0.00040] | [-0.00024, +0.00041] | +0.00037 | -0.00011 [-0.00049, +0.00028] | 4/8 | +0.0096 | 0.9% |
| C — Ordered logit semplice (4 parametri) | 0.9797 | +0.00012 [-0.00113, +0.00143] | [-0.00125, +0.00147] | +0.00046 | -0.00013 [-0.00184, +0.00154] | 4/8 | +0.0096 | 1.2% |
| C — Ordered logit flessibile (banda del pareggio dipende da gol attesi) | 0.9791 | +0.00073 [-0.00034, +0.00186] | [-0.00043, +0.00187] | +0.00114 | +0.00043 [-0.00100, +0.00185] | 4/8 | +0.0090 | 7.5% |
| D — data jul, finestra 240 g, F1 | 0.9798 | +0.00004 [-0.00013, +0.00022] | [-0.00013, +0.00021] | +0.00018 | -0.00006 [-0.00030, +0.00016] | 5/8 | +0.0097 | 0.4% |


## Commento

1. **Nessuna variante migliora il baseline v6 in modo distinguibile dal rumore** secondo la regola scritta prima (Δ held-out > 0 con IC a blocchi che esclude lo zero; per A, Δ su tutte con IC a blocchi > 0). Il divario dalle quote di chiusura resta 0.0097; la miglior riga (ordered logit flessibile, +0.0007) ne recupera il 7.5% con un IC che include lo zero.
2. **A, lunghezza del training**: il baseline ha 3 stagioni di training nel 2019/20 e 10 nel 2026/27 (da 5.478 a 17.937 partite). Anticipare il training (xG con 12 o 6 mesi di riscaldamento, oppure stack allenato dal 2013/14 con xG mancante imputato più indicatore) cambia la log-loss di al massimo +0.0002 (A1, scelta sulle validazione: +0.00016, IC a blocchi [−0.0001, +0.0004]). Con 6-13 stagioni di training il guadagno nel 2019/20-2020/21 resta nullo o negativo (A3/A4: da −0.0006 a −0.0020).
3. **Correzione al round 2**: lì avevo attribuito (con cautela) lo scarso guadagno di Elo-Odds nelle prime due stagioni alla finestra di training corta. Il round 3 non lo conferma: allungare il training non cambia nulla. La causa dell'effetto «guadagno concentrato dal 2021/22» resta non spiegata (resta compatibile con un cambio di regime del mercato dopo il 2020/21, ma non l'ho verificato). Ho corretto di conseguenza le frasi in `results.md`, `results_round2.md` e nello script del backtest.
4. **B, varianti di Elo-Odds**: Pinnacle al posto della media è identico (−0.00002; Pinnacle presente nel 91% delle partite di test). K per lega scelto sulle validazione (300/200/200/100/100) guadagna +0.0006 in validazione e perde −0.0003 fuori campione. I rating separati casa/trasferta (K=300, γ=0.5) sono l'esempio più istruttivo: +0.0020 in validazione con IC che esclude lo zero, ma −0.0004 fuori campione (IC [−0.0011, +0.0002]); nelle tre configurazioni con γ=0 il held-out è significativamente negativo (fino a −0.0026). Aggiungerli a eo_diff (B3b) non dà nulla (+0.0001).
5. **C, ordered logit**: sopra il nuovo baseline il flessibile dà +0.0007 su tutte le stagioni (IC a blocchi [−0.0004, +0.0019]) e +0.0004 fuori campione, senza stagioni stabili (4/8, con stagioni a +0.0058 e −0.0031). Non migliora secondo la regola, quindi non l'ho applicato alla matrice dei punteggi. Il pareggio medio si corregge (24.0% → 25.1%, reale 25.3%) ma la log-loss no.
6. **D, valore della rosa Transfermarkt**: nessun effetto (+0.00004 con la configurazione scelta; tutte e 8 le configurazioni tra −0.00005 e +0.00005). Il valore delle rose è già contenuto nei rating Elo-Odds, che derivano dalle quote. Per sottoinsieme: neopromosse −0.0002 (IC che include lo zero), resto −0.0000, prime 8 giornate (senza neopromosse) +0.0005 con IC che esclude lo zero (held-out +0.0004); è l'unico segnale nominale, ma è uno di tre sottoinsiemi guardati e vale 5 punti su diecimila: non lo considero un risultato.
7. **Limiti dei dati D**: il dataset non copre la seconda divisione, quindi per le neopromosse il valore della rosa è sottostimato (solo i giocatori già visti nelle prime divisioni); 12 club-stagione risultano «non affidabili» (< 12 giocatori valutati), tutti nel 2026/27 tranne la Cremonese 2025/26, e sono imputati col minimo della lega. Le valutazioni sono riferite al club al momento della valutazione, quindi i trasferimenti estivi tra la valutazione di giugno e il 1° agosto non sono visibili. Non è stato verificato in live.
8. **Metodo**: B3a è stata la migliore in validazione (+0.0020, IC che esclude lo zero) e non regge fuori campione (−0.0004): con 3 stagioni di validazione (5.376 partite) e una griglia di 6 configurazioni la scelta sulle sole validazione produce falsi positivi. Per questo il verdetto si basa sul held-out, non sulla validazione.
9. **Conclusione**: in produzione non cambierei nulla. Le informazioni «di squadra» passate che abbiamo provato (risultati, tiri, xG, quote di chiusura, valore di rosa) non aggiungono altro al modello attuale; è plausibile (ma non verificato) che il divario residuo dalle quote di chiusura (0.0097) dipenda da informazioni sulla singola partita, come formazioni, infortuni e movimenti di mercato.
