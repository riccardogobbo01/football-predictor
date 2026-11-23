# Round 12 — gialli della Serie A 2026/27 e monitoraggio a carta (controlli, solo backtest)

**La produzione non è stata toccata.** Protocollo scritto prima dell'analisi (in fondo). Rilancio: `python -I -X utf8 backtest/run_round12.py`.

---

## Sintesi

| Domanda | Risposta |
|---|---|
| Il livello dei gialli (L3, H = 4, k = 15) si applica alla Serie A? | **Sì**, dal 19/10 (versione s5): R casa ≈ 0,91 e R ospite ≈ 0,86; livello implicito sulle previsioni emesse 0,876 (−12 %), uguale prima e dopo il decadimento dell'arbitro (s5: 0,877; s6: 0,874). Le 8 partite del 16-18/10 erano state emesse prima del livello (previsione 4,03) |
| Il decadimento dell'effetto arbitro riduce il livello di lega? | **No.** Serie A 2026/27: effetto arbitro medio −3,2 % sia con pesi uniformi sia con il decadimento; media dei gialli prevista 3,98 contro 3,95. In generale il decadimento sposta il livello di meno di 1,3 punti per lega |
| Da dove nasce lo scarto? | Dalla **base del modello, da agosto**: gialli previsti 3,95 (con arbitro) contro 3,24 reali sulle 98 partite del CSV, rapporto 0,822 [0,772; 0,877]. Il livello recupera circa metà: 0,924 [0,861; 0,983] |
| Quanto è anomalo? | La Serie A 2026/27 è la **più bassa di 37 lega-stagioni** (2019/20-2026/27) sulle prime 98 partite: −2,8 dev. std senza livello, −3,3 con il livello |
| Correzione L4 (livello lento sotto quello di produzione) | **Non migliora**: tutte le 9 configurazioni peggiorano già in validazione; la migliore (H = 52, k = 40) in held-out −0,00048 [−0,00101; +0,00005] sul totale e −0,00054 [−0,00082; −0,00027] per squadra → «non distinguibile dal rumore». **Nessuna correzione proposta** |
| Monitoraggio a carta n = 0 | Nessun errore di filtro: il CSV stagionale di football-data.co.uk è fermo all'8/11 (ultimo aggiornamento il 9/11) |

## Commento

**1. Il livello c'è e funziona come progettato; la correzione è parziale per costruzione.** Per i gialli della Serie A il moltiplicatore passa da 0,99/0,82 (casa/ospite) il 16/10 a 0,91/0,86 il 16/11. Il rapporto reale/atteso pesato senza prior è 0,82-0,85, mentre R vale circa 0,875: la differenza è lo *shrinkage* verso 1 (k = 15 pseudo-partite contro 45-55 partite equivalenti pesate: il prior pesa il 22-34 %) più il ritardo d'inizio stagione (in agosto il livello era ancora vicino a 1: correzione −7 % contro un rapporto reale/base di 0,80). Il decadimento a 4 settimane e le pause per le nazionali tengono basso il numero di partite equivalenti.

**2. Il decadimento dell'effetto arbitro non è la causa.** Nella Serie A 2026/27 l'effetto arbitro medio vale −3,2 % con pesi uniformi e −3,2 % con il decadimento; la media prevista cambia di 0,03 gialli (3,98 → 3,95), cioè il decadimento abbassa leggermente la base, non la alza. Il livello non viene quindi «mangiato» dal decadimento.

