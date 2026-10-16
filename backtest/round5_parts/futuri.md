## Arbitro designato per le partite future (non implementato)

G migliora, quindi: come ottenere l'arbitro delle partite future in modo gratuito e automatico. Quello che segue è stato **verificato** dove indicato; il resto è indicato come «da verificare» perché le ricerche non hanno dato una fonte ufficiale affidabile.

**Cosa serve in realtà: due cose diverse**
1. L'**arbitro designato** per le partite da prevedere (nei prossimi 14 giorni).
2. L'**arbitro delle partite già giocate**, per aggiornare lo storico su cui si calcola l'effetto (R = rapporto tra gialli osservati e attesi nelle sue partite passate). Il dataset Transfermarkt usato nel backtest è una fotografia (ultima modifica 2026-09-05), non un feed giornaliero; football-data.co.uk ha l'arbitro solo per la Premier League. Quindi lo storico recente andrebbe **raccolto da noi**: salvare nel `history.csv` (o in un file a parte) l'arbitro che si è usato nella previsione di ogni partita e riusarlo quando la partita risulta giocata. Servono comunque una tabella esplicita di alias (come per le altre fonti) e un backfill una tantum dal dataset Transfermarkt fino a settembre 2026.

**Fonti, copertura e tempistica**

| Fonte | Costo / automazione | Cosa risulta | Tempistica per lega |
|---|---|---|---|
| **football-data.org** (già in uso, campo `referees` dell'API v4) | gratuita, già nel workflow | **Verificato oggi (16/10/2026)**: il campo c'è, ma nelle prossime due settimane solo 1 partita su 111 dei 5 campionati ha già l'arbitro (La Liga, mercoledì 21/10); le partite di questo fine settimana risultano ancora senza | Troppo tardi/lacunosa da sola; si può interrogare ogni giorno e usarla quando c'è |
| **Serie A**: AIA (aia-figc.it) e Lega Serie A | gratuita, pagine web; nessuna API trovata | Una sola riga per partita con arbitro | Secondo le notizie dei media, l'AIA pubblica di norma **il mercoledì per il fine settimana**, con comunicato separato per i turni infrasettimanali (fonte secondaria, **da verificare** sul sito AIA) |
| **La Liga**: RFEF (CTA) e laliga.com | gratuita, pagine web | Arbitro per partita | Da questa stagione (2025/26) le designazioni escono **il giorno prima di ogni partita** (una sola fonte, **da verificare**); fino al 2024/25 uscivano con più giorni di anticipo |
| **Bundesliga**: DFB e bundesliga.com | gratuita, pagine web | Arbitro, assistenti, VAR per partita | bundesliga.com dice che le designazioni sono pubblicate «tagesaktuell» (aggiornate di continuo); **non ho trovato il giorno fisso**; sono possibili sostituzioni a ridosso della partita |
| **Premier League**: PGMOL (e premierleague.com) | gratuita, canali ufficiali (sito, account X) | Arbitro per partita | **Non verificato**: non ho trovato il giorno di pubblicazione settimanale; le designazioni risultano comunque annunciate prima della giornata |
| **Ligue 1**: LFP (ligue1.com) / FFF | gratuita, pagine web | Arbitro e VAR per partita (esempio trovato: giornata 5 2025/26 pubblicata il 16/09/2025) | **Non verificato** il giorno fisso; la pubblicazione avviene prima della giornata |
| **Transfermarkt** (pagina della partita) | gratuita ma è scraping di un sito commerciale: andrebbe controllato il regolamento d'uso prima di farlo | L'arbitro compare dopo la designazione | Non verificata; non lo userei come fonte principale |

Coperture e orari esatti vanno misurati sul campo: proposta pratica = far girare per un paio di mesi un piccolo job giornaliero che interroga football-data.org e le pagine ufficiali e registra, per ogni partita, quanti giorni prima del calcio d'inizio compare l'arbitro. Con quei dati si decide se bastano i due-tre giorni di preavviso del job delle 07:00 UTC o serve una seconda esecuzione più vicina alla partita.

**Cosa mostrare quando l'arbitro non è ancora noto**
- Il modello usa R = 1 (effetto zero), che è esattamente come nel backtest tratta gli arbitri nuovi o sconosciuti (la stagione 2026/27 del backtest è tutta in questa condizione, con arbitro sconosciuto per tutte le 293 partite, e il modello con la forma b non peggiora il baseline: Δ log-loss del totale +0.0011).
- Nel pannello, accanto alle statistiche dei gialli, una riga «Arbitro: non ancora designato (previsione senza effetto arbitro)» oppure «Arbitro: Nome Cognome (media gialli storica ×1.12)»; la previsione si aggiorna al giorno successivo quando l'arbitro compare. Niente valore inventato né arbitro «medio».
- Se l'arbitro cambia all'ultimo momento (malattia): la previsione pubblicata resta quella calcolata con l'arbitro noto al momento del job; non si ricalcola a partita iniziata.
