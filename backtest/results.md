# Backtest walk-forward — Step 1-3

Test: 2019-08-09 → 2026-09-20 (stagioni 2019/20 → 2026/27), 12708 partite con quote medie valide. DC rifittato ogni 7 giorni (finestra 5 anni, xi=0.0018); stack stimato stagione per stagione sulle sole stagioni precedenti (dal 2013/14), 5 campionati insieme. Più basso = meglio (tranne accuratezza).

## Confronto tra modelli

| Campionato | Modello | N | Log-loss | RPS | Brier | Accuratezza |
|---|---|---:|---:|---:|---:|---:|
| Tutti | Quote medie senza margine (power) | 12708 | 0.9727 | 0.1963 | 0.5783 | 53.5% |
| Tutti | Quote chiusura senza margine (power) | 12708 | 0.9702 | 0.1956 | 0.5767 | 53.9% |
| Tutti | Dixon-Coles attuale (xi=0.0018) | 12708 | 0.9952 | 0.2026 | 0.5920 | 52.3% |
| Tutti | DC ricalibrato (stack su dc_lmu, dc_lnu) * | 12708 | 0.9963 | 0.2031 | 0.5930 | 52.3% |
| Tutti | DC + pi-ratings | 12708 | 0.9904 | 0.2017 | 0.5903 | 52.5% |
| Tutti | Poisson-stack senza Elo | 12708 | 0.9867 | 0.2006 | 0.5878 | 52.7% |
| Serie A | Quote medie senza margine (power) | 2709 | 0.9630 | 0.1910 | 0.5720 | 54.3% |
| Serie A | Quote chiusura senza margine (power) | 2709 | 0.9607 | 0.1904 | 0.5708 | 54.7% |
| Serie A | Dixon-Coles attuale (xi=0.0018) | 2709 | 0.9846 | 0.1971 | 0.5850 | 53.4% |
| Serie A | DC ricalibrato (stack su dc_lmu, dc_lnu) * | 2709 | 0.9882 | 0.1981 | 0.5872 | 53.4% |
| Serie A | DC + pi-ratings | 2709 | 0.9810 | 0.1964 | 0.5840 | 53.4% |
| Serie A | Poisson-stack senza Elo | 2709 | 0.9761 | 0.1949 | 0.5810 | 53.8% |
| Premier League | Quote medie senza margine (power) | 2710 | 0.9696 | 0.1983 | 0.5758 | 54.3% |
| Premier League | Quote chiusura senza margine (power) | 2710 | 0.9658 | 0.1970 | 0.5730 | 54.8% |
| Premier League | Dixon-Coles attuale (xi=0.0018) | 2710 | 0.9895 | 0.2040 | 0.5872 | 52.8% |
| Premier League | DC ricalibrato (stack su dc_lmu, dc_lnu) * | 2710 | 0.9912 | 0.2045 | 0.5884 | 52.7% |
| Premier League | DC + pi-ratings | 2710 | 0.9829 | 0.2028 | 0.5850 | 53.1% |
| Premier League | Poisson-stack senza Elo | 2710 | 0.9804 | 0.2020 | 0.5830 | 53.4% |
| Bundesliga | Quote medie senza margine (power) | 2178 | 0.9761 | 0.1983 | 0.5800 | 52.8% |
| Bundesliga | Quote chiusura senza margine (power) | 2178 | 0.9741 | 0.1979 | 0.5787 | 53.3% |
| Bundesliga | Dixon-Coles attuale (xi=0.0018) | 2178 | 1.0050 | 0.2056 | 0.5977 | 51.6% |
| Bundesliga | DC ricalibrato (stack su dc_lmu, dc_lnu) * | 2178 | 1.0016 | 0.2057 | 0.5967 | 51.7% |
| Bundesliga | DC + pi-ratings | 2178 | 0.9947 | 0.2040 | 0.5933 | 51.3% |
| Bundesliga | Poisson-stack senza Elo | 2178 | 0.9927 | 0.2035 | 0.5918 | 51.6% |
| La Liga | Quote medie senza margine (power) | 2729 | 0.9696 | 0.1926 | 0.5764 | 53.8% |
| La Liga | Quote chiusura senza margine (power) | 2729 | 0.9676 | 0.1919 | 0.5750 | 54.0% |
| La Liga | Dixon-Coles attuale (xi=0.0018) | 2729 | 0.9930 | 0.1989 | 0.5904 | 52.1% |
| La Liga | DC ricalibrato (stack su dc_lmu, dc_lnu) * | 2729 | 0.9956 | 0.1996 | 0.5921 | 51.9% |
| La Liga | DC + pi-ratings | 2729 | 0.9906 | 0.1987 | 0.5903 | 52.7% |
| La Liga | Poisson-stack senza Elo | 2729 | 0.9853 | 0.1972 | 0.5867 | 53.0% |
| Ligue 1 | Quote medie senza margine (power) | 2382 | 0.9877 | 0.2025 | 0.5888 | 52.4% |
| Ligue 1 | Quote chiusura senza margine (power) | 2382 | 0.9857 | 0.2019 | 0.5878 | 52.4% |
| Ligue 1 | Dixon-Coles attuale (xi=0.0018) | 2382 | 1.0074 | 0.2085 | 0.6022 | 51.6% |
| Ligue 1 | DC ricalibrato (stack su dc_lmu, dc_lnu) * | 2382 | 1.0073 | 0.2086 | 0.6022 | 51.4% |
| Ligue 1 | DC + pi-ratings | 2382 | 1.0052 | 0.2079 | 0.6006 | 51.3% |
| Ligue 1 | Poisson-stack senza Elo | 2382 | 1.0019 | 0.2070 | 0.5986 | 51.3% |