**3. Lo scarto non è del 16/10: è dell'intera stagione, ed è eccezionale.** Il modello di base sovrastima i gialli della Serie A dal primo mese (agosto 3,92 contro 3,15; settembre 4,02 contro 3,37; ottobre 3,91 contro 3,09). Sulle prime 98 partite il rapporto reale/previsto della Serie A 2026/27 (0,822 senza livello) è il più basso di tutte le 37 combinazioni lega-stagione dal 2019/20; le altre stanno a 1,06 ± 0,09. Un cambiamento di questa taglia non si era mai visto nei dati di allenamento, per questo il livello (scelto su 2019/20-2021/22) lo insegue con prudenza. **Cautela statistica:** il solo periodo dal 16/10 (51 partite con base salvata, 59 con quelle emesse prima del livello) ha uno scarto di −0,35 gialli con errore standard ≈ 0,31 (−1,1 errori standard); è l'intera stagione a essere significativa, non le ultime settimane. Nelle 59 partite citate, 8 sono state emesse con la versione s4 (previsione 4,03): senza di esse la media prevista è 3,39 contro 3,04 reali.

**4. Nessuna correzione proposta.** Il livello lento sotto quello di produzione peggiora in validazione in tutte e 9 le configurazioni (da −0,0008 a −0,0028), quindi la scelta cade sulla meno dannosa (memoria di 52 settimane, k = 40); in held-out il totale è −0,0005 con IC che comprende lo zero, la log-loss per squadra −0,0005 con IC che esclude zero (peggio). Per la sola Serie A 2026/27 L4 avrebbe prodotto 3,40 contro 3,24 reali (Δ +0,0064), ma sulle altre leghe del 2026/27 il segno è misto (Ligue 1 −0,0020, La Liga −0,0015, Premier +0,0017): un caso isolato non è una ragione per cambiare il modello. Il round 10 aveva già escluso un livello di stagione bayesiano sopra quello di produzione per i gialli. Se lo scarto della Serie A continuerà, il livello continuerà ad adattarsi da solo (R scende ancora, lentamente); un intervento specifico per la Serie A andrebbe validato come round a sé e oggi non ha una base nei dati storici.

**5. Cosa vede già l'utente.** Il pannello mostra la riga «Livello stagionale gialli Serie A: −x%» quando il moltiplicatore si discosta più del 5 % da 1: per i gialli della Serie A compare, e spiega che le medie attese includono già una riduzione del 12 %.

**6. Monitoraggio a carta.** Vedi la parte 3: il CSV stagionale non include ancora le partite del 20-22/11; i filtri funzionano (selezionano 2, 3 e 6 partite). Nessun problema nelle quote: `fixtures.csv` le ha per tutte le 190 partite del 20-23/11. Aspetto l'aggiornamento di football-data.co.uk (di norma lunedì-martedì); se vuoi, aggiungo il ripiego con `history.csv` descritto nella parte 3.

---

## Round 12 — gialli della Serie A 2026/27

Contesto dati fino al 2026-11-01 (ultimo ricalcolo del contesto di backtest); le partite successive sono solo nello storico emesso (parte 1.1).

### 1.1 Il livello dei gialli è applicato alla Serie A? (previsioni emesse, partite giocate con base salvata)

bm = media di base (con effetto arbitro) PRIMA del livello; livello implicito = previsione finale / bm.

| Versione del modello | N | dal | al | base prima del livello | previsione finale | reale | livello implicito |
|---|---|---|---|---|---|---|---|
| s5-livello | 32 | 2026-10-19 | 2026-11-02 | 3.92 | 3.44 | 3.06 | 0.877 |
| s6-arbitro-decay | 19 | 2026-11-06 | 2026-11-22 | 3.78 | 3.31 | 3.00 | 0.874 |
| tutte | 51 | 2026-10-19 | 2026-11-22 | 3.87 | 3.39 | 3.04 | 0.876 |

| Lega | N | base prima del livello | previsione finale | reale | livello implicito |
|---|---|---|---|---|---|
| Serie A (dal 16/10) | 51 | 3.87 | 3.39 | 3.04 | 0.876 |
| bundesliga (dal 16/10) | 36 | 3.62 | 3.66 | 4.03 | 1.013 |
| la_liga (dal 16/10) | 41 | 4.64 | 4.61 | 4.83 | 0.993 |
| ligue_1 (dal 16/10) | 41 | 3.68 | 3.71 | 3.88 | 1.007 |
| premier_league (dal 16/10) | 40 | 3.77 | 4.04 | 4.35 | 1.072 |

