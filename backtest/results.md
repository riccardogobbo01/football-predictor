# Backtest walk-forward — Step 1

Test: 2019-08-09 → 2026-09-20 (stagioni 2019/20 → 2026/27), 12708 partite con quote medie valide. Rifit ogni 7 giorni, finestra 5 anni, xi=0.0018. Più basso = meglio (tranne accuratezza).

| Campionato | Modello | N | Log-loss | RPS | Brier | Accuratezza |
|---|---|---:|---:|---:|---:|---:|
| Tutti | Quote medie senza margine (power) | 12708 | 0.9727 | 0.1963 | 0.5783 | 53.5% |
| Tutti | Dixon-Coles attuale (xi=0.0018) | 12708 | 0.9952 | 0.2026 | 0.5920 | 52.3% |
| Tutti | Quote chiusura senza margine (power) * | 12708 | 0.9702 | 0.1956 | 0.5767 | 53.9% |
| Serie A | Quote medie senza margine (power) | 2709 | 0.9630 | 0.1910 | 0.5720 | 54.3% |
| Serie A | Dixon-Coles attuale (xi=0.0018) | 2709 | 0.9846 | 0.1971 | 0.5850 | 53.4% |
| Serie A | Quote chiusura senza margine (power) * | 2709 | 0.9607 | 0.1904 | 0.5708 | 54.7% |
| Premier League | Quote medie senza margine (power) | 2710 | 0.9696 | 0.1983 | 0.5758 | 54.3% |
| Premier League | Dixon-Coles attuale (xi=0.0018) | 2710 | 0.9895 | 0.2040 | 0.5872 | 52.8% |
| Premier League | Quote chiusura senza margine (power) * | 2710 | 0.9658 | 0.1970 | 0.5730 | 54.8% |
| Bundesliga | Quote medie senza margine (power) | 2178 | 0.9761 | 0.1983 | 0.5800 | 52.8% |
| Bundesliga | Dixon-Coles attuale (xi=0.0018) | 2178 | 1.0050 | 0.2056 | 0.5977 | 51.6% |
| Bundesliga | Quote chiusura senza margine (power) * | 2178 | 0.9741 | 0.1979 | 0.5787 | 53.3% |
| La Liga | Quote medie senza margine (power) | 2729 | 0.9696 | 0.1926 | 0.5764 | 53.8% |
| La Liga | Dixon-Coles attuale (xi=0.0018) | 2729 | 0.9930 | 0.1989 | 0.5904 | 52.1% |
| La Liga | Quote chiusura senza margine (power) * | 2729 | 0.9676 | 0.1919 | 0.5750 | 54.0% |
| Ligue 1 | Quote medie senza margine (power) | 2382 | 0.9877 | 0.2025 | 0.5888 | 52.4% |
| Ligue 1 | Dixon-Coles attuale (xi=0.0018) | 2382 | 1.0074 | 0.2085 | 0.6022 | 51.6% |
| Ligue 1 | Quote chiusura senza margine (power) * | 2382 | 0.9857 | 0.2019 | 0.5878 | 52.4% |

\* Le quote di chiusura sono valutate sulle partite che le hanno (N può differire).

## Check di accettazione

- Dixon-Coles attuale: log-loss 0.9952 (atteso 0.994 ± 0.004) → OK
- Quote senza margine: log-loss 0.9727 (atteso 0.973 ± 0.004) → OK