\* Riga aggiuntiva: lo stack con le sole due feature del DC. Serve a separare l'effetto della semplice ricalibrazione da quello delle feature nuove.

_Run con `--no-elo`: **le righe DC + Elo e Poisson-stack completo mancano** (api.clubelo.com rispondeva 502). Rigenerare con `python -m backtest.run_backtest` quando ClubElo è raggiungibile; qui "Poisson-stack senza Elo" usa le 6 feature restanti._

## Differenza di log-loss (positivo = lo stack è migliore)

Bootstrap a blocchi per settimana ISO (tutte le leghe della stessa settimana restano insieme), 5000 ricampionamenti, IC 95% percentile.

| Confronto | Δ log-loss | IC 95% | Settimane |
|---|---:|---|---:|
| DC attuale − Poisson-stack senza Elo | +0.0085 | [+0.0054, +0.0119] | 270 |
| DC ricalibrato − Poisson-stack senza Elo | +0.0096 | [+0.0068, +0.0127] | 270 |

## Per stagione (log-loss)

| Stagione | N | Quote medie | DC attuale | Poisson-stack senza Elo | Δ (DC − stack) |
|---|---:|---:|---:|---:|---:|
| 2019/20 | 1504 | 0.9787 | 0.9981 | 0.9900 | +0.0080 |
| 2020/21 | 2047 | 0.9787 | 1.0051 | 0.9960 | +0.0091 |
| 2021/22 | 1825 | 0.9773 | 0.9961 | 0.9886 | +0.0075 |
| 2022/23 | 1826 | 0.9777 | 0.9984 | 0.9874 | +0.0110 |
| 2023/24 | 1752 | 0.9543 | 0.9767 | 0.9719 | +0.0049 |
| 2024/25 | 1752 | 0.9633 | 0.9850 | 0.9802 | +0.0048 |
| 2025/26 | 1752 | 0.9776 | 1.0021 | 0.9916 | +0.0105 |
| 2026/27 | 250 | 0.9780 | 1.0202 | 0.9873 | +0.0329 |

## Check di accettazione

- Step 1 — DC attuale: 0.9952 (atteso 0.994 ± 0.004) → OK
- Step 1 — quote: 0.9727 (atteso 0.973 ± 0.004) → OK
- Step 3 — stack ≤ 0.987: 0.9867 → OK
- Step 3 — stack migliore del DC in ogni stagione: 8/8 stagioni → OK
