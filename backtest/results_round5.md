# Round 5 — arbitro nel modello dei cartellini (G) e controllo sui corner (H), solo backtest

**Nulla della produzione è stato toccato.** Dati: tabella `games` di Transfermarkt (arbitro) e CSV di football-data.co.uk. Stesse regole dei round 3-4: criteri scritti prima, validazione 2019/20-2021/22, held-out dal 2022/23, IC bootstrap per partita e a blocchi per settimana ISO.

---
## Criteri fissati PRIMA di calcolare i risultati

Questa sezione è stata scritta prima di eseguire qualsiasi variante del round 5. Cosa è stato guardato prima: solo la presenza delle colonne arbitro (football-data.co.uk ha `Referee` solo per la Premier League, 100% delle partite dal 2014/15; la tabella `games` di Transfermarkt ha l'arbitro per il ~100% delle partite 2012/13-2025/26 e nessuna partita del 2026/27) e le colonne disponibili (HY/AY gialli, HF/AF falli, HC/AC corner; non ci sono colonne dei rossi nel dataset parsato del modello, che non ha un modello dei rossi). Nessuna log-loss e nessun esito sono stati usati per scegliere nulla.

**Regole comuni (come round 3-4)**
- **Validazione** = 2019/20, 2020/21, 2021/22; **held-out** = 2022/23 in poi. I parametri si scelgono solo sulle validazione: configurazione con la log-loss del totale più bassa in validazione; parità entro 0.0002 → la più semplice (ordine in tabella). Nessuna griglia viene estesa dopo aver visto i risultati.
- Δ = metrica(baseline) − metrica(variante) per le metriche «più basso = meglio»; positivo = variante migliore. IC 95% bootstrap appaiato (5000 ricampionamenti) per partita e a blocchi per settimana ISO.
- **Verdetto «migliora»**: Δ della log-loss del totale gialli sulle held-out > 0 con IC a blocchi che esclude lo zero.

### G — Arbitro nel modello dei cartellini gialli (campionati)

**Baseline**: il modello di produzione dei gialli, variante `with_xg` (`backtest/stats_model.py`): due regressioni di Poisson (gialli casa, gialli ospite) su feature proprie (Poisson attacco/difesa sui gialli e sui falli come ausiliaria) e comuni (DC gol, xG, pi-ratings, dummy di lega), alpha 1e-3, training dal 2016/17 stagione per stagione, totale = Binomiale Negativa con alpha a momenti. Test: tutte le partite dal 2019/20 con gialli, falli e corner disponibili.

**Arbitro**: dalla tabella `games` di Transfermarkt, abbinando ogni partita di campionato per (campionato, stagione, club casa, club ospite) con i `club_id` di `transfermarkt_aliases.py` (come nel round 4). Nome normalizzato (minuscolo, senza accenti né titoli «Dr.»/«Prof.»); chiave arbitro = (campionato, nome normalizzato). Controllo di coerenza: nella Premier League si confronta con la colonna `Referee` di football-data (stesso cognome normalizzato e stessa iniziale). Si riportano copertura per lega e stagione, numero di arbitri distinti e partite per arbitro.

**Effetto arbitro** (solo partite precedenti, data strettamente anteriore):
- Per ogni partita passata j dell'arbitro, con gialli totali y_j e totale atteso dal modello m_j (previsione walk-forward fuori campione per le stagioni ≥ 2019/20; per il 2016/17-2018/19, previsione in campione del modello del primo fold di test), si calcola R = (Σ y_j + k·m̄) / (Σ m_j + k·m̄), con k = «partite equivalenti» di shrinkage (empirical Bayes: k partite fittizie in cui y = m) e m̄ = media dei totali attesi della lega nel 2016/17-2018/19. Storico solo dal 2016/17. Arbitro senza partite precedenti (o sconosciuto) → R = 1, cioè effetto zero.
- **Due forme**: **(a)** moltiplicativa: le due medie attese (casa e ospite) sono moltiplicate per R (esponente fisso 1) e l'alpha della Binomiale Negativa si ristima a momenti sul training con le medie corrette; **(b)** regressore: log R entra come feature in entrambe le regressioni di Poisson (coefficiente appreso), alpha a momenti come nel baseline.
- **Griglia (10 configurazioni)**: k ∈ {5, 10, 20, 40, 80} × forma ∈ {a, b}. Ordine di semplicità: forma (a) prima di (b); k crescente. Metrica di scelta: log-loss del totale (−log p della Binomiale Negativa sul totale osservato, media per partita) in validazione.
- **G2 (variante falli)**: alla forma (b) con il k scelto si aggiunge un secondo regressore, log R_f, effetto arbitro sui falli calcolato come sopra con y = falli totali osservati e m = falli totali attesi dal modello Poisson attacco/difesa sui falli (la statistica ausiliaria del modello dei gialli). Confronto con baseline e con G1 (forma b, stesso k).
- **Rossi**: il modello non ha un modello dei rossi (nessuna colonna dei rossi nel dataset parsato): non applicabile, si dice e non si inventa.
- **Placebo**: con la configurazione scelta, i nomi degli arbitri sono permutati a caso tra le partite dello stesso campionato e stagione (seme fisso): il guadagno deve sparire.

**Metriche (tutte sullo stesso insieme di partite, baseline vs variante)**: log-loss del totale gialli (principale); correlazione per squadra (casa e ospite insieme) e del totale tra medie previste e gialli osservati; MAE del totale; log-loss delle linee Over/Under mostrate sul sito (2.5, 3.5, 4.5, 5.5) in media e per linea; copertura dell'intervallo all'80% del totale (obiettivo 0.80). IC per partita e a blocchi su tutte le metriche appaiate.

### H — Corner, solo come controllo

Stessa procedura applicata ai **corner** (modello dei corner del sito: Poisson attacco/difesa sui corner, ausiliaria = tiri), **senza scelta di parametri**: si usano forma e k scelti per G. L'arbitro non dovrebbe influire sui corner: se il guadagno è distinguibile da zero (IC a blocchi su tutte le stagioni che esclude lo zero) lo si segnala come possibile problema di abbinamento delle partite (o di un effetto reale dell'arbitro), da indagare.

