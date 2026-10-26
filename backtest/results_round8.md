# Round 8 — dispersione dei tiri per lega, stato di gara nei corner, effetto arbitro sui gialli (solo backtest)

**La produzione non è stata toccata.** Criteri nel prereg qui sotto (scritto prima di eseguire le analisi). Rilancio: `python -I -X utf8 backtest/run_round8.py` (M1, M2, M3 separabili: `... M3`).

---


**Nulla della produzione viene toccato.** Criteri scritti PRIMA di eseguire qualsiasi analisi del round. Stesse regole dei round precedenti: validazione 2019/20-2021/22, held-out dal 2022/23 (compreso il 2026/27 in corso), IC a blocchi per settimana ISO (5000 ricampionamenti per i Δ, 3000 per le medie), Δ = baseline − variante (positivo = la variante migliora), verdetto «migliora» se Δ held-out > 0 con IC a blocchi che esclude lo zero e Δ secondario (per squadra) ≥ 0 nell'held-out; «peggiora» se Δ held-out < 0 con IC sotto zero; altrimenti «non distinguibile dal rumore».

## Dati e baseline
- Contesto dati ricostruito all'esecuzione (football-data.co.uk fino al giorno disponibile; feature di produzione come nel round 7).
- **Baseline = la produzione attuale (s5-livello)**: modelli delle statistiche `stats_v3` (variante with_xg, un fit per stagione dal 2019/20 con training dal 2016/17), medie corrette dal livello stagionale di `config.LEVEL_PARAMS` calcolato col codice di produzione (`stats_v3.build_level` + `predictions.levels.Levels`, come in `run_round7_prod.py`), dispersioni come in produzione (alpha del totale; alpha per squadra stimato a momenti sul training del fold, separato casa/ospite per i tiri).
- Copertura degli intervalli = frequenza reale con cui il valore cade dentro l'intervallo meno la probabilità media dichiarata dall'intervallo (`stats_v3.nb_interval`), come in `results_intervals.md`. Criterio di accettabilità dell'intervallo: scarto ≤ 3 punti.

## M1 — dispersione dei tiri per lega
**Diagnosi.** Copertura degli intervalli per squadra (casa, ospite, casa+ospite) e del totale dei tiri, per lega, su tutto il backtest (2019/20-2026/27), sulle sole validazioni, sull'held-out e sul solo 2026/27; in più per stagione × lega. Si riportano le coperture reali e dichiarate e il numero di partite. Si segnala come «fuori» ogni cella con |scarto| > 3 punti e con almeno 150 partite (sotto, descrittiva).

**Variante M1.** Alpha per lega e per lato (casa, ospite), stimati a momenti sul training di ogni fold, SOLO per la distribuzione per squadra (intervalli per squadra, log-loss per squadra, Over/Under per squadra); l'alpha del totale resta quello attuale (nessun cambiamento del totale). Un'unica variante, nessuna griglia: se in una lega il training del fold ha meno di 500 partite si usa l'alpha globale del fold.
Metriche: log-loss per squadra, log-loss Over/Under per squadra (linee 10,5/12,5/14,5), copertura per lega (come sopra). Verdetto con le regole sopra; in più si dichiara l'esito sulla copertura: «risolve» se dopo la variante nessuna lega ha |scarto per squadra| > 3 punti su tutto il backtest.
Se la copertura per squadra in una lega resta sotto il nominale per un errore di LIVELLO della media (scarto della media prevista contro la reale di quella lega nel 2026/27) e non di dispersione, lo si scrive: l'alpha non può correggerlo (si riporta il rapporto reale/previsto delle medie per lega e lato nel 2026/27).