Scarto Serie A dal 16/10: previsto 3.39, reale 3.04 su 51 partite = -0.35; errore standard della media reale ≈ 0.31 (varianza della Binomiale Negativa con dispersione 0,12): scarto ≈ -1.1 errori standard.

**Moltiplicatori di produzione della Serie A per i gialli** (registro di `models/stack.json`, aggiornato al 2026-11-08; per le date successive il registro non contiene ancora le partite nuove):

| Data | R casa | R ospite | rapporto reale/atteso pesato (senza prior) | partite equivalenti pesate (n) | peso del prior k/(n+k) |
|---|---|---|---|---|---|
| 2026-10-16 | 0.992 | 0.822 | 0.848 | 29.4 | 34 % |
| 2026-10-19 | 0.967 | 0.830 | 0.847 | 35.0 | 30 % |
| 2026-11-02 | 0.881 | 0.848 | 0.823 | 50.8 | 23 % |
| 2026-11-09 | 0.904 | 0.856 | 0.844 | 54.0 | 22 % |
| 2026-11-16 | 0.908 | 0.862 | 0.844 | 45.4 | 25 % |

### 1.2 L'effetto arbitro a decadimento riduce il livello di lega?

Media di log R (effetto arbitro sui gialli, in %) per lega e stagione, **pesi uniformi / decadimento (emivita 182,5 giorni)**. Se il decadimento abbassasse il livello di lega la seconda cifra sarebbe sistematicamente più bassa.

| Lega | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---|---|---|---|---|---|---|---|
| Serie A | +2.7 / +3.8 | +1.5 / +0.4 | +1.5 / +0.0 | +1.8 / +0.1 | +0.9 / -0.9 | -1.7 / -3.5 | -3.2 / -3.6 | -3.2 / -3.2 |
| Premier League | +0.0 / +0.2 | -0.9 / -2.9 | -1.1 / -1.1 | -0.2 / +1.5 | +3.3 / +5.4 | +5.6 / +4.7 | +4.1 / +0.0 | +3.5 / +0.0 |
| Bundesliga | +0.8 / +1.6 | +2.0 / +2.0 | +1.8 / +0.1 | +2.1 / +1.0 | +3.3 / +3.0 | +2.8 / +1.4 | +3.1 / -0.4 | +1.0 / -2.0 |
| La Liga | -0.8 / +0.1 | -0.7 / -2.1 | -1.5 / -1.1 | +0.0 / +0.4 | +0.3 / -0.2 | -0.9 / -1.8 | -2.6 / -2.5 | -2.4 / -1.6 |
| Ligue 1 | +0.1 / +0.3 | +2.0 / +1.9 | +1.3 / +0.8 | +0.3 / -0.9 | -1.3 / -1.6 | -0.8 / +0.3 | +0.6 / -0.2 | -0.1 / -0.8 |

Differenza media (decadimento − uniforme), punti percentuali per lega: Bundesliga -1.31, Premier League -0.78, Ligue 1 -0.28, Serie A -0.89, La Liga -0.01. Nella Serie A 2026/27 l'effetto arbitro medio è -3.2 % con pesi uniformi e -3.2 % con il decadimento: **il decadimento non cambia il livello di lega**.

### 1.3 Dove nasce lo scarto della Serie A (gialli totali per partita, 2026/27)

| Mese | N | reale | modello senza arbitro | con arbitro (pesi uniformi) | con arbitro a decadimento | decadimento + livello di produzione |
|---|---|---|---|---|---|---|
| 2026-08 | 20 | 3.15 | 4.06 | 3.92 | 3.92 | 3.66 |
| 2026-09 | 30 | 3.37 | 4.16 | 4.07 | 4.02 | 3.52 |
| 2026-10 | 43 | 3.09 | 4.04 | 3.96 | 3.91 | 3.46 |
| 2026-11 | 5 | 4.20 | 4.06 | 3.91 | 3.92 | 3.31 |
| 2026/27 | 98 | 3.24 | 4.08 | 3.98 | 3.95 | 3.51 |

