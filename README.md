# ⚽ Football Predictor

Sistema predittivo per le partite delle top 5 leghe europee basato su:
- **Dixon-Coles** (modello Poisson con correzione per punteggi bassi)
- **ELO ratings** (ClubElo, aggiornamento giornaliero)

Tutte le fonti dati sono **gratuite**: football-data.org, Football-Data.co.uk CSV, ClubElo, Understat, Open-Meteo.

## Avvio locale

```bash
pip install -r requirements.txt
cp .env.example .env   # compila le API keys
python app.py          # apri http://localhost:5000
```

## Struttura

```
app.py            — Dashboard web (Flask)
main.py           — CLI
config.py         — Configurazione e API keys
collectors/       — Download dati (fdo, csv, elo, xg, meteo)
db/               — Schema SQLite
features/         — Feature engineering
predictions/      — Modello Dixon-Coles
scripts/          — Utility: init, aggiornamento giornaliero, prossimo turno
```

## Deploy su Railway

1. Crea un nuovo progetto su [railway.app](https://railway.app)
2. Connetti questo repo GitHub
3. Aggiungi un **volume** montato su `/data`
4. Imposta le variabili d'ambiente (vedi `.env.example`):
   - `FOOTBALL_DATA_ORG_KEY`
   - `DB_PATH=/data/football.db`
5. Al primo avvio esegui: `python scripts/init_railway.py`

Il cron giornaliero (`0 6 * * *`) esegue `scripts/daily_update.py` automaticamente.

## Licenza

MIT
