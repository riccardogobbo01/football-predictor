# Round 4 — formazione titolare (E) e gare di ritorno nelle coppe (F), solo backtest

**Nulla della produzione è stato toccato.** Dati: dataset dcaribou/transfermarkt-datasets (tabelle `game_lineups`, `appearances`, `games`, `player_valuations`, `clubs`; cache in `data/cache/transfermarkt/`, ignorata da git). Stesse regole del round 3: criteri scritti prima, validazione 2019/20-2021/22, held-out dal 2022/23, IC bootstrap (5000) per partita e a blocchi per settimana ISO.

---
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


## Esperimento E — Limite massimo della formazione titolare (campionati)

> **Questo è un test «a formazione nota».** Le feature usano gli 11 effettivamente schierati nella partita da prevedere, informazione che si conosce circa un'ora prima del calcio d'inizio: non c'è quando le previsioni si pubblicano. Il guadagno qui sotto è quindi un **limite massimo** di quanto potrebbe valere conoscere la formazione, non un guadagno ottenibile in produzione. La versione realistica è la «formazione prevista» (in fondo, solo se la condizione scritta prima è soddisfatta).

### Copertura

Partite di campionato abbinate a una partita del dataset Transfermarkt e con formazione completa per entrambe le squadre (esattamente 11 titolari) e almeno 3 partite di storico con minuti (N=5 / N=10). Le altre hanno differenze = 0 e indicatore `lu_miss` = 1 (stesso trattamento in training e in test).

| Stagione | Partite di test | Abbinate | Complete (N=5) | Complete (N=10) |
|---|---:|---:|---:|---:|
| 2019/20 | 1725 | 100.0% | 100.0% | 100.0% |
| 2020/21 | 1826 | 100.0% | 99.9% | 99.9% |
| 2021/22 | 1825 | 100.0% | 99.8% | 99.8% |
| 2022/23 | 1826 | 100.0% | 99.7% | 99.7% |
| 2023/24 | 1752 | 100.0% | 99.8% | 99.8% |
| 2024/25 | 1752 | 100.0% | 99.9% | 99.9% |
| 2025/26 | 1752 | 100.0% | 99.7% | 99.7% |
| 2026/27 | 293 | 0.0% | 0.0% | 0.0% |

Totale partite di test con formazione completa: N=5 97.5%, N=10 97.5%. Tutta la stagione 2026/27 manca nel dataset (ultimo aggiornamento 2026-09-05, valutazioni fino al 2026-06-12); anche il training dello stack dal 2016/17 al 2025/26 ha copertura completa (≥ 98% per stagione).

### Griglia di 6 configurazioni (ogni riga da sola vs baseline v6)

| Variante | Log-loss | Δ tutte (IC per partita) | Δ tutte (IC a blocchi) | Δ validazione | Δ held-out (IC a blocchi) | Stagioni migliorate |
|---|---:|---|---|---:|---|---:|
| E — N=5, quota minuti | 0.9794 | +0.00043 [-0.00027, +0.00115] | [-0.00038, +0.00124] | +0.00022 | +0.00058 [-0.00054, +0.00163] | 6/8 |
| E — N=5, valore | 0.9794 | +0.00045 [-0.00049, +0.00140] | [-0.00058, +0.00144] | +0.00153 | -0.00034 [-0.00168, +0.00097] | 3/8 |
| E — N=5, quota minuti + valore | 0.9788 | +0.00097 [-0.00012, +0.00203] | [-0.00023, +0.00212] | +0.00161 | +0.00050 [-0.00103, +0.00204] | 5/8 |
| E — N=10, quota minuti | 0.9791 | +0.00072 [+0.00008, +0.00138] | [-0.00002, +0.00144] | +0.00054 | +0.00086 [-0.00027, +0.00190] | 6/8 |
| E — N=10, valore | 0.9796 | +0.00025 [-0.00080, +0.00130] | [-0.00092, +0.00139] | +0.00115 | -0.00040 [-0.00181, +0.00100] | 4/8 |
| E — N=10, quota minuti + valore | 0.9789 | +0.00095 [-0.00020, +0.00208] | [-0.00031, +0.00221] | +0.00146 | +0.00058 [-0.00101, +0.00211] | 4/8 |

