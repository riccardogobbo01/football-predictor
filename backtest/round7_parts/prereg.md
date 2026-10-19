# Round 7 — diagnosi e correzione del livello stagionale (solo backtest)

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
