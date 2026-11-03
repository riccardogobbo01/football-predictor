## Caso di studio: Serie A 2026/27 (98 partite giocate)

Simulazione walk-forward con parametri scelti in validazione (N1: k=160, N2: k=160). Il 2026/27 non entra in nessuna scelta.

| Modello | Log-loss 1X2 | Log-loss Over 2,5 | Pareggi previsti | Over 2,5 previsto | Gol previsti a partita | 1 previsto | 2 previsto |
|---|---:|---:|---:|---:|---:|---:|---:|
| v6 (baseline) | 0.8868 | 0.6731 | 24.4% | 52.3% | 2.78 | 43.2% | 32.3% |
| N1 (k=160) | 0.8896 | 0.6721 | 24.2% | 53.3% | 2.83 | 42.3% | 33.5% |
| N2 (k=160) | 0.8886 | 0.6723 | 24.3% | 52.7% | 2.80 | 42.9% | 32.8% |
| Mercato (chiusura media, senza margine; 98 partite 1X2, 98 Over/Under) | 0.8835 | 0.6725 | – | 52.9% | – | – | – |
| **Reale** | | | **16.3%** | **60.2%** | **3.15** | **48.0%** | **35.7%** |

**Sensibilità a k, Serie A 2026/27 (descrittiva: la scelta di k resta quella della validazione)**

| Variante | Log-loss 1X2 | Log-loss Over 2,5 | Pareggi previsti | Over 2,5 previsto | Gol previsti a partita |
|---|---:|---:|---:|---:|---:|
| N1, k=10 | 0.9021 | 0.6755 | 24.0% | 54.8% | 2.89 |
| N1, k=20 | 0.8987 | 0.6741 | 24.0% | 54.6% | 2.89 |
| N1, k=40 | 0.8951 | 0.6729 | 24.0% | 54.3% | 2.87 |
| N1, k=80 | 0.8919 | 0.6722 | 24.1% | 53.8% | 2.85 |
| N1, k=160 | 0.8896 | 0.6721 | 24.2% | 53.3% | 2.83 |
| N1, k=320 | 0.8882 | 0.6723 | 24.3% | 52.9% | 2.81 |
| N2, k=10 | 0.8927 | 0.6716 | 24.2% | 53.3% | 2.83 |
| N2, k=20 | 0.8919 | 0.6716 | 24.2% | 53.2% | 2.82 |
| N2, k=40 | 0.8909 | 0.6718 | 24.2% | 53.1% | 2.82 |
| N2, k=80 | 0.8897 | 0.6720 | 24.3% | 52.9% | 2.81 |
| N2, k=160 | 0.8886 | 0.6723 | 24.3% | 52.7% | 2.80 |
| N2, k=320 | 0.8878 | 0.6725 | 24.4% | 52.5% | 2.79 |
| Oracolo a posteriori (R casa 1.07, R ospite 1.21: non utilizzabile) | 0.8821 | 0.6640 | 22.5% | 60.6% | 3.15 |

Andamento di R e z della Serie A 2026/27 (N1, k=160) all'inizio di ogni giornata (valori usati per prevedere le partite di quella giornata):

| Giornata | Partite già giocate | R casa | R ospite | z casa | z ospite | Filtro N2 attivo (casa / ospite) |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 0 | 1.000 | 1.000 | +0.00 | +0.00 | no / no |
| 2 | 10 | 0.988 | 0.997 | -0.76 | -0.18 | no / no |
| 3 | 20 | 0.974 | 1.006 | -1.30 | +0.27 | no / no |
| 4 | 30 | 0.978 | 1.030 | -0.92 | +1.15 | no / no |
| 5 | 40 | 0.993 | 1.058 | -0.28 | +2.00 | no / sì |
| 6 | 50 | 0.994 | 1.040 | -0.21 | +1.31 | no / no |
| 7 | 60 | 1.002 | 1.023 | +0.08 | +0.71 | no / no |
| 8 | 70 | 1.006 | 1.043 | +0.20 | +1.31 | no / no |
| 9 | 80 | 1.007 | 1.057 | +0.25 | +1.69 | no / no |
| 10 | 90 | 1.021 | 1.083 | +0.67 | +2.45 | no / sì |

**Tutte le leghe, 2026/27** (parametri scelti in validazione):

| Lega | Partite | Gol reali | Gol previsti v6 | N1 | N2 | Δ ll 1X2 v6 − N1 | Δ ll 1X2 v6 − N2 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Serie A | 98 | 3.15 | 2.78 | 2.83 | 2.80 | -0.00282 | -0.00181 |
| Premier League | 89 | 2.72 | 2.86 | 2.86 | 2.86 | -0.00255 | +0.00039 |
| Bundesliga | 72 | 3.50 | 3.16 | 3.26 | 3.26 | -0.00113 | -0.00073 |
| La Liga | 108 | 3.01 | 2.84 | 2.89 | 2.84 | -0.00035 | -0.00007 |
| Ligue 1 | 80 | 3.05 | 2.98 | 2.97 | 2.98 | -0.00221 | +0.00000 |
