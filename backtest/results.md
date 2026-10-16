# Backtest walk-forward — Step 1-3, 7.1 (xG Understat) ed Elo-Odds (produzione)

Test: 2019-08-09 → 2026-10-11 (stagioni 2019/20 → 2026/27), 12751 partite con quote medie valide. DC rifittato ogni 7 giorni (finestra 5 anni, xi=0.0018); xG: DC senza tau su xG Understat, xi=0.003, finestra 5 anni (nelle righe "ridge" con penalità ridge=2 sul solo DC degli xG; il DC dei gol non usa ridge). Lo stack è stimato stagione per stagione sulle sole stagioni precedenti, 5 campionati insieme. Più basso = meglio (tranne accuratezza).

Copertura xG: 21883/21886 partite dal 2014/15 abbinate a Understat (99.99%).

## Confronto tra modelli

| Campionato | Modello | N | Log-loss | RPS | Brier | Accuratezza |
|---|---|---:|---:|---:|---:|---:|
| Tutti | Quote medie senza margine (power) | 12751 | 0.9725 | 0.1962 | 0.5781 | 53.6% |
| Tutti | Quote chiusura senza margine (power) | 12751 | 0.9701 | 0.1955 | 0.5766 | 53.9% |
| Tutti | Dixon-Coles attuale (xi=0.0018) | 12751 | 0.9950 | 0.2025 | 0.5919 | 52.4% |
| Tutti | DC ricalibrato (stack su dc_lmu, dc_lnu) * | 12751 | 0.9961 | 0.2030 | 0.5929 | 52.3% |
| Tutti | DC + pi-ratings | 12751 | 0.9901 | 0.2016 | 0.5901 | 52.5% |
| Tutti | Stack senza xG (produzione, training dal 2013/14) | 12751 | 0.9864 | 0.2005 | 0.5876 | 52.7% |
| Tutti | Stack senza xG (training dal 2016/17) * | 12751 | 0.9864 | 0.2005 | 0.5876 | 52.7% |
| Tutti | Stack + xG Understat (training dal 2016/17) | 12751 | 0.9841 | 0.1998 | 0.5861 | 52.8% |
| Tutti | Stack + xG con ridge=2 sul DC xG (training dal 2016/17) | 12751 | 0.9831 | 0.1995 | 0.5855 | 52.8% |
| Tutti | Stack + xG ridge + Elo-Odds K=200 (produzione, training dal 2016/17) | 12751 | 0.9798 | 0.1984 | 0.5831 | 53.0% |
| Tutti | Stack senza xG + Elo-Odds K=200 (ripiego without_xg, training dal 2013/14) | 12751 | 0.9805 | 0.1986 | 0.5835 | 53.0% |
| Serie A | Quote medie senza margine (power) | 2717 | 0.9628 | 0.1908 | 0.5719 | 54.3% |
| Serie A | Quote chiusura senza margine (power) | 2717 | 0.9606 | 0.1903 | 0.5707 | 54.7% |
| Serie A | Dixon-Coles attuale (xi=0.0018) | 2717 | 0.9844 | 0.1969 | 0.5848 | 53.4% |
| Serie A | DC ricalibrato (stack su dc_lmu, dc_lnu) * | 2717 | 0.9879 | 0.1979 | 0.5871 | 53.3% |
| Serie A | DC + pi-ratings | 2717 | 0.9806 | 0.1962 | 0.5838 | 53.4% |
| Serie A | Stack senza xG (produzione, training dal 2013/14) | 2717 | 0.9758 | 0.1947 | 0.5807 | 53.8% |
| Serie A | Stack senza xG (training dal 2016/17) * | 2717 | 0.9755 | 0.1947 | 0.5806 | 53.8% |
| Serie A | Stack + xG Understat (training dal 2016/17) | 2717 | 0.9749 | 0.1944 | 0.5801 | 53.7% |
| Serie A | Stack + xG con ridge=2 sul DC xG (training dal 2016/17) | 2717 | 0.9748 | 0.1944 | 0.5799 | 53.7% |
| Serie A | Stack + xG ridge + Elo-Odds K=200 (produzione, training dal 2016/17) | 2717 | 0.9701 | 0.1930 | 0.5767 | 54.1% |
| Serie A | Stack senza xG + Elo-Odds K=200 (ripiego without_xg, training dal 2013/14) | 2717 | 0.9701 | 0.1930 | 0.5768 | 54.1% |
| Premier League | Quote medie senza margine (power) | 2719 | 0.9697 | 0.1983 | 0.5759 | 54.3% |
| Premier League | Quote chiusura senza margine (power) | 2719 | 0.9659 | 0.1969 | 0.5731 | 54.8% |
| Premier League | Dixon-Coles attuale (xi=0.0018) | 2719 | 0.9896 | 0.2040 | 0.5873 | 52.8% |
| Premier League | DC ricalibrato (stack su dc_lmu, dc_lnu) * | 2719 | 0.9913 | 0.2045 | 0.5886 | 52.7% |
| Premier League | DC + pi-ratings | 2719 | 0.9831 | 0.2028 | 0.5851 | 53.0% |
| Premier League | Stack senza xG (produzione, training dal 2013/14) | 2719 | 0.9806 | 0.2019 | 0.5831 | 53.4% |
| Premier League | Stack senza xG (training dal 2016/17) * | 2719 | 0.9809 | 0.2020 | 0.5833 | 53.3% |
| Premier League | Stack + xG Understat (training dal 2016/17) | 2719 | 0.9780 | 0.2010 | 0.5816 | 53.6% |
| Premier League | Stack + xG con ridge=2 sul DC xG (training dal 2016/17) | 2719 | 0.9771 | 0.2008 | 0.5811 | 53.3% |
| Premier League | Stack + xG ridge + Elo-Odds K=200 (produzione, training dal 2016/17) | 2719 | 0.9733 | 0.1997 | 0.5787 | 53.7% |
| Premier League | Stack senza xG + Elo-Odds K=200 (ripiego without_xg, training dal 2013/14) | 2719 | 0.9738 | 0.1999 | 0.5789 | 53.3% |
| Bundesliga | Quote medie senza margine (power) | 2187 | 0.9768 | 0.1985 | 0.5805 | 52.8% |
| Bundesliga | Quote chiusura senza margine (power) | 2187 | 0.9748 | 0.1980 | 0.5791 | 53.3% |
| Bundesliga | Dixon-Coles attuale (xi=0.0018) | 2187 | 1.0057 | 0.2059 | 0.5983 | 51.6% |
| Bundesliga | DC ricalibrato (stack su dc_lmu, dc_lnu) * | 2187 | 1.0021 | 0.2059 | 0.5972 | 51.8% |
| Bundesliga | DC + pi-ratings | 2187 | 0.9950 | 0.2041 | 0.5936 | 51.3% |
| Bundesliga | Stack senza xG (produzione, training dal 2013/14) | 2187 | 0.9929 | 0.2035 | 0.5920 | 51.6% |
| Bundesliga | Stack senza xG (training dal 2016/17) * | 2187 | 0.9926 | 0.2035 | 0.5919 | 51.6% |
| Bundesliga | Stack + xG Understat (training dal 2016/17) | 2187 | 0.9898 | 0.2025 | 0.5897 | 52.0% |
| Bundesliga | Stack + xG con ridge=2 sul DC xG (training dal 2016/17) | 2187 | 0.9892 | 0.2024 | 0.5894 | 51.9% |
| Bundesliga | Stack + xG ridge + Elo-Odds K=200 (produzione, training dal 2016/17) | 2187 | 0.9853 | 0.2012 | 0.5867 | 51.8% |
| Bundesliga | Stack senza xG + Elo-Odds K=200 (ripiego without_xg, training dal 2013/14) | 2187 | 0.9855 | 0.2012 | 0.5869 | 52.1% |
| La Liga | Quote medie senza margine (power) | 2737 | 0.9689 | 0.1923 | 0.5759 | 53.8% |
| La Liga | Quote chiusura senza margine (power) | 2737 | 0.9669 | 0.1916 | 0.5745 | 54.1% |
| La Liga | Dixon-Coles attuale (xi=0.0018) | 2737 | 0.9926 | 0.1987 | 0.5900 | 52.1% |
| La Liga | DC ricalibrato (stack su dc_lmu, dc_lnu) * | 2737 | 0.9952 | 0.1994 | 0.5918 | 51.8% |
| La Liga | DC + pi-ratings | 2737 | 0.9902 | 0.1985 | 0.5900 | 52.8% |
| La Liga | Stack senza xG (produzione, training dal 2013/14) | 2737 | 0.9848 | 0.1970 | 0.5864 | 53.1% |
| La Liga | Stack senza xG (training dal 2016/17) * | 2737 | 0.9849 | 0.1970 | 0.5863 | 52.9% |
| La Liga | Stack + xG Understat (training dal 2016/17) | 2737 | 0.9826 | 0.1963 | 0.5848 | 53.1% |
| La Liga | Stack + xG con ridge=2 sul DC xG (training dal 2016/17) | 2737 | 0.9798 | 0.1955 | 0.5829 | 53.0% |
| La Liga | Stack + xG ridge + Elo-Odds K=200 (produzione, training dal 2016/17) | 2737 | 0.9782 | 0.1948 | 0.5817 | 53.5% |
| La Liga | Stack senza xG + Elo-Odds K=200 (ripiego without_xg, training dal 2013/14) | 2737 | 0.9799 | 0.1952 | 0.5828 | 53.2% |
| Ligue 1 | Quote medie senza margine (power) | 2391 | 0.9868 | 0.2024 | 0.5882 | 52.5% |
| Ligue 1 | Quote chiusura senza margine (power) | 2391 | 0.9849 | 0.2018 | 0.5873 | 52.5% |
| Ligue 1 | Dixon-Coles attuale (xi=0.0018) | 2391 | 1.0064 | 0.2083 | 0.6015 | 51.7% |
| Ligue 1 | DC ricalibrato (stack su dc_lmu, dc_lnu) * | 2391 | 1.0064 | 0.2084 | 0.6015 | 51.4% |
| Ligue 1 | DC + pi-ratings | 2391 | 1.0043 | 0.2078 | 0.6000 | 51.4% |
| Ligue 1 | Stack senza xG (produzione, training dal 2013/14) | 2391 | 1.0009 | 0.2068 | 0.5979 | 51.3% |
| Ligue 1 | Stack senza xG (training dal 2016/17) * | 2391 | 1.0010 | 0.2068 | 0.5979 | 51.4% |
| Ligue 1 | Stack + xG Understat (training dal 2016/17) | 2391 | 0.9982 | 0.2061 | 0.5964 | 51.2% |
| Ligue 1 | Stack + xG con ridge=2 sul DC xG (training dal 2016/17) | 2391 | 0.9977 | 0.2060 | 0.5961 | 51.7% |
| Ligue 1 | Stack + xG ridge + Elo-Odds K=200 (produzione, training dal 2016/17) | 2391 | 0.9950 | 0.2050 | 0.5937 | 51.7% |
| Ligue 1 | Stack senza xG + Elo-Odds K=200 (ripiego without_xg, training dal 2013/14) | 2391 | 0.9959 | 0.2051 | 0.5940 | 51.9% |

