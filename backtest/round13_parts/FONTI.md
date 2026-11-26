# Round 13 — fonti alternative per tiri e giocatori (sonda del 24/11/2026)

Solo sonda: poche richieste (circa 80 pagine FotMob in totale, pausa 1,5 s), nessun download massivo, produzione non toccata. Strumenti: `scripts/sources_probe.py` (modalità `depth` e `ci`), workflow manuale `.github/workflows/probe_sources.yml`, `scripts/understat_status.py`.

## Understat (non raggiungibile dal 3/11: schema da fonti indirette)
Endpoint `getMatchData/{match_id}` (due librerie pubbliche; `match_id` già in `getLeagueData`). Campi dalla risposta di esempio della libreria (2021, non dal sito attuale): tiri con minuto, `player_id`, `situation` (Penalty), `result` (Goal, OwnGoal, SavedShot, MissedShots, BlockedShot, ShotOnPost), xG, `shotType`, coordinate, giocatore assistente (solo nome); roster con minuti, posizione, gialli, rossi, gol, assist, xG, xA, `roster_in/out`. **Mancano**: falli commessi e subiti, parate, tiri in porta per giocatore (solo tiri totali).

## FotMob (pagine pubbliche, verificato)
- **Accesso**: le pagine HTML (`/leagues/{id}/overview/{slug}?season=AAAA/AAAA` e `/matches/.../{codice}#{id}`) rispondono 200 a un client normale con User-Agent da browser; i dati stanno in `__NEXT_DATA__` (`content.shotmap`, `content.playerStats`, `content.lineup`, `content.matchFacts.events`). Nessun token, nessun Cloudflare. L'API `/api/*` (`matchDetails`, `leagues`) risponde 404 a un client normale e il `robots.txt` la vieta ai crawler generici (consentita solo a Googlebot e pochi altri): non usata. Peso: circa 1,1 MB per pagina partita, 1,1 MB per pagina lega.
- **soccerdata** (v2026.43.0): non ha un lettore FotMob.
- **Tiri**: `id, eventType (Goal, AttemptSaved, Miss, Post), teamId, playerId, playerName, x, y, min, minAdded, isBlocked, isOnTarget, goalCrossedY/Z, expectedGoals, expectedGoalsOnTarget, shotType, situation (RegularPlay, FromCorner, SetPiece, ThrowInSetPiece, FastBreak, **Penalty**), period, isOwnGoal, isSavedOffLine, isFromInsideBox, keeperId`. Rigore verificato: Pisa-Udinese 14/9/2025 (id 4803063), xG 0,788, `situation = Penalty`.
- **Giocatori** (`playerStats[id].stats`, gruppi Top stats/Attack/Defense/Duels): **Minutes played, Fouls committed, Was fouled, Total shots, Shots on target, Shots off target, Saves, Goals, Assists, xG, xA, xGOT, Tackles, Interceptions, Duels**, ecc.; posizione: `lineup...starters[].positionId` (slot di formazione) e `usualPlayingPositionId` (0 portiere, 1 difesa, 2 centrocampo, 3 attacco); cartellini: `matchFacts.events` di tipo `Card` con `card = Yellow/Red`; cambi: tipo `Substitution` con minuto e coppia entra/esce.
- **Profondità** (una partita per lega e stagione, giornata ~10; poi 4 partite in più dove mancava): i dati esistono dal **2016/17** per tutte e cinque le leghe, **ma a macchia**: circa il 15-20 % delle partite campionate (12 su ~63) non ha tiri o non ha statistiche giocatore (Serie A 2019/20, Bundesliga 2016/17, Ligue 1 2016/17 e 2020/21, Serie A 2022/23 senza tiri; la partita di prova di GitHub Actions, Inter-Torino 2025/26, è una di queste). Campione piccolo: la copertura vera si misura solo sull'universo.
- **Rischi ToS**: il piè di pagina dichiara che «l'uso di servizi automatici (robot, crawler, indicizzazione) e altri metodi di uso sistematico o regolare non è permesso». Un download di ~18.500 pagine da 1,1 MB (circa 20 GB, ~12 ore) è per definizione uso sistematico.

