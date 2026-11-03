# Round 10 — livello di stagione per lega (bayesiano) per gol e statistiche (solo backtest)

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
