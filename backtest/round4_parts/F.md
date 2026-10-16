## Esperimento F — Coppe: gare di ritorno

### Plausibilità dell'Elo ricostruito

Confronto tra il mio Elo a fine dati (2026-09) e il ranking attuale di clubelo.com (749 club): 492 club con abbinamento di nome sicuro (somiglianza ≥ 0.9) e partite nel 2025/26 o dopo. Correlazione di Pearson 0.423, di Spearman 0.360; pendenza ClubElo/mio Elo 0.40. Le scale non coincidono: i coefficienti si stimano comunque dai dati.

Primi 6 club per Elo ricostruito (mio / ClubElo): FC Barcelona 2078 / Barcelona 2032; Arsenal FC 2074 / Arsenal 2045; Manchester City 2039 / Man City 2024; Paris Saint-Germain 2028 / Paris SG 1969; Real Madrid 2020 / Real Madrid 1980; Inter Milan 1965 / Internazionale 1938.

### Campione

Partite delle fasi principali di CL/EL/UCOL 2012/13-2025/26 con punteggio e Elo: 5197 (finali escluse). Nel test 2016/17-2025/26: **3885 partite**, di cui **501 gare di ritorno** (validazione 2019/20-2021/22: 121; held-out 2022/23-2025/26: 380), 501 andate, 34 gare uniche a eliminazione diretta, 2849 partite dei gironi.

Partite ai supplementari riconosciute (minuti > 95): 51 nel test, di cui 50 gare di ritorno e 1 gare uniche; la classe 1X2 dei 90' è ricostruita con la regola scritta prima ed escluse dal training dei gol. Partite senza minuti nel dataset (supplementari non controllabili): 767 nel test, di cui 111 tra le gare di ritorno.

Log-loss 1X2 del baseline (modello Elo riallenato in walk-forward, Elo ricostruito) su tutte le 3885 partite del test: **0.9839**; sulle sole gare di ritorno: 1.0463. Non è confrontabile col 0.965 di `cups_model.json` (Elo diverso, insieme di partite diverso).

### Varianti (ogni forma da sola vs baseline)

Δ = log-loss(baseline) − log-loss(variante). «Tutte» = tutte le partite del test (la variante cambia solo le gare di ritorno, il resto varia di poco per il riallenamento); «ritorni» = solo gare di ritorno.

| Forma | Log-loss (tutte) | Δ tutte [IC a blocchi] | Δ ritorni [IC per partita] | IC a blocchi ritorni | Δ ritorni validazione | Δ ritorni held-out [IC a blocchi] |
|---|---:|---|---|---|---:|---|
| F1 — g lineare (clip ±3) | 0.9834 | +0.00051 [-0.00024, +0.00134] | +0.00507 [-0.00133, +0.01169] | [-0.00038, +0.01072] | -0.00240 | +0.00744 [+0.00093, +0.01422] |
| F2 — segno di g | 0.9835 | +0.00047 [-0.00042, +0.00143] | +0.00496 [-0.00205, +0.01217] | [-0.00166, +0.01167] | -0.00835 | +0.00920 [+0.00176, +0.01698] |
| F3 — due pendenze (g>0, g<0) | 0.9837 | +0.00022 [-0.00058, +0.00108] | +0.00362 [-0.00320, +0.01057] | [-0.00225, +0.00986] | -0.00391 | +0.00602 [-0.00123, +0.01323] |

Scelta sulle validazione (Δ su tutte le partite di validazione, parità entro 0.0002 → la più semplice): **F1 — g lineare (clip ±3)** (Δ validazione -0.00026); scegliendo sul Δ delle sole gare di ritorno in validazione sarebbe F1 — g lineare (clip ±3). Verdetto (Δ sulle gare di ritorno held-out, IC a blocchi): **migliora**.

Dettaglio della variante scelta, gare di ritorno: n = 501 (validazione 121, held-out 380); Δ +0.00507 [IC per partita -0.00133, +0.01169; IC a blocchi -0.00038, +0.01072]. Con così poche gare di ritorno gli intervalli sono larghi.

Coefficienti (log-gol attesi) del fit su tutte le stagioni fino al 2025/26, per illustrazione: casa elo_diff +0.188, g -0.055; ospite elo_diff -0.185, g +0.010; rho +0.029.

| Stagione | 2016/17 | 2017/18 | 2018/19 | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Gare di ritorno | 44 | 44 | 44 | 20 | 44 | 57 | 58 | 58 | 66 | 66 |
| Δ log-loss sui ritorni | +0.012 | +0.030 | -0.004 | -0.020 | -0.008 | +0.008 | -0.007 | +0.005 | +0.009 | +0.011 |
