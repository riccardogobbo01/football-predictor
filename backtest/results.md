# Backtest walk-forward — Step 1-3 e 7.1 (xG Understat)

Test: 2019-08-09 → 2026-09-20 (stagioni 2019/20 → 2026/27), 12708 partite con quote medie valide. DC rifittato ogni 7 giorni (finestra 5 anni, xi=0.0018); xG: DC senza tau su xG Understat, xi=0.003, finestra 5 anni (nelle righe "ridge" con penalità ridge=2 sul solo DC degli xG; il DC dei gol non usa ridge). Lo stack è stimato stagione per stagione sulle sole stagioni precedenti, 5 campionati insieme. Più basso = meglio (tranne accuratezza).

Copertura xG: 21836/21839 partite dal 2014/15 abbinate a Understat (99.99%).

## Confronto tra modelli

| Campionato | Modello | N | Log-loss | RPS | Brier | Accuratezza |
|---|---|---:|---:|---:|---:|---:|
| Tutti | Quote medie senza margine (power) | 12708 | 0.9727 | 0.1963 | 0.5783 | 53.5% |
| Tutti | Quote chiusura senza margine (power) | 12708 | 0.9702 | 0.1956 | 0.5767 | 53.9% |
| Tutti | Dixon-Coles attuale (xi=0.0018) | 12708 | 0.9952 | 0.2026 | 0.5920 | 52.3% |
| Tutti | DC ricalibrato (stack su dc_lmu, dc_lnu) * | 12708 | 0.9963 | 0.2031 | 0.5930 | 52.3% |
| Tutti | DC + pi-ratings | 12708 | 0.9904 | 0.2017 | 0.5903 | 52.4% |
| Tutti | Stack senza xG (produzione, training dal 2013/14) | 12708 | 0.9867 | 0.2006 | 0.5878 | 52.7% |
| Tutti | Stack senza xG (training dal 2016/17) * | 12708 | 0.9867 | 0.2006 | 0.5878 | 52.7% |
| Tutti | Stack + xG Understat (training dal 2016/17) | 12708 | 0.9844 | 0.1999 | 0.5863 | 52.8% |
| Tutti | Stack + xG con ridge=2 sul DC xG (training dal 2016/17) | 12708 | 0.9834 | 0.1996 | 0.5857 | 52.8% |
| Serie A | Quote medie senza margine (power) | 2709 | 0.9630 | 0.1910 | 0.5720 | 54.3% |
| Serie A | Quote chiusura senza margine (power) | 2709 | 0.9607 | 0.1904 | 0.5708 | 54.7% |
| Serie A | Dixon-Coles attuale (xi=0.0018) | 2709 | 0.9846 | 0.1971 | 0.5850 | 53.4% |
| Serie A | DC ricalibrato (stack su dc_lmu, dc_lnu) * | 2709 | 0.9881 | 0.1980 | 0.5872 | 53.4% |
| Serie A | DC + pi-ratings | 2709 | 0.9810 | 0.1964 | 0.5840 | 53.4% |
| Serie A | Stack senza xG (produzione, training dal 2013/14) | 2709 | 0.9761 | 0.1949 | 0.5810 | 53.8% |
| Serie A | Stack senza xG (training dal 2016/17) * | 2709 | 0.9759 | 0.1948 | 0.5808 | 53.8% |
| Serie A | Stack + xG Understat (training dal 2016/17) | 2709 | 0.9752 | 0.1946 | 0.5803 | 53.6% |
| Serie A | Stack + xG con ridge=2 sul DC xG (training dal 2016/17) | 2709 | 0.9751 | 0.1945 | 0.5801 | 53.7% |
| Premier League | Quote medie senza margine (power) | 2710 | 0.9696 | 0.1983 | 0.5758 | 54.3% |
| Premier League | Quote chiusura senza margine (power) | 2710 | 0.9658 | 0.1970 | 0.5730 | 54.8% |
| Premier League | Dixon-Coles attuale (xi=0.0018) | 2710 | 0.9895 | 0.2040 | 0.5872 | 52.8% |
| Premier League | DC ricalibrato (stack su dc_lmu, dc_lnu) * | 2710 | 0.9911 | 0.2045 | 0.5884 | 52.7% |
| Premier League | DC + pi-ratings | 2710 | 0.9829 | 0.2028 | 0.5849 | 53.1% |
| Premier League | Stack senza xG (produzione, training dal 2013/14) | 2710 | 0.9804 | 0.2019 | 0.5830 | 53.4% |
| Premier League | Stack senza xG (training dal 2016/17) * | 2710 | 0.9807 | 0.2020 | 0.5832 | 53.2% |
| Premier League | Stack + xG Understat (training dal 2016/17) | 2710 | 0.9778 | 0.2010 | 0.5815 | 53.7% |
| Premier League | Stack + xG con ridge=2 sul DC xG (training dal 2016/17) | 2710 | 0.9769 | 0.2008 | 0.5809 | 53.3% |
| Bundesliga | Quote medie senza margine (power) | 2178 | 0.9761 | 0.1983 | 0.5800 | 52.8% |
| Bundesliga | Quote chiusura senza margine (power) | 2178 | 0.9741 | 0.1979 | 0.5787 | 53.3% |
| Bundesliga | Dixon-Coles attuale (xi=0.0018) | 2178 | 1.0050 | 0.2056 | 0.5977 | 51.6% |
| Bundesliga | DC ricalibrato (stack su dc_lmu, dc_lnu) * | 2178 | 1.0016 | 0.2057 | 0.5967 | 51.8% |
| Bundesliga | DC + pi-ratings | 2178 | 0.9947 | 0.2040 | 0.5933 | 51.3% |
| Bundesliga | Stack senza xG (produzione, training dal 2013/14) | 2178 | 0.9927 | 0.2035 | 0.5918 | 51.6% |
| Bundesliga | Stack senza xG (training dal 2016/17) * | 2178 | 0.9925 | 0.2034 | 0.5918 | 51.6% |
| Bundesliga | Stack + xG Understat (training dal 2016/17) | 2178 | 0.9897 | 0.2024 | 0.5896 | 52.0% |
| Bundesliga | Stack + xG con ridge=2 sul DC xG (training dal 2016/17) | 2178 | 0.9890 | 0.2023 | 0.5893 | 51.8% |
| La Liga | Quote medie senza margine (power) | 2729 | 0.9696 | 0.1926 | 0.5764 | 53.8% |
| La Liga | Quote chiusura senza margine (power) | 2729 | 0.9676 | 0.1919 | 0.5750 | 54.0% |
| La Liga | Dixon-Coles attuale (xi=0.0018) | 2729 | 0.9930 | 0.1989 | 0.5904 | 52.1% |
| La Liga | DC ricalibrato (stack su dc_lmu, dc_lnu) * | 2729 | 0.9956 | 0.1996 | 0.5921 | 51.9% |
| La Liga | DC + pi-ratings | 2729 | 0.9907 | 0.1987 | 0.5904 | 52.7% |
| La Liga | Stack senza xG (produzione, training dal 2013/14) | 2729 | 0.9854 | 0.1972 | 0.5868 | 53.0% |
| La Liga | Stack senza xG (training dal 2016/17) * | 2729 | 0.9854 | 0.1972 | 0.5867 | 52.9% |
| La Liga | Stack + xG Understat (training dal 2016/17) | 2729 | 0.9831 | 0.1965 | 0.5851 | 53.0% |
| La Liga | Stack + xG con ridge=2 sul DC xG (training dal 2016/17) | 2729 | 0.9803 | 0.1957 | 0.5833 | 53.0% |
| Ligue 1 | Quote medie senza margine (power) | 2382 | 0.9877 | 0.2025 | 0.5888 | 52.4% |
| Ligue 1 | Quote chiusura senza margine (power) | 2382 | 0.9857 | 0.2019 | 0.5878 | 52.4% |
| Ligue 1 | Dixon-Coles attuale (xi=0.0018) | 2382 | 1.0074 | 0.2085 | 0.6022 | 51.6% |
| Ligue 1 | DC ricalibrato (stack su dc_lmu, dc_lnu) * | 2382 | 1.0073 | 0.2086 | 0.6022 | 51.4% |
| Ligue 1 | DC + pi-ratings | 2382 | 1.0052 | 0.2079 | 0.6006 | 51.3% |
| Ligue 1 | Stack senza xG (produzione, training dal 2013/14) | 2382 | 1.0019 | 0.2070 | 0.5986 | 51.3% |
| Ligue 1 | Stack senza xG (training dal 2016/17) * | 2382 | 1.0019 | 0.2070 | 0.5986 | 51.3% |
| Ligue 1 | Stack + xG Understat (training dal 2016/17) | 2382 | 0.9992 | 0.2063 | 0.5971 | 51.2% |
| Ligue 1 | Stack + xG con ridge=2 sul DC xG (training dal 2016/17) | 2382 | 0.9987 | 0.2062 | 0.5968 | 51.6% |

