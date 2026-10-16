## Criteri fissati PRIMA di calcolare i risultati

Questa sezione è stata scritta prima di eseguire qualsiasi variante del round 4. Cosa è stato guardato prima: solo struttura, copertura e dimensioni dei dati (nessuna log-loss, nessun esito usato per scegliere nulla): copertura delle formazioni (100% delle partite dal 2013/14), presenza di minuti oltre il 90' nelle gare ai supplementari, struttura della tabella `games` per le coppe, formato degli snapshot di clubelo.com.

**Regole comuni (come round 3)**
- Stagioni di **validazione**: 2019/20, 2020/21, 2021/22. Stagioni **held-out**: 2022/23 in poi. I parametri si scelgono solo sulle validazione: tra le configurazioni della griglia dichiarata, quella con il Δ log-loss più alto sulle validazione; a parità entro 0.0002 vince la più semplice (ordine in tabella). Nessuna griglia viene estesa dopo aver visto i risultati.
- Δ = log-loss(baseline) − log-loss(variante), positivo = variante migliore. IC 95% bootstrap appaiato (5000 ricampionamenti) sia per partita sia a blocchi per settimana ISO.
- **Verdetto «migliora»**: Δ held-out > 0 con IC 95% a blocchi che esclude lo zero; altrimenti «non distinguibile dal rumore» (o «peggiora» se Δ < 0 con IC che esclude lo zero).

---

### E — Limite massimo della formazione titolare (campionati)

**Cosa misura.** È un test «a formazione nota»: le feature usano gli 11 effettivamente schierati nella partita da prevedere, informazione che si conosce circa un'ora prima del calcio d'inizio e che quindi **non** è disponibile quando le previsioni si pubblicano (giorni prima). Il suo guadagno è un **limite massimo** di quanto potrebbe valere sapere la formazione, non un guadagno ottenibile in produzione. La versione realistica è la «formazione prevista» (sotto).

**Baseline**: modello in produzione v6-eloodds, variante with_xg (`XG_FEATURES_EO`), come nel round 3: 12.751 partite 2019/20 → 2026-10-12, log-loss 0.9798.

**Dati**: tabelle `game_lineups` (tipo `starting_lineup`), `appearances` (minuti), `games`, `player_valuations` del dataset dcaribou/transfermarkt-datasets (stesso bucket del round 3, ultima modifica 2026-09-05). Abbinamento partita ↔ football-data per (campionato, stagione, club casa, club ospite) con i `club_id` della tabella esplicita `transfermarkt_aliases.py`.

**Definizioni (solo dati precedenti alla partita, tranne la formazione schierata)**
- Storico di una squadra: le sue ultime N partite del dataset (qualsiasi competizione: campionato, coppe nazionali e internazionali) con data strettamente precedente alla partita e con righe in `appearances`.
- Minuti recenti di un giocatore m_p = somma dei minuti in quelle N partite. «Undici tipici» = i 11 con più minuti recenti (parità risolte per `player_id`).
- **Feature 1 `lu_cov`** = Σ_{p ∈ 11 schierati} m_p / Σ_{tutti i giocatori} m_p: quota dei minuti recenti coperti dagli 11 schierati.
- **Feature 2 `lu_val`** = log(V(11 schierati) / V(11 tipici)), con V(p) = ultima valutazione di mercato con data strettamente precedente alla partita (nessuna finestra di staleness); giocatore senza valutazione = 250.000 €.
- Entrambe entrano nello stack come differenza casa − ospite (`lu_cov_diff`, `lu_val_diff`).
- **Formazioni mancanti**: se per una delle due squadre non ci sono esattamente 11 titolari in `game_lineups`, o ci sono meno di 3 partite di storico con minuti, le due differenze valgono 0 e un indicatore `lu_miss` = 1 (aggiunto allo stack come feature). Si riportano copertura per stagione e guadagno separato sulle partite con formazione completa e sulle altre.
- **Griglia (6 configurazioni, ordine di semplicità)**: N ∈ {5, 10} × insieme di feature ∈ {solo `lu_cov`, solo `lu_val`, entrambe}. Si riportano tutte e 6; la scelta sulle validazione indica la configurazione «principale»; in tabella compaiono anche «entrambe» per N=5 e N=10.

**Formazione prevista (condizionale)**: solo se la configurazione scelta ha Δ held-out ≥ +0.002 con IC a blocchi che esclude lo zero, si fa anche la versione in cui gli 11 «schierati» sono sostituiti dagli 11 titolari dell'ultima partita della squadra (nessuna informazione della partita stessa), stesso N e stesso insieme di feature, e si confrontano le due versioni (appaiate).

---

### F — Coppe: gare di ritorno

**Baseline = modello coppe attuale** (struttura di `predictions/cups.py` / `models/cups_model.json`): elo_diff = (Elo casa − Elo ospite)/100; gol casa = exp(a_h + b_h·elo_diff), gol ospite = exp(a_a + b_a·elo_diff); stessa matrice Dixon-Coles con rho; 1X2 sui 90 minuti. Il file `cups_model.json` è stato allenato fuori dal repo su dati che qui non ci sono: per misurare un guadagno fuori campione il baseline viene **rifittato in walk-forward** stagione per stagione (test 2016/17 → 2025/26, training su tutte le stagioni precedenti dal 2012/13, pesi con emivita di 3 stagioni come dichiarato nel file del modello; regressioni di Poisson pesate, rho per massima verosimiglianza pesata). Quindi il baseline qui è «lo stesso modello, riallenato nel tempo», non i coefficienti del file.