Scelta sulle validazione (parità entro 0.0002 → la più semplice): **E — N=5, valore** (Δ validazione +0.00153). Verdetto: **non distinguibile dal rumore**.

**E — N=5, valore**

| Insieme | N | Δ log-loss | IC 95% per partita | IC 95% a blocchi per settimana |
|---|---:|---:|---|---|
| tutte le stagioni | 12751 | +0.00045 | [-0.00049, +0.00140] | [-0.00058, +0.00144] |
| validazione 2019/20-2021/22 | 5376 | +0.00153 | [+0.00006, +0.00303] | [-0.00001, +0.00307] |
| held-out 2022/23→ | 7375 | -0.00034 | [-0.00157, +0.00082] | [-0.00168, +0.00097] |

Log-loss 0.9794 (baseline 0.9798); Δ RPS +0.00017; Δ Brier +0.00038.

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0004 | +0.0021 | +0.0029 | -0.0003 | -0.0014 | +0.0025 | -0.0004 | -0.0115 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0008 | +0.0017 | +0.0010 | +0.0004 | -0.0018 |

**Guadagno su partite con formazione completa e sulle altre (variante scelta)**

| Insieme | N | Δ log-loss | IC 95% a blocchi |
|---|---:|---:|---|
| formazione completa | 12437 | +0.00071 | [-0.00021, +0.00161] |
| formazione mancante (indicatore = 1) | 314 | -0.00977 | [-0.02611, +0.00849] |

### Formazione prevista

Condizione scritta prima: Δ held-out ≥ +0.002 con IC a blocchi che esclude lo zero. Configurazione scelta: Δ held-out -0.00034, IC a blocchi [-0.00168, +0.00097] → condizione **NON soddisfatta**.

Non si fa la versione «formazione prevista», come stabilito.


### Analisi aggiuntiva (NON prevista dal prereg): solo partite con formazione disponibile, cioè fino al 2025/26

La stagione 2026/27 (293 partite) non è nel dataset: in quelle righe lo stack riceve `lu_miss` = 1 e peggiora. Qui si escludono, per vedere il limite massimo senza quell'artefatto. Le 6 configurazioni sono tutte mostrate (nessuna scelta nuova).

| Configurazione | N | Δ tutte (IC a blocchi) | Δ held-out 2022/23-2025/26 (IC a blocchi) |
|---|---:|---|---|
| — N=5, quota minuti | 12458 | +0.00071 [-0.00001, +0.00140] | +0.00108 [+0.00024, +0.00187] |
| — N=5, valore | 12458 | +0.00073 [-0.00020, +0.00166] | +0.00012 [-0.00105, +0.00127] |
| — N=5, quota minuti + valore | 12458 | +0.00125 [+0.00013, +0.00233] | +0.00099 [-0.00042, +0.00232] |
| — N=10, quota minuti | 12458 | +0.00101 [+0.00039, +0.00158] | +0.00137 [+0.00055, +0.00213] |
| — N=10, valore | 12458 | +0.00053 [-0.00054, +0.00160] | +0.00005 [-0.00120, +0.00127] |
| — N=10, quota minuti + valore | 12458 | +0.00123 [+0.00006, +0.00242] | +0.00106 [-0.00039, +0.00245] |


## Esperimento F — Coppe: gare di ritorno

### Plausibilità dell'Elo ricostruito

Confronto tra il mio Elo a fine dati (2026-09) e il ranking attuale di clubelo.com (749 club): 492 club con abbinamento di nome sicuro (somiglianza ≥ 0.9) e partite nel 2025/26 o dopo. Correlazione di Pearson 0.423, di Spearman 0.360; pendenza ClubElo/mio Elo 0.40. Le scale non coincidono: i coefficienti si stimano comunque dai dati.

Primi 6 club per Elo ricostruito (mio / ClubElo): FC Barcelona 2078 / Barcelona 2032; Arsenal FC 2074 / Arsenal 2045; Manchester City 2039 / Man City 2024; Paris Saint-Germain 2028 / Paris SG 1969; Real Madrid 2020 / Real Madrid 1980; Inter Milan 1965 / Internazionale 1938.