Rapporto reale/previsto della Serie A 2026/27 (Σ reali / Σ previsti, IC a blocchi per settimana): base (con arbitro a decadimento): 0.822 [0.772; 0.877]; dopo il livello di produzione: 0.924 [0.861; 0.983].

### 1.4 Quanto è insolito lo scarto della Serie A 2026/27

Rapporto reale/previsto sulle prime 98 partite di ciascuna lega-stagione 2019/20-2026/27 (stesso numero di partite della Serie A 2026/27), prima e dopo il livello di produzione:

|  | media delle altre lega-stagioni | dev. std | minimo | massimo | Serie A 2026/27 | scarto in dev. std | posizione su 37 (1 = la più bassa) |
|---|---|---|---|---|---|---|---|
| senza livello (base) | 1.062 | 0.086 | 0.929 | 1.278 | 0.822 | -2.8 | 1 |
| con il livello di produzione | 1.040 | 0.035 | 0.973 | 1.126 | 0.924 | -3.3 | 1 |

### 2. Correzione L4 (livello lento sotto quello di produzione)

Baseline = produzione (effetto arbitro a decadimento + livello H = 4, k = 15). Δ log-loss del totale = baseline − variante (positivo = migliora). Scelta sulla sola validazione 2019/20-2021/22.

| H lenta (settimane) | k lento | Δ validazione | Δ held-out (solo informativo) |
|---|---|---|---|
| 12 | 5 | -0.00283 | -0.00269 |
| 12 | 15 | -0.00249 | -0.00236 |
| 12 | 40 | -0.00190 | -0.00179 |
| 26 | 5 | -0.00150 | -0.00120 |
| 26 | 15 | -0.00142 | -0.00114 |
| 26 | 40 | -0.00125 | -0.00099 |
| 52 | 5 | -0.00083 | -0.00053 |
| 52 | 15 | -0.00081 | -0.00051 |
| 52 | 40 | -0.00076 | -0.00048 |

**Scelta in validazione: H lenta = 52, k lento = 40.** Δ validazione -0.00076 [-0.00150; -0.00009]; **Δ held-out 2022/23-2025/26: totale -0.00048 [-0.00101; +0.00005], per squadra -0.00054 [-0.00082; -0.00027] → non distinguibile dal rumore.**

Δ del totale per stagione di held-out:

| Stagione | N | Δ |
|---|---|---|
| 2022/23 | 1826 | -0.00045 |
| 2023/24 | 1752 | -0.00082 |
| 2024/25 | 1751 | -0.00007 |
| 2025/26 | 1752 | -0.00057 |

Δ del totale per lega (held-out):

| Lega | N | Δ |
|---|---|---|
| Serie A | 1520 | +0.00014 |
| Premier League | 1520 | -0.00065 |
| Bundesliga | 1223 | -0.00084 |
| La Liga | 1520 | -0.00031 |
| Ligue 1 | 1298 | -0.00086 |

**2026/27 (descrittivo, mai usato per scegliere):**

| Lega | N | reale | previsto produzione | previsto L4 | Δ log-loss (produzione − L4) |
|---|---|---|---|---|---|
| Serie A | 98 | 3.24 | 3.51 | 3.40 | +0.00639 |
| Premier League | 89 | 4.06 | 3.82 | 3.86 | +0.00171 |
| Bundesliga | 72 | 3.65 | 3.51 | 3.51 | -0.00084 |
| La Liga | 108 | 4.36 | 4.41 | 4.35 | -0.00145 |
| Ligue 1 | 80 | 3.51 | 3.44 | 3.43 | -0.00201 |
| Tutte | 447 | 3.79 | 3.78 | 3.74 | +0.00090 |