**Dati**: tabella `games` di Transfermarkt per Champions League (`CL`), Europa League (`EL`) e Conference League (`UCOL`), fasi principali (gironi ed eliminazione diretta; senza turni di qualificazione), stagioni 2012/13-2025/26.

**Modifica dichiarata prima di qualsiasi risultato: Elo ricostruito, non ClubElo.** Lo storico di ClubElo non è disponibile: l'API `api.clubelo.com` non risponde, le pagine `clubelo.com/AAAA-MM-GG` restituiscono sempre il ranking corrente (verificato su 2016-03-01, 2020-09-01 e 2024-03-01: valori identici) e le pagine dei singoli club mostrano solo gli ultimi 4 anni. L'Elo pre-partita è quindi **ricostruito con il metodo ClubElo / World Football Elo** su tutte le partite della tabella `games` (14 prime divisioni, coppe nazionali e internazionali, qualificazioni incluse), in ordine di data: rating iniziale 1500 per tutti i club, K = 20, vantaggio casa +100 punti (0 in finale), moltiplicatore sulla differenza reti G = 1 se |d| ≤ 1, 1.5 se |d| = 2, (11 + |d|)/8 altrimenti; aggiornamento R += K·G·(S − E) con S = 1/0.5/0 (punteggio registrato, supplementari inclusi), E = 1/(1+10^(−(ΔR+HFA)/400)). Parametri fissati qui, non ottimizzati. Il rating usato per una partita è quello PRIMA della partita (solo partite precedenti per data; due partite dello stesso club nello stesso giorno non esistono). Gli anni 2012-2015 servono da rodaggio (i club partono tutti da 1500 e i livelli dei campionati si allineano tramite le coppe europee); il test parte dal 2016/17. **Controllo di plausibilità**: correlazione tra il mio Elo al 2026-09-05 e il ranking attuale di clubelo.com (abbinamento di nomi automatico e prudente, solo coppie con somiglianza ≥ 0.9). Conseguenza: il baseline non è il modello `cups_model.json` (coefficienti stimati su ClubElo vero) ma lo stesso modello su un Elo ricostruito: valori assoluti di log-loss non confrontabili col 0.965 del file del modello.

**Esclusioni e supplementari (dichiarati prima dei risultati)**: le finali (campo neutro: la produzione fa la media delle orientazioni, qui ambigua) sono escluse da training e valutazione. Il dataset registra il punteggio dopo i supplementari, non ai 90'. Le partite giocate ai supplementari si riconoscono dai minuti giocati > 95 in `appearances` (disponibili per il 65-99% delle partite a seconda della stagione). Escludere queste partite sarebbe una selezione sull'esito (i supplementari si giocano proprio quando il ritorno finisce in un certo modo rispetto all'andata), quindi **non si escludono**: per le partite ai supplementari si ricostruisce la CLASSE 1X2 dei 90' con una regola esatta (sufficiente per la log-loss 1X2) — partita a eliminazione diretta in gara unica → pareggio ai 90'; gara di ritorno → il risultato ai 90' compensa esattamente l'andata, quindi vittoria della squadra che era in svantaggio (segno opposto a `g`), pareggio se `g` = 0 — e si **escludono dal training dei modelli dei gol** (il punteggio dei 90' non si conosce), restando nella valutazione. Le partite senza minuti disponibili non si possono controllare e usano il punteggio registrato (se ne riporta il numero, in particolare tra le gare di ritorno). La metrica è la log-loss 1X2 sui 90'.

**Gare di ritorno**: coppie di partite della stessa competizione e stagione, in fase a eliminazione diretta, con le stesse due squadre a campi invertiti a distanza di 1-30 giorni; la seconda è la gara di ritorno. Feature `g` = differenza reti dell'andata dal punto di vista della squadra che gioca in casa il ritorno (positivo = chi gioca in casa il ritorno era in vantaggio).

**Griglia (3 forme, ordine di semplicità)**: **F1** `g` lineare (clip tra −3 e +3); **F2** solo il segno di `g` (−1, 0, +1); **F3** due pendenze, una per `g > 0` e una per `g < 0` (clip tra −3 e +3). I termini valgono 0 fuori dalle gare di ritorno, entrano in entrambe le equazioni dei gol (coefficienti separati) e si stimano nello stesso fit pesato.

**Valutazione e verdetto**: Δ log-loss su tutte le partite di coppa del test e, separatamente, sulle sole gare di ritorno (con il loro numero). Il verdetto «migliora» per F si applica al Δ **sulle gare di ritorno** nelle stagioni held-out. Il campione è piccolo (poche centinaia di gare di ritorno): gli IC saranno larghi e lo si dice.

---

### Tabella finale e commento
Tabella riassuntiva con distanza dalle quote di chiusura (per E, riferita ai campionati; per F non esiste un riferimento di mercato nei dati) e commento di 5-10 righe, come nei round precedenti.
