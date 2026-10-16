## Criteri fissati PRIMA di calcolare i risultati

Questa sezione è stata scritta prima di eseguire qualsiasi variante del round 5. Cosa è stato guardato prima: solo la presenza delle colonne arbitro (football-data.co.uk ha `Referee` solo per la Premier League, 100% delle partite dal 2014/15; la tabella `games` di Transfermarkt ha l'arbitro per il ~100% delle partite 2012/13-2025/26 e nessuna partita del 2026/27) e le colonne disponibili (HY/AY gialli, HF/AF falli, HC/AC corner; non ci sono colonne dei rossi nel dataset parsato del modello, che non ha un modello dei rossi). Nessuna log-loss e nessun esito sono stati usati per scegliere nulla.

**Regole comuni (come round 3-4)**
- **Validazione** = 2019/20, 2020/21, 2021/22; **held-out** = 2022/23 in poi. I parametri si scelgono solo sulle validazione: configurazione con la log-loss del totale più bassa in validazione; parità entro 0.0002 → la più semplice (ordine in tabella). Nessuna griglia viene estesa dopo aver visto i risultati.
- Δ = metrica(baseline) − metrica(variante) per le metriche «più basso = meglio»; positivo = variante migliore. IC 95% bootstrap appaiato (5000 ricampionamenti) per partita e a blocchi per settimana ISO.
- **Verdetto «migliora»**: Δ della log-loss del totale gialli sulle held-out > 0 con IC a blocchi che esclude lo zero.

### G — Arbitro nel modello dei cartellini gialli (campionati)

**Baseline**: il modello di produzione dei gialli, variante `with_xg` (`backtest/stats_model.py`): due regressioni di Poisson (gialli casa, gialli ospite) su feature proprie (Poisson attacco/difesa sui gialli e sui falli come ausiliaria) e comuni (DC gol, xG, pi-ratings, dummy di lega), alpha 1e-3, training dal 2016/17 stagione per stagione, totale = Binomiale Negativa con alpha a momenti. Test: tutte le partite dal 2019/20 con gialli, falli e corner disponibili.

**Arbitro**: dalla tabella `games` di Transfermarkt, abbinando ogni partita di campionato per (campionato, stagione, club casa, club ospite) con i `club_id` di `transfermarkt_aliases.py` (come nel round 4). Nome normalizzato (minuscolo, senza accenti né titoli «Dr.»/«Prof.»); chiave arbitro = (campionato, nome normalizzato). Controllo di coerenza: nella Premier League si confronta con la colonna `Referee` di football-data (stesso cognome normalizzato e stessa iniziale). Si riportano copertura per lega e stagione, numero di arbitri distinti e partite per arbitro.

**Effetto arbitro** (solo partite precedenti, data strettamente anteriore):
- Per ogni partita passata j dell'arbitro, con gialli totali y_j e totale atteso dal modello m_j (previsione walk-forward fuori campione per le stagioni ≥ 2019/20; per il 2016/17-2018/19, previsione in campione del modello del primo fold di test), si calcola R = (Σ y_j + k·m̄) / (Σ m_j + k·m̄), con k = «partite equivalenti» di shrinkage (empirical Bayes: k partite fittizie in cui y = m) e m̄ = media dei totali attesi della lega nel 2016/17-2018/19. Storico solo dal 2016/17. Arbitro senza partite precedenti (o sconosciuto) → R = 1, cioè effetto zero.
- **Due forme**: **(a)** moltiplicativa: le due medie attese (casa e ospite) sono moltiplicate per R (esponente fisso 1) e l'alpha della Binomiale Negativa si ristima a momenti sul training con le medie corrette; **(b)** regressore: log R entra come feature in entrambe le regressioni di Poisson (coefficiente appreso), alpha a momenti come nel baseline.
- **Griglia (10 configurazioni)**: k ∈ {5, 10, 20, 40, 80} × forma ∈ {a, b}. Ordine di semplicità: forma (a) prima di (b); k crescente. Metrica di scelta: log-loss del totale (−log p della Binomiale Negativa sul totale osservato, media per partita) in validazione.
- **G2 (variante falli)**: alla forma (b) con il k scelto si aggiunge un secondo regressore, log R_f, effetto arbitro sui falli calcolato come sopra con y = falli totali osservati e m = falli totali attesi dal modello Poisson attacco/difesa sui falli (la statistica ausiliaria del modello dei gialli). Confronto con baseline e con G1 (forma b, stesso k).
- **Rossi**: il modello non ha un modello dei rossi (nessuna colonna dei rossi nel dataset parsato): non applicabile, si dice e non si inventa.
- **Placebo**: con la configurazione scelta, i nomi degli arbitri sono permutati a caso tra le partite dello stesso campionato e stagione (seme fisso): il guadagno deve sparire.

**Metriche (tutte sullo stesso insieme di partite, baseline vs variante)**: log-loss del totale gialli (principale); correlazione per squadra (casa e ospite insieme) e del totale tra medie previste e gialli osservati; MAE del totale; log-loss delle linee Over/Under mostrate sul sito (2.5, 3.5, 4.5, 5.5) in media e per linea; copertura dell'intervallo all'80% del totale (obiettivo 0.80). IC per partita e a blocchi su tutte le metriche appaiate.

### H — Corner, solo come controllo

Stessa procedura applicata ai **corner** (modello dei corner del sito: Poisson attacco/difesa sui corner, ausiliaria = tiri), **senza scelta di parametri**: si usano forma e k scelti per G. L'arbitro non dovrebbe influire sui corner: se il guadagno è distinguibile da zero (IC a blocchi su tutte le stagioni che esclude lo zero) lo si segnala come possibile problema di abbinamento delle partite (o di un effetto reale dell'arbitro), da indagare.

### Se G migliora

Si descrive (senza implementare) come ottenere gratis e in automatico l'arbitro designato per le partite future, con copertura e tempistica per lega e cosa mostrare quando non è ancora noto.