### Se G migliora

Si descrive (senza implementare) come ottenere gratis e in automatico l'arbitro designato per le partite future, con copertura e tempistica per lega e cosa mostrare quando non è ancora noto.


## Esperimento G — Arbitro nel modello dei cartellini gialli

### Abbinamento e copertura

Quota di partite di campionato con arbitro (abbinate a una partita Transfermarkt con arbitro indicato):

| Stagione | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| 2014/15 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| 2015/16 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| 2016/17 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| 2017/18 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| 2018/19 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| 2019/20 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| 2020/21 | 100.0% | 100.0% | 100.0% | 98.9% | 100.0% |
| 2021/22 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| 2022/23 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| 2023/24 | 100.0% | 100.0% | 100.0% | 99.7% | 100.0% |
| 2024/25 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| 2025/26 | 100.0% | 100.0% | 100.0% | 100.0% | 99.7% |
| 2026/27 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |

Dal 2016/17 (inizio dello storico dei modelli): 17931/18230 partite con arbitro. La stagione 2026/27 non è nel dataset: arbitro sconosciuto → effetto zero.

Arbitri distinti (dal 2016/17) e partite mediane per arbitro:

| Lega | Arbitri distinti | Partite mediane per arbitro |
|---|---:|---:|
| Serie A | 85 | 22 |
| Premier League | 44 | 60 |
| Bundesliga | 39 | 77 |
| La Liga | 47 | 59 |
| Ligue 1 | 53 | 49 |

Totale arbitri distinti: 268 (chiave = lega + nome).

**Controllo di coerenza con football-data (colonna `Referee`, solo Premier League)**: su 4560 partite 2014/15-2026/27 con arbitro in entrambe le fonti, stesso arbitro (stesso cognome e stessa iniziale) nel **97.6%** dei casi. Per le altre leghe football-data non ha l'arbitro: il controllo non è possibile.

