## Fase 2 — Verifica di produzione: il codice messo in produzione riproduce la fase 1

Parametri di produzione (`config.GAP_PARAMS`): tiri η=0.1, γ=1.0; tiri in porta η=0.05, γ=1.0. Il walk-forward usa `backtest/gap.py` (rating), `backtest/stats_v3.py` (matrice di progetto) e gli stessi stimatori di `backtest/stats_model.py` del training; il baseline è lo stesso della fase 1.

| Statistica | Δ log-loss totale (produzione) | Δ totale fase 1 | Δ per squadra (produzione) | Δ per squadra fase 1 | Differenza massima | Esito |
|---|---:|---:|---:|---:|---:|---|
| Tiri | +0.02073 | +0.02073 | +0.01495 | +0.01495 | 0.00e+00 | riprodotto |
| Tiri in porta | +0.00679 | +0.00679 | +0.00445 | +0.00445 | 0.00e+00 | riprodotto |

**Coerenza del serving** (stato GAP ricostruito dallo storico e `gap.predict`, contro la previsione pre-partita del backtest per l'ultima partita giocata di ogni campionato):

| Campionato | Statistica | Scarto massimo (casa, ospite) |
|---|---|---:|
| D1 | tiri | 0.0e+00 |
| E0 | tiri | 0.0e+00 |
| F1 | tiri | 0.0e+00 |
| I1 | tiri | 0.0e+00 |
| SP1 | tiri | 0.0e+00 |
| D1 | sot | 0.0e+00 |
| E0 | sot | 0.0e+00 |
| F1 | sot | 0.0e+00 |
| I1 | sot | 0.0e+00 |
| SP1 | sot | 0.0e+00 |

**Esito complessivo: tutto riprodotto**