### Campione

Partite delle fasi principali di CL/EL/UCOL 2012/13-2025/26 con punteggio e Elo: 5197 (finali escluse). Nel test 2016/17-2025/26: **3885 partite**, di cui **501 gare di ritorno** (validazione 2019/20-2021/22: 121; held-out 2022/23-2025/26: 380), 501 andate, 34 gare uniche a eliminazione diretta, 2849 partite dei gironi.

Partite ai supplementari riconosciute (minuti > 95): 51 nel test, di cui 50 gare di ritorno e 1 gare uniche; la classe 1X2 dei 90' è ricostruita con la regola scritta prima ed escluse dal training dei gol. Partite senza minuti nel dataset (supplementari non controllabili): 767 nel test, di cui 111 tra le gare di ritorno.

Log-loss 1X2 del baseline (modello Elo riallenato in walk-forward, Elo ricostruito) su tutte le 3885 partite del test: **0.9839**; sulle sole gare di ritorno: 1.0463. Non è confrontabile col 0.965 di `cups_model.json` (Elo diverso, insieme di partite diverso).

### Varianti (ogni forma da sola vs baseline)

Δ = log-loss(baseline) − log-loss(variante). «Tutte» = tutte le partite del test (la variante cambia solo le gare di ritorno, il resto varia di poco per il riallenamento); «ritorni» = solo gare di ritorno.

| Forma | Log-loss (tutte) | Δ tutte [IC a blocchi] | Δ ritorni [IC per partita] | IC a blocchi ritorni | Δ ritorni validazione | Δ ritorni held-out [IC a blocchi] |
|---|---:|---|---|---|---:|---|
| F1 — g lineare (clip ±3) | 0.9834 | +0.00051 [-0.00024, +0.00134] | +0.00507 [-0.00133, +0.01169] | [-0.00038, +0.01072] | -0.00240 | +0.00744 [+0.00093, +0.01422] |
| F2 — segno di g | 0.9835 | +0.00047 [-0.00042, +0.00143] | +0.00496 [-0.00205, +0.01217] | [-0.00166, +0.01167] | -0.00835 | +0.00920 [+0.00176, +0.01698] |
| F3 — due pendenze (g>0, g<0) | 0.9837 | +0.00022 [-0.00058, +0.00108] | +0.00362 [-0.00320, +0.01057] | [-0.00225, +0.00986] | -0.00391 | +0.00602 [-0.00123, +0.01323] |

Scelta sulle validazione (Δ su tutte le partite di validazione, parità entro 0.0002 → la più semplice): **F1 — g lineare (clip ±3)** (Δ validazione -0.00026); scegliendo sul Δ delle sole gare di ritorno in validazione sarebbe F1 — g lineare (clip ±3). Verdetto (Δ sulle gare di ritorno held-out, IC a blocchi): **migliora**.

Dettaglio della variante scelta, gare di ritorno: n = 501 (validazione 121, held-out 380); Δ +0.00507 [IC per partita -0.00133, +0.01169; IC a blocchi -0.00038, +0.01072]. Con così poche gare di ritorno gli intervalli sono larghi.

Coefficienti (log-gol attesi) del fit su tutte le stagioni fino al 2025/26, per illustrazione: casa elo_diff +0.188, g -0.055; ospite elo_diff -0.185, g +0.010; rho +0.029.

| Stagione | 2016/17 | 2017/18 | 2018/19 | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gare di ritorno | 44 | 44 | 44 | 20 | 44 | 57 | 58 | 58 | 66 | 66 |
| Δ log-loss sui ritorni | +0.012 | +0.030 | -0.004 | -0.020 | -0.008 | +0.008 | -0.007 | +0.005 | +0.009 | +0.011 |


## Tabella riassuntiva

### E — campionati (formazione NOTA: limite massimo, non ottenibile in produzione)

Baseline v6-eloodds 0.9798, quote di chiusura 0.9701, divario 0.0097. Δ = baseline − variante (positivo = meglio); validazione = 2019/20-2021/22, held-out = 2022/23 → oggi (comprende il 2026/27, senza dati di formazione). «Divario recuperato» = Δ tutte / divario.