Esempi di disaccordo: QPR-Sunderland 2014: TM «bobby madley» / FD «R Madley»; Leicester-Sunderland 2014: TM «bobby madley» / FD «R Madley»; Everton-Hull 2014: TM «bobby madley» / FD «R Madley»; Swansea-Tottenham 2014: TM «bobby madley» / FD «R Madley»; Aston Villa-Crystal Palace 2014: TM «bobby madley» / FD «R Madley».

### Baseline e insieme di valutazione

12751 partite di test (dal 2019/20) con gialli, falli e corner disponibili; stesso insieme per baseline e varianti. Baseline gialli: log-loss del totale 2.1186, correlazione per squadra 0.262, MAE 1.636, copertura 80% 0.867; media dei gialli per partita 4.08.

### Griglia: effetto arbitro sui gialli (10 configurazioni, ogni riga da sola vs baseline)

Δ = log-loss del totale (baseline − variante); forma a = moltiplicativa, b = regressore appreso; k = partite equivalenti di shrinkage.

| Forma | k | Log-loss totale | Δ tutte [IC a blocchi] | Δ validazione | Δ held-out [IC a blocchi] | Δ log-loss Over/Under | Δ corr. per squadra |
|---|---:|---:|---|---:|---|---:|---:|
| a | 5 | 2.1109 | +0.00770 [+0.00415, +0.01119] | +0.00808 | +0.00742 [+0.00293, +0.01173] | +0.00526 | +0.01808 |
| a | 10 | 2.1096 | +0.00902 [+0.00586, +0.01215] | +0.00979 | +0.00845 [+0.00436, +0.01237] | +0.00595 | +0.01952 |
| a | 20 | 2.1088 | +0.00979 [+0.00705, +0.01254] | +0.01087 | +0.00900 [+0.00540, +0.01245] | +0.00629 | +0.02015 |
| a | 40 | 2.1089 | +0.00971 [+0.00745, +0.01198] | +0.01084 | +0.00889 [+0.00588, +0.01176] | +0.00612 | +0.01943 |
| a | 80 | 2.1100 | +0.00859 [+0.00688, +0.01032] | +0.00947 | +0.00795 [+0.00565, +0.01020] | +0.00534 | +0.01697 |
| b | 5 | 2.1092 | +0.00940 [+0.00730, +0.01144] | +0.00993 | +0.00901 [+0.00637, +0.01157] | +0.00575 | +0.01837 |
| b | 10 | 2.1087 | +0.00989 [+0.00763, +0.01210] | +0.01057 | +0.00939 [+0.00653, +0.01215] | +0.00607 | +0.01935 |
| b | 20 | 2.1085 | +0.01016 [+0.00771, +0.01259] | +0.01101 | +0.00954 [+0.00646, +0.01253] | +0.00628 | +0.02001 |
| b | 40 | 2.1085 | +0.01010 [+0.00742, +0.01277] | +0.01110 | +0.00937 [+0.00601, +0.01256] | +0.00631 | +0.02016 |
| b | 80 | 2.1090 | +0.00966 [+0.00673, +0.01253] | +0.01076 | +0.00886 [+0.00533, +0.01225] | +0.00611 | +0.01971 |

**Scelta sulle validazione** (log-loss del totale; parità entro 0.0002 → la più semplice): **forma b, k = 20** (Δ validazione +0.01101). Verdetto: **migliora**.

**G1 — effetto arbitro sui gialli, forma b, k=20 (variante scelta)**

| Metrica | Baseline | Variante | Δ | IC per partita | IC a blocchi |
|---|---:|---:|---:|---|---|
| Log-loss del totale (NB) | 2.1186 | 2.1085 | +0.01016 | [+0.00769, +0.01254] | [+0.00771, +0.01259] |
| Log-loss Over/Under (media 4 linee) | 0.5886 | 0.5823 | +0.00628 | [+0.00483, +0.00773] | [+0.00488, +0.00769] |
| MAE del totale | 1.6357 | 1.6179 | +0.01783 | [+0.01300, +0.02254] | [+0.01339, +0.02240] |
| Copertura intervallo 80% (obiettivo 0.80) | 0.8672 | 0.8697 | +0.00243 | [-0.00039, +0.00525] | [-0.00045, +0.00525] |
| Correlazione per squadra | 0.2618 | 0.2818 | +0.02001 | — | [+0.01595, +0.02404] |
| Correlazione del totale | 0.2851 | 0.3153 | +0.03013 | — | [+0.02393, +0.03688] |