## M2 — corner e stato di gara
**Feature (tutte PRE-partita, dal modello 1X2 e dal modello dei tiri di produzione, fuori campione per stagione; in campione per il 2016/17-2018/19 come per le altre feature):**
1. `trail_h`, `trail_a`: frazione attesa della partita in cui la squadra di casa / ospite sta perdendo, dai gol attesi μ, ν del modello 1X2 v6 (stack with_xg + Elo-Odds): ∫₀¹ P(D_t < 0) dt per la casa e ∫₀¹ P(D_t > 0) dt per l'ospite, con D_t = differenza di due Poisson indipendenti di medie μt e νt, integrale numerico su 20 punti. (Dalla matrice dei punteggi si ottiene la sola probabilità a fine partita; la frazione di tempo in svantaggio è la grandezza che tocca il comportamento in campo, e usa lo stesso μ, ν.)
2. `shots_share`: log(media attesa dei tiri della casa / media attesa dei tiri dell'ospite) dal modello dei tiri (previsione fuori campione, prima del livello).
**Varianti** (si aggiungono come regressori alle due regressioni di Poisson dei corner, tutto il resto invariato): (a) solo `trail_h`, `trail_a`; (b) solo `shots_share`; (c) entrambe. Scelta sulle validazioni (Δ log-loss del totale; parità entro 0,0002 → la più semplice: (b), poi (a), poi (c)); verdetto sul held-out. Metriche: log-loss del totale e per squadra, Over/Under del totale, copertura degli intervalli per squadra e totale (tutte le stagioni e 2026/27); il livello stagionale dei corner (L3) viene riapplicato sopra la variante come in produzione.
**Esito richiesto.** Se la variante scelta non migliora il totale (verdetto diverso da «migliora») lo si scrive esplicitamente, perché in quel caso si propone di mostrare i corner con meno enfasi nel pannello.

## M3 — gialli: l'effetto arbitro nel 2026/27
1. **Calibrazione dell'effetto.** Coefficiente β di log R (regressore dell'arbitro, `ref_logR`) in una regressione di Poisson sui gialli totali con offset log(media attesa SENZA arbitro): β = 1 vuol dire effetto ben calibrato, β = 0 nessun effetto. β con IC a blocchi per le stagioni 2019/20-2025/26 insieme e per il 2026/27, e per i sottoinsiemi del 2026/27 qui sotto.
2. **Guadagno.** Δ log-loss del totale dei gialli (e per squadra) del modello con l'effetto arbitro contro lo stesso modello senza (regressore azzerato), sul 2026/27 e sui sottoinsiemi.
3. **Sottoinsiemi del 2026/27:** (A) partite tracciate in `docs/history.csv` con arbitro già noto prima del calcio d'inizio (`referee_first_seen` < `kickoff`); (B) partite tracciate con arbitro NON noto prima del calcio d'inizio; (C) partite non tracciate (prima del 9/10, l'arbitro è quello effettivo da `data/referees/matches.csv`). Nel backtest l'arbitro è sempre quello effettivo della partita: A e B servono a dire se l'effetto regge anche nelle partite dove, in produzione, l'arbitro era davvero noto in anticipo.
4. **Produzione.** Sulle righe di `history.csv` con `yellow_pred` e `yellow_real` (previsioni emesse prima del calcio d'inizio): errore medio assoluto e scarto medio (reale − previsto) dei gialli totali, per arbitro noto prima / non noto prima; solo descrittivo.
Il verdetto sull'effetto arbitro nel 2026/27: «regge» se β del 2026/27 ha un IC a blocchi che include β delle stagioni precedenti e che esclude lo zero; «non regge» se l'IC include lo zero; «indeterminato» se l'IC è troppo largo per escludere sia 0 sia il valore storico (larghezza > 1).


## M1 — dispersione dei tiri per lega

Baseline = produzione (livello stagionale + alpha casa/ospite globali del fold). Celle: probabilità dichiarata → frequenza reale (scarto in punti), numero di partite; **grassetto** = |scarto| > 3 punti con almeno 150 partite.

### Copertura degli intervalli dei tiri — Baseline (alpha globali)

| Lega | Insieme | Casa | Ospite | Squadra (casa+ospite) | Totale |
|---|---|---|---|---|---|
| Serie A | tutte | 80→78 (-2.1) <sub>2728</sub> | 80→79 (-0.7) <sub>2728</sub> | 80→79 (-1.4) <sub>5456</sub> | 80→79 (-1.4) <sub>2728</sub> |
| Serie A | validazione | 80→79 (-1.2) <sub>1140</sub> | 80→80 (-0.5) <sub>1140</sub> | 80→79 (-0.8) <sub>2280</sub> | 80→77 (-3.2) ** <sub>1140</sub> |
| Serie A | held-out | 80→77 (-2.8) <sub>1588</sub> | 80→79 (-0.9) <sub>1588</sub> | 80→78 (-1.9) <sub>3176</sub> | 80→80 (-0.0) <sub>1588</sub> |
| Serie A | 2026/27 | 80→74 (-6.4) <sub>68</sub> | 80→63 (-16.8) <sub>68</sub> | 80→68 (-11.6) <sub>136</sub> | 80→71 (-9.5) <sub>68</sub> |
| Premier League | tutte | 80→78 (-1.8) <sub>2729</sub> | 80→78 (-2.1) <sub>2729</sub> | 80→78 (-2.0) <sub>5458</sub> | 80→79 (-1.1) <sub>2729</sub> |
| Premier League | validazione | 80→78 (-1.8) <sub>1140</sub> | 80→77 (-3.1) ** <sub>1140</sub> | 80→78 (-2.4) <sub>2280</sub> | 80→80 (+0.0) <sub>1140</sub> |
| Premier League | held-out | 80→78 (-1.8) <sub>1589</sub> | 80→79 (-1.5) <sub>1589</sub> | 80→78 (-1.6) <sub>3178</sub> | 80→78 (-1.9) <sub>1589</sub> |
| Premier League | 2026/27 | 80→87 (+6.8) <sub>69</sub> | 80→72 (-7.7) <sub>69</sub> | 80→80 (-0.4) <sub>138</sub> | 80→77 (-3.2) <sub>69</sub> |
| Bundesliga | tutte | 80→80 (+0.3) <sub>2195</sub> | 80→78 (-2.1) <sub>2195</sub> | 80→79 (-0.9) <sub>4390</sub> | 80→79 (-1.0) <sub>2195</sub> |
| Bundesliga | validazione | 80→82 (+1.7) <sub>918</sub> | 80→78 (-1.6) <sub>918</sub> | 80→80 (+0.1) <sub>1836</sub> | 80→79 (-1.4) <sub>918</sub> |
| Bundesliga | held-out | 80→79 (-0.7) <sub>1277</sub> | 80→78 (-2.4) <sub>1277</sub> | 80→79 (-1.6) <sub>2554</sub> | 80→79 (-0.6) <sub>1277</sub> |
| Bundesliga | 2026/27 | 80→80 (-0.2) <sub>54</sub> | 80→70 (-9.6) <sub>54</sub> | 80→75 (-4.9) <sub>108</sub> | 80→69 (-11.7) <sub>54</sub> |
| La Liga | tutte | 80→79 (-1.3) <sub>2747</sub> | 80→78 (-2.1) <sub>2747</sub> | 80→78 (-1.7) <sub>5494</sub> | 80→80 (-0.5) <sub>2747</sub> |
| La Liga | validazione | 80→79 (-1.5) <sub>1140</sub> | 80→79 (-1.0) <sub>1140</sub> | 80→79 (-1.2) <sub>2280</sub> | 80→80 (+0.4) <sub>1140</sub> |
| La Liga | held-out | 80→79 (-1.2) <sub>1607</sub> | 80→77 (-2.9) <sub>1607</sub> | 80→78 (-2.1) <sub>3214</sub> | 80→79 (-1.1) <sub>1607</sub> |
| La Liga | 2026/27 | 80→76 (-4.1) <sub>87</sub> | 80→71 (-8.7) <sub>87</sub> | 80→74 (-6.4) ** <sub>174</sub> | 80→72 (-7.7) <sub>87</sub> |
| Ligue 1 | tutte | 80→78 (-2.2) <sub>2400</sub> | 80→78 (-2.0) <sub>2400</sub> | 80→78 (-2.1) <sub>4800</sub> | 80→79 (-1.0) <sub>2400</sub> |
| Ligue 1 | validazione | 80→77 (-3.3) ** <sub>1039</sub> | 80→78 (-2.4) <sub>1039</sub> | 80→77 (-2.9) <sub>2078</sub> | 80→79 (-1.3) <sub>1039</sub> |
| Ligue 1 | held-out | 80→79 (-1.3) <sub>1361</sub> | 80→78 (-1.7) <sub>1361</sub> | 80→79 (-1.5) <sub>2722</sub> | 80→79 (-0.7) <sub>1361</sub> |
| Ligue 1 | 2026/27 | 80→81 (+0.8) <sub>63</sub> | 80→75 (-5.3) <sub>63</sub> | 80→78 (-2.3) <sub>126</sub> | 80→76 (-3.8) <sub>63</sub> |
| Tutte | tutte | 80→79 (-1.5) <sub>12799</sub> | 80→78 (-1.8) <sub>12799</sub> | 80→78 (-1.6) <sub>25598</sub> | 80→79 (-1.0) <sub>12799</sub> |
| Tutte | validazione | 80→79 (-1.3) <sub>5377</sub> | 80→78 (-1.7) <sub>5377</sub> | 80→79 (-1.5) <sub>10754</sub> | 80→79 (-1.1) <sub>5377</sub> |
| Tutte | held-out | 80→78 (-1.6) <sub>7422</sub> | 80→78 (-1.9) <sub>7422</sub> | 80→78 (-1.7) <sub>14844</sub> | 80→79 (-0.9) <sub>7422</sub> |
| Tutte | 2026/27 | 80→79 (-0.8) <sub>341</sub> | 80→70 (-9.7) ** <sub>341</sub> | 80→75 (-5.2) ** <sub>682</sub> | 80→73 (-7.1) ** <sub>341</sub> |

### Copertura degli intervalli dei tiri — Variante M1 (alpha per lega e lato, solo per squadra)

| Lega | Insieme | Casa | Ospite | Squadra (casa+ospite) | Totale |
|---|---|---|---|---|---|
| Serie A | tutte | 80→78 (-2.0) <sub>2728</sub> | 80→79 (-1.1) <sub>2728</sub> | 80→79 (-1.6) <sub>5456</sub> | 80→79 (-1.4) <sub>2728</sub> |
| Serie A | validazione | 80→79 (-1.3) <sub>1140</sub> | 80→79 (-1.0) <sub>1140</sub> | 80→79 (-1.2) <sub>2280</sub> | 80→77 (-3.2) ** <sub>1140</sub> |
| Serie A | held-out | 80→78 (-2.5) <sub>1588</sub> | 80→79 (-1.2) <sub>1588</sub> | 80→78 (-1.9) <sub>3176</sub> | 80→80 (-0.0) <sub>1588</sub> |
| Serie A | 2026/27 | 80→75 (-5.2) <sub>68</sub> | 80→63 (-16.9) <sub>68</sub> | 80→69 (-11.1) <sub>136</sub> | 80→71 (-9.5) <sub>68</sub> |
| Premier League | tutte | 80→79 (-0.9) <sub>2729</sub> | 80→78 (-2.1) <sub>2729</sub> | 80→79 (-1.5) <sub>5458</sub> | 80→79 (-1.1) <sub>2729</sub> |
| Premier League | validazione | 80→79 (-0.7) <sub>1140</sub> | 80→77 (-3.1) ** <sub>1140</sub> | 80→78 (-1.9) <sub>2280</sub> | 80→80 (+0.0) <sub>1140</sub> |
| Premier League | held-out | 80→79 (-1.0) <sub>1589</sub> | 80→79 (-1.4) <sub>1589</sub> | 80→79 (-1.2) <sub>3178</sub> | 80→78 (-1.9) <sub>1589</sub> |
| Premier League | 2026/27 | 80→87 (+6.9) <sub>69</sub> | 80→72 (-7.7) <sub>69</sub> | 80→80 (-0.4) <sub>138</sub> | 80→77 (-3.2) <sub>69</sub> |
| Bundesliga | tutte | 80→79 (-0.8) <sub>2195</sub> | 80→79 (-1.1) <sub>2195</sub> | 80→79 (-0.9) <sub>4390</sub> | 80→79 (-1.0) <sub>2195</sub> |
| Bundesliga | validazione | 80→81 (+0.6) <sub>918</sub> | 80→79 (-0.7) <sub>918</sub> | 80→80 (-0.0) <sub>1836</sub> | 80→79 (-1.4) <sub>918</sub> |
| Bundesliga | held-out | 80→78 (-1.8) <sub>1277</sub> | 80→79 (-1.4) <sub>1277</sub> | 80→78 (-1.6) <sub>2554</sub> | 80→79 (-0.6) <sub>1277</sub> |
| Bundesliga | 2026/27 | 80→80 (-0.5) <sub>54</sub> | 80→70 (-9.6) <sub>54</sub> | 80→75 (-5.1) <sub>108</sub> | 80→69 (-11.7) <sub>54</sub> |
| La Liga | tutte | 80→78 (-2.4) <sub>2747</sub> | 80→77 (-2.6) <sub>2747</sub> | 80→78 (-2.5) <sub>5494</sub> | 80→80 (-0.5) <sub>2747</sub> |
| La Liga | validazione | 80→77 (-3.0) <sub>1140</sub> | 80→78 (-1.7) <sub>1140</sub> | 80→78 (-2.3) <sub>2280</sub> | 80→80 (+0.4) <sub>1140</sub> |
| La Liga | held-out | 80→78 (-2.0) <sub>1607</sub> | 80→77 (-3.3) ** <sub>1607</sub> | 80→77 (-2.6) <sub>3214</sub> | 80→79 (-1.1) <sub>1607</sub> |
| La Liga | 2026/27 | 80→76 (-4.2) <sub>87</sub> | 80→71 (-8.7) <sub>87</sub> | 80→74 (-6.5) ** <sub>174</sub> | 80→72 (-7.7) <sub>87</sub> |
| Ligue 1 | tutte | 80→78 (-1.9) <sub>2400</sub> | 80→79 (-1.6) <sub>2400</sub> | 80→78 (-1.7) <sub>4800</sub> | 80→79 (-1.0) <sub>2400</sub> |
| Ligue 1 | validazione | 80→77 (-3.0) ** <sub>1039</sub> | 80→79 (-1.6) <sub>1039</sub> | 80→78 (-2.3) <sub>2078</sub> | 80→79 (-1.3) <sub>1039</sub> |
| Ligue 1 | held-out | 80→79 (-1.0) <sub>1361</sub> | 80→79 (-1.6) <sub>1361</sub> | 80→79 (-1.3) <sub>2722</sub> | 80→79 (-0.7) <sub>1361</sub> |
| Ligue 1 | 2026/27 | 80→81 (+0.9) <sub>63</sub> | 80→75 (-5.4) <sub>63</sub> | 80→78 (-2.2) <sub>126</sub> | 80→76 (-3.8) <sub>63</sub> |
| Tutte | tutte | 80→78 (-1.6) <sub>12799</sub> | 80→78 (-1.7) <sub>12799</sub> | 80→78 (-1.7) <sub>25598</sub> | 80→79 (-1.0) <sub>12799</sub> |
| Tutte | validazione | 80→78 (-1.5) <sub>5377</sub> | 80→78 (-1.7) <sub>5377</sub> | 80→78 (-1.6) <sub>10754</sub> | 80→79 (-1.1) <sub>5377</sub> |
| Tutte | held-out | 80→78 (-1.7) <sub>7422</sub> | 80→78 (-1.8) <sub>7422</sub> | 80→78 (-1.7) <sub>14844</sub> | 80→79 (-0.9) <sub>7422</sub> |
| Tutte | 2026/27 | 80→79 (-0.6) <sub>341</sub> | 80→70 (-9.7) ** <sub>341</sub> | 80→75 (-5.2) ** <sub>682</sub> | 80→73 (-7.1) ** <sub>341</sub> |

### Baseline: copertura per squadra, per stagione e lega (probabilità dichiarata → reale)

| Stagione | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---|---|---|---|---|
| 2019/20 | 80→82 (+2.1) <sub>760</sub> | 80→79 (-0.8) <sub>760</sub> | 80→80 (-0.2) <sub>612</sub> | 80→79 (-1.1) <sub>760</sub> | 80→79 (-0.7) <sub>558</sub> |
| 2020/21 | 80→80 (-0.4) <sub>760</sub> | 80→76 (-4.4) ** <sub>760</sub> | 80→80 (-0.1) <sub>612</sub> | 80→78 (-2.1) <sub>760</sub> | 80→76 (-4.5) ** <sub>760</sub> |
| 2021/22 | 80→76 (-4.2) ** <sub>760</sub> | 80→78 (-2.1) <sub>760</sub> | 80→81 (+0.5) <sub>612</sub> | 80→80 (-0.5) <sub>760</sub> | 80→77 (-2.8) <sub>760</sub> |
| 2022/23 | 80→79 (-1.1) <sub>760</sub> | 80→79 (-1.5) <sub>760</sub> | 80→79 (-1.1) <sub>612</sub> | 80→80 (-0.3) <sub>760</sub> | 80→80 (-0.5) <sub>760</sub> |
| 2023/24 | 80→80 (-0.3) <sub>760</sub> | 80→77 (-3.5) ** <sub>760</sub> | 80→78 (-2.1) <sub>612</sub> | 80→78 (-2.3) <sub>760</sub> | 80→78 (-2.2) <sub>612</sub> |
| 2024/25 | 80→78 (-2.1) <sub>760</sub> | 80→78 (-1.8) <sub>760</sub> | 80→79 (-0.9) <sub>610</sub> | 80→79 (-1.3) <sub>760</sub> | 80→81 (+0.6) <sub>612</sub> |
| 2025/26 | 80→78 (-2.3) <sub>760</sub> | 80→80 (+0.1) <sub>760</sub> | 80→79 (-1.6) <sub>612</sub> | 80→77 (-3.4) ** <sub>760</sub> | 80→76 (-4.1) ** <sub>612</sub> |
| 2026/27 | 80→68 (-11.6) <sub>136</sub> | 80→80 (-0.4) <sub>138</sub> | 80→75 (-4.9) <sub>108</sub> | 80→74 (-6.4) ** <sub>174</sub> | 80→78 (-2.3) <sub>126</sub> |

### Livello nel 2026/27: rapporto reale / previsto (medie dopo il livello stagionale)

| Lega | Casa prev. → reale | Rapporto casa | Ospite prev. → reale | Rapporto ospite | Totale prev. → reale | Rapporto totale |
|---|---|---|---|---|---|---|
| Serie A | 14.5 → 15.1 | 1.043 [0.977, 1.100] | 11.8 → 14.0 | 1.182 [1.115, 1.257] | 26.3 → 29.1 | 1.106 [1.073, 1.135] |
| Premier League | 14.6 → 14.6 | 1.001 [0.946, 1.048] | 11.9 → 12.9 | 1.082 [1.006, 1.162] | 26.5 → 27.5 | 1.038 [0.996, 1.082] |
| Bundesliga | 15.8 → 16.8 | 1.058 [0.972, 1.152] | 12.9 → 14.4 | 1.117 [1.068, 1.183] | 28.8 → 31.2 | 1.084 [1.040, 1.129] |
| La Liga | 14.1 → 14.7 | 1.042 [0.958, 1.126] | 11.0 → 12.1 | 1.095 [1.006, 1.163] | 25.2 → 26.8 | 1.065 [0.998, 1.117] |
| Ligue 1 | 14.2 → 14.6 | 1.024 [0.930, 1.129] | 12.2 → 12.9 | 1.057 [0.984, 1.131] | 26.5 → 27.5 | 1.039 [0.971, 1.106] |

### Metriche della variante M1 contro la baseline

| Metrica | Baseline | M1 | Δ (base − M1) tutte [IC a blocchi] | Δ held-out [IC a blocchi] | Δ 2026/27 |
|---|---:|---:|---|---|---:|
| Log-loss per squadra | 2.86966 | 2.86989 | -0.00023 [-0.00061, +0.00016] | -0.00041 [-0.00088, +0.00006] | +0.00010 |
| Log-loss Over/Under per squadra | 0.56568 | 0.56572 | -0.00005 [-0.00014, +0.00005] | -0.00006 [-0.00018, +0.00007] | +0.00028 |
| Log-loss del totale (invariata per costruzione) | 3.12686 | 3.12686 | +0.00000 | | |

**Verdetto: non distinguibile dal rumore.** Scarto massimo per lega della copertura per squadra (tutte le stagioni): baseline 2.1 pp, M1 2.5 pp → la baseline era già entro il criterio e la variante non lo cambia (criterio: nessuna lega oltre 3 punti).


## M2 — corner e stato di gara

Feature pre-partita: `trail_h`/`trail_a` = frazione attesa della partita in cui la casa/l'ospite sta perdendo (dai gol attesi del modello 1X2 v6); `shots_share` = log(tiri attesi casa / tiri attesi ospite). Baseline = produzione (modello dei corner attuale + livello stagionale H=16, k=80). Δ = baseline − variante (positivo = la variante migliora); livello ricalcolato sulla variante.

| Variante | Δ ll totale tutte [IC a blocchi] | Δ totale validazione | Δ totale held-out [IC a blocchi] | Δ per squadra held-out | Δ O/U totale held-out | Δ totale 2026/27 | Verdetto |
|---|---|---:|---|---:|---:|---:|---|
| (a) trail_h+trail_a ← scelta | +0.00014 [-0.00014, +0.00041] | +0.00018 | +0.00010 [-0.00022, +0.00044] | +0.00097 | +0.00006 | +0.00103 | non distinguibile dal rumore |
| (b) shots_share | -0.00039 [-0.00070, -0.00006] | -0.00032 | -0.00044 [-0.00082, -0.00005] | +0.00100 | -0.00028 | -0.00263 | peggiora |
| (c) trail_h+trail_a+shots_share | -0.00023 [-0.00066, +0.00019] | -0.00013 | -0.00030 [-0.00083, +0.00021] | +0.00158 | -0.00021 | -0.00132 | non distinguibile dal rumore |

**Variante scelta in validazione: (a). Verdetto: non distinguibile dal rumore.** Log-loss del totale baseline 2.61276, variante 2.61262; per squadra 2.32784 → 2.32695.

**Copertura degli intervalli dei corner (dichiarata → reale, scarto in pp) baseline → variante scelta**

| Insieme | Squadra | Totale |
|---|---|---|
| tutte | 80→79 (-0.7) <sub>25598</sub> → 80→79 (-0.7) <sub>25598</sub> | 80→79 (-0.5) <sub>12799</sub> → 80→79 (-0.4) <sub>12799</sub> |
| validazione | 80→79 (-1.1) <sub>10754</sub> → 80→79 (-1.2) <sub>10754</sub> | 80→79 (-0.7) <sub>5377</sub> → 80→79 (-0.7) <sub>5377</sub> |
| held-out | 80→80 (-0.4) <sub>14844</sub> → 80→80 (-0.4) <sub>14844</sub> | 80→79 (-0.3) <sub>7422</sub> → 80→79 (-0.2) <sub>7422</sub> |
| 2026/27 | 80→79 (-1.3) <sub>682</sub> → 80→78 (-2.0) <sub>682</sub> | 80→74 (-5.6) <sub>341</sub> → 80→74 (-5.6) <sub>341</sub> |

Coefficienti standardizzati dell'ultimo fold (training fino al 2025/26) per le feature aggiunte: trail_h: casa -0.0292, ospite -0.0083; trail_a: casa +0.0704, ospite -0.0992.

**Nessuna variante migliora il totale dei corner in modo distinguibile dal rumore**: come concordato, si propone di mostrare i corner con meno enfasi nel pannello (ad es. sezione chiusa di default, senza handicap e «chi ne fa di più» in primo piano).


## M3 — gialli: l'effetto arbitro nel 2026/27

β = coefficiente di log R (effetto arbitro) in una regressione di Poisson dei gialli totali con offset log(media attesa SENZA arbitro): 1 = effetto ben calibrato, 0 = nessun effetto. Δ = (modello senza arbitro) − (modello con arbitro): positivo = l'arbitro migliora. IC a blocchi per settimana ISO.

| Insieme | Partite | Con arbitro noto (R≠1) | β [IC a blocchi] | Δ ll totale [IC] | Δ ll per squadra [IC] | Gialli previsti (senza arbitro) → reali |
|---|---:|---:|---|---|---|---|
| 2019/20-2025/26 | 12458 | 12348 | 0.88 [0.77, 0.99] | +0.01037 [+0.00790, +0.01287] | +0.00524 [+0.00401, +0.00650] | 4.11 → 4.09 |
| 2026/27 | 341 | 313 | 0.94 [0.49, 1.37] | +0.01309 [+0.00138, +0.02360] | +0.00632 [+0.00026, +0.01157] | 4.02 → 3.71 |
| 2026/27, A (arbitro noto prima) | 10 | 10 | 2.32 (IC non calcolabile: 1 settimane) | +0.05688 (IC non calcolabile: 1 settimane) | +0.02595 (IC non calcolabile: 1 settimane) | 4.11 → 4.10 |
| 2026/27, B (non noto prima) | 81 | 81 | 1.18 (IC non calcolabile: 2 settimane) | +0.01840 (IC non calcolabile: 2 settimane) | +0.00920 (IC non calcolabile: 2 settimane) | 3.92 → 4.00 |
| 2026/27, C (non tracciate, prima del 9/10) | 250 | 222 | 0.78 (IC non calcolabile: 6 settimane) | +0.00962 (IC non calcolabile: 6 settimane) | +0.00460 (IC non calcolabile: 6 settimane) | 4.05 → 3.60 |

**Verdetto sull'effetto arbitro nel 2026/27: regge** (β storico 0.88 [0.77, 0.99]; β 2026/27 0.94 [0.49, 1.37]).

**Produzione (righe di `history.csv`, previsioni emesse prima del calcio d'inizio)**

| Arbitro | Partite | Gialli previsti | Gialli reali | Scarto medio (reale − previsto) | Errore medio assoluto |
|---|---:|---:|---:|---:|---:|
| noto prima del calcio d'inizio | 30 | 3.94 | 3.70 | -0.24 | 1.54 |
| non noto prima | 65 | 3.86 | 4.42 | +0.56 | 1.73 |
| tutte | 95 | 3.88 | 4.19 | +0.31 | 1.67 |


## Appendice — ESPN contro football-data.co.uk


346 partite di campionato nel CSV, 346 abbinate a un evento ESPN (data ±1 giorno, nomi simili), 0 senza abbinamento.

| Campo | Confrontate | Uguali | % uguali |
|---|---:|---:|---:|
| Gol casa | 346 | 346 | 100.0% |
| Gol ospite | 346 | 346 | 100.0% |
| Gol del primo tempo (totale) | 346 | 346 | 100.0% |
| Tiri in porta casa | 346 | 343 | 99.1% |
| Tiri in porta ospite | 346 | 346 | 100.0% |
| Tiri casa | 346 | 337 | 97.4% |
| Tiri ospite | 346 | 340 | 98.3% |
| Corner casa | 346 | 340 | 98.3% |
| Corner ospite | 346 | 341 | 98.6% |
| Falli casa | 346 | 345 | 99.7% |
| Falli ospite | 346 | 340 | 98.3% |
| Gialli casa | 346 | 323 | 93.4% |
| Gialli ospite | 346 | 322 | 93.1% |


## Tabella riassuntiva

| Esperimento | Esito | Numeri chiave |
|---|---|---|
| M1 — alpha dei tiri per lega e lato (solo per squadra) | **non migliora**; la copertura storica era già a posto | scarto della copertura per squadra su tutto il backtest per lega: tra −0,9 e −2,1 punti (baseline) e tra −0,9 e −2,5 (M1); log-loss per squadra Δ held-out −0,00041 [−0,00088, +0,00006] |
| M1 — Serie A nel 2026/27 | **problema di livello, non di dispersione** | copertura per squadra 68% (ospite 63%, 68 partite); rapporto reale/previsto dei tiri dell'ospite 1,18 [1,12, 1,26]; con M1 resta 69% |
| M2 — corner e stato di gara | **nessuna variante migliora il totale** | (a) trail: Δ held-out +0,00010 [−0,00022, +0,00044]; (b) quota di tiri: −0,00044 [−0,00082, −0,00005] (peggiora); (c) entrambe: −0,00030 [−0,00083, +0,00021] |
| M3 — effetto arbitro sui gialli nel 2026/27 | **regge** (campione piccolo) | β 0,94 [0,49, 1,37] contro 0,88 [0,77, 0,99] storico; Δ log-loss del totale +0,0131 [+0,0014, +0,0236] |

## Commento

1. **M1 — gli intervalli dei tiri non hanno un problema di dispersione per lega.** Su 12.799 partite (2019/20-2026/27) la copertura per squadra, dichiarata 80%, è tra il 78% e il 79% in tutte e cinque le leghe, Serie A compresa (79%, −1,4 punti). Le celle stagione × lega che superano i 3 punti (Premier 2020/21 e 2023/24, Ligue 1 2020/21 e 2025/26, Serie A 2021/22, La Liga 2025/26) sono 6 su 35 (2019/20-2025/26), con scarti tra −3,4 e −4,5 punti e circa 760 osservazioni per cella: è l'ordine di grandezza del rumore. L'alpha per lega e lato non cambia nulla (copertura e log-loss per squadra invariate: Δ held-out −0,0004, IC che include lo zero) e **non conviene introdurlo**.
2. **Il 55-65% di copertura per squadra in Serie A è reale ma è un errore di livello dei tiri dell'ospite.** Nel 2026/27 le squadre ospiti della Serie A hanno fatto 14,0 tiri a partita contro 11,8 previsti (+18%, IC [+12%, +26%]); la copertura dell'intervallo per squadra è 68% (ospite 63%, casa 74%, 68 partite per lato), quella del totale 71% (68 partite). Cambiare l'alpha non può correggerlo: con M1 la stessa cella passa da 68% a 69%. Lo stesso segno compare in tutte le leghe (rapporto reale/previsto dei tiri dell'ospite tra 1,06 e 1,18, della casa tra 1,00 e 1,06) e suggerisce un livello dei tiri dell'ospite sistematicamente sottostimato nelle prime 7-8 giornate, che il livello stagionale (H=12, k=80, scelto in validazione) recupera solo in parte perché il suo shrinkage è forte. Con 341 partite non è abbastanza per cambiare la configurazione scelta in validazione; se lo scarto persiste a campione più grande vale la pena un nuovo round sul livello dei tiri **per lato** (casa/ospite con parametri propri).
3. **M2 — lo stato di gara non spiega i corner oltre le forze delle squadre.** La frazione attesa di partita in svantaggio non migliora il totale (Δ held-out +0,0001, IC che include lo zero) e i coefficienti hanno il segno opposto a quello atteso («chi insegue prende più corner»): più tempo in svantaggio atteso per la casa → casa −0,03 (quasi nullo); più tempo in svantaggio atteso per l'ospite → ospite −0,10, perché chi è atteso in svantaggio è la squadra più debole, che di corner ne ottiene meno e che le forze offensive/difensive già descrivono. La quota di tiri prevista peggiora il totale (−0,0004, IC che esclude lo zero). **Come concordato: i corner non migliorano con questa informazione, quindi propongo di mostrarli con meno enfasi.** Suggerimento concreto per il pannello: sezione «Corner» chiusa di default (lo è già), valore atteso e intervallo del totale come ora ma senza evidenziare Over/Under e handicap ±1,5 come mercati principali (restano come probabilità semplici, già senza evidenziazioni), con la nota «i corner sono la statistica meno prevedibile» — da decidere insieme.
4. **M3 — l'effetto arbitro sui gialli regge anche nel 2026/27.** Il coefficiente stimato sul 2026/27 (β = 0,94, 341 partite) è compatibile con quello storico (0,88 su 12.458 partite) ed esclude lo zero, anche se l'IC è largo (0,49-1,37). Il guadagno di log-loss del totale con l'arbitro è +0,0131 [+0,0014, +0,0236], in linea con il +0,0104 storico. La separazione richiesta tra partite con arbitro noto prima e non noto è, per ora, **troppo piccola per concludere**: nel backtest le partite tracciate sono 10 (arbitro noto prima) e 81 (non noto prima), in 1-2 settimane, quindi gli IC a blocchi non sono calcolabili (β puntuale 2,3 e 1,2, nessun valore interpretabile). Sulle 95 righe di produzione già giocate, con previsioni emesse prima del calcio d'inizio, l'errore medio assoluto dei gialli è 1,54 con arbitro noto prima (30 partite) contro 1,73 con arbitro non noto (65): coerente con un piccolo vantaggio, ma senza inferenza possibile. Lo scarto medio (reale − previsto) è +0,31 gialli a partita sulle 95 righe di produzione, mentre nel backtest 2026/27 il modello senza arbitro prevede 4,02 e i gialli reali sono 3,71: due periodi diversi (9-25 ottobre contro 21 agosto-18 ottobre) con scarti di segno opposto, quindi nessun segnale di bias del modello.
5. **Dati.** ESPN coincide con football-data.co.uk su 346 partite 2026/27 (abbinate tutte): gol e primo tempo 100%, tiri in porta 99-100%, falli 98-100%, corner 98%, tiri 97-98%, gialli di una squadra 93% (±1 nel resto). Per questo i gialli ESPN sono marcati provvisori nello storico e sostituiti dal CSV quando arriva.

