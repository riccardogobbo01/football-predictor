# Football Predictor — Guida per Claude Code

Sistema predittivo per statistiche di partite di calcio. Usa **solo fonti gratuite**.
Copertura: Serie A, Premier League, Bundesliga, La Liga, Ligue 1, Champions League, Europa League, Conference League.

## Comandi slash (in Claude Code)

Quando sei dentro la cartella del progetto con Claude Code, hai questi comandi slash disponibili:

| Comando | Descrizione |
|---|---|
| `/setup` | Prima installazione completa (dipendenze, DB, dati storici) |
| `/update [fonte]` | Aggiorna dati da tutte le fonti o una specifica |
| `/fixtures [lega]` | Prossime partite programmate |
| `/predict Milan Inter` | Previsione per una partita specifica |
| `/predict serie_a` | Previsioni per il prossimo turno di un campionato |
| `/team Juventus` | Profilo e statistiche di una squadra |
| `/fit [lega]` | Ri-addestra il modello Dixon-Coles |

## Script shell (senza Claude Code)

```bash
./football.sh setup                           # Prima installazione
./football.sh daily                           # Routine giornaliera automatica
./football.sh predict "Milan" "Inter"         # Previsione singola
./football.sh predict-all serie_a             # Tutto il prossimo turno
./football.sh fixtures champions_league 14   # Prossime partite CL
```

## Setup iniziale (una sola volta)

```bash
# 1. Installa dipendenze
pip install -r requirements.txt

# 2. Crea file .env con le chiavi API (entrambe gratuite, richiede registrazione)
cp .env.example .env
# Compila API_FOOTBALL_KEY e FOOTBALL_DATA_ORG_KEY nel file .env

# 3. Inizializza il database SQLite
python main.py init

# 4. Scarica i dati storici (necessario la prima volta — può richiedere alcuni minuti)
python main.py update --source historical

# 5. Aggiorna con i dati recenti
python main.py update
```

## Comandi principali

```bash
# Aggiornamento dati (lancia questo regolarmente — es. ogni giorno)
python main.py update                    # tutti i source
python main.py update --source elo       # solo ELO ratings
python main.py update --source xg        # solo xG (Understat)
python main.py update --source fixtures  # solo calendario

# Prossime partite
python main.py fixtures                  # tutti i campionati, prossimi 7 giorni
python main.py fixtures --league serie_a
python main.py fixtures --league champions_league --days 14

# Previsione partita
python main.py predict "Milan" "Inter"
python main.py predict "Arsenal" "Chelsea" --date 2026-09-20
python main.py predict --league serie_a --round next   # tutti i match del prossimo turno

# Info squadra
python main.py team "Juventus"           # forma, ELO, statistiche recenti
```

## Architettura

```
football-predictor/
├── main.py                  CLI entry point (argparse)
├── config.py                Chiavi API, league IDs, costanti
├── collectors/
│   ├── football_data_org.py  Calendario e risultati (football-data.org, GRATIS)
│   ├── understat.py          xG per i top 5 campionati (scraping, GRATIS)
│   ├── clubelo.py            ELO ratings (api.clubelo.com, GRATIS)
│   ├── football_data_csv.py  CSV storici 1993-oggi (football-data.co.uk, GRATIS)
│   └── open_meteo.py         Meteo stadi (api.open-meteo.com, GRATIS)
├── db/
│   └── schema.py            Inizializzazione SQLite (file: data/football.db)
├── features/
│   └── engineer.py          12 variabili derivate per ogni partita
├── predictions/
│   ├── dixon_coles.py       Modello Dixon-Coles (Poisson corretto)
│   └── output.py            Formattazione output terminale
└── data/
    └── stadiums.py          Coordinate GPS stadi per meteo
```

## Fonti dati (tutte gratuite)

| Fonte | Dati | Limite | Auth |
|---|---|---|---|
| football-data.org | Calendario, risultati, classifiche | 10 req/min | Free API key |
| Understat | xG, npxG, tiri per top 5 leghe | Nessuno | No |
| ClubElo | ELO ratings storici | Nessuno | No |
| Football-Data.co.uk | CSV storici (gol, tiri, corner, cartellini, quote) | Nessuno | No |
| Open-Meteo | Meteo orario per coordinate GPS | 10k req/giorno | No |

> API-Football free tier (100 req/giorno) è incluso come source opzionale per stats live
> più dettagliate — se non hai la chiave, il sistema funziona lo stesso con le fonti sopra.

## Modello predittivo

**Dixon-Coles** (1997): estende Poisson per correggere la sottostima dei punteggi bassi.

Ogni squadra ha:
- `α_i` — forza d'attacco (log-scale)
- `δ_i` — debolezza difensiva (log-scale)

Con home advantage `λ`:
- Gol attesi casa: `μ = exp(α_home + δ_away + λ)`
- Gol attesi fuori: `ν = exp(α_away + δ_home)`

Correzione Dixon-Coles `τ(ρ)` per punteggi 0-0, 1-0, 0-1, 1-1.

Il modello viene fitnato con **weighted log-likelihood** (le partite recenti pesano di più):
`w(t) = exp(-0.0018 * days_ago)`

**Statistiche secondarie** (Poisson semplice calibrato su dati storici):
- Corner: media mobile EMA-10 per coppia casa/trasferta
- Cartellini: media arbitro + media squadra + aggiustamento derby
- Tiri: `xG / 0.105` (xG medio per tiro nei top 5 campionati)
- Assist: `gol_attesi × 0.85`

## Come aggiungere una nuova lega

1. Aggiungere la lega in `config.py` → `LEAGUES`
2. Aggiungere il codice CSV in `config.py` → `FOOTBALL_DATA_CSV_CODES`
3. Eseguire `python main.py update --source historical` per scaricare i dati storici

## Note tecniche

- Database: SQLite in `data/football.db` (portabile, zero setup)
- Rate limiting: tutti i collector rispettano i limiti con `time.sleep` automatico
- Cache: i dati già scaricati non vengono ri-scaricati (basato su date)
- Logging: `data/football.log` per debug
