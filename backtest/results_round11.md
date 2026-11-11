# Round 11 — margine sul mercato (solo backtest)

**La produzione non è stata toccata.** Criteri nel prereg qui sotto (scritto prima di eseguire le analisi; V5 e V6 aggiunti con il loro prereg prima di calcolarli). Rilancio: `python -I -X utf8 backtest/run_round11.py [V1|V2|V3]` (V1 con cache in `round11_parts/_v1cache`, `R11_MAXNEW=n` configurazioni per invocazione), `python -I -X utf8 backtest/run_round11_v56.py` (V5 e V6), poi `run_round11_final.py`.

---

## Tabella riassuntiva

Held-out = 2022/23 in poi (2026/27 in corso incluso); validazione = 2019/20-2021/22 (per V1, 2020/21-2021/22: il 2019/20 serve solo come primo addestramento). Tra parentesi quadre gli IC 95 % a blocchi per settimana ISO.

| Parte | Domanda | Risultato nell'held-out | Verdetto |
|---|---|---|---|
| V1 · 1X2, quote di **chiusura** (AvgC) | il modello aggiunge informazione? | peso del modello w_m = 0,024 [−0,194; 0,247]; peso del mercato 1,062. Guadagno di log-loss rispetto al solo mercato calibrato −0,00003 [−0,00025; +0,00020] | **no** |
| V1 · 1X2, quote **pre-partita** (Avg) | idem | w_m = −0,020 [−0,272; 0,227]; guadagno +0,00001 [−0,00020; +0,00021] | **no** |
| V1 · Over/Under 2,5, chiusura | idem | w_m = −0,071 [−0,311; 0,183]; guadagno −0,00004 [−0,00012; +0,00004] | **no** |
| V1 · Over/Under 2,5, pre-partita | idem | w_m = +0,066 [−0,210; 0,350]; guadagno −0,00006 [−0,00034; +0,00021] | **no** |
| V2 · correlazione divario → spostamento | la quota si sposta verso il modello? | 1X2: correlazione −0,000 [−0,030; 0,030], pendenza controllata 0,002 [−0,019; 0,024]; Over 2,5: −0,014 [−0,039; 0,013] | **no** |
| V2 · divergenze > soglia | verso il modello più del 50 %? | 1X2 (τ = 8 scelta): 53,8 % [48,4; 59,0], +0,33 pt [−0,05; +0,72], 669 casi; Over 2,5 (τ = 5): 46,7 % [44,6; 48,8], −0,08 pt [−0,20; +0,04] | **no in generale**; debole tendenza verso il modello solo per divari ≥ 8 punti sul 1X2 (IC che sfiora lo zero), non sull'Over |
| V3 · scommesse 1X2, quote **massime** (θ = 0,20) | rendimento a puntata fissa | 1.133 scommesse, ROI −19,3 % [−30,7; −7,8], CLV −1,3 % [−2,5; 0,0] (puntare tutto alla Max: CLV −1,6 %) | **perdente** |
| V3 · scommesse 1X2, quote **medie** (θ = 0,20) | idem | 499 scommesse, ROI −25,5 % [−39,5; −11,4], CLV −8,9 % | **perdente** |
| V3 · scommesse Over/Under 2,5 (Max θ = 0,10 / Avg θ = 0,08) | idem | Max: 1.840 scommesse, ROI −4,2 % [−9,1; +0,8], CLV −3,5 %; Avg: 1.357 scommesse, ROI −8,7 % [−14,5; −3,0] | **perdente** |
| V4 · mercati secondari | registro quote: costi e limiti | The Odds API: piano gratuito (500 crediti/mese) copre 1 istantanea per partita × 2 mercati (≈ 416 crediti); servono ≈ 1.250 crediti/mese per 2 istantanee × 3 mercati. **Tiri solo per giocatore, falli non trovati** | da decidere (vedi V4) |
| V5a · favorite in trasferta, Serie A | l'anomalia si conferma? | soglia scelta in validazione 45 %: eccesso +6,2 pt [+1,2; +11,0]; nel 2013/14-2018/19 (indipendente) +3,1 pt [−1,2; +7,2] | **coerente nel periodo di scoperta, non confermata** |
| V5b · il modello la cattura? | modello vs mercato sul sottoinsieme | il modello dà all'ospite il 54,5 % contro il 56,5 % del mercato (osservato 62,7 %); log-loss del modello peggiore di 0,020 [0,010; 0,030] | **no, fa peggio del mercato** |
| V5c · correzione Serie A (K2) | guadagno complessivo | Δ log-loss +0,00082 [−0,00034; +0,00193] su 5 leghe; +0,0038 [−0,0013; +0,0090] sulla sola Serie A | **non distinguibile dal rumore** |
| V5d · scommesse sulle favorite in trasferta (quota media) | rendimento, drawdown | held-out 365 scommesse, ROI +7,4 % [−1,6; +16,2]; scoperta 658 scommesse ROI +9,3 % [+2,8; +15,8]; 2013/14-2018/19 ROI +2,5 % [−5,1; +9,6]; drawdown massimo 9,7 unità (atteso 6,6-21,1) | positivo in scoperta, non confermato fuori |
| V6 · controllo dell'anomalia | quanto è facile trovarne una per caso? | cella Serie A: z = 3,60; probabilità che **almeno una delle 105 celle** abbia z ≥ 3,60 per puro caso: **1,7 %** (ROI: 2,9 %) | non è solo rumore sulle 105 celle; ma altre anomalie emergono nelle condizioni scelte in anticipo |

## Commento onesto

**1. V1 e V2 non mostrano alcuna informazione aggiuntiva del modello rispetto al mercato: lo dico chiaramente.**
- Combinando le log-probabilità del modello e del mercato, il peso del modello è zero in tutte le otto configurazioni (1X2 e Over/Under 2,5; chiusura e pre-partita; più due sensibilità con B365 e Pinnacle): nell'held-out va da −0,10 a +0,07 con IC larghi circa ±0,2-0,3, quello del mercato resta vicino a 1. Il guadagno di log-loss è dell'ordine di 10⁻⁴ o meno, di segno variabile, con IC che comprendono sempre lo zero; per lega i guadagni restano dell'ordine di 10⁻⁴ (tabelle sotto) e i pesi per stagione oscillano intorno a zero (solo il 2026/27, 447 partite, mostra +0,5, con errore standard di circa 0,4). Il modello da solo ha una log-loss peggiore del mercato di 0,006-0,009 sul 1X2 (0,9736 contro 0,9651 alla chiusura e 0,9673 alle quote pre-partita) e di 0,005-0,008 sull'Over 2,5.
- Non cambia nulla usando le quote raccolte giorni prima invece di quelle di chiusura: il modello non ha informazione che il mercato di giorni prima non avesse già. È coerente col fatto che nel modello c'è già una feature costruita sulle quote passate (Elo-Odds): la parte che non viene dal mercato non aggiunge nulla alla quota della partita.
- Il divario modello − quota pre-partita non predice lo spostamento successivo verso la chiusura (correlazione −0,000 sul 1X2, −0,014 sull'Over 2,5). Con divergenze oltre 8 punti sul 1X2 la quota si muove verso il modello nel 53,8 % dei casi (IC 48,4-59,0 %, comprende il 50 %) e di +0,33 pt in media (IC [−0,05; +0,72]); nella validazione era +0,39 pt con IC sopra zero (da lì la scelta di τ = 8). È l'unico accenno di segnale del round: piccolo, poche partite (669), ai bordi della significatività e solo sul 1X2; con τ = 3 e 5 non c'è nulla. Sull'Over 2,5 il segno è opposto (−0,08 pt). Un'unica cella isolata va nominata: nella Serie A, sui divari di 8 punti, lo spostamento verso il modello è +1,2 pt nella validazione e +0,8 pt nell'held-out (entrambi con IC sopra zero, 199 e 116 casi); è una cella su dieci (5 leghe × 2 finestre) senza correzione per le molteplicità e a ridosso dell'anomalia di V5: la riporto, non la valorizzo.
- Attenzione a cosa non dimostra: tra la raccolta pre-partita e la chiusura arrivano formazioni e infortuni che il modello non vede, quindi un modello migliore di questo potrebbe comunque non muovere il mercato. V1 è il test più forte e dice lo stesso.

**2. V3 conferma, non smentisce.** Con le quote massime il ROI nell'held-out è −19 % sul 1X2 (IC interamente sotto zero) e −4 % sull'Over/Under 2,5; con le quote medie, che sono quelle realistiche, −25 % e −9 %. Con le quote massime le soglie scelte in validazione davano ROI positivi (+1,9 % e +3,5 %), che nell'held-out non reggono, come ci si aspetta quando non c'è un vantaggio reale. Il CLV delle scommesse selezionate (−1,3 % sul 1X2 con la Max) è praticamente quello di puntare su tutto alla Max (−1,6 %): la selezione non porta a prezzi migliori della chiusura. Potenza: con poche migliaia di scommesse l'IC del ROI è di diversi punti, quindi V3 non potrebbe dimostrare un vantaggio piccolo; ma qui non c'è neppure un vantaggio piccolo.

**3. V5 — favorite in trasferta in Serie A: l'effetto c'è nei dati usati per scoprirlo, ma non posso dirlo confermato.**
- Riproduzione: ritrovo 822-830 partite (a seconda del metodo di calcolo del margine), 60,4-60,7 % di vittorie contro 53,3-54,3 %, ROI +8,0/+8,4 % alle quote pre-partita e +8,1/+8,6 % a quelle di chiusura, positivo in tutte le 8 stagioni (la 8ª è la parziale 2026/27, 26 partite): i numeri tornano, con una stagione in più positiva rispetto a quella indicata.
- Nell'held-out l'eccesso è +6,2 punti con IC [1,2; 11,0] a soglia 45 % (scelta in validazione; a 40 % è +6,0 [1,6; 10,6]), ma l'**held-out non è indipendente dall'ipotesi** (le stagioni 2019/20-2026/27 sono quelle in cui è stata trovata). La verifica davvero esterna sono le sei stagioni 2013/14-2018/19: eccesso positivo (+3,1 pt) ma circa la metà e con IC [−1,2; +7,2], compatibile con zero. Anche nella Premier, nello stesso periodo, la stessa regola dava +3,9 [−0,1; +7,9], poi −0,8: nei campionati diversi dalla Serie A l'effetto non ricompare dopo il 2019.
- Il ROI è meno solido dell'eccesso: held-out +7,4 % con IC [−1,6; +16,2] (comprende lo zero), scoperta +9,3 % [+2,8; +15,8]. Il ROI alla chiusura è uguale a quello pre-partita: il mercato non «corregge» lo sbaglio tra la raccolta e la chiusura. Il drawdown massimo osservato (9,7 unità nell'held-out) è nella norma (atteso 6,6-21,1).
- **Il modello v6 non lo cattura, anzi** (V5b): sulle partite con ospite favorito dà all'ospite il 54,5 % (mercato 56,5 %, osservato 62,7 %) e ha una log-loss peggiore del mercato di 0,020. Su tutta la Serie A è peggiore del mercato di 0,007. È normale: il modello eredita la struttura del mercato e in più usa un vantaggio casa medio.
- La correzione specifica della Serie A (V5c) impara coefficienti sensati (intercetta di vantaggio casa e interazione «ospite favorito» b ≈ +0,3/+0,4) ma il guadagno complessivo nell'held-out è +0,0008 con IC [−0,0003; +0,0019]: non distinguibile dal rumore, ed è stimato sulle stesse stagioni dell'anomalia. Non è da portare in produzione.