## Sofascore
- **Accesso**: un client normale riceve **403** (`{"error":{"code":403,"reason":"Forbidden"}}`, server Varnish) sull'API `api.sofascore.com`, su `robots.txt` e sulla homepage. Un browser vero funziona (il pannello integrato carica il sito); il sito usa API sullo stesso dominio (`/api/v1/unique-tournament/{id}/season/{id}/...`). **soccerdata** legge solo il calendario (`leagues`, `seasons`, `rounds`, `events`) e lo fa con un client che imita l'impronta TLS di un browser (`tls_requests`), con proxy opzionali (Tor, liste pubbliche) e Selenium per altri siti: cioè aggira la protezione. **Non l'ho aggirata né ho provato richieste programmatiche tramite il browser** (l'ambiente di esecuzione le ha negate come accesso non autorizzato).
- **Campi** (shotmap, lineups con statistiche, statistics): **non verificati** in questa sessione. Dalla documentazione pubblica che conosco, ma da confermare: shotmap con xG, xGOT, situazione, tipo di tiro, minuto e giocatore; lineups con minuti, rating, falli commessi/subiti, tiri, tiri in porta, parate.
- **Profondità**: non verificata.
- **Rischi ToS**: art. 2.8-2.9 dei termini: vietate l'estrazione e il riutilizzo del contenuto del database (diritto sui generis UE) senza consenso scritto, lo scraping e l'overload con richieste automatiche.

## GitHub Actions (workflow `probe_sources.yml`, lanciato a mano il 24/11/2026)
| Fonte | Esito da Actions | Locale |
|---|---|---|
| FotMob pagina lega Serie A 2025/26 | 200, 380 partite finite | 200, 380 |
| FotMob pagina partita Monza-Inter 2026/27 (id 5749645) | 200, 1.129.944 byte, 20 tiri con xG, 43 giocatori con statistiche, falli commessi/subiti, tiri, tiri in porta, parate, minuti, 4 cartellini, 10 cambi | identico (stessi byte) |
| Sofascore API (`seasons`, `shotmap`) | 403 | 403 |
| Understat (`getLeagueData`) | pagina di manutenzione | pagina di manutenzione |
(Il primo tentativo con Inter-Torino 2025/26 dava 0 tiri sia da Actions sia in locale: è una partita senza dati su FotMob, non un blocco.)

## Tabella
| | Understat | FotMob | Sofascore |
|---|---|---|---|
| Tiri: minuto, giocatore con id, situazione (rigore), esito (in porta, autogol), xG | sì (da verificare sul sito vivo): minute, player_id, Penalty, result Goal/OwnGoal/Saved/..., xG | sì, verificato: min, playerId, Penalty, eventType + isOnTarget + isOwnGoal, xG e xGOT, keeperId | non verificato |
| Giocatori: minuti, posizione, gialli, rossi | sì | sì (posizione come slot di formazione + ruolo abituale) | non verificato |
| **Falli commessi e subiti**, tiri in porta, parate per giocatore | **no** (solo tiri totali) | **sì** | non verificato |
| xG/xA per giocatore | sì | sì | non verificato |
| Storico dal 2016/17 | sì (30.000+ partite in cache di `getLeagueData` dal 2014/15) | dal 2016/17 ma con buchi (~15-20 % delle partite campionate) | non verificato |
| Accesso da locale | **in manutenzione dal 3/11** | sì (pagine pubbliche) | **403** con client normale |
| Accesso da Actions | in manutenzione | **sì, identico al locale** | **403** |
| Costo per ~18.500 partite | 18.500 richieste da ~28 KB (~6,5-9 ore) | 18.500 pagine da ~1,1 MB (~20 GB, ~12 ore) | n.d. |
| Stabilità | schema stabile da anni, ma ora 3 settimane di manutenzione | pagine Next.js: struttura che può cambiare senza preavviso; API ufficiosa vietata dal robots.txt | protezione anti-bot attiva |
| ToS | non verificabile ora | uso sistematico dichiarato non permesso | scraping ed estrazione vietati |

## Decisioni dell'utente (26/11/2026)
- **Understat resta la fonte primaria** per tiri, xG e roster appena torna online (il controllo periodico ogni 6 ore resta attivo; il download parte solo dopo la conferma della sonda sullo schema).
- **FotMob: nessuno scaricamento storico.** Solo usi mirati e piccoli in futuro (riempire buchi puntuali, campi che a Understat mancano su sottoinsiemi ridotti).
- **Sofascore: escluso.**

## API-Football (sonda del 26/11/2026): chiusa
Il piano gratuito non dà la stagione in corso (solo 2022-2024) e non ha il parametro `ids`: non serve alla produzione. Dettagli in `backtest/round13_parts/APIFOOTBALL.md`. Decisione dell'utente: fonte chiusa, nessuna raccolta.
