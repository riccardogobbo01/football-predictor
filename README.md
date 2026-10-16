# ⚽ Football Predictor

Sistema predittivo per le partite delle top 5 leghe europee basato su:
- **Dixon-Coles** (modello Poisson con correzione per punteggi bassi)
- **ELO ratings** (ClubElo, aggiornamento giornaliero)

Tutte le fonti dati sono **gratuite**: football-data.org, Football-Data.co.uk CSV, ClubElo, Understat, Open-Meteo.

## Modello in produzione (pagina statica su GitHub Pages)

La pagina `docs/index.html` e `docs/predictions.json` sono generate da `scripts/generate_static.py` (workflow
**Daily predictions**, ogni giorno alle 07:00 UTC) con un **Poisson-stack**: due regressioni di Poisson (gol casa,
gol trasferta) su queste feature, tutte calcolate solo con partite precedenti:

| Feature | Cosa è |
|---|---|
| `dc_lmu`, `dc_lnu` | Dixon-Coles sui gol (xi=0.0018, finestra 5 anni) |
| `sot_lmu`, `sot_lnu` | Poisson attacco/difesa sui tiri in porta |
| `pi_gd`, `pi_diff` | pi-ratings |
| `xg_lmu`, `xg_lnu` | Dixon-Coles sugli xG Understat (ridge=2); solo nel modello `with_xg` |
| `eo_diff` | **Elo-Odds**: differenza di rating Elo casa − ospite prima della partita |

**Elo-Odds** (`backtest/eloodds.py`, K=200): un Elo per campionato in cui il «risultato» di ogni partita è la
probabilità implicita del mercato, `S = P(1) + 0.5·P(X)`, dalle quote di **chiusura** di football-data.co.uk
(colonne `AvgCH/AvgCD/AvgCA`, prima del 2019/20 Pinnacle in chiusura) senza margine (metodo power). I rating si
ricostruiscono ogni giorno da tutto lo storico (dal 2012/13) usando solo partite già giocate: le quote della partita da
prevedere non entrano mai. Squadra nuova = media dei 3 rating più bassi del campionato. Dove la chiusura di una partita
manca si usano le quote medie pre-partita (4 partite su 25.538 nello storico, tutte 2012-2018); senza nemmeno
quelle la partita non aggiorna i rating. Nel pannello di dettaglio il rating compare nel «Contesto».

Backtest walk-forward 2019/20 → oggi (12.751 partite, `python -m backtest.run_backtest`, risultati in
`backtest/results.md`): log-loss dello stack con xG da 0.9831 a **0.9798** con Elo-Odds (Δ +0.0033, IC 95% a blocchi per
settimana [+0.0018, +0.0048]; quote di chiusura 0.9701). Il guadagno è concentrato dal 2021/22 in poi. Gli esperimenti
del round 2 (porte chiuse, forze implicite DC, ricalibrazione 1X2) sono in `backtest/results_round2.md`: non portati in produzione.

**Allenamento**: workflow **Weekly stack training** (`scripts/train_stack.py`, lunedì 05:00 UTC) salva
`models/stack.json`. Se Understat non risponde **oppure** le quote storiche di chiusura non si scaricano o sono troppo
incomplete (file di stagione mancanti, meno del 95% di partite con quote in una stagione, assenti nelle partite recenti)
l'allenamento esce con errore senza toccare `models/stack.json`. Il job giornaliero si ferma (senza riscrivere `docs/`)
se nelle partite degli ultimi 60 giorni mancano le quote per più della metà.

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