---

## Parte 3 — monitoraggio a carta: perché n = 0

**Non c'è un errore nel filtro: mancano i dati nel CSV stagionale di football-data.co.uk.**

| Controllo | Risultato |
|---|---|
| Ultima partita nei CSV stagionali 2026/27 (5 campionati) | **8 novembre 2026** |
| Ultimo aggiornamento dei file (`Last-Modified`) | lunedì 9 novembre, 10:03 GMT; nessun aggiornamento da allora (controllo del 23 novembre, mattina) |
| Partite giocate tra l'11 e il 19 novembre | nessuna (pausa per le nazionali): per questo n = 0 dall'11/11 al 19/11 è corretto |
| Partite del 20-22 novembre nel CSV stagionale | **assenti** (il file si ferma al 9/11) |
| `fixtures.csv` (aggiornato venerdì 20/11) | contiene le 190 partite 20-23/11, tutte con quote medie `AvgH/AvgD/AvgA` |
| Storico emesso (`docs/history.csv`) | 45 partite giocate 20-22/11 con risultato provvisorio ESPN e probabilità di mercato dalle `fixtures`; tutte abbinabili alle quote di `fixtures.csv` |

Il monitoraggio a carta usa il CSV stagionale (come il backtest): finché football-data.co.uk non lo aggiorna non vede le partite giocate. Di norma lo aggiorna il lunedì o il martedì dopo il turno (il 9/11 è stato aggiornato il lunedì alle 10:03 GMT, dopo il turno del 7-8/11); il job delle 04:17 UTC di stamattina gira prima di quell'orario.

**Verifica dei filtri sulle partite già giocate** (risultato ESPN provvisorio + quote medie di `fixtures.csv`, senza passare dal CSV; solo per controllare la selezione, numeri troppo piccoli per qualunque conclusione):

| Regola | Partite selezionate | Vinte | Probabilità implicita media | ROI teorico a quota media |
|---|---|---|---|---|
| (a) Serie A, ospite ≥ 45 % | 2 (Parma-Roma, Atalanta-Inter) | 1 (Roma) | 68,6 % | −36,0 % |
| (b) La Liga, favorita in casa ≥ 60 % | 3 (Athletic-Espanyol, Real Madrid-Celta, Barça-Villarreal) | 2 | 77,3 % | −21,3 % |
| (c) Pareggio tra squadre equilibrate | 6 | 2 | 26,1 % | +12,8 % |

I filtri selezionano le partite attese: appena il CSV si aggiorna il monitoraggio mostrerà n = 2, 3 e 6 (più i recuperi del 23/11), con quote medie pre-partita di football-data.co.uk e IC dalle 30 partite in poi.

