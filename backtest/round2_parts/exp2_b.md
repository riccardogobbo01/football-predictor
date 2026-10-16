### 2a — sensibilità e varianti

**Decadimento oltre il range 0.002-0.005** (sensibilità: l'ottimo del range richiesto è al bordo).

| xi | MSE log-lambda 2016-18 | Δ log-loss totale | IC 95% | Stagioni migliorate |
|---:|---:|---:|---|---:|
| 0.006 | 0.01868 | +0.00168 | [+0.00060, +0.00277] | 7/8 |
| 0.008 | 0.01964 | +0.00201 | [+0.00085, +0.00317] | 7/8 |
| 0.01 | 0.02109 | +0.00219 | [+0.00099, +0.00339] | 7/8 |
| 0.015 | 0.02593 | +0.00211 | [+0.00094, +0.00329] | 6/8 |

Minimo dell'errore pre-test sull'intera griglia: xi = 0.005. Per le varianti sotto si usa xi = 0.005 (miglior valore DENTRO il range richiesto).

**Varianti** (xi fisso come sopra; ogni riga da sola vs baseline).

| Variante | Log-loss | RPS | Brier | Δ log-loss vs baseline | IC 95% | Stagioni migliorate |
|---|---:|---:|---:|---:|---|---:|
| 2a — principale (closing medio, rho=-0.08, ridge 2, xi=0.005) | 0.9817 | 0.1991 | 0.5845 | +0.00146 | [+0.00046, +0.00248] | 7/8 |
| 2a — ridge 0.5 (xi=0.005) | 0.9814 | 0.1991 | 0.5843 | +0.00169 | [+0.00060, +0.00279] | 7/8 |
| 2a — ridge 5 (xi=0.005) | 0.9820 | 0.1992 | 0.5847 | +0.00110 | [+0.00022, +0.00201] | 7/8 |
| 2a — Poisson indipendente (rho=0), xi=0.005 | 0.9817 | 0.1991 | 0.5845 | +0.00145 | [+0.00046, +0.00247] | 7/8 |
| 2a — Pinnacle in chiusura (dove disponibile), xi=0.005 | 0.9816 | 0.1991 | 0.5844 | +0.00151 | [+0.00051, +0.00253] | 7/8 |
| 2a — senza xG nello stack (sostituisce l'xG), xi=0.005 | 0.9825 | 0.1994 | 0.5850 | +0.00064 | [-0.00078, +0.00210] | 6/8 |

Nota sulla variante Pinnacle: le quote Pinnacle in chiusura mancano per metà del 2025/26 e per tutto il 2026/27; dove mancano si ricade sulla media di mercato in chiusura. La variante "senza xG" toglie xg_lmu/xg_lnu dallo stack e li sostituisce con le forze implicite: dice quanto delle informazioni xG è già contenuto nel mercato.

### 2b — Elo-Odds (Wunderlich & Memmert)

Elo per campionato in cui il "risultato" è S = P(1) + 0.5·P(X) dalle quote di chiusura senza margine (power); vantaggio casa HFA = media corrente di S nel campionato; squadra nuova = media delle 3 più deboli; feature dello stack = differenza di rating pre-partita `eo_diff` (rating casa − ospite). K scelto col criterio pre-test: errore quadratico tra punteggio atteso Elo e S nelle stagioni 2016-2018 (nessun esito, nessun dato di test).

| K | MSE(E−S) 2016-18 | Log-loss | Δ log-loss vs baseline | IC 95% | Stagioni migliorate |
|---:|---:|---:|---:|---|---:|
| 5 | 0.00841 | 0.9825 | +0.00059 | [+0.00003, +0.00116] | 7/8 |
| 10 | 0.00529 | 0.9826 | +0.00049 | [-0.00007, +0.00109] | 7/8 |
| 20 | 0.00384 | 0.9826 | +0.00048 | [-0.00015, +0.00114] | 6/8 |
| 30 | 0.00329 | 0.9825 | +0.00066 | [-0.00008, +0.00142] | 7/8 |
| 45 | 0.00286 | 0.9821 | +0.00106 | [+0.00016, +0.00198] | 6/8 |
| 60 | 0.00261 | 0.9816 | +0.00149 | [+0.00044, +0.00255] | 6/8 |
| 80 | 0.00241 | 0.9812 | +0.00198 | [+0.00080, +0.00319] | 6/8 |
| 100 | 0.00229 | 0.9808 | +0.00237 | [+0.00109, +0.00367] | 6/8 |
| 150 | 0.00214 | 0.9801 | +0.00301 | [+0.00159, +0.00444] | 6/8 |
| 200 | 0.00211 | 0.9798 | +0.00332 | [+0.00184, +0.00481] | 6/8 |
| 300 | 0.00223 | 0.9797 | +0.00340 | [+0.00191, +0.00489] | 6/8 |
| 500 | 0.00333 | 0.9809 | +0.00224 | [+0.00093, +0.00352] | 6/8 |

K scelto col criterio pre-test: **200**.

**2b — Elo-Odds K=200 — variante principale**

| Metrica | Variante | Baseline | Δ (base − variante) | IC 95% |
|---|---:|---:|---:|---|
| Log-loss 1X2 | 0.9798 | 0.9831 | +0.00332 | [+0.00184, +0.00481] |
| RPS | 0.1984 | 0.1995 | +0.00107 | [+0.00059, +0.00155] |
| Brier | 0.5831 | 0.5855 | +0.00239 | [+0.00139, +0.00341] |

(Δ positivo = variante migliore; N = 12751; stagioni migliorate: 6/8)

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0004 | -0.0016 | +0.0034 | +0.0030 | +0.0073 | +0.0055 | +0.0057 | +0.0065 |
| N | 1725 | 1826 | 1825 | 1826 | 1752 | 1752 | 1752 | 293 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0047 | +0.0038 | +0.0038 | +0.0017 | +0.0026 |

**Combinazione 2a + 2b nello stesso stack**

| Variante | Log-loss | RPS | Brier | Δ log-loss vs baseline | IC 95% | Stagioni migliorate |
|---|---:|---:|---:|---:|---|---:|
| 2a+2b — forze implicite (xi=0.005) + Elo-Odds (K=200) | 0.9801 | 0.1986 | 0.5833 | +0.00302 | [+0.00148, +0.00456] | 6/8 |
