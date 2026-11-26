# Round 13 — sonda di API-Football (piano gratuito), 26/11/2026

Solo sonda: **9 richieste su 10 di tetto** (contatore persistente in `data/cache/apifootball_probe/count.json`, script `scripts/apifootball_probe.py`; risposte grezze nella stessa cartella, ignorata da git). Nessuna raccolta attivata, produzione non toccata. La chiave viene dall'ambiente o da `.env` e non è mai stampata né salvata.

## Piano e stagioni accessibili
- `status`: piano **Free**, 100 richieste al giorno, 10 al minuto (intestazioni `X-RateLimit`).
- `leagues?id=135`: la copertura dichiarata (eventi, formazioni, statistiche giocatore) va dal 2010; statistiche per giocatore dal 2015/16.
- **Accesso reale con il piano gratuito: solo le stagioni 2022-2024** (cioè 2022/23, 2023/24, 2024/25). Richiesta sulla stagione 2026: errore `plan` «Free plans do not have access to this season, try from 2022 to 2024». La 2025/26 non l'ho provata direttamente, ma il messaggio la esclude.
- Il parametro `ids` (più partite in una richiesta) **non è disponibile** sul piano gratuito («Free plans do not have access to the Ids parameter»).

## Una partita di Serie A (Atalanta-Fiorentina 3-2, 15/9/2024, id 1223625), 2 richieste
**Statistiche per giocatore** (`fixtures/players`, 1 richiesta, 31 KB, 2 squadre, 46 giocatori): minuti, ruolo, numero, voto, **tiri totali e in porta**, **gol, assist, parate, gol subiti**, **falli commessi e subiti**, gialli, rossi, rigori (procurati, commessi, segnati, sbagliati, parati), fuorigioco, passaggi, contrasti, duelli, dribbling.
- Valori mancanti = `null`: per chi non è sceso in campo è ovvio (minuti null), ma per chi ha giocato `null` può essere zero o dato mancante e non si distingue (falli commessi non nulli per 20 giocatori su 46; tiri per 13 su 46).
- Controlli di coerenza: minuti per squadra = 990 esatti (11 × 90); gialli e gol coincidono con gli eventi; **tiri in porta contro gol subiti + parate non tornano esattamente** (Atalanta 7 tiri in porta contro 2 gol subiti + 4 parate = 6; Fiorentina 5 contro 3 + 4 = 7): scarti di 1-2, quindi le parate di API-Football non sono ricostruibili dai tiri in porta e viceversa. Falli commessi da una squadra contro falli subiti dall'altra: 16 contro 14 e 15 contro 15.

**Eventi** (`fixtures/events`, 1 richiesta, 5 KB, 18 eventi): minuto (`elapsed` più `extra` per il recupero), squadra, giocatore, assist, tipo e dettaglio.
- Gol: `Normal Goal`; nella partita Como-Bologna (id 1223627, 3ª richiesta di eventi) un **`Own Goal`** (N. Casale) attribuito alla squadra che segna (Como), non a quella del giocatore.
- Cartellini: `Yellow Card` / `Red Card` con il motivo (`Foul`, `Argument`); un secondo giallo compare come `Yellow Card` più `Red Card` nello stesso minuto (Parma-Udinese, Keita al 73').
- Sostituzioni: `subst` con minuto, giocatore che esce in `player` e quello che entra in `assist`, numero del cambio.
- `Var`: `Goal confirmed`, `Penalty cancelled`.
- **Rigori segnati: non osservati nel campione** (3 partite di eventi: nessun rigore segnato); la documentazione prevede il dettaglio `Penalty` / `Missed Penalty` e il blocco giocatore ha `penalty.scored/missed/saved`. Non verificato sul campo.
- Non ci sono i tiri con xG né le coordinate: gli eventi sono solo gol, cartellini, cambi e VAR.

## Richieste al giorno per raccogliere le partite giocate dei 5 campionati
Partite per giorno di gioco nei 5 campionati (dai CSV di football-data, 2023/24-2025/26): **media 9,5 nei giorni con partite, mediana 5, 90° percentile 21, massimo 35** (nessun giorno oltre 45).
- Per partita servono **2 richieste** (giocatori + eventi; niente `ids`). Più 1-5 richieste per l'elenco delle partite del giorno.
- Media ≈ 20 al giorno; 90° percentile ≈ 45; picco ≈ 75. **Starebbe nel limite di 100 al giorno**, con margine ridotto nei giorni di picco; il limite di 10 al minuto impone almeno 10 minuti per 100 richieste.
- **Ma con il piano gratuito la stagione in corso non è accessibile**, quindi la raccolta quotidiana delle partite correnti **non è possibile**. Servirebbe un piano a pagamento (prezzo e limiti da verificare sul sito del fornitore: non verificati).
- Riempimento dello storico accessibile (2022/23-2024/25, 5 campionati): circa 5.330 partite → circa 10.700 richieste → **circa 107 giorni a 100 al giorno**, più qualche decina di richieste per gli elenchi (non verificato se l'elenco di una stagione intera arrivi in una sola risposta).

## Limiti da tenere presenti
- Solo 3 stagioni storiche accessibili, tutte dopo il 2022: coprono l'held-out ma non la validazione 2019/20-2021/22.
- Nessun xG né posizione dei tiri.
- 3 partite osservate: la qualità sulle altre leghe e stagioni è sconosciuta.