**Possibile miglioria (non implementata, da decidere):** oggi la sezione si riempie solo quando il CSV è aggiornato, cioè con 1-3 giorni di ritardo e, dopo una pausa, anche di più. `history.csv` ha già i risultati (ESPN provvisori) e la probabilità di mercato senza margine, ma non salva le quote medie: bisognerebbe aggiungere tre colonne (`AvgH/AvgD/AvgA` da `fixtures.csv`, all'emissione) e usarle come ripiego quando il CSV non ha ancora la partita. Il rendimento a quota media si calcolerebbe così fin dal giorno dopo la partita.

---

# Protocollo (prereg)

# Round 12 — gialli della Serie A 2026/27 e monitoraggio a carta (controlli)

**La produzione non viene toccata.** Criteri scritti PRIMA di eseguire l'analisi. Stesse regole di sempre: scelte solo sulla validazione 2019/20-2021/22, held-out 2022/23-2025/26 (il 2026/27 in corso a parte, descrittivo e mai usato per scegliere), IC a blocchi per settimana ISO, Δ = baseline − variante (positivo = la variante migliora), verdetto «migliora» se Δ del totale in held-out > 0 con IC a blocchi che esclude lo zero e Δ per squadra ≥ 0; «peggiora» se < 0 con IC sotto zero; altrimenti «non distinguibile dal rumore».

## Parte 1 — il livello dei gialli (L3, H = 4, k = 15) si applica alla Serie A? E il decadimento dell'effetto arbitro?
Diagnosi, nessuna scelta:
1. **Il livello è applicato?** Dallo storico emesso (`docs/history.csv`): rapporto tra gialli previsti finali e medie di base prima del livello (`bm_gialli`), per versione e mese; moltiplicatori di produzione (`predictions.levels.Levels` con il registro di `models/stack.json`) per data, casa e ospite.
2. **Il decadimento riduce il livello di lega?** Per ciascuna lega e stagione dal 2019/20: media del log dell'effetto arbitro dei gialli (`ref_logR`) con pesi uniformi e con il decadimento di produzione (emivita 182,5 giorni). Se il decadimento abbassasse il livello di lega la media (e la media prevista) calerebbe rispetto ai pesi uniformi in modo sistematico.
3. **Dove nasce lo scarto della Serie A?** Medie dei gialli del 2026/27 per mese: reale contro modello senza arbitro, con arbitro uniforme, con arbitro a decadimento e con il livello di produzione; rapporto reale/previsto con IC a blocchi.
4. **Quanto è significativo?** Rapporto reale/previsto della Serie A, con IC, contro la distribuzione dei rapporti reale/previsto di tutte le altre combinazioni lega-stagione dopo il livello di produzione a parità di numero di partite giocate (primi ~100 incontri).

## Parte 2 — correzione candidata (una sola famiglia, fissata ora)
**L4 = livello a due scale di tempo.** Se la diagnosi mostra uno spostamento persistente di tutta la stagione che il livello di produzione corregge solo in parte (shrinkage k = 15 e decadimento a 4 settimane dimezzano il peso dei dati), si prova ad aggiungere sotto di esso un livello lento: R_lento con emivita H_L ∈ {12, 26, 52} settimane e k_L ∈ {5, 15, 40} (stessa formula, per lega e per lato, sulle medie di base), poi il livello di produzione (H = 4, k = 15) calcolato sulle medie già corrette dal livello lento (con il moltiplicatore lento che valeva alla data di ciascuna partita passata). Previsione finale = media di base × R_lento × R_veloce.
- **Baseline**: produzione attuale (effetto arbitro a decadimento, livello H = 4, k = 15). **Scelta** di (H_L, k_L) sulla sola validazione: massimo Δ della log-loss del totale; parità entro 0,0002 → la più semplice (k più alto, poi H più alto).
- **Metriche**: log-loss del totale (primaria) e per squadra, e per la Serie A 2026/27 media prevista contro reale. (La copertura degli intervalli del prereg iniziale non viene riportata: gli intervalli del backtest di questo round sono a quantili e non quelli a massima probabilità usati in produzione, quindi non confrontabili con il criterio dei 3 punti.)
- Il round 10 aveva già provato un livello di stagione bayesiano sopra quello di produzione per i gialli (B1/B2): non migliorava. L4 è diverso (memoria oltre la stagione, applicato prima del livello veloce) e si prova una sola volta.
- **Nessuna correzione va in produzione se non migliora l'held-out.** Se non migliora si riporta solo la diagnosi.

## Parte 3 — monitoraggio a carta: n = 0
Controllo, nessuna scelta: ultima partita presente nei CSV stagionali di football-data.co.uk e data di aggiornamento dei file; partite dal 21/11 in `fixtures.csv` (quote medie disponibili) e nello storico emesso (risultati ESPN provvisori); applicazione dei filtri (a), (b), (c) ai dati disponibili per verificare che non ci siano errori di selezione; conteggio atteso a CSV aggiornato.
