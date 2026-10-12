# Backtest walk-forward — Statistiche attese (tiri, corner, gialli)

Test: 2019-08-09 → 2026-09-20, 12708 partite (stagioni dal 2019/20) con tutte le statistiche. Modello stimato stagione per stagione sulle sole stagioni precedenti (dal 2016/17, tutte le leghe insieme); metodo a medie rifatto ogni settimana. Totale = Binomiale Negativa con alpha stimato a momenti sul training.

## Confronto modello vs metodo a medie

| Statistica | Metodo | Corr. per squadra | Corr. differenza casa−ospite | MAE totale | Copertura 80% | Log-loss O/U (media linee) |
|---|---|---:|---:|---:|---:|---:|
| Tiri | Medie (Poisson sul totale) | 0.471 | 0.498 | 4.505 | 0.818 | 0.6356 |
| Tiri | Medie (NB, alpha del modello) | 0.471 | 0.498 | 4.505 | 0.818 | 0.6338 |
| Tiri | **Modello con xG** | 0.506 | 0.533 | 4.491 | 0.818 | 0.6342 |
| Tiri | Modello senza xG (ripiego) | 0.505 | 0.533 | 4.491 | 0.817 | 0.6350 |
| Tiri | _alpha NB medio_ | | | | | 0.0091 |
| Corner | Medie (Poisson sul totale) | 0.307 | 0.330 | 2.697 | 0.838 | 0.6537 |
| Corner | Medie (NB, alpha del modello) | 0.307 | 0.330 | 2.697 | 0.838 | 0.6525 |
| Corner | **Modello con xG** | 0.360 | 0.393 | 2.683 | 0.841 | 0.6471 |
| Corner | Modello senza xG (ripiego) | 0.360 | 0.392 | 2.680 | 0.842 | 0.6469 |
| Corner | _alpha NB medio_ | | | | | 0.0131 |
| Gialli | Medie (Poisson sul totale) | 0.237 | 0.139 | 1.649 | 0.864 | 0.5918 |
| Gialli | Medie (NB, alpha del modello) | 0.237 | 0.139 | 1.649 | 0.864 | 0.5918 |
| Gialli | **Modello con xG** | 0.262 | 0.187 | 1.636 | 0.867 | 0.5886 |
| Gialli | Modello senza xG (ripiego) | 0.262 | 0.188 | 1.634 | 0.867 | 0.5886 |
| Gialli | _alpha NB medio_ | | | | | 0.0015 |

## Log-loss delle linee Over/Under (più basso = meglio)

| Statistica | Linea | Medie (Poisson) | Medie (NB) | Modello con xG | Modello senza xG |
|---|---:|---:|---:|---:|---:|
| Tiri | 23.5 | 0.6568 | 0.6560 | 0.6565 | 0.6573 |
| Tiri | 25.5 | 0.6597 | 0.6578 | 0.6582 | 0.6592 |
| Tiri | 27.5 | 0.5904 | 0.5876 | 0.5879 | 0.5884 |
| Corner | 8.5 | 0.6659 | 0.6644 | 0.6592 | 0.6588 |
| Corner | 9.5 | 0.6929 | 0.6917 | 0.6863 | 0.6860 |
| Corner | 10.5 | 0.6649 | 0.6639 | 0.6593 | 0.6590 |
| Corner | 11.5 | 0.5910 | 0.5900 | 0.5838 | 0.5836 |
| Gialli | 2.5 | 0.5381 | 0.5381 | 0.5328 | 0.5328 |
| Gialli | 3.5 | 0.6586 | 0.6585 | 0.6534 | 0.6533 |
| Gialli | 4.5 | 0.6458 | 0.6458 | 0.6442 | 0.6440 |
| Gialli | 5.5 | 0.5249 | 0.5249 | 0.5241 | 0.5241 |

## Confronto con il backtest di riferimento

| Statistica | Metrica | Riferimento | Questo backtest | Esito |
|---|---|---:|---:|---|
| Tiri | Corr. squadra, medie | 0.475 | 0.471 | OK |
| Tiri | Corr. squadra, modello | 0.508 | 0.506 | OK |
| Tiri | Corr. differenza, medie | 0.506 | 0.498 | OK |
| Tiri | Corr. differenza, modello | 0.535 | 0.533 | OK |
| Tiri | Copertura 80% (modello) | 0.820 | 0.818 | OK |
| Corner | Corr. squadra, medie | 0.316 | 0.307 | OK |
| Corner | Corr. squadra, modello | 0.361 | 0.360 | OK |
| Corner | Corr. differenza, medie | 0.339 | 0.330 | OK |
| Corner | Corr. differenza, modello | 0.393 | 0.393 | OK |
| Corner | Copertura 80% (modello) | 0.840 | 0.841 | OK |
| Gialli | Corr. squadra, medie | 0.242 | 0.237 | OK |
| Gialli | Corr. squadra, modello | 0.262 | 0.262 | OK |
| Gialli | Copertura 80% (modello) | 0.870 | 0.867 | OK |

## Stabilità per stagione (correlazione per squadra: modello − medie)

| Stagione | N | Tiri | Corner | Gialli |
|---|---:|---:|---:|---:|
| 2019/20 | 1725 | +0.023 | +0.049 | +0.010 |
| 2020/21 | 1826 | +0.042 | +0.058 | +0.007 |
| 2021/22 | 1826 | +0.044 | +0.073 | +0.041 |
| 2022/23 | 1826 | +0.033 | +0.034 | +0.029 |
| 2023/24 | 1752 | +0.023 | +0.047 | +0.032 |
| 2024/25 | 1751 | +0.053 | +0.063 | +0.031 |
| 2025/26 | 1752 | +0.037 | +0.050 | +0.050 |
| 2026/27 | 250 | +0.084 | +0.079 | +0.048 |

## Controlli

- Numero di partite: 12708 (riferimento 12403) → OK
- Tiri — Corr. squadra, medie: 0.471 (rif. 0.475, tolleranza ±0.015) → OK
- Tiri — Corr. squadra, modello: 0.506 (rif. 0.508, tolleranza ±0.015) → OK
- Tiri — Corr. differenza, medie: 0.498 (rif. 0.506, tolleranza ±0.015) → OK
- Tiri — Corr. differenza, modello: 0.533 (rif. 0.535, tolleranza ±0.015) → OK
- Tiri — Copertura 80% (modello): 0.818 (rif. 0.820, tolleranza ±0.03) → OK
- Corner — Corr. squadra, medie: 0.307 (rif. 0.316, tolleranza ±0.015) → OK
- Corner — Corr. squadra, modello: 0.360 (rif. 0.361, tolleranza ±0.015) → OK
- Corner — Corr. differenza, medie: 0.330 (rif. 0.339, tolleranza ±0.015) → OK
- Corner — Corr. differenza, modello: 0.393 (rif. 0.393, tolleranza ±0.015) → OK
- Corner — Copertura 80% (modello): 0.841 (rif. 0.840, tolleranza ±0.03) → OK
- Gialli — Corr. squadra, medie: 0.237 (rif. 0.242, tolleranza ±0.015) → OK
- Gialli — Corr. squadra, modello: 0.262 (rif. 0.262, tolleranza ±0.015) → OK
- Gialli — Copertura 80% (modello): 0.867 (rif. 0.870, tolleranza ±0.03) → OK
