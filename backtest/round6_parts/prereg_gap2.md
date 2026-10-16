## Fase 1 — Estensione della griglia dei GAP ratings: criteri fissati PRIMA di guardare i risultati

Nel round 6 la configurazione scelta per i GAP (η = 0.05, γ = 0.5) stava sul bordo della griglia dichiarata e il guadagno cresceva con entrambi i parametri. Questa sezione è stata scritta prima di eseguire qualsiasi configurazione nuova; nessun risultato con η > 0.05 o γ > 0.5 era stato visto (γ = 0.75 e 1.0 e η = 0.10-0.20 non erano mai stati calcolati). Definizioni, metriche, insieme di valutazione, validazione (2019/20-2021/22), held-out (dal 2022/23) e IC (a blocchi per settimana ISO, 5000 ricampionamenti; per partita anche) sono quelli del prereg del round 6.

**Griglia 1** (12 configurazioni): η ∈ {0.05, 0.10, 0.15, 0.20} × γ ∈ {0.5, 0.75, 1.0}. γ = 1 significa che l'aggiornamento dei rating dell'altro campo vale quanto quello del campo giocato; γ > 1 non ha senso e non si prova.

**Scelta**, separatamente per tiri e per tiri in porta (baseline del tiri = modello dei tiri attuale; baseline dei tiri in porta = modello I senza GAP, come nel round 6): configurazione con il Δ della log-loss del totale più alto sulle sole stagioni di validazione; parità entro 0.0002 → la più semplice (η più basso, poi γ più basso).

**Bordo e seconda (ultima) estensione.** Se per una statistica la configurazione scelta ha η = 0.20, si aggiunge UNA volta η ∈ {0.30, 0.40} (con γ ∈ {0.5, 0.75, 1.0}) e si sceglie di nuovo sull'unione delle griglie con la stessa regola; poi ci si ferma, anche se l'ottimo fosse ancora sul bordo. Un ottimo con γ = 1.0 non porta ad alcuna estensione (γ ha il limite naturale 1). Il passaggio a una seconda estensione vale per ogni statistica separatamente.

**Verifica fuori campione.** Per la configurazione scelta si riportano Δ della log-loss del totale e per squadra (tutte le stagioni, validazione, held-out) con IC a blocchi, correlazioni, MAE, copertura 80%/90%, ECE O/U. Verdetto come nel round 6: «migliora» se Δ totale held-out > 0 con IC a blocchi che esclude lo zero e Δ per squadra held-out ≥ 0. Si riporta anche la differenza rispetto alla configurazione del round 6 (η = 0.05, γ = 0.5), con IC.

I parametri scelti qui sono quelli della fase 2 (messa in produzione).
