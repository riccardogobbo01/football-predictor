## Tabella riassuntiva

Baseline = stack Poisson (DC gol, DC tiri in porta, pi-ratings, DC xG con ridge 2; training dal 2016/17), 12751 partite 2019/20 → 2026-10-12. Δ = log-loss(baseline) − log-loss(variante): positivo = meglio. Riferimento: quote di chiusura senza margine (power) = **0.9701** (con normalizzazione semplice 0.9704); divario baseline − chiusura = 0.0130. «Divario recuperato» = Δ / divario.

| Variante | Log-loss | Δ vs baseline | IC 95% | Stagioni migliorate | Δ 2019/20-2021/22 | Δ 2022/23→oggi | Distanza dalle quote di chiusura | Divario recuperato |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| *Quote di chiusura (power)* | 0.9701 | +0.01305 | — | — | — | — | 0.0000 | 100% |
| Baseline (stack + xG ridge) | 0.9831 | +0.00000 | — | — | +0.0000 | +0.0000 | +0.0130 | 0.0% |
| E1 1a — dummy porte chiuse (DC + regressione) | 0.9828 | +0.00031 | [-0.00015, +0.00079] | 5/8 | +0.0006 | +0.0001 | +0.0127 | 2.4% |
| E1 1a-ii — dummy solo nella regressione | 0.9827 | +0.00038 | [-0.00009, +0.00086] | 5/8 | +0.0009 | -0.0000 | +0.0127 | 2.9% |
| E1 1b — intercette di lega | 0.9835 | -0.00041 | [-0.00071, -0.00012] | 2/8 | -0.0005 | -0.0003 | +0.0135 | -3.1% |
| E1 1a+1b | 0.9832 | -0.00012 | [-0.00067, +0.00044] | 4/8 | +0.0001 | -0.0003 | +0.0132 | -0.9% |
| E2 2a — forze implicite, xi=0.005 (ridge 2) | 0.9817 | +0.00146 | [+0.00046, +0.00248] | 7/8 | +0.0015 | +0.0014 | +0.0116 | 11.2% |
| E2 2a — xi=0.010 (oltre il range, sensibilità) | 0.9809 | +0.00219 | [+0.00099, +0.00339] | 7/8 | +0.0020 | +0.0023 | +0.0109 | 16.8% |
| E2 2a — ridge 0.5 | 0.9814 | +0.00169 | [+0.00060, +0.00279] | 7/8 | +0.0017 | +0.0017 | +0.0114 | 12.9% |
| E2 2a — Pinnacle | 0.9816 | +0.00151 | [+0.00051, +0.00253] | 7/8 | +0.0016 | +0.0015 | +0.0115 | 11.6% |
| E2 2a — Poisson indipendente | 0.9817 | +0.00145 | [+0.00046, +0.00247] | 7/8 | +0.0015 | +0.0014 | +0.0116 | 11.1% |
| E2 2a — senza xG nello stack | 0.9825 | +0.00064 | [-0.00078, +0.00210] | 6/8 | +0.0003 | +0.0009 | +0.0124 | 4.9% |
| E2 2b — Elo-Odds K=60 | 0.9816 | +0.00149 | [+0.00044, +0.00255] | 6/8 | +0.0004 | +0.0023 | +0.0116 | 11.4% |
| E2 2b — Elo-Odds K=200 (scelto) | 0.9798 | +0.00332 | [+0.00184, +0.00481] | 6/8 | +0.0005 | +0.0054 | +0.0097 | 25.5% |
| E2 2b — Elo-Odds K=300 | 0.9797 | +0.00340 | [+0.00191, +0.00489] | 6/8 | +0.0003 | +0.0057 | +0.0096 | 26.1% |
| E2 2a+2b | 0.9801 | +0.00302 | [+0.00148, +0.00456] | 6/8 | -0.0001 | +0.0053 | +0.0100 | 23.1% |
| E3 baseline + temperature scaling + bias pareggio | 0.9829 | +0.00021 | [-0.00029, +0.00072] | 5/8 | -0.0002 | +0.0005 | +0.0128 | 1.6% |
| E3 baseline + temperature scaling, T pareggio separata | 0.9830 | +0.00015 | [-0.00032, +0.00063] | 5/8 | -0.0003 | +0.0005 | +0.0129 | 1.2% |
| E3 baseline + ordered logit flessibile | 0.9830 | +0.00010 | [-0.00075, +0.00096] | 4/8 | -0.0003 | +0.0004 | +0.0129 | 0.8% |
| E3 Elo-Odds K=200 + ordered logit flessibile | 0.9791 | +0.00406 | [+0.00242, +0.00571] | 6/8 | +0.0016 | +0.0058 | +0.0090 | 31.1% |
| E3 Elo-Odds K=200 + temperature scaling + bias | 0.9796 | +0.00357 | [+0.00203, +0.00509] | 6/8 | +0.0004 | +0.0059 | +0.0095 | 27.3% |
| C1 — 2a + 2b (i due positivi significativi) | 0.9801 | +0.00302 | [+0.00148, +0.00456] | 6/8 | -0.0001 | +0.0053 | +0.0100 | 23.1% |
| C2 — 2b + 1a (Elo-Odds + porte chiuse) | 0.9791 | +0.00407 | [+0.00250, +0.00568] | 7/8 | +0.0021 | +0.0055 | +0.0090 | 31.2% |
| C3 — 2a + 2b + 1a (tutti i positivi, anche non significativi) | 0.9793 | +0.00385 | [+0.00225, +0.00549] | 7/8 | +0.0016 | +0.0055 | +0.0092 | 29.5% |
| C2 + ricalibrazione (ordered logit flessibile) | 0.9782 | +0.00492 | [+0.00318, +0.00668] | 7/8 | +0.0026 | +0.0066 | +0.0081 | 37.7% |
| C2 + ricalibrazione (temperature scaling + bias pareggio) | 0.9788 | +0.00432 | [+0.00268, +0.00596] | 7/8 | +0.0018 | +0.0061 | +0.0087 | 33.1% |
| C2 + ricalibrazione (temperature scaling con T pareggio separata) | 0.9789 | +0.00426 | [+0.00262, +0.00588] | 7/8 | +0.0018 | +0.0061 | +0.0088 | 32.6% |