**4. V6 — le anomalie non sono tutte rumore, e questo complica la lettura.**
- La simulazione nulla (il mercato è calibrato, 10.000 simulazioni) dà alla cella della Serie A una probabilità di cella dello 0,03 % e una **probabilità di famiglia dell'1,7 %** (ROI: 2,9 %) su 105 celle: per un eccesso di questa grandezza servirebbero circa 2.000-3.000 prove indipendenti perché emerga per caso una volta su due. Se la ricerca originale era più ampia della mia famiglia, l'argomento si indebolisce: non lo posso sapere.
- Ma i numeri complessivi dicono che la calibrazione del mercato non è perfetta in generale: nella famiglia ci sono 7 celle con z ≥ 2,5 contro 0,7 attese (sono in realtà due gruppi: la Serie A ospite favorito e La Liga favorita in casa con p ≥ 55-60 %); delle 24 celle scelte in anticipo, 5 hanno |z| > 2 (attese circa 1; le celle sono però correlate). Le più forti: Serie A ospite favorito (z = 3,60), Serie A outsider in casa (z = −2,72, ROI −36 %: è lo stesso insieme di partite visto dal lato opposto, non un'evidenza indipendente), La Liga favorita in casa (z = 2,63, ROI +5,2 %, 7 stagioni su 8 positive, ma 2013/14-2018/19 +0,5 pt), pareggi tra squadre equilibrate nei cinque campionati (z = 2,61, +2,3 pt, ma ROI +2,1 % non distinguibile da zero perché il margine sui pareggi è alto). In quattro campionati su cinque la condizione di V5 non dà nulla.
- Lettura prudente: in Serie A un piccolo bias favorita/sfavorita probabilmente esiste (le favorite vincono più di quanto dica la quota, gli outsider meno; l'eccesso 2013/14-2018/19 è già positivo, +3 pt), ma l'ampiezza osservata dopo il 2019 è quella che si sovrastima quando si seleziona l'effetto più forte tra molte possibilità: la stima fuori campione, circa la metà, è la più onesta. Non è dimostrato.

**5. Cosa farei (non lo faccio senza il tuo ok).** Nessuna modifica del modello né della produzione. Per l'anomalia della Serie A: monitoraggio prospettico con regola fissata ora (ospite favorito ≥ 45 % o ≥ 40 % in Serie A, quota media pre-partita, 1 unità, nessuna soglia da ottimizzare), usando ciò che `history.csv` registra già (probabilità del mercato dalle quote dei fixtures e risultato); l'estensione richiede solo uno script di resoconto. Per un eccesso di +6 punti servono circa 520 partite nuove (circa 6 stagioni al ritmo di 85-100 a stagione) per un test con potenza dell'80 %; per +3 punti (la grandezza fuori campione) circa 2.100, oltre venti stagioni: il verdetto prospettico sarà lento, e meglio aspettarselo. Per V4: serve la tua decisione sul piano (gratuito con 1 istantanea e 2 mercati, oppure ~30 $/mese) e una chiave API; tiri di squadra e falli non risultano coperti da questo fornitore.

**Limiti di questo round.** Quote medie «pre-partita» = raccolta di football-data.co.uk giorni prima, non l'apertura vera; prima del 2019/20 la fonte è BbAv/B365. Margine tolto col metodo power (la normalizzazione semplice dà gli stessi numeri a meno di 0,5 punti). Una riga di quote Over/Under di chiusura con Over a 0,42 (errore dei dati) e tre righe Pinnacle a 0,00 sono escluse da V1. Le ristime del bootstrap dei pesi sono 2.000 per ogni intervallo. I file delle pagine di The Odds API non erano leggibili da questo ambiente: V4 va verificato con una chiamata di prova prima di decidere.


---

# Preregistrazione

# Round 11 — margine sul mercato (solo backtest)

**La produzione non viene toccata.** Criteri scritti PRIMA di eseguire qualsiasi analisi del round. Stesse regole dei round precedenti: validazione 2019/20-2021/22 (solo qui si scelgono soglie e parametri), **held-out dal 2022/23** (2022/23-2025/26 più il 2026/27 in corso, riportato anche a parte), IC 95% a blocchi per settimana ISO (ricampionamento delle settimane), nessun parametro viene toccato dopo aver visto l'held-out.

## Dati
- **Modello**: stack di produzione v6 (with_xg + Elo-Odds), walk-forward per stagione (training dal 2016/17 sulle sole stagioni precedenti); probabilità 1X2 e Over 2,5 dalla matrice dei punteggi (`round7_lib.goals_walk_forward` + `goal_markets`). Le previsioni sono fuori campione solo dal 2019/20; il 2016-2018 non si usa.
- **Nota di indipendenza**: il modello contiene già una feature di mercato (Elo-Odds: rating costruiti con le quote di chiusura delle partite PASSATE; le quote della partita da prevedere non entrano mai). Quindi modello e mercato non sono indipendenti: il test misura se la parte *non* mercato del modello aggiunge qualcosa alla quota della partita stessa.
- **Mercato** (football-data.co.uk, colonne lette direttamente dai CSV in cache, backtest-only): pre-partita = media dei bookmaker `AvgH/D/A`, `Avg>2.5/<2.5` (raccolta giorni prima, non il giorno della partita), B365 (`B365H/D/A`, `B365>2.5/<2.5`) come sensibilità, `MaxH/D/A`, `Max>2.5/<2.5` per le scommesse; chiusura = `AvgCH/D/A`, `AvgC>2.5/<2.5`, Pinnacle `PSC*`/`PC>2.5` (solo dove esiste: fino al 2025/26) come sensibilità. Margine tolto col metodo power (`round2_lib.devig`).
- **Campione**: partite 2019/20+ con previsione OOS e quote valide. Ogni confronto usa lo stesso insieme di partite per tutte le sue colonne (campione comune a chiusura e pre-partita per V1 e V2).

## V1 — il modello aggiunge informazione al mercato?
**Regressione logistica multinomiale (conditional logit)**: utilità dell'esito c = a_c + w_m·log p_modello,c + w_k·log p_mercato,c, con pesi condivisi tra gli esiti e due intercette libere (a_X, a_2; a_1 = 0). Stessa cosa per Over/Under 2,5: logit P(Over) = a + w_m·logit p_modello + w_k·logit p_mercato. Si stima separatamente con **quote di chiusura (AvgC)** e **pre-partita (Avg)**; sensibilità: B365 pre-partita, Pinnacle di chiusura.
- **Walk-forward**: per la stagione s il modello combinato si stima su tutte le stagioni 2019/20…s−1 (le prime previsioni OOS sono quelle del 2019/20, che quindi servono solo da primo training); si valuta su s. Test: 2020/21 in poi; «validazione» = 2020/21-2021/22 (2019/20 non è testabile), «held-out» = 2022/23+. Nessun iperparametro da scegliere.
- **Peso del modello (w_m) con IC**: stima sull'insieme dell'held-out (2022/23+) e sull'insieme di tutte le stagioni OOS, IC 95% col bootstrap a blocchi per settimana *rifacendo la stima* (2000 ricampionamenti); si riportano anche w_k, la somma w_m + w_k e i pesi per stagione.
- **Guadagno di log-loss** (per partita; positivo = il combinato è meglio): (i) rispetto al **solo mercato calibrato** con lo stesso walk-forward (w_k e intercette, senza modello) — confronto principale, a parità di flessibilità; (ii) rispetto al **solo mercato grezzo** (probabilità senza margine). Entrambi con IC per partita e a blocchi. Riportati anche modello da solo (grezzo) e mercato grezzo.
- **Verdetto**: «il modello aggiunge informazione» solo se, nell'held-out, il guadagno (i) è > 0 con IC a blocchi che esclude lo zero **e** l'IC di w_m esclude lo zero; «non aggiunge» se il guadagno (i) ha IC che comprende lo zero o è negativo e w_m ha IC che comprende lo zero; altrimenti «informazione ambigua» (descritta). Se il guadagno rispetto al mercato grezzo è positivo ma quello rispetto al mercato calibrato no, il merito è della calibrazione, non del modello, e lo si dice.

## V2 — closing line value
Per ogni partita e per ogni esito (1, X, 2; per O/U 2,5 il lato Over, con il segno che porta al lato Under): **d = p_modello − p_pre** (pre-partita Avg senza margine) e **m = p_chiusura − p_pre** (AvgC senza margine meno Avg senza margine), in punti percentuali.
- **Correlazione** tra d e m (Pearson, partita×esito, IC a blocchi per settimana) e **pendenza** della regressione m su d (quota del divario «recuperata» dal mercato), con e senza controllo per il livello della probabilità pre-partita (effetto favorita/sfavorita), per tutti gli esiti, per esito, per lega, per O/U 2,5.
- **Soglie τ ∈ {3, 5, 8} punti**: sulle coppie partita-esito con |d| > τ si riporta la **quota di casi in cui la quota si muove verso il modello** (segno di m = segno di d; i movimenti nulli sono esclusi dalla frazione e il loro peso è riportato) e il **movimento medio verso il modello** (m·segno(d), in punti, con IC a blocchi). Il caso nullo è 50 % e 0 punti.
- **Soglia scelta in validazione**: la τ con il limite inferiore dell'IC 95 % a blocchi più alto del movimento medio verso il modello nella validazione (parità → τ più bassa). Le tre soglie sono riportate comunque nell'held-out; la tabella per esito/lega/O/U usa la τ scelta.
- Contesto da tenere presente: tra la raccolta pre-partita e la chiusura arrivano formazioni, infortuni e flussi di denaro che il modello non vede; una correlazione bassa non è di per sé un difetto. Una correlazione positiva e distinguibile da zero a parità di livello sarebbe invece il segnale di informazione che il mercato riconosce poi.

## V3 — simulazione di scommesse a puntata fissa (verifica finale)
Puntata fissa di 1 unità su ogni esito con **p_modello × quota > 1 + θ**, quota = **Max pre-partita** (miglior quota tra i bookmaker raccolti: ottimistica). Un esito per riga; più esiti della stessa partita possono qualificarsi. Mercati: 1X2 e Over/Under 2,5, ciascuno con il proprio θ.
- **θ scelta in validazione** dalla griglia {0; 0,03; 0,05; 0,08; 0,10; 0,15; 0,20}: ROI massimo nella validazione tra le soglie con almeno 150 scommesse (parità → θ più alta). Poi invariata nell'held-out.
- **Varianti quote**: (a) Max (quella principale); (b) **quote medie pre-partita (Avg)**: segnale e regolamento con le Avg, θ scelta di nuovo in validazione; (c) segnale con Max e regolamento con le Avg (misura quanto pesa l'ottimismo della Max).
- **Si riporta**: numero di scommesse, ROI (profitto / n scommesse) con IC a blocchi per settimana (ratio bootstrap, 5000), ROI per lega e per esito (1, X, 2, Over, Under), **CLV medio** delle scommesse = media di (quota giocata × p_chiusura senza margine − 1) e CLV rispetto alla quota di chiusura media grezza.
- **Riferimenti** (stesso periodo): ROI e CLV di puntare *tutti* gli esiti alla Max, e alle Avg (il costo del margine/dello spread tra Max e chiusura), per leggere il CLV delle scommesse al netto del vantaggio meccanico della Max sulla chiusura media.
- Potenza: con quote medie intorno a 3-5 la deviazione standard del profitto per scommessa è circa 2-3 unità; per poche migliaia di scommesse l'IC del ROI è di decine di punti. Il ROI non può provare un vantaggio piccolo: si legge insieme a V1 e V2 e il CLV è l'indicatore meno rumoroso.

## V4 — registro quote dei mercati secondari (preparazione, non attivazione)
Nessun codice di produzione e nessuna chiamata a servizi a pagamento. Si valuta (documentazione ufficiale al giorno dell'analisi): se il piano gratuito di The Odds API, o un'alternativa gratuita, copre per Serie A, Premier, Bundesliga, La Liga e Ligue 1 i mercati `alternate_totals_cards`, `alternate_totals_corners`, `player_shots`; quante richieste/crediti al mese servono per i nostri volumi (partite a settimana per lega × mercati × frequenza di raccolta); lo schema delle colonne da aggiungere a `history.csv` per salvare ogni giorno quote e previsioni del modello e misurare dopo qualche settimana il margine su gialli, falli, tiri e corner; costi e limiti **prima** di implementare.

## Tabella riassuntiva e commento
Una tabella finale con i verdetti di V1-V3 e il commento onesto: se V1 e V2 non mostrano informazione aggiuntiva, lo si scrive chiaramente, senza ripiegare sui risultati favorevoli di V3 (che è solo una verifica finale e non entra nei criteri di V1/V2).

---

# Aggiunte richieste dopo V1-V4: V5 (favorite in trasferta in Serie A) e V6 (controllo dell'anomalia)
Scritte PRIMA di eseguire qualsiasi analisi su queste condizioni. Stesse regole: scelte SOLO nella validazione 2019/20-2021/22, held-out dal 2022/23 (fino al 2026/27 in corso), IC 95% a blocchi per settimana ISO, produzione non toccata.

## Avvertenza sull'indipendenza (da leggere prima dei risultati)
L'anomalia di V5 è stata trovata guardando le quote **2019/20-2026/27**: sono le stesse stagioni della validazione e dell'held-out. Quindi per *questa ipotesi* nessuna di quelle stagioni è davvero fuori campione: la suddivisione validazione/held-out può mostrare solo se l'effetto è **coerente tra sottoperiodi**, non confermarlo. Per questo il round usa due controlli aggiuntivi, dichiarati qui:
1. **Stagioni 2013/14-2018/19** (football-data.co.uk, quote medie pre-partita e di chiusura già nel nostro archivio, copertura 100 %): non sono state usate per scoprire l'anomalia, quindi sono un controllo davvero indipendente (con la riserva che la fonte delle quote medie prima del 2019/20 può essere BbAv/B365 invece di Avg).
2. **Controllo delle molteplicità (V6)**: simulazione sotto l'ipotesi nulla «il mercato è calibrato» per stimare quanto spesso, guardando molte condizioni, emerge per caso un eccesso come quello della Serie A.
(Le partite del 2026/27 giocate dopo questo round saranno una verifica futura, non fanno parte del round.)

Verdetto finale su V5a: **«confermata»** solo se (i) nell'held-out l'eccesso (vittorie osservate − probabilità implicita) ha IC a blocchi che esclude zero **e** (ii) nelle stagioni 2013/14-2018/19 l'eccesso è > 0 con IC che esclude zero **e** (iii) il p-value di famiglia di V6 è < 0,05; **«coerente nel periodo di scoperta ma non confermata»** se vale (i) ma non (ii) o (iii); **«non confermata»** se l'IC dell'held-out comprende lo zero.

## Dati
Tutti e cinque i campionati; `feat` (backtest/round7_lib.build_ctx7): esito, quote medie **pre-partita** `odds_h/d/a` (AvgH/D/A, o BbAv/B365 dove manca; la «quota media di apertura» del testo: sono le medie raccolte giorni prima), quote medie **di chiusura** `cl_h/d/a`. Probabilità senza margine col metodo power (come nel resto del round; il passo 0 riproduce anche i numeri con la normalizzazione semplice). Probabilità del modello v6 solo dal 2019/20 (fuori campione). Finestre: **pre-2019** = 2013/14-2018/19; **validazione** = 2019/20-2021/22; **held-out** = 2022/23-2026/27 (in corso); **scoperta** = validazione + held-out.

## V5 — favorite in trasferta in Serie A
**Passo 0 (solo riproduzione, nessuna decisione):** Serie A, finestra di scoperta, soglia 40 %: N, vittorie ospiti, probabilità implicita media, ROI alle quote medie pre-partita e di chiusura, stagioni positive su totale; da confrontare con 827 partite, 61 % contro 53 %, +8,7 %, +8,9 %, 7 stagioni su 8.

**V5a — verifica.** Sottoinsieme A_t = partite di Serie A con p_ospite (pre-partita, senza margine) ≥ t, **t ∈ {35 %, 40 %, 45 %}**. Per finestra (pre-2019, validazione, held-out) e per stagione: N, probabilità implicita media, frequenza osservata di vittoria dell'ospite, **eccesso = osservata − implicita** (punti) con IC a blocchi, ROI a 1 unità alla quota media pre-partita (AvgA) con IC a blocchi, ROI alla quota media di chiusura, CLV = quota pre × p_chiusura senza margine − 1. **Soglia scelta in validazione**: la t con il limite inferiore dell'IC 95 % a blocchi dell'eccesso più alto nella validazione (parità → t più bassa). Verdetto come sopra. Confronto sugli altri quattro campionati con la stessa t (descrittivo; il controllo vero è V6).

**V5b — il modello v6 lo cattura?** Sul sottoinsieme A_t* (t* da V5a) nella finestra 2019/20+: probabilità media prevista dell'ospite dal modello, dal mercato pre-partita e dal mercato di chiusura, contro la frequenza osservata; differenza modello − mercato con IC a blocchi; **log-loss 1X2** del modello e del mercato e **guadagno = ll(mercato) − ll(modello)** (positivo = il modello è meglio) con IC a blocchi, per validazione e held-out; ripetuto su tutta la Serie A. Il modello «cattura» l'effetto solo se p_modello − p_mercato (ospite) è > 0 con IC che esclude zero **e** il guadagno è > 0 con IC che esclude zero; altrimenti «non lo cattura».

**V5c — correzione (eseguita comunque; rilevante se V5b dice «non lo cattura»).** Walk-forward per stagione sulle sole partite di Serie A: per la stagione s si stima su 2019/20…s−1 (test da 2020/21) e si applica alla Serie A (le altre leghe restano invariate, quindi il guadagno complessivo è diluito di circa 1/5). Utilità = log p_v6 + correzione:
- **K1**: intercette di classe specifiche della Serie A (pareggio e ospite rispetto alla casa): «vantaggio casa della Serie A».
- **K2**: K1 + termine di interazione b · 1[p_modello,ospite ≥ t*] · 1[esito = ospite] («ospite favorito × lega»; usa la probabilità del modello, non le quote, perché in produzione la correzione deve poter funzionare senza la quota della partita).
Scelta tra K1 e K2 in validazione (2020/21-2021/22): minore log-loss 1X2 della Serie A; differenza < 0,0002 → K1. Misure: Δ log-loss 1X2 = baseline − variante (positivo = migliora) su **tutte e 5 le leghe** (guadagno complessivo, metrica primaria), sulla sola Serie A e sul sottoinsieme A_t*, in validazione e held-out, IC a blocchi; parametri stimati per fold. Verdetto: «migliora» se il Δ complessivo nell'held-out è > 0 con IC che esclude zero; «peggiora» se < 0 con IC sotto zero; altrimenti «non distinguibile dal rumore». Nessuna modifica della produzione in ogni caso.

**V5d — scommesse.** 1 unità su ogni partita di Serie A in A_t* alla **quota media** pre-partita (AvgA; non la Max), regolamento a quella quota; riferimento anche alla quota media di chiusura. ROI con IC a blocchi per finestra e per stagione; CLV; **massimo drawdown** (massima discesa picco-valle del profitto cumulato, in unità, con le partite in ordine di data) nell'held-out e nella finestra di scoperta; distribuzione (5°, 50°, 95° percentile) del massimo drawdown ricampionando le settimane con rimpiazzo (stesso numero di settimane), per leggere il drawdown osservato contro quello atteso per puro caso con quel ROI. Riferimenti: tutte le trasferte in Serie A; stessa regola negli altri campionati.

## V6 — controllo dell'anomalia
**Condizioni scelte ora, prima di guardare i dati** (nessuna soglia viene ottimizzata: una sola soglia per condizione):
- **H** — favorita in casa: p_casa (pre-partita) ≥ 60 %, esito = vittoria in casa.
- **D** — pareggi tra squadre equilibrate: |p_casa − p_ospite| ≤ 10 punti, esito = pareggio.
- **O** — outsider in casa: p_casa ≤ 25 %, esito = vittoria in casa (bias favorita/sfavorita).
- **A** — la condizione di V5 (p_ospite ≥ 40 %, esito = ospite), per confronto.
Ciascuna per i 5 campionati (e tutti insieme): per ogni cella N, probabilità implicita, frequenza osservata, eccesso, **z = (osservati − Σp) / √Σp(1−p)**, ROI alla quota media pre-partita con IC a blocchi, nelle finestre pre-2019, validazione, held-out e scoperta; stagioni positive.

**Quante anomalie di questa grandezza emergono per caso.** Simulazione sotto l'ipotesi nulla «il mercato è calibrato»: gli esiti 1X2 di tutte le partite della finestra di scoperta vengono estratti dalle probabilità pre-partita senza margine (indipendenti tra partite), **10.000 simulazioni**, stessi partizionamenti e stesse soglie. La **famiglia E** di celle (ciascuna con almeno 100 partite nella finestra di scoperta, altrimenti esclusa sia nei dati sia nelle simulazioni):
- esito 1 o 2 con p_esito ≥ t, t ∈ {35, 40, 45, 50, 55, 60} %, per lega (fino a 60 celle);
- pareggio con |p_casa − p_ospite| ≤ δ, δ ∈ {5, 10, 15} punti, per lega (15 celle);
- esito 1 o 2 con p_esito ≤ t, t ∈ {20, 25, 30} %, per lega (30 celle).
Si riportano: (i) il valore z e il ROI osservati nella cella Serie A/ospite/≥ 40 % e il loro percentile nella distribuzione nulla della cella stessa (p-value di cella); (ii) il **p-value di famiglia** = frazione di simulazioni in cui *almeno una* cella della famiglia E ha z ≥ z osservato della cella Serie A (stesso test sul ROI); (iii) numero atteso di celle con z ≥ 2, 2,5, 3 sotto l'ipotesi nulla contro quello osservato nei dati reali (unilaterale e bilaterale); (iv) probabilità, nella cella, di ≥ 7 stagioni positive su 8 sotto l'ipotesi nulla.
Giudizio: se il p-value di famiglia è ≥ 0,05 e il numero di celle con |z| > 2 osservato è simile a quello atteso per caso, l'anomalia della Serie A è compatibile con l'effetto di molte osservazioni; se è basso e le stagioni 2013/14-2018/19 vanno nella stessa direzione, merita un monitoraggio prospettico (non produzione).

## Tabella riassuntiva e commento
Come sopra: tabella con i verdetti di V1-V6 e commento onesto; se V1/V2 e V5/V6 non mostrano informazione o anomalia robusta, lo si scrive chiaramente.


---

## V1 — il modello aggiunge informazione al mercato?

Conditional logit walk-forward (utilità = a_c + w_m·log p_modello + w_k·log p_mercato). Δ = log-loss(riferimento) − log-loss(combinato): **positivo = il combinato è meglio**. Validazione = 2020/21-2021/22, held-out = 2022/23+, «2026/27» = stagione in corso (solo descrittivo). IC 95% a blocchi per settimana ISO.

### 1X2

| Configurazione | Insieme | N | ll modello | ll mercato grezzo | ll mercato calibrato | ll combinato | Δ vs mercato calibrato [IC blocchi] | Δ vs mercato grezzo [IC blocchi] |
|---|---|---|---|---|---|---|---|---|
| 1X2 chiusura (AvgC) | validazione | 3651 | 0.9888 | 0.9765 | 0.9763 | 0.9762 | 0.00006 [-0.00015; 0.00026] | 0.00032 [-0.00047; 0.00108] |
|  | held-out | 7529 | 0.9736 | 0.9651 | 0.9653 | 0.9653 | -0.00003 [-0.00025; 0.00020] | -0.00022 [-0.00087; 0.00042] |
|  | 2026/27 | 447 | 0.9540 | 0.9488 | 0.9496 | 0.9500 | -0.00037 [-0.00127; 0.00032] | -0.00112 [-0.00414; 0.00204] |
| 1X2 pre-partita (Avg) | validazione | 3651 | 0.9888 | 0.9796 | 0.9794 | 0.9793 | 0.00005 [-0.00006; 0.00016] | 0.00031 [-0.00056; 0.00114] |
|  | held-out | 7529 | 0.9736 | 0.9673 | 0.9673 | 0.9673 | 0.00001 [-0.00020; 0.00021] | 0.00006 [-0.00065; 0.00077] |
|  | 2026/27 | 447 | 0.9540 | 0.9511 | 0.9519 | 0.9525 | -0.00055 [-0.00142; 0.00018] | -0.00139 [-0.00492; 0.00243] |
| 1X2 pre-partita (B365) — sensibilità | validazione | 3647 | 0.9884 | 0.9803 | 0.9798 | 0.9799 | -0.00016 [-0.00046; 0.00013] | 0.00036 [-0.00080; 0.00149] |
|  | held-out | 7529 | 0.9736 | 0.9676 | 0.9678 | 0.9679 | -0.00002 [-0.00007; 0.00001] | -0.00028 [-0.00110; 0.00052] |
|  | 2026/27 | 447 | 0.9540 | 0.9517 | 0.9531 | 0.9532 | -0.00005 [-0.00012; 0.00001] | -0.00145 [-0.00530; 0.00264] |
| 1X2 chiusura Pinnacle — sensibilità | validazione | 3652 | 0.9888 | 0.9769 | 0.9766 | 0.9766 | 0.00004 [-0.00017; 0.00024] | 0.00028 [-0.00054; 0.00106] |
|  | held-out | 6228 | 0.9715 | 0.9625 | 0.9627 | 0.9627 | -0.00003 [-0.00021; 0.00016] | -0.00029 [-0.00096; 0.00038] |

**Pesi** (conditional logit su tutte le partite dell'insieme; IC a blocchi con ristima, 2000 ricampionamenti):

| Configurazione | Campione | N | peso modello w_m [IC] | peso mercato w_k [IC] | w_m + w_k [IC] |
|---|---|---|---|---|---|
| 1X2 chiusura (AvgC) | held-out 2022/23+ | 7529 | 0.024 [-0.194; 0.247] | 1.062 [0.860; 1.260] | 1.085 [1.019; 1.156] |
|  | tutte (2019/20+) | 12905 | -0.041 [-0.187; 0.119] | 1.079 [0.937; 1.210] | 1.038 [0.990; 1.087] |
| 1X2 pre-partita (Avg) | held-out 2022/23+ | 7529 | -0.020 [-0.272; 0.227] | 1.108 [0.882; 1.355] | 1.088 [1.021; 1.158] |
|  | tutte (2019/20+) | 12905 | -0.071 [-0.222; 0.089] | 1.116 [0.968; 1.259] | 1.045 [0.998; 1.094] |
| 1X2 pre-partita (B365) — sensibilità | held-out 2022/23+ | 7529 | 0.051 [-0.189; 0.286] | 1.033 [0.825; 1.261] | 1.084 [1.019; 1.153] |
|  | tutte (2019/20+) | 12901 | 0.015 [-0.131; 0.164] | 1.018 [0.880; 1.156] | 1.033 [0.986; 1.082] |
| 1X2 chiusura Pinnacle — sensibilità | held-out 2022/23+ | 6228 | 0.031 [-0.215; 0.273] | 1.068 [0.841; 1.302] | 1.099 [1.023; 1.174] |
|  | tutte (2019/20+) | 11605 | -0.023 [-0.193; 0.134] | 1.063 [0.920; 1.216] | 1.040 [0.993; 1.089] |

**Pesi per stagione** (w_m / w_k, stima sulla sola stagione):

| Configurazione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---|---|---|---|---|---|---|---|
| 1X2 chiusura (AvgC) | -0.02 / 0.97 | -0.09 / 1.09 | -0.11 / 1.10 | -0.10 / 1.06 | +0.02 / 1.21 | +0.04 / 1.07 | +0.04 / 1.01 | +0.47 / 0.69 |
| 1X2 pre-partita (Avg) | -0.04 / 1.00 | +0.05 / 0.97 | -0.19 / 1.20 | -0.05 / 1.01 | -0.16 / 1.39 | +0.05 / 1.07 | -0.11 / 1.14 | +0.57 / 0.61 |
| 1X2 pre-partita (B365) — sensibilità | +0.08 / 0.86 | +0.22 / 0.78 | -0.19 / 1.17 | +0.08 / 0.87 | -0.21 / 1.43 | +0.14 / 0.98 | +0.02 / 1.03 | +0.63 / 0.55 |
| 1X2 chiusura Pinnacle — sensibilità | -0.05 / 0.99 | -0.02 / 1.03 | -0.04 / 1.03 | -0.10 / 1.07 | +0.07 / 1.16 | +0.08 / 1.02 | +0.26 / 0.90 | — |

**Δ vs mercato calibrato per lega, held-out** (×10⁻³, tra parentesi N):

| Configurazione | Serie A | Premier | Bundesliga | La Liga | Ligue 1 |
|---|---|---|---|---|---|
| 1X2 chiusura (AvgC) | -0.25 (1618) | +0.04 (1609) | +0.15 (1296) | +0.04 (1628) | -0.09 (1378) |
| 1X2 pre-partita (Avg) | -0.07 (1618) | -0.29 (1609) | +0.27 (1296) | +0.09 (1628) | +0.08 (1378) |

### Over/Under 2,5

| Configurazione | Insieme | N | ll modello | ll mercato grezzo | ll mercato calibrato | ll combinato | Δ vs mercato calibrato [IC blocchi] | Δ vs mercato grezzo [IC blocchi] |
|---|---|---|---|---|---|---|---|---|
| Over/Under 2,5 chiusura (AvgC) | validazione | 3650 | 0.6792 | 0.6735 | 0.6741 | 0.6744 | -0.00030 [-0.00088; 0.00038] | -0.00091 [-0.00165; -0.00019] |
|  | held-out | 7529 | 0.6742 | 0.6662 | 0.6662 | 0.6663 | -0.00004 [-0.00012; 0.00004] | -0.00005 [-0.00028; 0.00017] |
|  | 2026/27 | 447 | 0.6571 | 0.6473 | 0.6471 | 0.6473 | -0.00021 [-0.00048; 0.00009] | -0.00006 [-0.00077; 0.00063] |
| Over/Under 2,5 pre-partita (Avg) | validazione | 3650 | 0.6792 | 0.6761 | 0.6768 | 0.6771 | -0.00028 [-0.00124; 0.00082] | -0.00102 [-0.00196; -0.00007] |
|  | held-out | 7529 | 0.6742 | 0.6691 | 0.6691 | 0.6692 | -0.00006 [-0.00034; 0.00021] | -0.00011 [-0.00046; 0.00024] |
|  | 2026/27 | 447 | 0.6571 | 0.6528 | 0.6526 | 0.6520 | 0.00060 [-0.00034; 0.00164] | 0.00077 [-0.00011; 0.00176] |
| Over/Under 2,5 pre-partita (B365) — sensibilità | validazione | 3643 | 0.6790 | 0.6760 | 0.6768 | 0.6769 | -0.00016 [-0.00111; 0.00092] | -0.00090 [-0.00188; 0.00008] |
|  | held-out | 7529 | 0.6742 | 0.6690 | 0.6690 | 0.6691 | -0.00010 [-0.00039; 0.00019] | -0.00014 [-0.00050; 0.00022] |
|  | 2026/27 | 447 | 0.6571 | 0.6544 | 0.6541 | 0.6534 | 0.00071 [-0.00026; 0.00176] | 0.00092 [-0.00002; 0.00203] |
| Over/Under 2,5 chiusura Pinnacle — sensibilità | validazione | 3642 | 0.6794 | 0.6737 | 0.6742 | 0.6745 | -0.00031 [-0.00085; 0.00026] | -0.00084 [-0.00163; -0.00010] |
|  | held-out | 6167 | 0.6763 | 0.6679 | 0.6679 | 0.6679 | -0.00005 [-0.00020; 0.00010] | 0.00002 [-0.00040; 0.00043] |

**Pesi** (conditional logit su tutte le partite dell'insieme; IC a blocchi con ristima, 2000 ricampionamenti):

| Configurazione | Campione | N | peso modello w_m [IC] | peso mercato w_k [IC] | w_m + w_k [IC] |
|---|---|---|---|---|---|
| Over/Under 2,5 chiusura (AvgC) | held-out 2022/23+ | 7529 | -0.071 [-0.311; 0.183] | 1.067 [0.897; 1.250] | 0.996 [0.839; 1.166] |
|  | tutte (2019/20+) | 12903 | -0.010 [-0.188; 0.170] | 1.022 [0.879; 1.162] | 1.012 [0.903; 1.122] |
| Over/Under 2,5 pre-partita (Avg) | held-out 2022/23+ | 7529 | 0.066 [-0.210; 0.350] | 0.981 [0.769; 1.200] | 1.047 [0.891; 1.217] |
|  | tutte (2019/20+) | 12903 | 0.130 [-0.061; 0.330] | 0.921 [0.758; 1.087] | 1.051 [0.943; 1.161] |
| Over/Under 2,5 pre-partita (B365) — sensibilità | held-out 2022/23+ | 7529 | 0.059 [-0.215; 0.343] | 0.989 [0.776; 1.205] | 1.047 [0.892; 1.219] |
|  | tutte (2019/20+) | 12897 | 0.136 [-0.058; 0.332] | 0.913 [0.753; 1.075] | 1.049 [0.941; 1.160] |
| Over/Under 2,5 chiusura Pinnacle — sensibilità | held-out 2022/23+ | 6167 | -0.099 [-0.387; 0.198] | 1.131 [0.925; 1.333] | 1.032 [0.845; 1.217] |
|  | tutte (2019/20+) | 11534 | -0.006 [-0.192; 0.188] | 1.043 [0.893; 1.188] | 1.037 [0.920; 1.155] |

**Pesi per stagione** (w_m / w_k, stima sulla sola stagione):

| Configurazione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---|---|---|---|---|---|---|---|
| Over/Under 2,5 chiusura (AvgC) | +0.30 / 0.89 | -0.07 / 0.92 | -0.06 / 1.09 | -0.05 / 1.01 | +0.04 / 1.15 | -0.18 / 1.14 | -0.31 / 1.08 | +0.44 / 0.88 |
| Over/Under 2,5 pre-partita (Avg) | +0.47 / 0.77 | +0.06 / 0.81 | +0.08 / 0.97 | -0.11 / 1.15 | +0.26 / 1.00 | +0.10 / 0.92 | -0.16 / 0.97 | +0.62 / 0.67 |
| Over/Under 2,5 pre-partita (B365) — sensibilità | +0.46 / 0.77 | +0.11 / 0.76 | +0.10 / 0.93 | -0.21 / 1.25 | +0.27 / 0.98 | +0.07 / 0.94 | -0.08 / 0.91 | +0.69 / 0.60 |
| Over/Under 2,5 chiusura Pinnacle — sensibilità | +0.31 / 0.88 | -0.05 / 0.91 | -0.03 / 1.09 | +0.05 / 1.03 | +0.02 / 1.19 | -0.22 / 1.17 | -0.24 / 1.05 | — |

**Δ vs mercato calibrato per lega, held-out** (×10⁻³, tra parentesi N):

| Configurazione | Serie A | Premier | Bundesliga | La Liga | Ligue 1 |
|---|---|---|---|---|---|
| Over/Under 2,5 chiusura (AvgC) | -0.05 (1618) | -0.00 (1609) | -0.02 (1296) | -0.07 (1628) | -0.04 (1378) |
| Over/Under 2,5 pre-partita (Avg) | -0.17 (1618) | +0.38 (1609) | +0.03 (1296) | -0.30 (1628) | -0.26 (1378) |


---

## V2 — closing line value

Per ogni partita ed esito: **d = p_modello − p_pre** (Avg pre-partita senza margine) e **m = p_chiusura − p_pre** (AvgC senza margine meno Avg senza margine), in punti percentuali. 1X2: 3 righe per partita; Over/Under 2,5: lato Over (per divario negativo il segno porta al lato Under). Validazione = 2019/20-2021/22, held-out = 2022/23+. IC 95% a blocchi per settimana ISO. La pendenza «controllata» include il livello della probabilità pre-partita (e per il 1X2 le variabili di esito).

### Descrizione dei divari

| Mercato | Insieme | N | dev. std d (pt) | dev. std m (pt) | % |d|>3 | % |d|>5 | % |d|>8 |
|---|---|---|---|---|---|---|---|
| 1X2 | validazione | 16128 | 3.86 | 2.45 | 32.8 | 15.3 | 4.9 |
| 1X2 | held-out | 22587 | 3.30 | 2.26 | 26.9 | 10.3 | 3.0 |
| 1X2 | 2026/27 | 1341 | 4.05 | 2.44 | 35.5 | 19.5 | 5.5 |
| Over 2,5 | validazione | 5375 | 4.67 | 3.04 | 51.1 | 26.9 | 8.8 |
| Over 2,5 | held-out | 7529 | 4.93 | 2.92 | 54.1 | 30.6 | 10.3 |
| Over 2,5 | 2026/27 | 447 | 6.42 | 3.50 | 55.5 | 34.2 | 13.6 |

### 1. Correlazione e pendenza

Pendenza = di quanti punti si sposta in media la probabilità per ogni punto di divario modello − pre-partita (1 = il mercato recupera tutto il divario, 0 = nessuna relazione).

| Mercato | Insieme | N | correlazione [IC] | pendenza [IC] | pendenza controllata [IC] |
|---|---|---|---|---|---|
| 1X2 (tutti gli esiti) | validazione | 16128 | 0.019 [-0.015; 0.054] | 0.012 [-0.010; 0.034] | 0.024 [0.000; 0.048] |
|  | held-out | 22587 | -0.000 [-0.030; 0.030] | -0.000 [-0.021; 0.019] | 0.002 [-0.019; 0.024] |
|  | 2026/27 | 1341 | 0.006 [-0.047; 0.085] | 0.004 [-0.028; 0.057] | 0.005 [-0.041; 0.068] |
| Over 2,5 | validazione | 5375 | 0.053 [0.018; 0.088] | 0.035 [0.012; 0.058] | 0.062 [0.036; 0.087] |
|  | held-out | 7529 | -0.014 [-0.039; 0.013] | -0.008 [-0.023; 0.008] | 0.041 [0.022; 0.061] |
|  | 2026/27 | 447 | 0.055 [-0.050; 0.139] | 0.030 [-0.027; 0.080] | 0.024 [-0.024; 0.072] |

**Per esito (1X2), held-out e validazione:**

| Esito | Insieme | N | correlazione [IC] | pendenza [IC] | pendenza controllata [IC] |
|---|---|---|---|---|---|
| 1 (casa) | validazione | 5376 | 0.025 [-0.012; 0.061] | 0.016 [-0.008; 0.039] | 0.025 [-0.000; 0.050] |
|  | held-out | 7529 | 0.005 [-0.027; 0.039] | 0.003 [-0.020; 0.026] | 0.005 [-0.020; 0.031] |
| X (pareggio) | validazione | 5376 | 0.004 [-0.029; 0.039] | 0.003 [-0.020; 0.024] | 0.054 [0.029; 0.078] |
|  | held-out | 7529 | -0.068 [-0.096; -0.041] | -0.043 [-0.061; -0.026] | 0.006 [-0.017; 0.030] |
| 2 (ospite) | validazione | 5376 | 0.019 [-0.019; 0.058] | 0.012 [-0.014; 0.038] | 0.023 [-0.003; 0.050] |
|  | held-out | 7529 | 0.015 [-0.017; 0.048] | 0.010 [-0.013; 0.032] | 0.008 [-0.015; 0.032] |

**Per lega (1X2 tutti gli esiti e Over 2,5), held-out:**

| Lega | N 1X2 | correlazione 1X2 | pend. controllata 1X2 | N Over | correlazione Over | pend. controllata Over |
|---|---|---|---|---|---|---|
| Serie A | 4854 | 0.008 [-0.059; 0.074] | 0.028 [-0.028; 0.078] | 1618 | -0.018 [-0.073; 0.038] | 0.035 [-0.006; 0.074] |
| Premier | 4827 | 0.023 [-0.032; 0.077] | 0.000 [-0.038; 0.039] | 1609 | 0.057 [0.012; 0.103] | 0.057 [0.025; 0.089] |
| Bundesliga | 3888 | 0.006 [-0.048; 0.062] | 0.002 [-0.039; 0.040] | 1296 | -0.032 [-0.097; 0.034] | 0.000 [-0.037; 0.042] |
| La Liga | 4884 | 0.006 [-0.039; 0.052] | 0.037 [0.002; 0.073] | 1628 | -0.047 [-0.107; 0.010] | 0.054 [0.005; 0.104] |
| Ligue 1 | 4134 | -0.047 [-0.106; 0.014] | -0.023 [-0.071; 0.027] | 1378 | -0.002 [-0.067; 0.064] | 0.052 [-0.003; 0.108] |

### 2. Partite con divergenza > soglia

«Verso il modello» = il segno dello spostamento m coincide con quello del divario d (i movimenti esattamente nulli sono esclusi dalla frazione; la loro quota è riportata). Caso nullo: 50 % e 0 punti. Movimento medio = m·segno(d), in punti percentuali.

| Mercato | τ (pt) | Insieme | N coppie | % verso il modello [IC] | movimento medio verso il modello (pt) [IC] | % movimenti nulli |
|---|---|---|---|---|---|---|
| 1X2 | 3 | validazione | 5294 | 48.6 [46.6; 50.5] | -0.006 [-0.122; 0.104] | 0.0 |
|  |  | held-out | 6074 | 48.2 [46.3; 50.1] | -0.035 [-0.135; 0.069] | 0.0 |
|  |  | 2026/27 | 476 | 49.2 [45.5; 53.2] | 0.002 [-0.194; 0.256] | 0.0 |
|  | 5 | validazione | 2473 | 49.1 [46.5; 51.8] | 0.028 [-0.156; 0.206] | 0.0 |
|  |  | held-out | 2335 | 50.1 [47.2; 53.0] | 0.068 [-0.118; 0.258] | 0.0 |
|  |  | 2026/27 | 261 | 46.7 [40.5; 53.2] | -0.062 [-0.411; 0.292] | 0.0 |
|  | 8 | validazione | 795 | 54.5 [50.3; 58.3] | 0.390 [0.033; 0.756] | 0.0 |
|  |  | held-out | 669 | 53.8 [48.4; 59.0] | 0.334 [-0.045; 0.720] | 0.0 |
|  |  | 2026/27 | 74 | 50.0 [43.3; 60.3] | 0.305 [-0.339; 1.103] | 0.0 |
| Over 2,5 | 3 | validazione | 2749 | 51.3 [48.8; 53.8] | 0.195 [0.040; 0.340] | 2.1 |
|  |  | held-out | 4070 | 47.4 [45.6; 49.2] | -0.112 [-0.216; -0.013] | 1.2 |
|  |  | 2026/27 | 248 | 50.2 [46.1; 54.7] | 0.311 [-0.086; 0.812] | 0.4 |
|  | 5 | validazione | 1446 | 51.3 [48.3; 54.3] | 0.283 [0.087; 0.469] | 2.1 |
|  |  | held-out | 2302 | 46.7 [44.6; 48.8] | -0.081 [-0.202; 0.038] | 1.3 |
|  |  | 2026/27 | 153 | 45.1 [39.8; 50.0] | -0.053 [-0.490; 0.403] | 0.0 |
|  | 8 | validazione | 473 | 53.8 [49.2; 58.6] | 0.443 [0.060; 0.812] | 1.7 |
|  |  | held-out | 772 | 46.0 [42.9; 49.1] | -0.113 [-0.308; 0.089] | 1.4 |
|  |  | 2026/27 | 61 | 47.5 [38.5; 58.9] | 0.258 [-0.620; 1.272] | 0.0 |

**Soglia scelta in validazione** (limite inferiore dell'IC del movimento medio verso il modello più alto; parità → τ più bassa): 1X2 τ = 8, Over/Under 2,5 τ = 5.

### 3. Per esito, per lega e per Over/Under 2,5 (τ = 8 per il 1X2; τ = 5 per Over/Under)

| Esito | Insieme | N | % verso il modello [IC] | movimento medio (pt) [IC] |
|---|---|---|---|---|
| 1 (casa) | validazione | 429 | 56.4 [52.3; 60.2] | 0.550 [0.157; 0.926] |
|  | held-out | 353 | 52.7 [46.4; 58.6] | 0.407 [-0.051; 0.857] |
| X (pareggio) | validazione | 10 | — | — |
|  | held-out | 12 | — | — |
| 2 (ospite) | validazione | 356 | 52.2 [46.5; 57.7] | 0.208 [-0.235; 0.699] |
|  | held-out | 304 | 54.9 [49.1; 60.9] | 0.260 [-0.124; 0.651] |

| Lega (1X2) | Insieme | N | % verso il modello [IC] | movimento medio (pt) [IC] |
|---|---|---|---|---|
| Serie A | validazione | 199 | 61.8 [54.7; 68.6] | 1.203 [0.407; 2.044] |
|  | held-out | 116 | 51.7 [38.7; 62.8] | 0.844 [0.034; 1.563] |
| Premier | validazione | 162 | 45.7 [36.9; 55.0] | -0.508 [-1.186; 0.139] |
|  | held-out | 160 | 53.1 [42.7; 63.8] | 0.301 [-0.389; 1.009] |
| Bundesliga | validazione | 131 | 48.1 [36.0; 60.5] | -0.384 [-1.227; 0.467] |
|  | held-out | 127 | 59.8 [48.4; 69.6] | 0.311 [-0.503; 1.032] |
| La Liga | validazione | 171 | 57.3 [48.4; 65.7] | 0.648 [0.101; 1.159] |
|  | held-out | 149 | 53.7 [42.4; 64.2] | 0.282 [-0.380; 0.903] |
| Ligue 1 | validazione | 132 | 56.8 [45.8; 66.9] | 0.698 [-0.103; 1.535] |
|  | held-out | 117 | 50.4 [39.3; 62.6] | -0.039 [-0.801; 0.774] |

| Lega (Over/Under 2,5) | Insieme | N | % verso il modello [IC] | movimento medio (pt) [IC] |
|---|---|---|---|---|
| Serie A | validazione | 318 | 56.8 [50.6; 63.0] | 0.637 [0.228; 1.022] |
|  | held-out | 570 | 45.6 [41.5; 49.8] | -0.192 [-0.444; 0.075] |
| Premier | validazione | 221 | 47.2 [40.7; 53.5] | 0.106 [-0.335; 0.543] |
|  | held-out | 390 | 52.1 [47.3; 56.7] | 0.238 [-0.030; 0.506] |
| Bundesliga | validazione | 285 | 52.2 [46.2; 58.2] | 0.167 [-0.211; 0.560] |
|  | held-out | 372 | 48.8 [42.7; 54.7] | 0.007 [-0.311; 0.320] |
| La Liga | validazione | 398 | 49.1 [43.5; 54.6] | 0.232 [-0.121; 0.581] |
|  | held-out | 649 | 43.9 [40.3; 47.5] | -0.229 [-0.441; -0.015] |
| Ligue 1 | validazione | 224 | 50.5 [44.1; 57.0] | 0.194 [-0.211; 0.582] |
|  | held-out | 321 | 45.5 [39.9; 51.5] | -0.078 [-0.453; 0.320] |
| Tutte le leghe | validazione | 1446 | 51.3 [48.3; 54.3] | 0.283 [0.087; 0.469] |
|  | held-out | 2302 | 46.7 [44.6; 48.8] | -0.081 [-0.202; 0.038] |

| Lato (Over/Under 2,5) | Insieme | N | % verso il modello [IC] | movimento medio (pt) [IC] |
|---|---|---|---|---|
| modello più alto del mercato sull'Over | validazione | 909 | 50.7 [46.6; 55.1] | 0.226 [-0.040; 0.488] |
|  | held-out | 1548 | 45.5 [42.8; 48.2] | -0.148 [-0.305; 0.011] |
| modello più alto sull'Under | validazione | 537 | 52.4 [47.7; 57.0] | 0.379 [0.048; 0.663] |
|  | held-out | 754 | 49.3 [45.4; 53.5] | 0.056 [-0.163; 0.300] |


---

## V3 — simulazione di scommesse a puntata fissa (verifica finale)

1 unità su ogni esito con **p_modello × quota > 1 + θ**. Quote: Max e Avg **pre-partita** (raccolte giorni prima). θ scelta in validazione (ROI massimo con almeno 150 scommesse), poi invariata. CLV = media di (quota giocata × p_chiusura senza margine − 1) con p_chiusura da AvgC. IC 95% a blocchi per settimana ISO.

### 1X2

**Scelta della soglia in validazione (Max (quote massime: segnale e regolamento))** — scommesse e ROI nelle stagioni 2019/20-2021/22 (almeno 150 scommesse):

| θ | N scommesse | ROI (%) |  |
|---|---|---|---|
| 0.00 | 7483 | 0.87 |  |
| 0.03 | 5746 | 0.85 |  |
| 0.05 | 4763 | 0.09 |  |
| 0.08 | 3582 | 0.73 |  |
| 0.10 | 2967 | 1.18 |  |
| 0.15 | 1899 | 0.67 |  |
| 0.20 | 1203 | 1.93 | ◄ scelta |

**Scelta della soglia in validazione (Avg (quote medie: segnale e regolamento))** — scommesse e ROI nelle stagioni 2019/20-2021/22 (almeno 150 scommesse):

| θ | N scommesse | ROI (%) |  |
|---|---|---|---|
| 0.00 | 4651 | -7.51 |  |
| 0.03 | 3341 | -9.50 |  |
| 0.05 | 2691 | -9.75 |  |
| 0.08 | 1917 | -12.05 |  |
| 0.10 | 1552 | -13.82 |  |
| 0.15 | 911 | -11.52 |  |
| 0.20 | 530 | 0.44 | ◄ scelta |

**Riferimento: puntare su tutti gli esiti** (CLV = valore atteso della quota giocata alle probabilità di chiusura senza margine: è il punto di partenza da cui leggere il CLV delle scommesse selezionate; la Max è la quota più alta tra i bookmaker raccolti, ma resta sotto il prezzo «giusto» della chiusura):

| Strategia | Insieme | N scommesse | ROI (%) [IC blocchi] | CLV (%) [IC blocchi] |
|---|---|---|---|---|
| tutti gli esiti alla Max | validazione | 16128 | 0.99 [-0.50; 2.48] | -0.53 [-0.65; -0.41] |
| tutti gli esiti alle Avg | validazione | 16128 | -4.64 [-5.93; -3.36] | -5.92 [-6.04; -5.80] |
| tutti gli esiti alla Max | held-out | 22587 | -2.86 [-3.99; -1.69] | -1.58 [-1.81; -1.37] |
| tutti gli esiti alle Avg | held-out | 22587 | -7.18 [-8.21; -6.14] | -6.10 [-6.28; -5.93] |
| tutti gli esiti alla Max | 2026/27 | 1341 | -6.28 [-9.73; -2.27] | -3.37 [-3.98; -2.70] |
| tutti gli esiti alle Avg | 2026/27 | 1341 | -10.23 [-13.34; -6.52] | -7.87 [-8.31; -7.40] |

**Max (quote massime: segnale e regolamento)** — θ = 0.20

| Insieme | N scommesse | ROI (%) [IC blocchi] | CLV (%) vs chiusura senza margine [IC] | CLV (%) vs quota di chiusura grezza, margine incluso [IC] |
|---|---|---|---|---|
| validazione | 1203 | 1.93 [-12.08; 16.95] | -0.61 [-1.53; 0.31] | 9.55 [8.57; 10.52] |
| held-out | 1133 | -19.30 [-30.74; -7.82] | -1.30 [-2.50; -0.03] | 10.79 [9.47; 12.13] |
| 2026/27 | 108 | -6.52 [-28.47; 10.43] | -4.10 [-7.71; 1.09] | 13.00 [9.37; 17.62] |

Per stagione (held-out):

| Stagione | N | ROI (%) [IC] | CLV (%) [IC] |
|---|---|---|---|
| 2022/23 | 288 | -17.95 [-43.22; 2.75] | 1.41 [-0.89; 3.48] |
| 2023/24 | 280 | -33.35 [-54.84; -11.24] | -1.89 [-4.53; 0.89] |
| 2024/25 | 259 | -16.61 [-40.60; 8.32] | -1.79 [-3.41; 0.04] |
| 2025/26 | 198 | -11.87 [-38.59; 19.47] | -2.24 [-4.23; 0.42] |
| 2026/27 | 108 | -6.52 [-28.47; 10.43] | -4.10 [-7.71; 1.09] |

Per lega (held-out):

| Lega | N | ROI (%) [IC] | CLV (%) [IC] |
|---|---|---|---|
| Serie A | 215 | -25.48 [-49.76; 1.23] | 0.10 [-2.25; 2.99] |
| Premier | 305 | -12.58 [-36.49; 12.14] | 0.57 [-1.32; 2.49] |
| Bundesliga | 165 | -15.17 [-48.83; 20.25] | -2.02 [-4.96; 0.79] |
| La Liga | 294 | -25.04 [-44.96; -4.68] | -2.46 [-4.25; -0.48] |
| Ligue 1 | 154 | -17.44 [-49.05; 14.89] | -3.94 [-6.76; -1.09] |

Per esito (held-out):

| Esito | N | ROI (%) [IC] | CLV (%) [IC] |
|---|---|---|---|
| 1 | 342 | -24.80 [-42.28; -5.99] | -0.49 [-1.87; 0.99] |
| X | 181 | -4.52 [-44.64; 38.13] | -4.94 [-7.03; -2.84] |
| 2 | 610 | -20.60 [-35.21; -4.78] | -0.67 [-2.32; 0.99] |

Per esito (validazione):

| Esito | N | ROI (%) [IC] | CLV (%) [IC] |
|---|---|---|---|
| 1 | 644 | 3.20 [-12.91; 20.09] | -0.33 [-1.40; 0.73] |
| X | 141 | -4.84 [-39.71; 31.41] | -5.66 [-7.90; -3.57] |
| 2 | 418 | 2.25 [-30.01; 43.41] | 0.67 [-0.72; 2.18] |

**Avg (quote medie: segnale e regolamento)** — θ = 0.20

| Insieme | N scommesse | ROI (%) [IC blocchi] | CLV (%) vs chiusura senza margine [IC] | CLV (%) vs quota di chiusura grezza, margine incluso [IC] |
|---|---|---|---|---|
| validazione | 530 | 0.44 [-16.04; 17.78] | -7.32 [-8.60; -6.01] | 0.98 [-0.23; 2.18] |
| held-out | 499 | -25.45 [-39.45; -11.42] | -8.92 [-10.41; -7.33] | 1.45 [0.00; 2.89] |
| 2026/27 | 46 | 1.93 [-29.85; 33.83] | -15.20 [-17.75; -9.07] | 1.12 [-2.06; 6.55] |

Per stagione (held-out):

| Stagione | N | ROI (%) [IC] | CLV (%) [IC] |
|---|---|---|---|
| 2022/23 | 128 | -17.62 [-50.58; 7.85] | -5.03 [-8.37; -1.35] |
| 2023/24 | 101 | -31.68 [-64.99; 16.25] | -8.89 [-12.26; -5.24] |
| 2024/25 | 117 | -42.93 [-64.04; -22.63] | -8.77 [-10.71; -6.40] |
| 2025/26 | 107 | -21.59 [-46.91; 8.35] | -11.06 [-12.37; -9.72] |
| 2026/27 | 46 | 1.93 [-29.85; 33.83] | -15.20 [-17.75; -9.07] |

Per lega (held-out):

| Lega | N | ROI (%) [IC] | CLV (%) [IC] |
|---|---|---|---|
| Serie A | 97 | -44.22 [-73.21; -12.14] | -7.42 [-9.49; -5.41] |
| Premier | 132 | -9.11 [-44.72; 30.20] | -7.22 [-10.06; -3.98] |
| Bundesliga | 77 | -44.70 [-80.02; -3.01] | -11.96 [-16.09; -8.15] |
| La Liga | 128 | -20.53 [-49.50; 12.70] | -10.17 [-12.83; -7.34] |
| Ligue 1 | 65 | -17.49 [-57.68; 30.63] | -8.53 [-12.10; -4.51] |

Per esito (held-out):

| Esito | N | ROI (%) [IC] | CLV (%) [IC] |
|---|---|---|---|
| 1 | 174 | -27.41 [-50.19; -3.24] | -7.42 [-9.07; -5.71] |
| X | 59 | -30.07 [-76.27; 17.28] | -13.33 [-16.59; -9.53] |
| 2 | 266 | -23.14 [-43.36; -1.68] | -8.92 [-10.97; -6.78] |

Per esito (validazione):

| Esito | N | ROI (%) [IC] | CLV (%) [IC] |
|---|---|---|---|
| 1 | 334 | -5.05 [-23.25; 12.68] | -6.96 [-8.56; -5.25] |
| X | 40 | 16.48 [-47.62; 81.73] | -12.39 [-16.81; -8.88] |
| 2 | 156 | 8.08 [-30.89; 53.53] | -6.77 [-9.03; -4.47] |

**Segnale con Max, regolamento alle quote medie** — θ = 0.20

| Insieme | N scommesse | ROI (%) [IC blocchi] | CLV (%) vs chiusura senza margine [IC] | CLV (%) vs quota di chiusura grezza, margine incluso [IC] |
|---|---|---|---|---|
| validazione | 1203 | -7.91 [-19.84; 4.80] | -9.02 [-9.92; -8.15] | -0.00 [-0.79; 0.74] |
| held-out | 1133 | -25.37 [-36.01; -14.83] | -9.90 [-10.94; -8.85] | 0.87 [-0.07; 1.84] |
| 2026/27 | 108 | -14.44 [-33.75; -0.40] | -14.36 [-17.56; -10.68] | 0.42 [-1.70; 3.34] |

### Over/Under 2,5

**Scelta della soglia in validazione (Max (quote massime: segnale e regolamento))** — scommesse e ROI nelle stagioni 2019/20-2021/22 (almeno 150 scommesse):

| θ | N scommesse | ROI (%) |  |
|---|---|---|---|
| 0.00 | 4900 | 0.37 |  |
| 0.03 | 3535 | 0.59 |  |
| 0.05 | 2776 | -0.73 |  |
| 0.08 | 1844 | 1.35 |  |
| 0.10 | 1370 | 3.46 | ◄ scelta |
| 0.15 | 657 | 1.07 |  |
| 0.20 | 299 | -1.32 |  |

**Scelta della soglia in validazione (Avg (quote medie: segnale e regolamento))** — scommesse e ROI nelle stagioni 2019/20-2021/22 (almeno 150 scommesse):

| θ | N scommesse | ROI (%) |  |
|---|---|---|---|
| 0.00 | 3033 | -4.32 |  |
| 0.03 | 1960 | -3.46 |  |
| 0.05 | 1420 | -1.99 |  |
| 0.08 | 859 | -1.97 | ◄ scelta |
| 0.10 | 603 | -3.09 |  |
| 0.15 | 271 | -3.49 |  |
| 0.20 | 120 | -3.79 |  |

**Riferimento: puntare su tutti gli esiti** (CLV = valore atteso della quota giocata alle probabilità di chiusura senza margine: è il punto di partenza da cui leggere il CLV delle scommesse selezionate; la Max è la quota più alta tra i bookmaker raccolti, ma resta sotto il prezzo «giusto» della chiusura):

| Strategia | Insieme | N scommesse | ROI (%) [IC blocchi] | CLV (%) [IC blocchi] |
|---|---|---|---|---|
| tutti gli esiti alla Max | validazione | 10750 | -1.18 [-1.68; -0.66] | -1.20 [-1.29; -1.12] |
| tutti gli esiti alle Avg | validazione | 10750 | -5.23 [-5.69; -4.77] | -5.25 [-5.32; -5.18] |
| tutti gli esiti alla Max | held-out | 15058 | -2.40 [-2.89; -1.90] | -2.34 [-2.52; -2.17] |
| tutti gli esiti alle Avg | held-out | 15058 | -5.66 [-6.13; -5.20] | -5.63 [-5.77; -5.49] |
| tutti gli esiti alla Max | 2026/27 | 894 | -4.74 [-6.78; -2.55] | -3.84 [-4.27; -3.33] |
| tutti gli esiti alle Avg | 2026/27 | 894 | -7.84 [-9.88; -5.65] | -7.25 [-7.43; -7.04] |

**Max (quote massime: segnale e regolamento)** — θ = 0.10

| Insieme | N scommesse | ROI (%) [IC blocchi] | CLV (%) vs chiusura senza margine [IC] | CLV (%) vs quota di chiusura grezza, margine incluso [IC] |
|---|---|---|---|---|
| validazione | 1370 | 3.46 [-2.72; 9.69] | -1.52 [-2.08; -0.96] | 5.68 [5.12; 6.24] |
| held-out | 1840 | -4.15 [-9.11; 0.81] | -3.54 [-4.00; -3.09] | 3.93 [3.53; 4.36] |
| 2026/27 | 113 | -2.27 [-21.29; 19.47] | -2.25 [-6.09; 1.48] | 8.63 [5.87; 11.26] |

Per stagione (held-out):

| Stagione | N | ROI (%) [IC] | CLV (%) [IC] |
|---|---|---|---|
| 2022/23 | 453 | -3.10 [-11.69; 5.44] | -2.99 [-3.69; -2.28] |
| 2023/24 | 505 | -6.08 [-17.28; 5.26] | -3.88 [-4.60; -3.06] |
| 2024/25 | 433 | -1.36 [-12.24; 9.21] | -2.61 [-3.30; -1.93] |
| 2025/26 | 336 | -6.89 [-17.04; 2.11] | -5.42 [-6.34; -4.45] |
| 2026/27 | 113 | -2.27 [-21.29; 19.47] | -2.25 [-6.09; 1.48] |

Per lega (held-out):

| Lega | N | ROI (%) [IC] | CLV (%) [IC] |
|---|---|---|---|
| Serie A | 436 | -3.49 [-14.10; 7.04] | -3.60 [-4.34; -2.86] |
| Premier | 305 | 7.63 [-4.14; 19.64] | -1.12 [-2.77; 0.70] |
| Bundesliga | 306 | -8.42 [-21.54; 4.82] | -4.74 [-5.91; -3.51] |
| La Liga | 570 | -8.27 [-18.53; 1.53] | -4.59 [-5.21; -3.96] |
| Ligue 1 | 223 | -5.17 [-18.75; 8.74] | -2.41 [-3.56; -1.27] |

Per esito (held-out):

| Esito | N | ROI (%) [IC] | CLV (%) [IC] |
|---|---|---|---|
| Over 2,5 | 1183 | -5.35 [-10.65; -0.10] | -2.91 [-3.49; -2.24] |
| Under 2,5 | 657 | -1.99 [-12.79; 8.70] | -4.67 [-5.54; -3.70] |

Per esito (validazione):

| Esito | N | ROI (%) [IC] | CLV (%) [IC] |
|---|---|---|---|
| Over 2,5 | 795 | 2.05 [-5.17; 9.07] | -1.17 [-1.84; -0.50] |
| Under 2,5 | 575 | 5.42 [-5.66; 16.80] | -1.99 [-2.95; -1.13] |

**Avg (quote medie: segnale e regolamento)** — θ = 0.08

| Insieme | N scommesse | ROI (%) [IC blocchi] | CLV (%) vs chiusura senza margine [IC] | CLV (%) vs quota di chiusura grezza, margine incluso [IC] |
|---|---|---|---|---|
| validazione | 859 | -1.97 [-10.08; 5.76] | -6.28 [-6.92; -5.68] | 0.64 [-0.01; 1.23] |
| held-out | 1357 | -8.71 [-14.49; -2.95] | -7.90 [-8.39; -7.43] | -0.60 [-0.95; -0.24] |
| 2026/27 | 83 | -1.64 [-20.57; 19.79] | -11.71 [-14.56; -8.91] | -0.69 [-2.62; 1.19] |

Per stagione (held-out):

| Stagione | N | ROI (%) [IC] | CLV (%) [IC] |
|---|---|---|---|
| 2022/23 | 330 | -8.37 [-18.01; 1.41] | -6.87 [-7.66; -6.01] |
| 2023/24 | 365 | -12.80 [-24.29; -1.11] | -7.71 [-8.45; -6.93] |
| 2024/25 | 333 | -5.76 [-19.62; 7.94] | -6.92 [-7.69; -6.17] |
| 2025/26 | 246 | -9.50 [-22.04; 2.13] | -9.61 [-10.73; -8.49] |
| 2026/27 | 83 | -1.64 [-20.57; 19.79] | -11.71 [-14.56; -8.91] |

Per lega (held-out):

| Lega | N | ROI (%) [IC] | CLV (%) [IC] |
|---|---|---|---|
| Serie A | 331 | -8.37 [-19.81; 3.51] | -7.42 [-8.21; -6.58] |
| Premier | 199 | -1.32 [-15.89; 13.38] | -7.02 [-8.20; -5.86] |
| Bundesliga | 231 | -6.89 [-22.68; 8.53] | -9.29 [-10.70; -7.83] |
| La Liga | 448 | -12.41 [-23.57; -1.18] | -8.56 [-9.21; -7.91] |
| Ligue 1 | 148 | -11.11 [-27.51; 4.85] | -5.99 [-7.32; -4.65] |

Per esito (held-out):

| Esito | N | ROI (%) [IC] | CLV (%) [IC] |
|---|---|---|---|
| Over 2,5 | 873 | -10.82 [-16.91; -4.70] | -7.27 [-7.74; -6.80] |
| Under 2,5 | 484 | -4.93 [-16.77; 7.38] | -9.03 [-9.99; -8.00] |

Per esito (validazione):

| Esito | N | ROI (%) [IC] | CLV (%) [IC] |
|---|---|---|---|
| Over 2,5 | 487 | 0.47 [-8.79; 9.52] | -5.66 [-6.38; -4.96] |
| Under 2,5 | 372 | -5.17 [-18.80; 8.51] | -7.10 [-8.32; -6.03] |

**Segnale con Max, regolamento alle quote medie** — θ = 0.10

| Insieme | N scommesse | ROI (%) [IC blocchi] | CLV (%) vs chiusura senza margine [IC] | CLV (%) vs quota di chiusura grezza, margine incluso [IC] |
|---|---|---|---|---|
| validazione | 1370 | -1.63 [-7.46; 4.24] | -6.40 [-6.91; -5.93] | 0.41 [-0.08; 0.86] |
| held-out | 1840 | -8.23 [-12.99; -3.47] | -7.74 [-8.18; -7.32] | -0.62 [-0.92; -0.31] |
| 2026/27 | 113 | -8.84 [-27.45; 12.75] | -10.46 [-12.67; -8.64] | -0.39 [-1.53; 0.53] |


---

## V4 — registro quote dei mercati secondari (preparazione, nulla è attivato)

Nessun codice di produzione modificato, nessuna chiave API creata, nessuna chiamata a servizi esterni a pagamento. **Prima di implementare servono le tue decisioni su costi e limiti qui sotto.**

### Come è stata fatta la verifica (e cosa NON è verificato)
Le pagine ufficiali di The Odds API (guida v4, elenco mercati, prezzi) **non si sono lasciate leggere da questo ambiente** (connessione resettata a ogni tentativo, anche dal browser integrato). Ho quindi usato solo i frammenti dei risultati di ricerca web: la pagina ufficiale «List of API Betting Markets» compare nei risultati, ma i dettagli sul piano gratuito vengono da siti di terzi, in parte concorrenti (OddsPapi, SharpAPI, SportsGameOdds). **I numeri sotto vanno confermati con una chiamata di prova** (l'intestazione di risposta `x-requests-remaining` dice quanti crediti costa ogni richiesta) prima di decidere.

| Voce | Cosa risulta | Affidabilità |
|---|---|---|
| Piano gratuito The Odds API | 500 crediti al mese, senza carta | alta (concorde in tutte le fonti) |
| Costo di una richiesta | 1 credito per mercato per regione (esempio: 3 mercati × 2 regioni = 6 crediti); dati storici 10× | media (fonti di terzi, concordi) |
| Piano a pagamento di ingresso | ~30 $/mese per 20.000 crediti (una fonte dice 25 $) | media (prezzi discordanti) |
| Mercati calcio nell'elenco ufficiale | «Total Corners (Over/Under)», «Total Cards / Bookings (Over/Under)», «Player Shots», «Player Shots on Target»; i mercati giocatore risultano per Premier, Ligue 1, Bundesliga, Serie A, La Liga | media (frammento della pagina ufficiale) |
| Chiavi esatte `alternate_totals_corners`, `alternate_totals_cards`, `player_shots` | i primi due compaiono nella tabella degli «altri mercati calcio»; `player_shots` e `player_shots_on_target` tra i mercati giocatore | media; la chiave del tiro del giocatore va controllata (`player_shots` vs `player_shots_on_target`) |
| Mercati aggiuntivi solo con l'endpoint per singola partita (`/events/{id}/odds`) e solo per alcuni bookmaker/regioni | così risultano dalla documentazione per i mercati non-base | media |
| I mercati aggiuntivi sono inclusi nel piano gratuito? | le fonti non concordano («tutti i mercati» vs «dipende da sport e bookmaker») | **non verificato** |
| Copertura per lega e bookmaker dei corner/cartellini | non trovata | **non verificato** |
| Storico delle quote | solo piano a pagamento, 10× i crediti → non si può recuperare il passato: il registro va avviato per accumulare | media |

### Cosa si può misurare e cosa no (indipendentemente dal fornitore)
- **Gialli e corner (totali di partita)**: esiste il mercato Over/Under e il modello ha già la distribuzione (`stats_json`: media, intervalli, probabilità): è l'unico confronto diretto possibile.
- **Tiri**: il mercato elencato è **per giocatore** (`player_shots`, `player_shots_on_target`). Il modello prevede i tiri **di squadra**: non c'è un confronto diretto e non si ricostruisce il totale dalla somma dei giocatori (le quote giocatore non coprono tutti i giocatori e il margine si somma). Per misurare il margine sui tiri serve un mercato di squadra (tiri totali / tiri in porta della squadra), che **non risulta nell'elenco**.
- **Falli**: nessun mercato trovato nelle fonti consultate → **non misurabile** con questo fornitore.
- Quindi, con The Odds API, il margine misurabile è su **gialli e corner**; i tiri solo se il fornitore ha le linee di squadra, i falli no.

### Volumi e costo (The Odds API, 1 regione, calcolati sulle formule sopra)
Partite a settimana nei 5 campionati (Serie A 10, Premier 10, Bundesliga 9, La Liga 10, Ligue 1 9) = **48**, circa **208 al mese** nella stagione. Costo per partita e per istantanea = (numero di mercati) × (numero di regioni).

| Scenario | Crediti/mese | Piano gratuito (500) |
|---|---|---|
| 1 istantanea per partita, 2 mercati (cartellini + corner) | 208 × 2 = **416** | **sì**, con 84 crediti di margine |
| 1 istantanea per partita, 3 mercati (+ tiri giocatore) | 208 × 3 = **624** | **no** (+25 %) |
| 2 istantanee per partita (giorni prima + vicino al calcio d'inizio, serve per il CLV), 2 mercati | 208 × 4 = **832** | no |
| 2 istantanee, 3 mercati | 208 × 6 = **1.248** | no; ci sta nel piano da 20.000 (~6 %) |
| Raccolta quotidiana (≈ 3 istantanee per partita nei 3 giorni prima), 3 mercati | 208 × 9 = **1.872** | no; ci sta nel piano da 20.000 (~9 %) |

(L'elenco delle partite, `/events`, nella documentazione risulta gratuito: da confermare con la prova.) Il piano gratuito basta quindi solo per **una istantanea per partita e due mercati**; con una sola istantanea si misura il margine (confronto con l'esito) ma **non il CLV** sui mercati secondari. Per avere due istantanee e i tre mercati serve il piano a pagamento (~30 $/mese), da tenere solo per le stagioni di misura (non è un vincolo fisso).

### Alternative gratuite (non verificate: solo frammenti di ricerca)
- **RapidOddsAPI**: 250 crediti gratuiti, elenca corner e cartellini; nessun cenno ai tiri; credito insufficiente per un registro continuo.
- **TheRundown**: piano gratuito con 20.000 dati/giorno e 200.000/mese, ma con bookmaker americani, ritardo di 5 minuti e senza conferma di mercati calcio secondari.
- **OddsPapi** (concorrente di The Odds API): dichiara un piano gratuito da 250 richieste con molti bookmaker; copertura dei mercati secondari non verificata.
- **API-Football**: ha un'API quote con mercati corner e cartellini; piano gratuito con limite giornaliero basso (dalla mia conoscenza ~100 richieste/giorno, non verificato qui) e limiti sulle stagioni; da controllare.
Nessuna è stata provata: ognuna richiede un account e una chiave, che non posso creare io.

### Schema proposto (non implementato)
`history.csv` ha una riga per partita (upsert fino al calcio d'inizio) e già le colonne `stats_json` (medie, intervalli, probabilità) e `bm_*`; le quote dei mercati secondari sono molte per partita (mercato × linea × bookmaker × istantanea) e non entrano in colonne larghe. Si propone quindi:

1. **Registro grezzo, a righe lunghe, solo in aggiunta**: `docs/odds_log.csv` (non letto dal sito)
   `snapshot_utc, league, match_date, home, away, event_id, market, scope, player, line, bookmaker, odds_over, odds_under, source, request_credits`
   - `market` ∈ {cards, corners, shots, sot}; `scope` ∈ {match, home, away, player}; una riga per bookmaker e linea; nessuna riga viene riscritta.
2. **Riepilogo in `history.csv`**, per statistica S ∈ {gialli, corner, tiri, sot} e solo per le linee di partita (totale):
   `q_S_line` (linea più vicina al 50 % del mercato), `q_S_over`, `q_S_under` (mediana dei bookmaker, quote), `q_S_pover_mkt` (probabilità Over senza margine), `q_S_snap` (istante dell'istantanea), e `m_S_pover` (probabilità Over del modello alla stessa linea, calcolata dalla distribuzione di `stats_json`/`nb_interval` **al momento dell'emissione**, non dopo). Per il CLV, una seconda istantanea: `q_S_pover_mkt_close`, `q_S_snap_close`.
   Sono 4 statistiche × 7 colonne = 28 colonne in più (da riempire solo se l'istantanea esiste; l'upsert esistente le lascia congelate dopo il calcio d'inizio come le altre).
3. **Misura dopo qualche settimana**: log-loss dell'Over/Under del modello contro quello del mercato alla stessa linea (stesso schema di V1), correlazione divario modello − mercato / spostamento verso la chiusura (stesso schema di V2). Stima di potenza: la deviazione standard per partita della differenza di log-loss su un mercato binario è dell'ordine di 0,02-0,03, quindi con ~200 partite per statistica (circa 4-5 settimane a 48 partite) l'errore standard è ~0,0015-0,002: si distinguono differenze di qualche millesimo, non di decimi di millesimo.

### Cosa serve per decidere
1. Piano: gratuito (1 istantanea, cartellini + corner, 416 crediti/mese) oppure a pagamento (~30 $/mese) per due istantanee e i tiri.
2. Una chiave API (la crei tu su the-odds-api.com; va in un secret di GitHub Actions) e una prova di una chiamata per confermare costi, mercati e bookmaker per le cinque leghe.
3. Se i tiri ti interessano davvero: serve un fornitore con le linee di squadra; con questo, no.


---

## V5 — favorite in trasferta in Serie A

### Passo 0 — riproduzione dei numeri dell'analisi originale (solo controllo dei dati, nessuna decisione)

| margine tolto con | N (≥ 40 %) | % ospite vince | % implicita | ROI quota media pre (%) | ROI quota media chiusura (%) | stagioni con eccesso > 0 |
|---|---|---|---|---|---|---|
| norm | 822 | 60.7 | 53.3 | 8.4 | 8.6 | 8/8 |
| power | 830 | 60.4 | 54.3 | 8.0 | 8.1 | 8/8 |

Originale: 827 partite, 61 % contro 53 %, +8,7 % (apertura) e +8,9 % (chiusura), 7 stagioni su 8.

### V5a — verifica con soglia scelta in validazione

| Soglia / gruppo | Finestra | N | % implicita | % osservata | eccesso (pt) [IC blocchi] | ROI quota pre (%) [IC] | ROI quota chiusura (%) [IC] | CLV (%) [IC] |
|---|---|---|---|---|---|---|---|---|
| p_ospite ≥ 35 % | 2013/14-2018/19 (indipendente) | 765 | 50.4 | 52.9 | 2.5 [-0.5; 5.5] | 1.2 [-5.2; 7.7] | 2.7 [-3.8; 9.4] | -3.3 [-3.8; -2.8] |
|  | validazione 2019/20-2021/22 | 475 | 51.1 | 55.6 | 4.5 [0.3; 8.8] | 4.8 [-3.6; 13.5] | 4.3 [-4.0; 12.9] | -2.8 [-3.5; -2.1] |
|  | held-out 2022/23+ | 604 | 49.9 | 54.6 | 4.7 [0.4; 9.0] | 5.0 [-3.8; 13.9] | 5.3 [-3.5; 14.2] | -3.6 [-4.2; -3.1] |
| p_ospite ≥ 40 % | 2013/14-2018/19 (indipendente) | 603 | 53.9 | 56.9 | 3.0 [-0.7; 6.5] | 2.4 [-4.4; 9.3] | 3.6 [-3.3; 10.6] | -3.1 [-3.6; -2.5] |
|  | validazione 2019/20-2021/22 | 367 | 55.1 | 61.3 | 6.2 [1.4; 10.9] | 8.5 [-0.2; 17.4] | 8.2 [-0.4; 16.8] | -2.6 [-3.4; -1.7] |
|  | held-out 2022/23+ | 463 | 53.6 | 59.6 | 6.0 [1.6; 10.6] | 7.5 [-1.1; 16.2] | 8.1 [-0.5; 16.9] | -3.1 [-3.7; -2.6] |
| p_ospite ≥ 45 % | 2013/14-2018/19 (indipendente) | 459 | 57.5 | 60.6 | 3.1 [-1.2; 7.2] | 2.5 [-5.1; 9.6] | 3.7 [-4.2; 11.1] | -2.9 [-3.6; -2.2] |
|  | validazione 2019/20-2021/22 | 293 | 58.3 | 66.2 | 7.9 [2.1; 13.3] | 11.8 [2.3; 21.3] | 11.2 [2.0; 20.6] | -2.0 [-2.9; -1.1] |
|  | held-out 2022/23+ | 365 | 56.5 | 62.7 | 6.2 [1.2; 11.0] | 7.4 [-1.6; 16.2] | 7.8 [-1.2; 16.6] | -3.0 [-3.6; -2.4] |

**Soglia scelta in validazione** (limite inferiore dell'IC dell'eccesso più alto): **t* = 45 %**.

**Verdetto V5a (criteri della preregistrazione):** (i) held-out: eccesso 6.2 [1.2; 11.0] punti → IC esclude zero; (ii) 2013/14-2018/19: eccesso 3.1 [-1.2; 7.2] punti → IC comprende zero o negativo; (iii) p-value di famiglia V6 = 1.7 % → < 5 %. **→ coerente nel periodo di scoperta ma non confermata.**

**Per stagione (Serie A, p_ospite ≥ 45 %):**

| Stagione | N | % implicita | % osservata | eccesso (pt) [IC] | ROI quota pre (%) [IC] |
|---|---|---|---|---|---|
| 2013/14 | 63 | 55.4 | 57.1 | 1.7 [-8.6; 11.8] | -1.3 [-20.6; 16.5] |
| 2014/15 | 58 | 54.9 | 51.7 | -3.2 [-16.7; 9.1] | -6.2 [-29.8; 16.5] |
| 2015/16 | 69 | 55.7 | 60.9 | 5.2 [-6.5; 16.2] | 6.7 [-13.6; 27.7] |
| 2016/17 | 83 | 59.3 | 63.9 | 4.6 [-4.6; 13.8] | 5.1 [-10.8; 21.2] |
| 2017/18 | 94 | 59.9 | 64.9 | 5.0 [-3.3; 12.9] | 5.4 [-8.9; 19.6] |
| 2018/19 | 92 | 57.8 | 60.9 | 3.1 [-7.8; 12.9] | 2.0 [-17.1; 19.7] |
| 2019/20 | 93 | 57.9 | 66.7 | 8.8 [-2.9; 20.5] | 14.0 [-6.8; 33.0] |
| 2020/21 | 105 | 59.5 | 64.8 | 5.3 [-3.7; 14.5] | 6.5 [-9.3; 21.6] |
| 2021/22 | 95 | 57.4 | 67.4 | 9.9 [2.1; 17.5] | 15.5 [1.5; 28.6] |
| 2022/23 | 87 | 55.7 | 55.2 | -0.5 [-11.4; 11.0] | -4.5 [-24.5; 17.3] |
| 2023/24 | 80 | 55.3 | 61.3 | 5.9 [-4.1; 16.6] | 7.2 [-10.5; 26.8] |
| 2024/25 | 87 | 56.6 | 67.8 | 11.2 [0.5; 21.6] | 16.9 [-2.6; 35.7] |
| 2025/26 | 85 | 58.0 | 64.7 | 6.7 [-2.6; 14.7] | 7.1 [-8.8; 21.3] |
| 2026/27 (parziale) | 26 | 58.0 | 69.2 | 11.3 [-2.8; 22.3] | 16.7 [-5.6; 33.8] |

**Stessa regola negli altri campionati (descrittivo):**

| Soglia / gruppo | Finestra | N | % implicita | % osservata | eccesso (pt) [IC blocchi] | ROI quota pre (%) [IC] | ROI quota chiusura (%) [IC] | CLV (%) [IC] |
|---|---|---|---|---|---|---|---|---|
| Serie A | 2013/14-2018/19 (indipendente) | 459 | 57.5 | 60.6 | 3.1 [-1.2; 7.2] | 2.5 [-5.1; 9.6] | 3.7 [-4.2; 11.1] | -2.9 [-3.6; -2.2] |
|  | scoperta 2019/20+ | 658 | 57.3 | 64.3 | 7.0 [3.3; 10.5] | 9.3 [2.8; 15.8] | 9.3 [2.9; 15.7] | -2.5 [-3.1; -2.0] |
| Premier | 2013/14-2018/19 (indipendente) | 482 | 59.1 | 63.1 | 3.9 [-0.1; 7.9] | 4.3 [-2.7; 11.1] | 4.9 [-2.3; 11.7] | -1.6 [-2.2; -1.1] |
|  | scoperta 2019/20+ | 647 | 58.9 | 58.1 | -0.8 [-4.6; 3.1] | -4.2 [-10.8; 2.6] | -3.5 [-10.2; 3.4] | -2.7 [-3.1; -2.2] |
| Bundesliga | 2013/14-2018/19 (indipendente) | 312 | 60.3 | 56.1 | -4.2 [-9.0; 0.6] | -10.4 [-18.4; -2.1] | -9.5 [-17.7; -1.1] | -2.4 [-3.0; -1.8] |
|  | scoperta 2019/20+ | 459 | 59.5 | 56.9 | -2.6 [-6.7; 1.6] | -7.3 [-14.5; -0.0] | -7.3 [-14.5; 0.1] | -2.7 [-3.2; -2.2] |
| La Liga | 2013/14-2018/19 (indipendente) | 382 | 62.6 | 61.0 | -1.6 [-6.8; 3.6] | -4.5 [-13.2; 4.2] | -3.4 [-12.2; 5.4] | -2.5 [-3.2; -1.9] |
|  | scoperta 2019/20+ | 432 | 57.2 | 59.7 | 2.6 [-2.0; 7.1] | 3.1 [-5.2; 10.9] | 2.4 [-5.8; 10.3] | -2.1 [-2.6; -1.5] |
| Ligue 1 | 2013/14-2018/19 (indipendente) | 259 | 59.1 | 61.0 | 1.9 [-3.7; 7.6] | 0.4 [-9.6; 10.4] | 2.5 [-7.9; 12.8] | -3.0 [-3.7; -2.3] |
|  | scoperta 2019/20+ | 468 | 57.0 | 56.6 | -0.3 [-4.4; 4.0] | -4.1 [-11.4; 3.7] | -4.5 [-11.8; 3.1] | -2.2 [-2.8; -1.6] |

### V5b — il modello v6 cattura l'effetto?

Sottoinsieme: Serie A, p_ospite (mercato pre-partita) ≥ 45 %, previsioni fuori campione del modello (2019/20+). Guadagno = log-loss(mercato) − log-loss(modello): positivo = il modello è meglio.

| Sottoinsieme | Finestra | N | % ospite modello | % ospite mercato pre | % ospite mercato chiusura | % osservata | modello − mercato (pt) [IC] | ll modello | ll mercato pre | guadagno vs mercato pre [IC] | guadagno vs mercato chiusura [IC] |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A_t* (p_ospite ≥ 45 %) | validazione 2019/20-2021/22 | 293 | 56.1 | 58.3 | 58.7 | 66.2 | -2.18 [-2.89; -1.44] | 0.8786 | 0.8737 | -0.0049 [-0.0184; 0.0087] | -0.0115 [-0.0289; 0.0055] |
|  | held-out 2022/23+ | 365 | 54.5 | 56.5 | 56.5 | 62.7 | -2.04 [-2.58; -1.50] | 0.9169 | 0.8972 | -0.0197 [-0.0296; -0.0099] | -0.0198 [-0.0316; -0.0076] |
| tutta la Serie A | validazione 2019/20-2021/22 | 1139 | 32.0 | 32.9 | 32.8 | 35.0 | -0.95 [-1.37; -0.57] | 0.9647 | 0.9570 | -0.0077 [-0.0147; -0.0008] | -0.0112 [-0.0191; -0.0030] |
|  | held-out 2022/23+ | 1618 | 31.6 | 31.5 | 31.5 | 32.0 | 0.09 [-0.06; 0.25] | 0.9710 | 0.9637 | -0.0073 [-0.0117; -0.0029] | -0.0085 [-0.0140; -0.0029] |

### V5c — correzione specifica della Serie A (walk-forward)

K1 = intercette di classe della Serie A (vantaggio casa); K2 = K1 + interazione «ospite favorito» (p_modello,ospite ≥ t*) per l'esito ospite. Stimate su 2019/20…s−1 sulle sole partite di Serie A, applicate alla Serie A nella stagione s (da 2020/21); altre leghe invariate. Δ = log-loss(baseline) − log-loss(variante): positivo = migliora.

Parametri per fold (a_X / a_2 rispetto alla casa; b = coefficiente dell'interazione):

| Test | N addestramento | K1: a_X / a_2 | K2: a_X / a_2 | K2: b |
|---|---|---|---|---|
| 2020/21 | 380 | +0.126 / +0.331 | +0.140 / +0.262 | +0.285 |
| 2021/22 | 760 | +0.196 / +0.263 | +0.211 / +0.184 | +0.297 |
| 2022/23 | 1139 | +0.217 / +0.254 | +0.234 / +0.166 | +0.319 |
| 2023/24 | 1519 | +0.193 / +0.190 | +0.204 / +0.126 | +0.225 |
| 2024/25 | 1899 | +0.197 / +0.143 | +0.214 / +0.048 | +0.340 |
| 2025/26 | 2279 | +0.208 / +0.146 | +0.227 / +0.033 | +0.413 |
| 2026/27 | 2659 | +0.203 / +0.161 | +0.222 / +0.050 | +0.410 |

| Insieme | Finestra | Variante | N | ll baseline | ll variante | Δ [IC blocchi] |
|---|---|---|---|---|---|---|
| tutte e 5 le leghe (guadagno complessivo) | validazione 2020/21-2021/22 | K1 | 3651 | 0.9888 | 0.9882 | 0.00064 [-0.00092; 0.00220] |
|  | validazione 2020/21-2021/22 | K2 | 3651 | 0.9888 | 0.9878 | 0.00107 [-0.00064; 0.00285] |
| solo Serie A | validazione 2020/21-2021/22 | K1 | 759 | 0.9620 | 0.9590 | 0.00306 [-0.00456; 0.01034] |
|  | validazione 2020/21-2021/22 | K2 | 759 | 0.9620 | 0.9569 | 0.00515 [-0.00318; 0.01342] |
| Serie A, p_ospite mercato ≥ 45 % | validazione 2020/21-2021/22 | K1 | 200 | 0.8716 | 0.8522 | 0.01939 [0.00589; 0.03285] |
|  | validazione 2020/21-2021/22 | K2 | 200 | 0.8716 | 0.8480 | 0.02360 [-0.00031; 0.04751] |
| tutte e 5 le leghe (guadagno complessivo) | held-out 2022/23+ | K1 | 7529 | 0.9736 | 0.9736 | 0.00006 [-0.00077; 0.00089] |
|  | held-out 2022/23+ | K2 | 7529 | 0.9736 | 0.9728 | 0.00082 [-0.00034; 0.00193] |
| solo Serie A | held-out 2022/23+ | K1 | 1618 | 0.9710 | 0.9707 | 0.00026 [-0.00341; 0.00415] |
|  | held-out 2022/23+ | K2 | 1618 | 0.9710 | 0.9672 | 0.00382 [-0.00131; 0.00902] |
| Serie A, p_ospite mercato ≥ 45 % | held-out 2022/23+ | K1 | 365 | 0.9169 | 0.9145 | 0.00233 [-0.00554; 0.00985] |
|  | held-out 2022/23+ | K2 | 365 | 0.9169 | 0.9063 | 0.01057 [-0.00563; 0.02606] |

**Scelta in validazione** (log-loss della Serie A: K1 0.9590, K2 0.9569, baseline 0.9620; K2 solo se migliora di almeno 0,0002): **K2**. Guadagno complessivo nell'held-out con K2: Δ = 0.00082 [-0.00034; 0.00193] → **non distinguibile dal rumore**.

### V5d — scommesse a puntata fissa sulle favorite in trasferta di Serie A (quota media, non massima)

1 unità sull'ospite in ogni partita di Serie A con p_ospite ≥ 45 %, alla quota media pre-partita; riferimento alla quota media di chiusura. Drawdown = massima discesa picco-valle del profitto cumulato (in unità, partite in ordine di data).

| Finestra | N scommesse | profitto (unità) | ROI quota pre (%) [IC blocchi] | ROI quota chiusura (%) [IC] | CLV (%) [IC] | max drawdown osservato (unità) | drawdown ricampionando settimane (5° / 50° / 95° perc.) |
|---|---|---|---|---|---|---|---|
| 2013/14-2018/19 (indipendente) | 459 | +11.3 | 2.5 [-5.1; 9.6] | 3.7 [-4.2; 11.1] | -2.9 [-3.6; -2.2] | 10.7 | 8.6 / 15.9 / 31.0 |
| validazione 2019/20-2021/22 | 293 | +34.6 | 11.8 [2.3; 21.3] | 11.2 [2.0; 20.6] | -2.0 [-2.9; -1.1] | 6.8 | 5.1 / 8.3 / 14.1 |
| held-out 2022/23+ | 365 | +26.9 | 7.4 [-1.6; 16.2] | 7.8 [-1.2; 16.6] | -3.0 [-3.6; -2.4] | 9.7 | 6.6 / 11.3 / 21.1 |
| scoperta 2019/20+ | 658 | +61.4 | 9.3 [2.8; 15.8] | 9.3 [2.9; 15.7] | -2.5 [-3.1; -2.0] | 9.7 | 7.8 / 12.1 / 21.4 |

**Riferimenti:**

| Soglia / gruppo | Finestra | N | % implicita | % osservata | eccesso (pt) [IC blocchi] | ROI quota pre (%) [IC] | ROI quota chiusura (%) [IC] | CLV (%) [IC] |
|---|---|---|---|---|---|---|---|---|
| tutte le trasferte, Serie A | 2013/14-2018/19 (indipendente) | 2280 | 29.9 | 29.9 | 0.0 [-1.7; 1.8] | -12.5 [-19.2; -6.0] | -8.3 [-15.4; -1.1] | -8.5 [-9.0; -8.0] |
|  | scoperta 2019/20+ | 2757 | 32.1 | 33.2 | 1.1 [-0.6; 2.8] | -5.6 [-11.9; 0.7] | -5.3 [-11.7; 1.3] | -6.9 [-7.2; -6.5] |
| favorite in trasferta ≥ soglia, altri 4 campionati | 2013/14-2018/19 (indipendente) | 1435 | 60.3 | 60.6 | 0.3 [-2.2; 2.8] | -2.0 [-6.3; 2.4] | -0.9 [-5.3; 3.5] | -2.3 [-2.6; -2.0] |
|  | scoperta 2019/20+ | 2006 | 58.2 | 57.8 | -0.4 [-2.5; 1.7] | -3.3 [-7.0; 0.3] | -3.3 [-7.0; 0.3] | -2.4 [-2.7; -2.1] |


---

## V6 — controllo dell'anomalia

### 1. Quante anomalie emergono per caso (simulazione nulla, 10000 simulazioni)

Ipotesi nulla: il mercato (pre-partita, senza margine) è calibrato; esiti 1X2 di tutte le partite 2019/20+ (12905) estratti dalle sue probabilità. Famiglia E: **105 celle** (lega × condizione, almeno 100 partite). Cella chiave = Serie A, esito 2, p_ospite ≥ 40 % (830 partite).

| Statistica (cella chiave, dati reali) | valore osservato | p-value di cella (unilaterale) | p-value di famiglia (almeno una delle 105 celle altrettanto estrema) |
|---|---|---|---|
| z dell'eccesso (vittorie osservate − attese) | 3.60 | 0.03 % | 1.7 % |
| z del ROI alla quota media pre-partita | 3.43 | 0.04 % | 2.9 % |

Massimo di z nella famiglia sotto l'ipotesi nulla: mediana 2.35, 90° percentile 3.04, 95° 3.25, 99° 3.74 (contro lo z osservato nella cella chiave: 3.60). P(massimo bilaterale |z| ≥ |z chiave|) = 2.7 %.

Stagioni positive della cella chiave: osservate 8 su 8; probabilità sotto l'ipotesi nulla di ottenerne almeno 7: 3.2 % (nella singola cella).

**Celle della famiglia oltre soglia: attese per caso contro osservate nei dati reali (le celle sono sovrapposte, il confronto è tra medie):**

| Soglia | attese sotto l'ipotesi nulla (media) | osservate nei dati reali |
|---|---|---|
| z ≥ 2,0 | 2.45 | 7 |
| z ≥ 2,5 | 0.71 | 7 |
| z ≥ 3,0 | 0.16 | 4 |
| |z| ≥ 2,0 | 4.78 | 11 |
| |z| ≥ 2,5 | 1.33 | 10 |
| |z| ≥ 3,0 | 0.30 | 5 |

**Le 12 celle con z più alto nei dati reali:**

| Cella | N | z eccesso | z ROI |
|---|---|---|---|
| Serie A · esito 2 con p ≥ 45% | 658 | 3.66 | 3.62 |
| Serie A · esito 2 con p ≥ 40% | 830 | 3.60 | 3.43 |
| Serie A · esito 2 con p ≥ 50% | 509 | 3.14 | 3.10 |
| Serie A · esito 2 con p ≥ 35% | 1079 | 3.12 | 2.68 |
| Serie A · esito 2 con p ≥ 55% | 375 | 2.85 | 2.89 |
| La Liga · esito 1 con p ≥ 55% | 766 | 2.77 | 2.69 |
| La Liga · esito 1 con p ≥ 60% | 540 | 2.63 | 2.63 |
| La Liga · pareggio con |p1−p2| ≤ 5 pt | 274 | 1.98 | 2.09 |
| Serie A · pareggio con |p1−p2| ≤ 10 pt | 508 | 1.93 | 1.86 |
| La Liga · pareggio con |p1−p2| ≤ 10 pt | 586 | 1.90 | 1.95 |
| La Liga · esito 1 con p ≥ 35% | 1882 | 1.84 | 1.54 |
| La Liga · esito 1 con p ≥ 40% | 1573 | 1.77 | 1.50 |

### 2. Le quattro condizioni scelte prima di guardare i dati, nei cinque campionati

Una soglia per condizione, nessuna ottimizzazione. Cella = « N · eccesso in punti [IC blocchi] · ROI a quota media pre-partita [IC] ». z e stagioni positive nella finestra di scoperta.

**H — favorita in casa: p_casa ≥ 60 % → vittoria in casa**

| Lega | pre-2019 (indipendente) | validazione | held-out | scoperta | z (scoperta) | stagioni con eccesso > 0 |
|---|---|---|---|---|---|---|
| Serie A | 569 · +0.6 [-3.3; +4.3] · -1.5 [-6.8; +3.7] | 269 · -2.2 [-7.5; +2.7] · -5.0 [-12.3; +1.9] | 345 · +0.6 [-4.4; +5.5] · -1.2 [-8.4; +5.7] | 614 · -0.6 [-4.2; +2.7] · -2.9 [-7.9; +2.2] | -0.33 | 4/8 |
| Premier | 541 · +1.2 [-2.4; +4.6] · -0.1 [-5.0; +4.8] | 261 · -3.8 [-8.9; +1.5] · -6.8 [-13.9; +0.4] | 376 · -2.4 [-7.0; +2.0] · -5.5 [-11.7; +0.9] | 637 · -3.0 [-6.4; +0.5] · -6.0 [-10.9; -1.3] | -1.71 | 2/8 |
| Bundesliga | 368 · -2.5 [-7.0; +1.9] · -5.3 [-11.4; +1.0] | 203 · -1.3 [-7.8; +4.8] · -3.3 [-12.8; +5.2] | 281 · -1.6 [-6.7; +3.5] · -4.4 [-11.4; +2.8] | 484 · -1.5 [-5.5; +2.4] · -3.9 [-9.6; +1.9] | -0.76 | 4/8 |
| La Liga | 573 · +0.5 [-2.9; +3.9] · -1.4 [-6.4; +3.4] | 229 · +3.0 [-2.9; +8.8] · +3.0 [-5.3; +11.0] | 311 · +6.5 [+1.9; +11.0] · +6.8 [+0.3; +12.9] | 540 · +5.0 [+1.4; +8.5] · +5.2 [+0.2; +10.5] | 2.63 | 7/8 |
| Ligue 1 | 391 · +2.3 [-2.1; +6.5] · +0.6 [-5.6; +6.5] | 168 · -2.6 [-10.0; +4.5] · -6.1 [-16.5; +3.9] | 298 · +0.5 [-4.4; +5.0] · -1.3 [-8.1; +5.4] | 466 · -0.6 [-4.5; +3.3] · -3.0 [-8.7; +2.4] | -0.29 | 3/8 |
| Tutti i campionati | 2442 · +0.5 [-1.2; +2.2] · -1.4 [-3.9; +1.0] | 1130 · -1.4 [-4.1; +1.2] · -3.7 [-7.5; -0.0] | 1611 · +0.7 [-1.5; +2.8] · -1.2 [-4.3; +1.8] | 2741 · -0.2 [-2.0; +1.5] · -2.2 [-4.6; +0.1] | -0.24 | 3/8 |

**D — equilibrio: |p_casa − p_ospite| ≤ 10 pt → pareggio**

| Lega | pre-2019 (indipendente) | validazione | held-out | scoperta | z (scoperta) | stagioni con eccesso > 0 |
|---|---|---|---|---|---|---|
| Serie A | 380 · -0.3 [-5.0; +4.5] · -7.2 [-22.1; +8.2] | 215 · +1.2 [-5.1; +7.5] · -1.4 [-22.0; +19.9] | 293 · +5.8 [+0.3; +11.6] · +12.9 [-5.2; +31.8] | 508 · +3.9 [-0.3; +8.2] · +6.8 [-7.1; +21.0] | 1.93 | 5/8 |
| Premier | 404 · +2.8 [-1.7; +7.3] · +4.6 [-10.1; +19.4] | 214 · +2.8 [-3.6; +9.6] · +5.1 [-16.0; +27.7] | 306 · +0.5 [-4.5; +5.6] · -3.6 [-20.9; +14.9] | 520 · +1.4 [-2.5; +5.6] · -0.0 [-13.4; +14.0] | 0.73 | 5/8 |
| Bundesliga | 412 · +0.5 [-3.6; +4.7] · -4.2 [-17.5; +10.1] | 179 · -2.7 [-9.0; +4.4] · -15.0 [-37.9; +9.5] | 279 · +2.2 [-3.6; +8.0] · +1.3 [-19.9; +22.1] | 458 · +0.3 [-4.1; +4.8] · -5.0 [-20.7; +10.5] | 0.14 | 3/8 |
| La Liga | 381 · +4.5 [-0.1; +9.2] · +8.4 [-6.8; +24.1] | 243 · +6.5 [+1.1; +12.5] · +15.4 [-1.8; +33.1] | 343 · +1.6 [-3.2; +6.2] · +0.2 [-14.8; +15.9] | 586 · +3.6 [-0.1; +7.0] · +6.5 [-5.0; +17.8] | 1.90 | 7/8 |
| Ligue 1 | 477 · +0.8 [-3.1; +5.0] · -3.3 [-15.7; +9.6] | 215 · +6.5 [+0.4; +12.8] · +16.3 [-2.6; +36.8] | 273 · -1.4 [-6.3; +3.5] · -11.4 [-27.6; +5.0] | 488 · +2.1 [-1.8; +6.0] · +0.8 [-11.9; +13.5] | 1.01 | 4/8 |
| Tutti i campionati | 2054 · +1.6 [-0.4; +3.6] · -0.5 [-6.8; +6.2] | 1066 · +3.1 [+0.4; +5.9] · +5.0 [-4.6; +14.6] | 1494 · +1.8 [-0.6; +4.1] · +0.0 [-7.7; +7.7] | 2560 · +2.3 [+0.6; +4.2] · +2.1 [-3.7; +8.3] | 2.61 | 7/8 |

**O — outsider in casa: p_casa ≤ 25 % → vittoria in casa**

| Lega | pre-2019 (indipendente) | validazione | held-out | scoperta | z (scoperta) | stagioni con eccesso > 0 |
|---|---|---|---|---|---|---|
| Serie A | 402 · -2.8 [-6.1; +0.8] · -24.1 [-42.6; -4.8] | 232 · -5.6 [-9.4; -1.6] · -42.1 [-62.3; -20.9] | 317 · -3.5 [-7.3; +0.5] · -31.4 [-50.1; -10.9] | 549 · -4.4 [-7.1; -1.5] · -35.9 [-49.6; -21.2] | -2.72 | 1/8 |
| Premier | 438 · +2.4 [-1.0; +6.0] · +4.9 [-16.1; +27.3] | 231 · +2.9 [-2.2; +7.9] · +3.2 [-27.5; +36.8] | 291 · -1.2 [-5.6; +3.2] · -17.2 [-39.6; +6.6] | 522 · +0.6 [-2.7; +4.0] · -8.2 [-26.7; +11.7] | 0.38 | 4/8 |
| Bundesliga | 246 · +4.0 [-0.6; +8.7] · +7.8 [-17.6; +34.7] | 169 · +5.3 [-1.0; +11.9] · +31.0 [-9.6; +77.1] | 169 · -1.9 [-7.1; +3.6] · -17.6 [-49.2; +16.8] | 338 · +1.7 [-2.4; +6.2] · +6.7 [-19.7; +35.3] | 0.87 | 4/8 |
| La Liga | 328 · +3.4 [-0.5; +7.5] · +12.9 [-15.5; +43.3] | 168 · -1.2 [-6.8; +4.9] · -8.8 [-38.5; +25.5] | 207 · -3.2 [-8.3; +1.9] · -19.8 [-46.9; +9.6] | 375 · -2.3 [-6.1; +1.6] · -14.9 [-36.0; +6.5] | -1.20 | 4/8 |
| Ligue 1 | 229 · +0.6 [-4.1; +5.6] · -10.7 [-37.4; +18.4] | 141 · -1.0 [-6.6; +5.1] · -8.3 [-43.7; +32.4] | 222 · -1.8 [-6.2; +2.7] · -21.9 [-42.7; +0.7] | 363 · -1.5 [-5.0; +2.2] · -16.6 [-36.5; +4.5] | -0.75 | 2/8 |
| Tutti i campionati | 1643 · +1.3 [-0.5; +3.2] · -2.3 [-13.5; +9.4] | 941 · -0.1 [-2.2; +2.1] · -6.8 [-19.9; +7.2] | 1206 · -2.4 [-4.4; -0.3] · -22.3 [-33.1; -11.0] | 2147 · -1.4 [-2.8; +0.2] · -15.5 [-24.1; -6.8] | -1.68 | 4/8 |

**A — favorita in trasferta (V5): p_ospite ≥ 40 % → vittoria dell'ospite**

| Lega | pre-2019 (indipendente) | validazione | held-out | scoperta | z (scoperta) | stagioni con eccesso > 0 |
|---|---|---|---|---|---|---|
| Serie A | 603 · +3.0 [-0.7; +6.5] · +2.4 [-4.4; +9.3] | 367 · +6.2 [+1.4; +10.9] · +8.5 [-0.2; +17.4] | 463 · +6.0 [+1.6; +10.6] · +7.5 [-1.1; +16.2] | 830 · +6.1 [+2.8; +9.4] · +8.0 [+1.8; +14.1] | 3.60 | 8/8 |
| Premier | 591 · +2.7 [-1.1; +6.4] · +1.5 [-5.0; +8.4] | 357 · +0.7 [-4.0; +5.3] · -1.1 [-10.4; +7.6] | 487 · -1.8 [-6.6; +2.8] · -6.6 [-15.8; +2.1] | 844 · -0.7 [-4.1; +2.5] · -4.3 [-10.8; +2.1] | -0.43 | 4/8 |
| Bundesliga | 423 · -4.3 [-8.5; -0.2] · -11.5 [-19.2; -3.5] | 281 · -3.0 [-8.5; +2.7] · -8.2 [-18.5; +2.0] | 353 · +2.3 [-2.6; +7.3] · +2.8 [-6.9; +12.4] | 634 · -0.0 [-3.7; +3.7] · -2.1 [-9.3; +4.9] | -0.01 | 4/8 |
| La Liga | 508 · -1.5 [-6.1; +3.1] · -5.1 [-13.4; +3.2] | 274 · -0.4 [-6.0; +5.2] · -3.6 [-14.4; +7.4] | 352 · +3.9 [-1.1; +8.8] · +5.6 [-4.2; +14.8] | 626 · +2.0 [-1.7; +5.5] · +1.6 [-5.6; +8.5] | 1.04 | 5/8 |
| Ligue 1 | 410 · +3.8 [-0.6; +8.4] · +4.5 [-4.2; +13.7] | 246 · +1.7 [-3.9; +7.5] · +0.2 [-11.3; +11.3] | 386 · +0.4 [-4.2; +5.1] · -2.5 [-11.4; +6.2] | 632 · +0.9 [-2.8; +4.6] · -1.5 [-8.6; +5.8] | 0.47 | 4/8 |
| Tutti i campionati | 2535 · +0.9 [-0.8; +2.7] · -1.3 [-4.6; +2.1] | 1525 · +1.3 [-0.9; +3.6] · -0.3 [-4.8; +4.1] | 2041 · +2.1 [-0.0; +4.1] · +1.1 [-2.9; +5.2] | 3566 · +1.8 [+0.2; +3.3] · +0.5 [-2.5; +3.4] | 2.17 | 7/8 |