\* Righe di controllo: servono a separare l'effetto delle feature nuove da quello della semplice ricalibrazione (DC ricalibrato) e della finestra di training più corta (stack senza xG dal 2016/17).

## Differenza di log-loss (positivo = il secondo modello è migliore)

Bootstrap a blocchi per settimana ISO (tutte le leghe della stessa settimana restano insieme), 5000 ricampionamenti, IC 95% percentile.

| Confronto | Δ log-loss | IC 95% | Settimane |
|---|---:|---|---:|
| Stack senza xG (produzione, training dal 2013/14) → Stack + xG Understat (training dal 2016/17) | +0.0022 | [+0.0009, +0.0036] | 271 |
| Stack senza xG (training dal 2016/17) * → Stack + xG Understat (training dal 2016/17) | +0.0022 | [+0.0009, +0.0036] | 271 |
| Stack + xG Understat (training dal 2016/17) → Stack + xG con ridge=2 sul DC xG (training dal 2016/17) | +0.0010 | [+0.0004, +0.0017] | 271 |
| Stack senza xG (produzione, training dal 2013/14) → Stack + xG con ridge=2 sul DC xG (training dal 2016/17) | +0.0033 | [+0.0018, +0.0048] | 271 |
| Dixon-Coles attuale (xi=0.0018) → Stack + xG con ridge=2 sul DC xG (training dal 2016/17) | +0.0119 | [+0.0085, +0.0156] | 271 |
| Dixon-Coles attuale (xi=0.0018) → Stack senza xG (produzione, training dal 2013/14) | +0.0086 | [+0.0056, +0.0119] | 271 |
| Dixon-Coles attuale (xi=0.0018) → Stack + xG Understat (training dal 2016/17) | +0.0109 | [+0.0076, +0.0145] | 271 |
| Stack + xG con ridge=2 sul DC xG (training dal 2016/17) → Stack + xG ridge + Elo-Odds K=200 (produzione, training dal 2016/17) | +0.0033 | [+0.0018, +0.0048] | 271 |
| Stack senza xG (produzione, training dal 2013/14) → Stack senza xG + Elo-Odds K=200 (ripiego without_xg, training dal 2013/14) | +0.0059 | [+0.0040, +0.0078] | 271 |
| Stack senza xG (produzione, training dal 2013/14) → Stack + xG ridge + Elo-Odds K=200 (produzione, training dal 2016/17) | +0.0066 | [+0.0045, +0.0086] | 271 |
| Dixon-Coles attuale (xi=0.0018) → Stack + xG ridge + Elo-Odds K=200 (produzione, training dal 2016/17) | +0.0152 | [+0.0119, +0.0188] | 271 |