\* Righe di controllo: servono a separare l'effetto delle feature nuove da quello della semplice ricalibrazione (DC ricalibrato) e della finestra di training più corta (stack senza xG dal 2016/17).

## Differenza di log-loss (positivo = il secondo modello è migliore)

Bootstrap a blocchi per settimana ISO (tutte le leghe della stessa settimana restano insieme), 5000 ricampionamenti, IC 95% percentile.

| Confronto | Δ log-loss | IC 95% | Settimane |
|---|---:|---|---:|
| Stack senza xG (produzione, training dal 2013/14) → Stack + xG Understat (training dal 2016/17) | +0.0022 | [+0.0009, +0.0036] | 270 |
| Stack senza xG (training dal 2016/17) * → Stack + xG Understat (training dal 2016/17) | +0.0022 | [+0.0009, +0.0036] | 270 |
| Stack + xG Understat (training dal 2016/17) → Stack + xG con ridge=2 sul DC xG (training dal 2016/17) | +0.0010 | [+0.0004, +0.0017] | 270 |
| Stack senza xG (produzione, training dal 2013/14) → Stack + xG con ridge=2 sul DC xG (training dal 2016/17) | +0.0033 | [+0.0018, +0.0048] | 270 |
| Dixon-Coles attuale (xi=0.0018) → Stack + xG con ridge=2 sul DC xG (training dal 2016/17) | +0.0118 | [+0.0083, +0.0156] | 270 |
| Dixon-Coles attuale (xi=0.0018) → Stack senza xG (produzione, training dal 2013/14) | +0.0085 | [+0.0054, +0.0119] | 270 |
| Dixon-Coles attuale (xi=0.0018) → Stack + xG Understat (training dal 2016/17) | +0.0108 | [+0.0074, +0.0144] | 270 |

