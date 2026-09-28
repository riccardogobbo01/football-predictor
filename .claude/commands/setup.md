# /setup — Setup completo del Football Predictor

Esegui il setup completo del sistema Football Predictor. Fai questi passi nell'ordine:

1. Installa tutte le dipendenze Python con `pip install -r requirements.txt --break-system-packages`

2. Controlla se esiste il file `.env`. Se non esiste, copialo da `.env.example` e avvisa l'utente che deve inserire la chiave API di football-data.org (registrazione gratuita su https://www.football-data.org/client/register).

3. Inizializza il database con `python main.py init`

4. Scarica i dati storici con `python main.py update --source historical` (può richiedere qualche minuto — avvisa l'utente)

5. Aggiorna i dati recenti con `python main.py update`

6. Mostra all'utente un riepilogo di cosa è stato installato e i comandi disponibili:
   - `/update` — aggiorna tutti i dati dalle fonti
   - `/fixtures` — mostra le prossime partite
   - `/predict` — previsioni per le prossime partite
   - `/team` — profilo e statistiche di una squadra
   - `/fit` — ri-fitta il modello predittivo

Se qualcosa va storto, mostra l'errore e suggerisci la soluzione.