## Per stagione (log-loss)

| Stagione | N | Quote medie | DC attuale | Stack senza xG | Stack + xG | Stack + xG ridge | Δ (senza xG − con xG) | Δ (xG − xG ridge) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2019/20 | 1725 | 0.9752 | 0.9952 | 0.9871 | 0.9832 | 0.9819 | +0.0039 | +0.0013 |
| 2020/21 | 1826 | 0.9820 | 1.0086 | 0.9994 | 0.9935 | 0.9918 | +0.0059 | +0.0017 |
| 2021/22 | 1825 | 0.9773 | 0.9961 | 0.9886 | 0.9880 | 0.9877 | +0.0006 | +0.0003 |
| 2022/23 | 1826 | 0.9777 | 0.9984 | 0.9873 | 0.9862 | 0.9859 | +0.0011 | +0.0004 |
| 2023/24 | 1752 | 0.9543 | 0.9767 | 0.9719 | 0.9701 | 0.9700 | +0.0018 | +0.0001 |
| 2024/25 | 1752 | 0.9633 | 0.9850 | 0.9802 | 0.9746 | 0.9745 | +0.0056 | +0.0001 |
| 2025/26 | 1752 | 0.9776 | 1.0021 | 0.9916 | 0.9918 | 0.9903 | -0.0002 | +0.0014 |
| 2026/27 | 293 | 0.9672 | 1.0090 | 0.9743 | 0.9899 | 0.9781 | -0.0156 | +0.0118 |

