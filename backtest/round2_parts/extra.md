### Diagnostica su Elo-Odds: il guadagno compare solo dal 2021/22?

Il guadagno di 2b (K=200) è ≈0 o negativo nel 2019/20 e 2020/21 e +0.003/+0.007 dal 2021/22. Due spiegazioni possibili: (i) cambio di fonte delle quote (Pinnacle in chiusura fino al 2018/19 nel training, media di mercato dopo); (ii) lo stack con xG si allena solo dal 2016/17 (gli xG partono dal 2014 e il DC xG ha bisogno di 2 anni di storia): per il 2019/20 ha solo 3 stagioni di training per imparare il peso di una feature rumorosa come il rating Elo-Odds.

| Prova | Log-loss | Δ log-loss [IC 95%] | Δ per stagione (2019/20 → 2026/27) |
|---|---:|---|---|
| 2b K=200 con Pinnacle in chiusura ovunque (vs baseline) | 0.9798 | +0.00330 [+0.00182, +0.00479] | -0.0006, -0.0015, +0.0032, +0.0031, +0.0073, +0.0054, +0.0057, +0.0065 |
| Stack SENZA xG, training dal 2013/14: con Elo-Odds vs senza (stessa finestra) | 0.9805 | +0.00591 [+0.00404, +0.00781] | +0.0031, +0.0021, +0.0043, +0.0051, +0.0097, +0.0096, +0.0076, +0.0061 |
| Stack senza xG + Elo-Odds (training dal 2013/14) vs baseline con xG | 0.9805 | +0.00266 [+0.00081, +0.00459] | -0.0020, -0.0055, +0.0034, +0.0036, +0.0078, +0.0039, +0.0064, +0.0099 |

Lettura: cambiare fonte non cambia il quadro (i); con più stagioni di training (ii) Elo-Odds migliora in TUTTE le stagioni, compreso il 2019/20. Il basso guadagno delle prime due stagioni è quindi compatibile con la finestra di training corta imposta dagli xG (3 stagioni nel 2019/20) più che con un difetto del segnale (non è una prova: la seconda riga cambia anche il modello di base). In produzione il modello with_xg si allena dal 2016/17 fino all'ultima stagione (circa 10 stagioni), cioè nella situazione delle stagioni recenti del backtest, dove il guadagno è più grande. **Errata (round 3, esperimento A):** allungare il training dello stack (fino a 13 stagioni) non cambia il guadagno nelle prime due stagioni, quindi la lunghezza del training non è la spiegazione; la causa non è chiarita.