Log-loss Over/Under per linea (Δ = baseline − variante, IC a blocchi): 2.5: 0.5327 → 0.5277 (Δ +0.00507 [+0.00335, +0.00674]); 3.5: 0.6533 → 0.6465 (Δ +0.00686 [+0.00508, +0.00871]); 4.5: 0.6443 → 0.6367 (Δ +0.00755 [+0.00579, +0.00938]); 5.5: 0.5241 → 0.5185 (Δ +0.00566 [+0.00388, +0.00741]).

Log-loss del totale per periodo: validazione Δ +0.01101 [+0.00714, +0.01477] (n=5377); held-out Δ +0.00954 [+0.00646, +0.01253] (n=7374).

Nei dati di test l'arbitro è noto per il 97.7% delle partite; |log R| mediano 0.054 (R tra 0.87 e 1.13 tra il 5° e il 95° percentile).

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss totale | +0.0189 | +0.0080 | +0.0065 | +0.0097 | +0.0033 | +0.0116 | +0.0150 | +0.0011 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss totale | +0.0173 | +0.0052 | +0.0013 | +0.0167 | +0.0083 |

### G2 — in più l'effetto arbitro sui falli (forma b, stesso k)

Regressore aggiuntivo log R_f: rapporto tra falli osservati e attesi (modello Poisson attacco/difesa sui falli) nelle partite passate dell'arbitro. Il modello non ha un modello dei rossi: la variante «rossi» non è applicabile.

**G2 vs baseline (k=20)**

| Metrica | Baseline | Variante | Δ | IC per partita | IC a blocchi |
|---|---:|---:|---:|---|---|
| Log-loss del totale (NB) | 2.1186 | 2.1085 | +0.01011 | [+0.00766, +0.01249] | [+0.00765, +0.01256] |
| Log-loss Over/Under (media 4 linee) | 0.5886 | 0.5824 | +0.00626 | [+0.00482, +0.00771] | [+0.00486, +0.00767] |
| MAE del totale | 1.6357 | 1.6180 | +0.01771 | [+0.01289, +0.02243] | [+0.01326, +0.02229] |
| Copertura intervallo 80% (obiettivo 0.80) | 0.8672 | 0.8693 | +0.00204 | [-0.00078, +0.00486] | [-0.00086, +0.00487] |
| Correlazione per squadra | 0.2618 | 0.2817 | +0.01988 | — | [+0.01579, +0.02395] |
| Correlazione del totale | 0.2851 | 0.3151 | +0.03000 | — | [+0.02375, +0.03674] |

Log-loss Over/Under per linea (Δ = baseline − variante, IC a blocchi): 2.5: 0.5327 → 0.5277 (Δ +0.00507 [+0.00335, +0.00674]); 3.5: 0.6533 → 0.6465 (Δ +0.00682 [+0.00503, +0.00868]); 4.5: 0.6443 → 0.6367 (Δ +0.00752 [+0.00575, +0.00936]); 5.5: 0.5241 → 0.5185 (Δ +0.00565 [+0.00387, +0.00739]).

Log-loss del totale per periodo: validazione Δ +0.01099 [+0.00710, +0.01474] (n=5377); held-out Δ +0.00947 [+0.00637, +0.01246] (n=7374).

G2 rispetto a G1 (forma b, k=20): Δ log-loss totale -0.00005, IC a blocchi [-0.00010, +0.00000].

### Placebo

Arbitri permutati a caso tra le partite dello stesso campionato e stagione, stessa configurazione (forma b, k=20): Δ log-loss del totale +0.00013, IC a blocchi [-0.00015, +0.00042] (con gli arbitri veri: +0.01016).