Stagioni in cui l'xG non migliora (Δ ≤ 0): 2025/26: Δ -0.0002 su 1752 partite (errore standard ±0.0014, 0.2 errori standard); 2026/27: Δ -0.0156 su 293 partite (errore standard ±0.0067, 2.3 errori standard).

## Elo-Odds (modello di produzione) per stagione e per lega

Rating Elo-Odds K=200 sulle quote di chiusura (metodo power); quote usate: chiusura per 25534 partite su 25538, ripiego sulle quote pre-partita per 4, nessuna quota per 0. Δ = log-loss(stack + xG ridge) − log-loss(+ Elo-Odds): positivo = Elo-Odds migliore.

| Stagione | N | Stack + xG ridge | + Elo-Odds | Δ |
|---|---:|---:|---:|---:|
| 2019/20 | 1725 | 0.9819 | 0.9823 | -0.0005 |
| 2020/21 | 1826 | 0.9918 | 0.9934 | -0.0016 |
| 2021/22 | 1825 | 0.9877 | 0.9843 | +0.0034 |
| 2022/23 | 1826 | 0.9859 | 0.9828 | +0.0030 |
| 2023/24 | 1752 | 0.9700 | 0.9627 | +0.0073 |
| 2024/25 | 1752 | 0.9745 | 0.9690 | +0.0055 |
| 2025/26 | 1752 | 0.9903 | 0.9846 | +0.0057 |
| 2026/27 | 293 | 0.9781 | 0.9716 | +0.0065 |

| Campionato | N | Stack + xG ridge | + Elo-Odds | Δ |
|---|---:|---:|---:|---:|
| Serie A | 2717 | 0.9748 | 0.9701 | +0.0047 |
| Premier League | 2719 | 0.9771 | 0.9733 | +0.0038 |
| Bundesliga | 2187 | 0.9892 | 0.9853 | +0.0038 |
| La Liga | 2737 | 0.9798 | 0.9782 | +0.0017 |
| Ligue 1 | 2391 | 0.9977 | 0.9950 | +0.0026 |

Δ medio 2019/20-2021/22: +0.0005; dal 2022/23: +0.0054. La causa non è chiarita: il round 3 (esperimento A, backtest/results_round3.md) esclude che dipenda dalla lunghezza del training dello stack.


### Modello di ripiego without_xg: guadagno di eo_diff

Stesso confronto sul modello senza xG (training dal 2013/14, come in produzione per il ripiego).

| Modello | Log-loss | RPS | Brier |
|---|---:|---:|---:|
| Stack senza xG (produzione, training dal 2013/14) | 0.9864 | 0.2005 | 0.5876 |
| Stack senza xG + Elo-Odds K=200 (ripiego without_xg, training dal 2013/14) | 0.9805 | 0.1986 | 0.5835 |

