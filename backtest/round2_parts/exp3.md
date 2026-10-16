## Esperimento 3 — Ricalibrazione 1X2

Ricalibratore rifittato ogni 7 giorni su TUTTE le previsioni out-of-sample del modello di partenza per partite già concluse (finestra espansiva, dalla prima partita di test); finché le partite concluse sono meno di 600 si usa l'identità (burn-in: le prime settimane del 2019/20). Input: x1 = log(λ casa/λ ospite), x2 = λ casa + λ ospite; output: 1X2. Δ = log-loss(modello di partenza) − log-loss(ricalibrato): positivo = la ricalibrazione migliora; IC 95% bootstrap appaiato per partita.

### Ricalibrazione di: baseline

Partite in burn-in (identità): 645 su 12751.

| Ricalibratore | Log-loss | RPS | Brier | Δ log-loss vs modello di partenza [IC 95%] | Δ vs baseline [IC 95%] | Stagioni migliorate (vs partenza) |
|---|---:|---:|---:|---|---|---:|
| Ordered logit (4 parametri) | 0.9837 | 0.1996 | 0.5860 | -0.00061 [-0.00171, +0.00050] | -0.00061 [-0.00171, +0.00050] | 3/8 |
| Ordered logit flessibile (banda del pareggio dipende da gol attesi) | 0.9830 | 0.1996 | 0.5855 | +0.00010 [-0.00075, +0.00096] | +0.00010 [-0.00075, +0.00096] | 4/8 |
| Temperature scaling globale | 0.9833 | 0.1996 | 0.5856 | -0.00019 [-0.00047, +0.00010] | -0.00019 [-0.00047, +0.00010] | 2/8 |
| Temperature scaling con T separata per il pareggio | 0.9830 | 0.1995 | 0.5854 | +0.00015 [-0.00032, +0.00063] | +0.00015 [-0.00032, +0.00063] | 5/8 |
| Temperature scaling + bias sul pareggio | 0.9829 | 0.1995 | 0.5854 | +0.00021 [-0.00029, +0.00072] | +0.00021 [-0.00029, +0.00072] | 5/8 |

**Dettaglio del migliore (Temperature scaling + bias sul pareggio) vs baseline**

| Metrica | Variante | Baseline | Δ (base − variante) | IC 95% |
|---|---:|---:|---:|---|
| Log-loss 1X2 | 0.9829 | 0.9831 | +0.00021 | [-0.00029, +0.00072] |
| RPS | 0.1995 | 0.1995 | -0.00001 | [-0.00009, +0.00007] |
| Brier | 0.5854 | 0.5855 | +0.00009 | [-0.00022, +0.00039] |

(Δ positivo = variante migliore; N = 12751; stagioni migliorate: 5/8)

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0010 | +0.0001 | +0.0003 | -0.0003 | +0.0013 | +0.0006 | +0.0006 | -0.0000 |
| N | 1725 | 1826 | 1825 | 1826 | 1752 | 1752 | 1752 | 293 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0012 | -0.0003 | +0.0006 | +0.0000 | -0.0006 |

Pareggio dopo la ricalibrazione (Temperature scaling + bias sul pareggio): previsto medio 0.2507 contro reale 0.2525 (prima 0.2398).

Parametri dell'ultimo rifit (ts_b): -0.033, 0.088.

### Ricalibrazione di: migliore tra 1 e 2 (Elo-Odds K=200)

Partite in burn-in (identità): 645 su 12751.

| Ricalibratore | Log-loss | RPS | Brier | Δ log-loss vs modello di partenza [IC 95%] | Δ vs baseline [IC 95%] | Stagioni migliorate (vs partenza) |
|---|---:|---:|---:|---|---|---:|
| Ordered logit (4 parametri) | 0.9797 | 0.1984 | 0.5831 | +0.00012 [-0.00118, +0.00139] | +0.00344 [+0.00171, +0.00521] | 4/8 |
| Ordered logit flessibile (banda del pareggio dipende da gol attesi) | 0.9791 | 0.1983 | 0.5827 | +0.00073 [-0.00036, +0.00182] | +0.00406 [+0.00242, +0.00571] | 4/8 |
| Temperature scaling globale | 0.9800 | 0.1985 | 0.5833 | -0.00023 [-0.00069, +0.00024] | +0.00309 [+0.00161, +0.00458] | 1/8 |
| Temperature scaling con T separata per il pareggio | 0.9796 | 0.1985 | 0.5831 | +0.00016 [-0.00042, +0.00075] | +0.00349 [+0.00196, +0.00500] | 4/8 |
| Temperature scaling + bias sul pareggio | 0.9796 | 0.1985 | 0.5831 | +0.00024 [-0.00036, +0.00085] | +0.00357 [+0.00203, +0.00509] | 5/8 |