## Esperimento H — Corner, controllo

Stessa procedura applicata ai corner con la configurazione scelta per G (forma b, k=20), senza scelta di parametri. Baseline corner: log-loss del totale 2.6157.

**H — effetto arbitro sui corner**

| Metrica | Baseline | Variante | Δ | IC per partita | IC a blocchi |
|---|---:|---:|---:|---|---|
| Log-loss del totale (NB) | 2.6157 | 2.6150 | +0.00067 | [+0.00033, +0.00101] | [+0.00033, +0.00100] |
| Log-loss Over/Under (media 4 linee) | 0.6472 | 0.6467 | +0.00050 | [+0.00027, +0.00072] | [+0.00027, +0.00072] |
| MAE del totale | 2.6820 | 2.6794 | +0.00257 | [+0.00146, +0.00368] | [+0.00146, +0.00371] |
| Copertura intervallo 80% (obiettivo 0.80) | 0.8410 | 0.8415 | +0.00047 | [-0.00071, +0.00173] | [-0.00063, +0.00163] |
| Correlazione per squadra | 0.3597 | 0.3602 | +0.00054 | — | [+0.00023, +0.00086] |
| Correlazione del totale | 0.1537 | 0.1567 | +0.00301 | — | [+0.00128, +0.00477] |

Log-loss Over/Under per linea (Δ = baseline − variante, IC a blocchi): 8.5: 0.6592 → 0.6587 (Δ +0.00048 [+0.00023, +0.00074]); 9.5: 0.6863 → 0.6857 (Δ +0.00057 [+0.00029, +0.00084]); 10.5: 0.6594 → 0.6589 (Δ +0.00050 [+0.00024, +0.00076]); 11.5: 0.5841 → 0.5836 (Δ +0.00043 [+0.00019, +0.00067]).

Log-loss del totale per periodo: validazione Δ +0.00016 [-0.00021, +0.00053] (n=5377); held-out Δ +0.00104 [+0.00053, +0.00156] (n=7374).

Esito del controllo: Δ log-loss del totale +0.00067, IC a blocchi su tutte le stagioni [+0.00033, +0.00100] → **distinguibile da zero**: possibile problema di abbinamento (o effetto reale dell'arbitro), da indagare.


### Analisi aggiuntiva (NON prevista dal prereg): da dove viene il segnale sui corner?

Premier League: accordo sul solo cognome tra Transfermarkt e football-data = 99.6% su 4560 partite (le differenze rimaste a livello di iniziale sono nomi diversi della stessa persona, es. «Bobby» / «R Madley»).

**Δ log-loss del totale per lega (arbitri da Transfermarkt, forma b, k=20; IC a blocchi)**

| Lega | Gialli | Corner |
|---|---|---|
| Serie A | +0.01732 [+0.01221, +0.02250] | +0.00149 [+0.00072, +0.00229] |
| Premier League | +0.00521 [+0.00059, +0.00978] | +0.00012 [-0.00046, +0.00069] |
| Bundesliga | +0.00132 [-0.00396, +0.00657] | +0.00079 [-0.00018, +0.00175] |
| La Liga | +0.01669 [+0.01015, +0.02342] | +0.00044 [-0.00036, +0.00124] |
| Ligue 1 | +0.00826 [+0.00289, +0.01355] | +0.00051 [-0.00020, +0.00122] |

**Premier League, stessa procedura con le due fonti dell'arbitro** (football-data = fonte indipendente dall'abbinamento Transfermarkt)

| Fonte | Gialli | Corner |
|---|---|---|
| Transfermarkt | +0.00521 [+0.00059, +0.00978] | +0.00012 [-0.00046, +0.00069] |
| football-data (colonna Referee) | +0.00582 [+0.00141, +0.01025] | +0.00000 [-0.00033, +0.00034] |


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


## Tabella riassuntiva