Δ log-loss (senza eo_diff − con eo_diff) = +0.0059, IC 95% a blocchi per settimana [+0.0040, +0.0078].

| Stagione | N | Senza Elo-Odds | Con Elo-Odds | Δ |
|---|---:|---:|---:|---:|
| 2019/20 | 1725 | 0.9871 | 0.9839 | +0.0031 |
| 2020/21 | 1826 | 0.9994 | 0.9973 | +0.0021 |
| 2021/22 | 1825 | 0.9886 | 0.9843 | +0.0043 |
| 2022/23 | 1826 | 0.9873 | 0.9822 | +0.0051 |
| 2023/24 | 1752 | 0.9719 | 0.9621 | +0.0097 |
| 2024/25 | 1752 | 0.9802 | 0.9706 | +0.0096 |
| 2025/26 | 1752 | 0.9916 | 0.9840 | +0.0076 |
| 2026/27 | 293 | 0.9743 | 0.9682 | +0.0061 |

| Campionato | N | Senza Elo-Odds | Con Elo-Odds | Δ |
|---|---:|---:|---:|---:|
| Serie A | 2717 | 0.9758 | 0.9701 | +0.0057 |
| Premier League | 2719 | 0.9806 | 0.9738 | +0.0068 |
| Bundesliga | 2187 | 0.9929 | 0.9855 | +0.0073 |
| La Liga | 2737 | 0.9848 | 0.9799 | +0.0049 |
| Ligue 1 | 2391 | 1.0009 | 0.9959 | +0.0050 |

## Stagione in corso e neopromosse (log-loss)

Neopromossa = squadra assente dallo stesso campionato nella stagione precedente. Tra parentesi l'errore standard del Δ (xG − xG ridge).

| Sottoinsieme | N | Stack senza xG | Stack + xG | Stack + xG ridge | Δ (xG − xG ridge) |
|---|---:|---:|---:|---:|---:|
| 2026/27 (stagione in corso) | 293 | 0.9743 | 0.9899 | 0.9781 | +0.0118 (±0.0051) |
| 2026/27 con ridge, solo partite con neopromosse | 81 | 0.9823 | 1.0413 | 1.0033 | +0.0379 (±0.0180) |
| Tutte le stagioni, neopromosse ad agosto-settembre | 617 | 0.9733 | 0.9783 | 0.9682 | +0.0101 (±0.0048) |
| Tutte le stagioni, resto delle partite | 12134 | 0.9870 | 0.9844 | 0.9839 | +0.0006 (±0.0002) |

## Check di accettazione

- Step 1 — DC attuale: 0.9950 (atteso 0.994 ± 0.004) → OK
- Step 1 — quote: 0.9725 (atteso 0.973 ± 0.004) → OK
- Step 3 — stack senza xG ≤ 0.987: 0.9864 → OK
- Step 3 — stack migliore del DC in ogni stagione: 8/8 stagioni → OK
- Step 7.1 — abbinamento nomi xG (≥ 99% delle partite): 99.99% → OK
- Step 7.1 — guadagno xG ≥ +0.0015 (atteso circa +0.002/+0.003): +0.0022 (stack 0.9864 → 0.9841) → OK
- Step 7.1 — IC 95% del guadagno xG esclude lo zero: [+0.0009, +0.0036] → OK
- Step 7.1 — stack + xG migliore in ogni stagione: 6/8 stagioni → NON SUPERATO
- Ridge xG — guadagno ≥ +0.0003 (atteso circa +0.0007): +0.0010 (stack + xG 0.9841 → con ridge 0.9831) → OK
- Ridge xG — IC 95% del guadagno esclude lo zero: [+0.0004, +0.0017] → OK
- Ridge xG — migliore in ogni stagione (informativo): 8/8 stagioni → OK
- Elo-Odds — log-loss coerente col round 2 (0.9798 ± 0.0008): 0.9798 → OK
- Elo-Odds — guadagno ≥ +0.002 (round 2: +0.0033): +0.0033 (stack + xG ridge 0.9831 → con Elo-Odds 0.9798) → OK
- Elo-Odds — IC 95% a blocchi per settimana del guadagno esclude lo zero: [+0.0018, +0.0048] → OK
- Elo-Odds su without_xg (ripiego) — IC 95% a blocchi per settimana del guadagno esclude lo zero (altrimenti togliere eo_diff dal ripiego): +0.0059 [+0.0040, +0.0078] → OK
- Elo-Odds su without_xg — migliore in ogni stagione (informativo): 8/8 stagioni → OK
- Elo-Odds — migliore in ogni stagione (informativo): 6/8 stagioni → NON SUPERATO