| Variante | Log-loss | Δ tutte [IC per partita] | IC a blocchi | Δ validazione | Δ held-out [IC a blocchi] | Stagioni migliorate | Distanza dalla chiusura | Divario recuperato |
|---|---:|---|---|---:|---|---:|---:|---:|
| *Quote di chiusura (power)* | 0.9701 | — | — | — | — | — | 0.0000 | 100% |
| **Baseline v6-eloodds** | 0.9798 | — | — | — | — | — | +0.0097 | 0% |
| E — N=5, quota minuti | 0.9794 | +0.00043 [-0.00027, +0.00115] | [-0.00038, +0.00124] | +0.00022 | +0.00058 [-0.00054, +0.00163] | 6/8 | +0.0093 | 4.4% |
| E — N=5, valore (scelta sulle validazione) | 0.9794 | +0.00045 [-0.00049, +0.00140] | [-0.00058, +0.00144] | +0.00153 | -0.00034 [-0.00168, +0.00097] | 3/8 | +0.0093 | 4.6% |
| E — N=5, quota minuti + valore | 0.9788 | +0.00097 [-0.00012, +0.00203] | [-0.00023, +0.00212] | +0.00161 | +0.00050 [-0.00103, +0.00204] | 5/8 | +0.0088 | 10.0% |
| E — N=10, quota minuti | 0.9791 | +0.00072 [+0.00008, +0.00138] | [-0.00002, +0.00144] | +0.00054 | +0.00086 [-0.00027, +0.00190] | 6/8 | +0.0090 | 7.4% |
| E — N=10, valore | 0.9796 | +0.00025 [-0.00080, +0.00130] | [-0.00092, +0.00139] | +0.00115 | -0.00040 [-0.00181, +0.00100] | 4/8 | +0.0095 | 2.6% |
| E — N=10, quota minuti + valore | 0.9789 | +0.00095 [-0.00020, +0.00208] | [-0.00031, +0.00221] | +0.00146 | +0.00058 [-0.00101, +0.00211] | 4/8 | +0.0088 | 9.8% |

Formazione prevista: non eseguita (condizione Δ held-out ≥ +0.002 con IC che esclude lo zero non soddisfatta).

### F — coppe, gare di ritorno

Baseline = modello Elo delle coppe riallenato in walk-forward su Elo ricostruito: log-loss 0.9839 su 3885 partite del test (501 gare di ritorno). Non esiste un riferimento di mercato nei dati delle coppe, quindi niente distanza dalle quote di chiusura. Δ = baseline − variante.

| Forma | Δ tutte le partite [IC a blocchi] | Δ gare di ritorno [IC per partita] | IC a blocchi (ritorni) | Δ ritorni validazione | Δ ritorni held-out [IC a blocchi] |
|---|---|---|---|---:|---|
| F1 — g lineare (clip ±3) (scelta) | +0.00051 [-0.00024, +0.00134] | +0.00507 [-0.00133, +0.01169] | [-0.00038, +0.01072] | -0.00240 | +0.00744 [+0.00093, +0.01422] |
| F2 — segno di g | +0.00047 [-0.00042, +0.00143] | +0.00496 [-0.00205, +0.01217] | [-0.00166, +0.01167] | -0.00835 | +0.00920 [+0.00176, +0.01698] |
| F3 — due pendenze (g>0, g<0) | +0.00022 [-0.00058, +0.00108] | +0.00362 [-0.00320, +0.01057] | [-0.00225, +0.00986] | -0.00391 | +0.00602 [-0.00123, +0.01323] |

Verdetto F secondo la regola scritta prima (Δ sulle gare di ritorno held-out, IC a blocchi): **migliora**; vedi il commento per i limiti.


## Commento

