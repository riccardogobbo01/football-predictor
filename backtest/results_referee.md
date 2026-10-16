# Backtest «come in produzione» — effetto arbitro sui gialli

Walk-forward per stagione (training dal 2016/17, test dal 2019/20), effetto arbitro con k=20 come regressore (round 5, forma b). Storico arbitri: data/referees/matches.csv (Transfermarkt 2016/17-2025/26 + football-data.org 2026/27). Arbitro noto per 18203/18230 partite dal 2016/17.

## Variante with_xg

- 12751 partite di test. Log-loss del totale gialli: senza arbitro **2.1186** → con arbitro **2.1082**.
- Δ = +0.01039, IC 95% per partita [+0.00802, +0.01284], a blocchi per settimana [+0.00795, +0.01278]; held-out 2022/23→: +0.00994 [+0.00686, +0.01296].
- MAE del totale: 1.6357 → 1.6172.
- Per stagione (Δ log-loss): 2019/20 +0.0189, 2020/21 +0.0080, 2021/22 +0.0065, 2022/23 +0.0097, 2023/24 +0.0033, 2024/25 +0.0116, 2025/26 +0.0150, 2026/27 +0.0112

**Controllo**: log-loss con arbitro 2.1082 contro 2.1085 del round 5 (tolleranza ±0.003; la differenza residua viene dal 2026/27, dove ora l'arbitro è noto per le partite già giocate) e IC a blocchi > 0 → OK.

## Variante without_xg

- 12751 partite di test. Log-loss del totale gialli: senza arbitro **2.1184** → con arbitro **2.1080**.
- Δ = +0.01043, IC 95% per partita [+0.00803, +0.01287], a blocchi per settimana [+0.00797, +0.01281]; held-out 2022/23→: +0.00989 [+0.00682, +0.01292].
- MAE del totale: 1.6340 → 1.6158.
- Per stagione (Δ log-loss): 2019/20 +0.0194, 2020/21 +0.0080, 2021/22 +0.0065, 2022/23 +0.0095, 2023/24 +0.0036, 2024/25 +0.0116, 2025/26 +0.0147, 2026/27 +0.0106

**Controllo**: IC a blocchi del guadagno > 0 → OK (variante di ripiego, non misurata nel round 5).
