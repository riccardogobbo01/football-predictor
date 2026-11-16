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
