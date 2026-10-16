## Esperimento 2 — Forze implicite dalle quote passate

### Gol attesi impliciti: copertura e gestione dei dati mancanti

- Quote 1X2 di chiusura: 25534/25538 partite (2012/13 → oggi; Pinnacle in chiusura fino al 2018/19, media di mercato in chiusura dal 2019/20). Senza 1X2 (4 partite) il lambda implicito è NaN e la partita non entra nei rifit.
- Quote Over/Under 2.5: per le stagioni 2012/13-2018/19 la chiusura O/U non esiste nei file; si usa la media pre-chiusura dei bookmaker (BbAv>2.5 / BbAv<2.5), dal 2019/20 la chiusura media (AvgC>2.5 / AvgC<2.5). Partite con O/U da chiusura: 12755, da media pre-chiusura: 12782, **senza alcuna quota O/U: 1** su 25538 (di cui 1 nel periodo di test, 12751 partite).
- Gestione: dove manca l'O/U si risolve con le sole tre probabilità 1X2 (2 incognite, 2 equazioni indipendenti: sistema esattamente identificato, stesso solver). Con una sola partita interessata la scelta è irrilevante.
- Rimozione del margine: metodo power (il migliore dell'esperimento 0, a pari merito con Shin; differenze ≤ 0.0004).
- Ricostruzione: Poisson con correlazione Dixon-Coles fissa rho = -0.08 (scelta guardando solo la capacità di riprodurre le probabilità di mercato, minimo dell'errore su una griglia 0 / −0.05 / −0.08 / −0.10 / −0.13 / −0.16: nessun esito di partita coinvolto). Con Poisson indipendente (rho=0) il pareggio di mercato è sottostimato di 1.6 punti percentuali in media; con rho=−0.08 di circa 0.6.

Qualità della ricostruzione (rho=-0.08): errore medio assoluto su P(1)/P(X)/P(2): 0.0024/0.0057/0.0033; gol attesi impliciti medi 1.574 - 1.212 contro gol reali 1.545 - 1.225.

### 2a — Modello di forza DC sui lambda impliciti → feature dello stack

Come per gli xG: DC senza tau (attacco / difesa / casa), finestra 5 anni, rifit settimanale, ridge = 2, target continuo = lambda implicito della partita. Le feature `mk_lmu`, `mk_lnu` (log gol attesi del modello di forza) si aggiungono a quelle del baseline (DC gol, tiri in porta, pi-ratings, xG) nelle due regressioni di Poisson; training dello stack dal 2016/17, test dal 2019/20, come il baseline.

**Scelta del decadimento xi.** Tre criteri, mostrati per trasparenza: (i) errore di previsione del lambda implicito nelle stagioni 2016-2018 (precedenti al test; nessun esito, nessun dato di test); (ii) Δ log-loss dello stack nelle stagioni 2019/20-2021/22 (periodo di scelta); (iii) Δ log-loss nelle stagioni 2022/23 → oggi (valutazione fuori dal periodo di scelta).

| xi | MSE log-lambda 2016-18 | Δ log-loss 2019-21 | Δ log-loss 2022→ | Δ log-loss totale [IC 95%] |
|---:|---:|---:|---:|---|
| 0.002 | 0.02069 | +0.00092 | +0.00055 | +0.00071 [-0.00004, +0.00145] |
| 0.003 | 0.01926 | +0.00110 | +0.00081 | +0.00093 [+0.00010, +0.00178] |
| 0.004 | 0.01864 | +0.00132 | +0.00113 | +0.00121 [+0.00029, +0.00215] |
| 0.005 | 0.01850 | +0.00153 | +0.00141 | +0.00146 [+0.00046, +0.00248] |

Scelto xi = **0.005** con il criterio (i) (pre-test, indipendente dal periodo di valutazione); il criterio (ii) avrebbe scelto xi = 0.005.

| Variante | Log-loss | RPS | Brier | Δ log-loss vs baseline | IC 95% | Stagioni migliorate |
|---|---:|---:|---:|---:|---|---:|
| 2a — stack + forze implicite (xi=0.002) | 0.9824 | 0.1993 | 0.5850 | +0.00071 | [-0.00004, +0.00145] | 6/8 |
| 2a — stack + forze implicite (xi=0.003) | 0.9822 | 0.1993 | 0.5848 | +0.00093 | [+0.00010, +0.00178] | 6/8 |
| 2a — stack + forze implicite (xi=0.004) | 0.9819 | 0.1992 | 0.5846 | +0.00121 | [+0.00029, +0.00215] | 7/8 |
| 2a — stack + forze implicite (xi=0.005) | 0.9817 | 0.1991 | 0.5845 | +0.00146 | [+0.00046, +0.00248] | 7/8 |

**2a — stack + forze implicite (xi=0.005) — variante principale**

| Metrica | Variante | Baseline | Δ (base − variante) | IC 95% |
|---|---:|---:|---:|---|
| Log-loss 1X2 | 0.9817 | 0.9831 | +0.00146 | [+0.00046, +0.00248] |
| RPS | 0.1991 | 0.1995 | +0.00038 | [+0.00007, +0.00070] |
| Brier | 0.5845 | 0.5855 | +0.00101 | [+0.00033, +0.00170] |

(Δ positivo = variante migliore; N = 12751; stagioni migliorate: 7/8)

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0015 | +0.0017 | +0.0014 | +0.0005 | +0.0026 | -0.0011 | +0.0033 | +0.0036 |
| N | 1725 | 1826 | 1825 | 1826 | 1752 | 1752 | 1752 | 293 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0010 | +0.0003 | +0.0007 | +0.0031 | +0.0021 |