1. **E, limite massimo con formazione nota: piccolo.** Anche conoscendo gli 11 effettivamente schierati, la migliore configurazione (quota minuti + valore, N=5) guadagna +0.0010 su tutte le stagioni (IC a blocchi [−0.0002, +0.0021]) e +0.0005 fuori campione (IC che include lo zero): recupera circa il 10% del divario di 0.0097 dalle quote di chiusura. La configurazione scelta sulle validazione (solo valore, N=5) ha Δ held-out −0.0003. Nessuna configurazione soddisfa il verdetto «migliora».
2. **«Formazione prevista» non eseguita**: la condizione scritta prima (Δ held-out ≥ +0.002 con IC che esclude lo zero) non è soddisfatta, nemmeno dal limite massimo. Una formazione prevista (gli 11 dell'ultima partita) non può valere più della formazione nota.
3. **Analisi aggiuntiva, non prevista dal prereg**: escludendo la stagione 2026/27, che non è nel dataset (293 partite con indicatore «formazione mancante», dove la configurazione scelta peggiora di 0.0115), la sola quota di minuti con N=10 guadagna +0.0010 su tutte le stagioni (IC a blocchi [+0.0004, +0.0016]) e +0.0014 fuori campione ([+0.0006, +0.0021]). È statisticamente distinguibile da zero ma piccolo e sotto la soglia di +0.002: lo riporto come limite massimo, non come risultato da adottare. Le feature misurano rotazioni/assenze rispetto ai titolari abituali e il valore di mercato degli 11: non catturano ruolo, gravità degli infortuni o motivazioni, quindi il limite è per questa famiglia di feature, non per ogni informazione sulla formazione.
4. **Copertura E**: 100% delle partite di campionato abbinate a una partita Transfermarkt; formazione completa (11 titolari per entrambe) e ≥ 3 partite di storico nel 99.7-100% delle partite per stagione; mancanti trattate con differenze = 0 e indicatore. Il dataset non contiene partite del 2026/27 (valutazioni fino al 12 giugno 2026).
5. **F, gare di ritorno: segnale fragile, non adottabile così.** Nel test ci sono 501 gare di ritorno (121 in validazione, 380 held-out), 50 delle quali ai supplementari (classe dei 90' ricostruita con la regola esatta scritta prima). La forma scelta (F1, g lineare) dà +0.0051 sulle gare di ritorno (IC a blocchi [−0.0004, +0.0107]) e +0.0074 nelle held-out (IC a blocchi [+0.0009, +0.0142]): per la regola scritta prima il verdetto è formalmente «migliora». Ma in validazione le tre forme peggiorano (da −0.0024 a −0.0084), il segno cambia da stagione a stagione (6 stagioni su 10 positive; −0.020 nel 2019/20) e gli intervalli su tutte le gare di ritorno includono lo zero. Il coefficiente è piccolo e plausibile: ogni gol di vantaggio dell'andata riduce di circa il 5% i gol attesi della squadra in casa nel ritorno (quella in vantaggio); quasi nessun effetto sull'ospite.
6. **Limite serio di F**: lo storico di ClubElo non è accessibile (API spenta, pagine per data ferme al ranking corrente), quindi l'Elo è ricostruito dalle partite di Transfermarkt con parametri fissi. Per i club più forti coincide bene col ClubElo attuale (es. Barcelona 2078 contro 2032, Arsenal 2074 contro 2045), ma su tutti i 492 club abbinati la correlazione è solo 0.42: i campionati minori non sono calibrati tra loro. Il baseline ottiene così 0.9839 (non confrontabile con lo 0.965 di `cups_model.json`) ed è più debole del modello vero; un baseline debole può gonfiare il guadagno di un termine in più.
7. **Cosa farei**: non cambiare il modello delle coppe sulla base di questo test. Se vuoi verificare davvero il termine dell'andata, serve rifare F con l'Elo storico vero: tu hai già i dati offline con cui è stato allenato `cups_model.json` (1.796 partite con Elo pre-partita); se me li passi (anche solo data, squadre, punteggio, Elo casa/ospite, fase) rifaccio F in poche ore con lo stesso prereg.
8. **In produzione resta tutto com'è.** Dopo quattro round le informazioni di squadra e di formazione che abbiamo potuto provare non spostano il modello oltre il rumore, tranne Elo-Odds (round 2), già in produzione; il divario di 0.0097 dalle quote di chiusura non è spiegato né dalla lunghezza del training, né da valore di rosa, né dalle formazioni titolari come le abbiamo misurate.
