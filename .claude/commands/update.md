# /update — Aggiorna tutti i dati

Aggiorna il Football Predictor con i dati più recenti da tutte le fonti gratuite.

Se l'utente ha specificato una fonte (es. `/update elo`, `/update xg`, `/update fixtures`), aggiorna solo quella.
Altrimenti aggiorna tutto.

Fonti disponibili:
- `fixtures` — calendario e prossime partite (football-data.org)
- `results` — risultati partite recenti (football-data.org)
- `csv` — dati storici CSV con tiri, corner, cartellini, quote (football-data.co.uk)
- `xg` — expected goals xG (Understat, scraping gratuito)
- `elo` — ELO ratings aggiornati (ClubElo, gratuito)
- `weather` — previsioni meteo per gli stadi (Open-Meteo, gratuito)
- `stats` — ricalcola le statistiche aggregate da arbitri e squadre

Comandi da eseguire in ordine:

```bash
python main.py update
```

Oppure per una fonte specifica (usa il valore che l'utente ha passato dopo `/update`):
```bash
python main.py update --source <fonte>
```

Dopo l'aggiornamento, mostra quante partite sono state sincronizzate e quando è l'ultimo dato disponibile.
Se ci sono errori su singole fonti (es. chiave API mancante), segnalali ma continua con le altre.
