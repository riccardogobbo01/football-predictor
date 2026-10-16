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