12751 partite di test (2019/20 → 2026-10-12). Δ = baseline − variante per le perdite (log-loss del totale, Over/Under, MAE), variante − baseline per le correlazioni; positivo = variante migliore. Validazione = 2019/20-2021/22, held-out = 2022/23 →. Per le statistiche attese non esiste un riferimento di mercato nei dati: la colonna «distanza dalle quote di chiusura» non si applica.

| Variante | Log-loss totale (base → var.) | Δ tutte [IC per partita] | IC a blocchi | Δ validazione | Δ held-out [IC a blocchi] | Δ Over/Under | Δ MAE | Δ corr. squadra | Δ corr. totale |
|---|---|---|---|---:|---|---:|---:|---:|---:|
| **G1 — gialli, arbitro forma b, k=20 (scelta)** | 2.1186 → 2.1085 | +0.01016 [+0.00769, +0.01254] | [+0.00771, +0.01259] | +0.01101 | +0.00954 [+0.00646, +0.01253] | +0.00628 | +0.0178 | +0.0200 | +0.0301 |
| G1 — gialli, forma a (moltiplicativa), k=20 | 2.1186 → 2.1088 | +0.00979 [+0.00694, +0.01253] | [+0.00705, +0.01254] | +0.01087 | +0.00900 [+0.00540, +0.01245] | +0.00629 | +0.0149 | +0.0201 | +0.0303 |
| G1 — gialli, forma b, k=5 (shrinkage minimo) | 2.1186 → 2.1092 | +0.00940 [+0.00735, +0.01140] | [+0.00730, +0.01144] | +0.00993 | +0.00901 [+0.00637, +0.01157] | +0.00575 | +0.0166 | +0.0184 | +0.0276 |
| G1 — gialli, forma b, k=80 (shrinkage massimo) | 2.1186 → 2.1090 | +0.00966 [+0.00677, +0.01246] | [+0.00673, +0.01253] | +0.01076 | +0.00886 [+0.00533, +0.01225] | +0.00611 | +0.0166 | +0.0197 | +0.0299 |
| G2 — gialli + arbitro sui falli (b, k=20) | 2.1186 → 2.1085 | +0.01011 [+0.00766, +0.01249] | [+0.00765, +0.01256] | +0.01099 | +0.00947 [+0.00637, +0.01246] | +0.00626 | +0.0177 | +0.0199 | +0.0300 |
| Placebo — arbitri permutati (b, k=20) | 2.1186 → 2.1185 | +0.00013 [-0.00014, +0.00040] | [-0.00015, +0.00042] | -0.00020 | +0.00037 [+0.00006, +0.00066] | +0.00012 | +0.0004 | +0.0001 | +0.0002 |
| **H — corner con arbitro (controllo, b, k=20)** | 2.6157 → 2.6150 | +0.00067 [+0.00033, +0.00101] | [+0.00033, +0.00100] | +0.00016 | +0.00104 [+0.00053, +0.00156] | +0.00050 | +0.0026 | +0.0005 | +0.0030 |

Verdetto G (regola scritta prima: Δ held-out sul totale gialli > 0 con IC a blocchi che esclude lo zero): **migliora**. Controllo H: distinguibile da zero (vedi commento).


## Commento