## Per stagione (log-loss)

| Stagione | N | Quote medie | DC attuale | Stack senza xG | Stack + xG | Stack + xG ridge | Δ (senza xG − con xG) | Δ (xG − xG ridge) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2019/20 | 1725 | 0.9752 | 0.9952 | 0.9871 | 0.9832 | 0.9819 | +0.0039 | +0.0013 |
| 2020/21 | 1826 | 0.9820 | 1.0086 | 0.9994 | 0.9935 | 0.9918 | +0.0059 | +0.0017 |
| 2021/22 | 1825 | 0.9773 | 0.9961 | 0.9886 | 0.9880 | 0.9877 | +0.0006 | +0.0003 |
| 2022/23 | 1826 | 0.9777 | 0.9984 | 0.9874 | 0.9862 | 0.9859 | +0.0011 | +0.0004 |
| 2023/24 | 1752 | 0.9543 | 0.9767 | 0.9719 | 0.9701 | 0.9700 | +0.0018 | +0.0001 |
| 2024/25 | 1752 | 0.9633 | 0.9850 | 0.9802 | 0.9746 | 0.9745 | +0.0056 | +0.0001 |
| 2025/26 | 1752 | 0.9776 | 1.0021 | 0.9916 | 0.9918 | 0.9903 | -0.0002 | +0.0014 |
| 2026/27 | 250 | 0.9780 | 1.0202 | 0.9873 | 1.0056 | 0.9917 | -0.0183 | +0.0139 |

Stagioni in cui l'xG non migliora (Δ ≤ 0): 2025/26: Δ -0.0002 su 1752 partite (errore standard ±0.0014, 0.2 errori standard); 2026/27: Δ -0.0183 su 250 partite (errore standard ±0.0078, 2.4 errori standard).

## Stagione in corso e neopromosse (log-loss)

Neopromossa = squadra assente dallo stesso campionato nella stagione precedente. Tra parentesi l'errore standard del Δ (xG − xG ridge).

| Sottoinsieme | N | Stack senza xG | Stack + xG | Stack + xG ridge | Δ (xG − xG ridge) |
|---|---:|---:|---:|---:|---:|
| 2026/27 (stagione in corso) | 250 | 0.9873 | 1.0056 | 0.9917 | +0.0139 (±0.0059) |
| 2026/27 con ridge, solo partite con neopromosse | 69 | 1.0171 | 1.0910 | 1.0448 | +0.0463 (±0.0209) |
| Tutte le stagioni, neopromosse ad agosto-settembre | 617 | 0.9733 | 0.9783 | 0.9682 | +0.0101 (±0.0048) |
| Tutte le stagioni, resto delle partite | 12091 | 0.9874 | 0.9847 | 0.9842 | +0.0006 (±0.0002) |

## Check di accettazione

- Step 1 — DC attuale: 0.9952 (atteso 0.994 ± 0.004) → OK
- Step 1 — quote: 0.9727 (atteso 0.973 ± 0.004) → OK
- Step 3 — stack senza xG ≤ 0.987: 0.9867 → OK
- Step 3 — stack migliore del DC in ogni stagione: 8/8 stagioni → OK
- Step 7.1 — abbinamento nomi xG (≥ 99% delle partite): 99.99% → OK
- Step 7.1 — guadagno xG ≥ +0.0015 (atteso circa +0.002/+0.003): +0.0022 (stack 0.9867 → 0.9844) → OK
- Step 7.1 — IC 95% del guadagno xG esclude lo zero: [+0.0009, +0.0036] → OK
- Step 7.1 — stack + xG migliore in ogni stagione: 6/8 stagioni → NON SUPERATO
- Ridge xG — guadagno ≥ +0.0003 (atteso circa +0.0007): +0.0010 (stack + xG 0.9844 → con ridge 0.9834) → OK
- Ridge xG — IC 95% del guadagno esclude lo zero: [+0.0004, +0.0017] → OK
- Ridge xG — migliore in ogni stagione (informativo): 8/8 stagioni → OK
