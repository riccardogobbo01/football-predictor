### Weekend 16-18/10 (partite non ancora nei CSV di football-data.co.uk)

Risultati finali da theScore; previsioni = quelle pubblicate dal sito prima del weekend (commit `dd8bd91`, modello di produzione con i dati fino al 12/10). Stesse partite per lega (le partite del 19/10 non sono incluse).

| Lega | N | Gol previsti (media) | Gol reali (media) | Rapporto | Over 2,5 previsto | Over 2,5 reale |
|---|---:|---:|---:|---:|---:|---:|
| Serie A | 8 | 2.85 | 3.50 | 1.23 | 0.54 | 0.75 |
| Premier League | 9 | 2.99 | 2.44 | 0.82 | 0.57 | 0.33 |
| Bundesliga | 9 | 3.20 | 3.00 | 0.94 | 0.61 | 0.56 |
| La Liga | 9 | 2.98 | 3.00 | 1.01 | 0.57 | 0.44 |
| Ligue 1 | 9 | 2.99 | 3.89 | 1.30 | 0.57 | 0.78 |
| **Tutte** | 44 | 3.01 | 3.16 | 1.05 | 0.57 | 0.57 |

Con 44 partite l'errore standard della media dei gol è circa 0,25 per partita: lo scarto complessivo (+0,15) è dentro il rumore; le differenze per lega (8-9 partite ciascuna, errore standard circa 0,6) non sono interpretabili.

### Moltiplicatori correnti L3 (configurazioni scelte in validazione) dopo l'ultima partita giocata

Rapporto di livello per lega e lato (casa / ospite) applicato alle medie previste.

| Statistica | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---|---|---|---|---|
| Tiri (H=12, k=40) | 1.05 / 1.05 | 1.02 / 1.03 | 1.06 / 1.04 | 1.04 / 1.03 | 1.03 / 1.03 |
| Tiri in porta (H=8, k=40) | 0.98 / 1.06 | 1.00 / 1.03 | 1.07 / 1.01 | 1.06 / 1.03 | 1.04 / 1.00 |
| Corner (H=12, k=40) | 0.97 / 0.95 | 0.95 / 0.99 | 1.06 / 1.01 | 1.01 / 1.02 | 0.99 / 1.03 |
| Falli (H=4, k=15) | 0.98 / 0.88 | 1.03 / 1.07 | 1.02 / 1.05 | 1.00 / 0.99 | 0.98 / 1.01 |
| Gialli (H=4, k=15) | 1.02 / 0.82 | 1.00 / 1.06 | 0.97 / 0.92 | 0.97 / 0.97 | 1.03 / 0.89 |
