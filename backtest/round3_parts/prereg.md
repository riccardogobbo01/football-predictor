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