1. **G: l'arbitro migliora in modo netto il modello dei gialli.** Con la configurazione scelta sulle validazione (regressore, k = 20) la log-loss del totale scende di 0.0102 (IC a blocchi [+0.0077, +0.0126]; validazione +0.0110, held-out +0.0095), la log-loss degli Over/Under mostrati sul sito di 0.0063, il MAE di 0.018 gialli, la correlazione per squadra sale da 0.262 a 0.282 e quella del totale da 0.285 a 0.315. Tutte le 10 configurazioni della griglia migliorano, con Δ tra +0.0077 e +0.0102: il risultato non dipende dalla scelta di forma o shrinkage. Tutte le stagioni sono positive (da +0.0011 nel 2026/27, senza arbitri, a +0.0189 nel 2019/20); per lega l'effetto è forte in Serie A (+0.017) e La Liga (+0.017), medio in Ligue 1 (+0.008) e Premier League (+0.005), nullo in Bundesliga (+0.001, IC che include lo zero).
2. **È un effetto grande rispetto a tutti i round precedenti** (Elo-Odds valeva +0.003 sul 1X2), ma sono metriche diverse: qui la log-loss è quella del totale dei gialli (≈ 2.12 per partita), non l'1X2. In termini relativi, la dimensione tipica dell'effetto è modesta: R tra 0.87 e 1.13 tra il 5° e il 95° percentile (un arbitro «severo» vale circa +13% di gialli rispetto all'atteso).
3. **Controlli superati.** Il placebo (arbitri permutati tra le partite della stessa lega e stagione) dà +0.0001 su tutte le stagioni con IC che include lo zero (nella sola parte held-out +0.0004, IC a blocchi [+0.0001, +0.0007], 25 volte meno del valore con gli arbitri veri: è la parte di guadagno che viene dal solo ristimare il modello con un regressore in più), contro +0.0102 con gli arbitri veri; la Premier League con l'arbitro di football-data (fonte indipendente dall'abbinamento Transfermarkt) dà lo stesso risultato (+0.0058 contro +0.0052). L'accordo sul cognome tra le due fonti è 99.6% su 4.560 partite (97.6% con anche l'iniziale: le differenze sono nomi diversi della stessa persona, es. «Bobby»/«R Madley»).
4. **Copertura**: arbitro noto per il 98.9-100% delle partite di ogni lega e stagione dal 2014/15 al 2025/26 (le uniche lacune: La Liga 2020/21 98.9% e 2023/24 99.7%, Ligue 1 2025/26 99.7%), 268 arbitri distinti (lega + nome) dal 2016/17, da 22 a 77 partite mediane per arbitro a seconda della lega (Serie A più bassa: 85 arbitri). La stagione 2026/27 non è nel dataset: arbitro sconosciuto, effetto zero.
5. **G2, falli**: aggiungere l'effetto arbitro sui falli non migliora (Δ rispetto a G1 −0.00005, IC a blocchi [−0.0001, +0.0000]): l'informazione sul numero di gialli è già nell'effetto sui gialli. **Rossi**: il modello non ha un modello dei rossi, quindi la variante non è applicabile.
6. **Coerenza della calibrazione**: la copertura dell'intervallo all'80% resta intorno a 0.87 (obiettivo 0.80, già sopra-coperto nel baseline: l'alpha della Binomiale Negativa è troppo alto) e non cambia in modo significativo (+0.0024, IC che include lo zero); non è stato toccato.
7. **H, corner (controllo)**: l'arbitro dovrebbe contare poco, e conta poco: Δ +0.0007 sulla log-loss del totale (IC a blocchi [+0.0003, +0.0010]), cioè 15 volte meno dei gialli. Per la regola scritta prima è «distinguibile da zero» e quindi va indagato: l'analisi aggiuntiva mostra che non somiglia a un problema di abbinamento. Per lega il segnale è tutto in Serie A (+0.0015, IC [+0.0007, +0.0023]); in Premier League è zero sia con l'arbitro di Transfermarkt sia con quello di football-data (+0.0001 e 0.0000). Un abbinamento sbagliato non spiegherebbe perché il segnale dei gialli, molto più forte, sia identico con le due fonti. L'ipotesi più semplice è un effetto reale piccolo (stile di gioco/interruzioni) in una lega; non lo ho verificato oltre.
8. **Per la produzione** (non implementato, come richiesto): l'arbitro designato non è ancora disponibile in modo affidabile da una fonte gratuita già in uso (football-data.org lo riporta oggi solo per 1 partita su 111 nelle prossime due settimane); le fonti ufficiali delle leghe lo pubblicano da un giorno a qualche giorno prima (tempistica verificata solo in parte, dettagli sopra). In più serve raccogliere noi lo storico dell'arbitro delle partite giocate, perché il dataset Transfermarkt non è aggiornato ogni giorno. Il guadagno è però il più grande che questa serie di round ha trovato sulle statistiche attese: vale la pena misurare per un paio di mesi la copertura e la tempistica reali prima di implementare.
