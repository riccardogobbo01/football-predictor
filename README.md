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

**Statistiche attese e arbitro**: tiri, corner e gialli hanno un loro modello (Poisson attacco/difesa + regressioni di Poisson +
Binomiale Negativa sul totale, `backtest/stats_model.py`). Il modello dei **gialli** ha in più l'**effetto arbitro** (round 5,
`backtest/refeffect.py`): `log R`, con R = (Σ gialli osservati + k·m̄) / (Σ gialli attesi + k·m̄) sulle partite passate dell'arbitro
(k = 20 partite equivalenti di shrinkage, m̄ = media della lega), come regressore. Arbitro non ancora designato, sconosciuto o senza
storico = effetto zero. Backtest walk-forward (`python -m backtest.run_referee_backtest`): log-loss del totale gialli da 2.1186 a
2.1082, Δ +0.0104, IC 95% a blocchi per settimana [+0.0080, +0.0128]. L'arbitro designato viene dal campo `referees` di
football-data.org (lo stesso della chiave già usata per le partite); lo storico degli arbitri è in `data/referees/matches.csv`
(Transfermarkt 2016/17-2025/26 + football-data.org 2026/27, creato da `scripts/build_referee_history.py`) e prosegue nella colonna
`referee` di `docs/history.csv`. L'abbinamento dei nomi arbitro tra le fonti è la tabella esplicita `backtest/referee_aliases.py`.
Il training settimanale ricalcola gli effetti con le sole partite passate e li salva in `models/stack.json["referees"]`.
`history.csv` registra anche arbitro, data/ora della prima comparsa, gialli, tiri, tiri in porta e falli (totali) previsti e reali, i gol
del primo tempo previsti e reali, e `stats_version` (`config.STATS_VERSION`, separata da `MODEL_VERSION`, che riguarda solo il modello 1X2).

**Versioni `s3-gap` e `s4-intervalli` delle statistiche** (round 6, `backtest/stats_v3.py`, risultati in `backtest/results_round6.md`):
- **Tiri e tiri in porta**: i rating di attacco/difesa sono sostituiti dai **GAP ratings** di Wheatcroft (`backtest/gap.py`, quattro rating
  per squadra aggiornati partita dopo partita; parametri scelti sulle sole stagioni di validazione, `config.GAP_PARAMS`: tiri η=0.10, γ=1.0,
  tiri in porta η=0.05, γ=1.0). Per tiri, tiri in porta e totale il pannello mostra valore atteso e intervallo all'80%, più le linee Over/Under del totale.
  Lo stato dei GAP viene ricostruito ogni giorno dallo storico.
- **Falli**: blocco nuovo con effetto arbitro (stessa formula dei gialli, `models/stack.json["referees_fouls"]`). **Gialli**: solo il totale, con la riga dell'arbitro.
- **«Chi ne fa di più»** (più tiri, più gialli, più corner) e **handicap corner ±1,5** dalla copula gaussiana con marginali Binomiali Negative,
  integrazione numerica (nessuna simulazione); ρ stimato in training (tiri per campionato, corner e gialli unico).
- **Primo tempo**: quota dei gol del primo tempo per campionato stimata in training × gol attesi del modello 1X2; 1X2 al riposo e Over 0,5 / 1,5.
- Il pannello è diviso in sezioni richiudibili: Gol e risultati → Primo tempo → Tiri → Corner → Cartellini e falli → Contesto (le prime due aperte).
- **Intervalli** (`s4-intervalli`): per ogni statistica (tiri, tiri in porta, corner, gialli, falli), per squadra e totale, il pannello mostra l'intervallo di valori
  interi consecutivi centrato sui più probabili la cui probabilità reale è la più vicina all'80% (a parità la maggiore), con la probabilità accanto, ad es. «1–3 (78%)»
  (`stats_v3.nb_interval`). Verifica walk-forward in `backtest/results_intervals.md` (`python -I -X utf8 backtest/run_intervals.py`): scarto massimo tra probabilità
  dichiarata e frequenza reale 2,3 punti. I tiri hanno la dispersione (alpha) separata per casa e ospite (`alpha_home`/`alpha_away` in `models/stack.json`);
  con un solo alpha l'ospite era fuori dal criterio dei 3 punti. `python -I -X utf8 backtest/run_intervals_alpha.py` verifica che non peggiori le log-loss.
- **Livello stagionale** (`s5-livello`, round 7 fase 2, `backtest/results_round7.md`): per ogni lega, statistica e lato (casa/ospite) un moltiplicatore sulle medie
  attese, R = (Σ w·y + k·m̄)/(Σ w·μ + k·m̄) sulle partite precedenti della lega (w = 0,5^(giorni/(7·H)), μ = previsione fuori campione del modello), (H, k) per
  statistica in `config.LEVEL_PARAMS`, scelti sulle sole stagioni di validazione. Il registro delle somme giornaliere sta in `models/stack.json["stats_v3"]["level"]`
  (costruito dal training); ogni giorno le partite giocate dopo l'ultimo allenamento si aggiungono dallo storico (`bm_<statistica>_h/_a` = medie di base salvate
  al momento dell'emissione, `predictions/levels.py`). Nel pannello compare «Livello stagionale <statistica> <lega>: +X%» solo se il totale cambia di più del 5%.
- **Arbitri della Serie A** (`predictions/referee_sources.py`): AIA (`aia-figc.it/designazioni/can/`, 2 richieste per run, designazioni di solito il mercoledì per
  le partite da venerdì a lunedì) → fantacalcio.it (solo se l'AIA non e' utilizzabile) → football-data.org. Un cambio di struttura della pagina AIA non blocca il
  job: avviso nel log e ripiego. `history.csv` registra la fonte (`referee_source`); un arbitro nuovo ha effetto zero (alias in `AIA_ALIASES` per i cognomi ambigui,
  es. Colombo). Se football-data.org indica un arbitro diverso da quello AIA (cambio dell'ultimo momento) prevale football-data.org e il conflitto e' nel log.
- **Storico congelato al calcio d'inizio**: `history.csv` ha la colonna `kickoff` (UTC); dopo quell'istante una riga non si riscrive piu' e una partita gia' iniziata
  senza previsione non viene aggiunta. `p_o25` = probabilita' di Over 2,5 emessa, usata dal riquadro di monitoraggio (calibrazione dell'Over 2,5: previsto medio
  contro reale); `scripts/backfill_o25.py` la ricostruisce dalle copie di `predictions.json` in git per le righe precedenti.
- `python -I -X utf8 backtest/run_round6_prod.py` riproduce con il codice di produzione i risultati della fase 1 del round 6.

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