**Dettaglio del migliore (Ordered logit flessibile (banda del pareggio dipende da gol attesi)) vs migliore tra 1 e 2 (Elo-Odds K=200)**

| Metrica | Variante | Baseline | Δ (base − variante) | IC 95% |
|---|---:|---:|---:|---|
| Log-loss 1X2 | 0.9791 | 0.9798 | +0.00073 | [-0.00036, +0.00182] |
| RPS | 0.1983 | 0.1984 | +0.00011 | [-0.00017, +0.00040] |
| Brier | 0.5827 | 0.5831 | +0.00037 | [-0.00033, +0.00107] |

(Δ positivo = variante migliore; N = 12751; stagioni migliorate: 4/8)

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0009 | +0.0058 | -0.0016 | -0.0031 | +0.0022 | +0.0026 | -0.0002 | +0.0024 |
| N | 1725 | 1826 | 1825 | 1826 | 1752 | 1752 | 1752 | 293 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0041 | -0.0004 | -0.0004 | -0.0007 | +0.0009 |

Pareggio dopo la ricalibrazione (Ordered logit flessibile (banda del pareggio dipende da gol attesi)): previsto medio 0.2514 contro reale 0.2525 (prima 0.2400).

Parametri dell'ultimo rifit (olflex): 1.476, 0.119, 0.079, 0.203, -0.258, 0.091.

### Coerenza di punteggio consigliato e mercati derivati

**baseline + Temperature scaling + bias sul pareggio**

- Matrice riponderata (ogni cella × P_nuova/P_vecchia della sua classe di esito): 1X2 della matrice = 1X2 ricalibrato, errore massimo 3.3e-16.
- Over 2.5 (log-loss): prima 0.6748, dopo 0.6747; Δ (prima − dopo) +0.00009 [-0.00006, +0.00024]. Probabilità media prevista: 0.5421 → 0.5381 (reale 0.5341).
- BTTS (log-loss): prima 0.6838, dopo 0.6838; Δ +0.00007 [-0.00003, +0.00017]. Probabilità media: 0.5366 → 0.5393 (reale 0.5458).
- Esito consigliato (regola della produzione, soglia pareggio 0.42): cambia in 2.2% delle partite; pareggi consigliati 21.6% → 23.8% (reali 25.3%); esito giusto 50.9% → 50.4%; risultato esatto 12.09% → 12.27%.
- Senza riponderazione (si cambiano solo le tre probabilità 1X2 e si lascia la matrice com'è) la matrice resterebbe incoerente: scarto medio tra P ricalibrata e 1X2 della matrice 0.78 punti percentuali (massimo 4.1); in 0.0% delle partite l'esito più probabile della matrice non coincide con quello delle probabilità ricalibrate.

**migliore tra 1 e 2 (Elo-Odds K=200) + Ordered logit flessibile (banda del pareggio dipende da gol attesi)**

- Matrice riponderata (ogni cella × P_nuova/P_vecchia della sua classe di esito): 1X2 della matrice = 1X2 ricalibrato, errore massimo 3.3e-16.
- Over 2.5 (log-loss): prima 0.6742, dopo 0.6741; Δ (prima − dopo) +0.00010 [-0.00012, +0.00032]. Probabilità media prevista: 0.5411 → 0.5369 (reale 0.5341).
- BTTS (log-loss): prima 0.6839, dopo 0.6837; Δ +0.00014 [-0.00002, +0.00029]. Probabilità media: 0.5353 → 0.5383 (reale 0.5458).
- Esito consigliato (regola della produzione, soglia pareggio 0.42): cambia in 7.7% delle partite; pareggi consigliati 21.5% → 25.0% (reali 25.3%); esito giusto 51.2% → 50.4%; risultato esatto 11.95% → 12.03%.
- Senza riponderazione (si cambiano solo le tre probabilità 1X2 e si lascia la matrice com'è) la matrice resterebbe incoerente: scarto medio tra P ricalibrata e 1X2 della matrice 1.61 punti percentuali (massimo 10.4); in 4.0% delle partite l'esito più probabile della matrice non coincide con quello delle probabilità ricalibrate.

**Come gestirlo in produzione (proposta).** Se la ricalibrazione entrasse, non va applicata solo alle tre probabilità 1X2: va applicata alla matrice dei punteggi. Si riscala ogni cella (i, j) per P_nuova/P_vecchia dell'esito a cui appartiene (casa / pareggio / trasferta) e si rinormalizza. Così 1X2, punteggio consigliato, 5 risultati esatti, Over/Under e BTTS derivano tutti dalla stessa matrice e restano coerenti per costruzione; la forma dei punteggi dentro ciascun esito non cambia. I parametri del ricalibratore (pochi numeri) si rifittano nel job settimanale di training e si salvano in models/ (JSON), il job giornaliero li applica con numpy. La soglia REC_DRAW_THRESHOLD va riverificata dopo il cambio, perché sposta la distribuzione di P(X).
