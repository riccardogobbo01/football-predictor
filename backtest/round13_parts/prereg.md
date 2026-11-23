# Round 13 — fondamenta dati: tiri e giocatori da Understat (solo dati)

**Nessun modello, la produzione non si tocca.** Protocollo scritto PRIMA di scaricare qualsiasi partita. Il download storico parte solo dopo l'ok esplicito dopo il passo 1.

## Cosa si scarica
Per ogni partita giocata di Understat dal 2016/17 (cache di `getLeagueData`, 5 campionati) il dettaglio `GET https://understat.com/getMatchData/{match_id}` (header `X-Requested-With: XMLHttpRequest`, stesso schema di `getLeagueData`). Il `match_id` è già nel JSON di `getLeagueData` (`dates[].id`, presente e univoco in tutte le 18.329 partite giocate del 2016/17-2026/27 nella nostra cache; oggi `backtest/understat.py` lo scarta in `_season_matches`).
Campi attesi (schema della risposta di esempio della libreria `understatapi` 0.7.1, partita del 2021: **da verificare sul sito vivo con `scripts/understat_match_probe.py`**):
- **shots** (`h`, `a`): `id, minute, result, X, Y, xG, player, h_a, player_id, situation, season, shotType, match_id, h_team, a_team, h_goals, a_goals, date, player_assisted, lastAction`; valori osservati nelle risposte di esempio: situation ∈ {OpenPlay, FromCorner, SetPiece, DirectFreekick, **Penalty**}, result ∈ {Goal, **OwnGoal**, SavedShot, MissedShots, BlockedShot, ShotOnPost}, shotType ∈ {RightFoot, LeftFoot, Head, OtherBodyPart}.
- **rosters** (`h`, `a`, un dizionario per giocatore): `id, player_id, team_id, player, position, positionOrder, h_a, time (minuti giocati), goals, own_goals, shots, assists, key_passes, xG, xA, xGChain, xGBuildup, yellow_card, red_card, roster_in, roster_out` (collegano le righe di roster dei cambi; il minuto del cambio si ricava da `time`).
- **tmpl**: informazioni partita (`id, fid, h, a, date, h_goals, a_goals, h_xg, a_xg, forecast, h_shot, a_shot, h_shotOnTarget, ...`).

## Universo e abbinamento
Universo = partite con `isResult` in `getLeagueData`, stagioni 2016/17-2026/27, 5 campionati, **abbinate** alle partite di football-data.co.uk con la procedura già in produzione (`UNDERSTAT_ALIASES`, chiave campionato-stagione-casa-trasferta, data entro 5 giorni; massimo 1 % di non abbinate, regola esistente). Le soglie sotto si calcolano sulle partite abbinate.

## Soglie (fissate ora; nessuna viene toccata dopo aver visto i dati)
**Primarie** — il round è «superato» solo se valgono entrambe:
1. **Copertura ≥ 98 %** delle partite abbinate: risposta con HTTP 200, JSON con `shots` e `rosters` per entrambe le squadre, almeno 11 righe di roster per squadra; `shots` può essere vuoto solo se Understat dichiara zero tiri (`h_shot + a_shot = 0`). Si riporta anche per lega e stagione; una lega-stagione sotto il 95 % è segnalata a parte.
2. **Coerenza dei gol ≥ 99,5 %** delle partite con risposta valida: i gol ricostruiti dai tiri (`result = Goal` più gli `OwnGoal` secondo la convenzione sotto) coincidono con il punteggio ufficiale di football-data.co.uk **per entrambe le squadre**. *Convenzione degli autogol:* due candidate, C1 «l'autogol elencato tra i tiri di X vale per l'avversario», C2 «vale per X»; la scelta si fa **solo sulla stagione 2016/17** (partite con almeno un autogol) e poi si applica alle altre stagioni senza ritoccarla; se nessuna delle due spiega il 2016/17 al 99 % o più si riporta e ci si ferma.

**Secondarie** (solo riportate; sotto soglia → si descrive, il round resta superato):
- somma degli xG dei tiri contro l'xG di squadra di `getLeagueData` entro 0,02 in ≥ 99 % delle partite;
- gol dei roster (`goals` + `own_goals`) coerenti con i tiri in ≥ 99 %;
- minuti totali per squadra tra 990 e 1.200 in ≥ 99 % (11 × 90 più recupero e cambi);
- gialli e rossi dei roster contro football-data.co.uk (`HY, AY, HR, AR`): uguali in ≥ 97 % (le definizioni sul secondo giallo possono differire);
- `player_id` presente nel 100 % dei tiri e dei roster; nessun `id` di tiro duplicato; minuto del tiro tra 0 e 130; i rigori (`situation = Penalty`) con xG tra 0,70 e 0,85 in ≥ 95 % dei casi;
- numero di tiri Understat contro `HS + AS` di football-data.co.uk (media e correlazione, solo descrittivo: le definizioni di «tiro» differiscono).

## Protocollo di download (quando sarà autorizzato; decisioni del 24/11/2026)
- **Un lotto = una stagione per comando** (`python backtest/understat_matches.py SEASON 2016`), cinque campionati, circa 1.800 richieste (30-45 minuti), dal 2016/17 in poi.
- **Riprendibile con un file di stato** (`data/cache/understat/matches/state.json`: per stagione le partite scaricate, quelle fallite e il motivo): rilanciare lo stesso comando riparte da dove si era fermato e riprova le fallite.
- Sequenziale, una richiesta al secondo di pausa, nessun parallelismo, User-Agent esplicito; 4 tentativi con attesa 5/15/45 s; **JSON grezzi** una partita per file in `data/cache/understat/matches/{match_id}.json`, nella **cache ignorata da git**.
- **Arresto immediato** se arriva la pagina di manutenzione o altro non-JSON, se 5 richieste consecutive falliscono o se più del 2 % delle richieste di una finestra di 200 fallisce; lo stato resta salvato.
- Nessuna richiesta oltre l'elenco delle partite abbinate dell'universo.

## Prodotti
`backtest/understat_matches.py` (scaricatore e parser), **tabelle derivate in `csv.gz` per stagione, con commit**: `data/understat/{matches,shots,players}_{stagione}.csv.gz` (partite, tiri, giocatori; ordine e colonne fissati nello script), `backtest/results_round13.md` con le soglie sopra, copertura e coerenza per lega e stagione, esempi di incoerenze. Nessun collegamento con modelli, previsioni o sito.

**Stato (24/11/2026): round in pausa**: Understat è in manutenzione dal 3/11 (`scripts/understat_status.py`; controllo periodico con l'attività pianificata `understat-controllo`). La sonda `scripts/understat_match_probe.py` è pronta. Si valuta intanto una fonte alternativa o di ripiego (FotMob, Sofascore): vedi `backtest/round13_parts/FONTI.md`.
