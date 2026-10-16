## Esperimento D — Valore della rosa Transfermarkt

Dati: dataset dcaribou/transfermarkt-datasets (file `player_valuations.csv.gz`, `clubs.csv.gz`, `players.csv.gz`, `competitions.csv.gz`, scaricati il 2026-10-16 dal bucket pubblico del progetto, ultima modifica 2026-09-05; ultima valutazione nei dati: 2026-06-12). Abbinamento nomi: tabella esplicita `backtest/transfermarkt_aliases.py` (176 squadre dei 5 campionati dal 2012/13; controllo di copertura superato: nessuna squadra senza alias).

### Copertura e affidabilità dei valori (data 1 agosto, finestra 365 giorni)

Club-stagione 2019/20 → oggi: 776; non affidabili (< 12 giocatori valutati): 12.

| Lega | club-stagione non affidabili (2019/20 →) |
|---|---|
| Serie A | Cremonese 2025/26 (11), Frosinone 2026/27 (3) |
| Premier League | Coventry 2026/27 (9), Hull 2026/27 (11) |
| Bundesliga | Elversberg 2026/27 (4), Paderborn 2026/27 (2), Schalke 04 2026/27 (4) |
| La Liga | La Coruna 2026/27 (1), Malaga 2026/27 (1), Santander 2026/27 (2) |
| Ligue 1 | Le Mans 2026/27 (2), Troyes 2026/27 (3) |

Giocatori valutati per club (mediana tra club affidabili): 35; valore mediano di una rosa: 202 M€.

### Griglia di 8 configurazioni (ogni riga da sola vs baseline v6)

| Variante | Log-loss | Δ tutte (IC per partita) | Δ tutte (IC a blocchi) | Δ validazione | Δ held-out (IC a blocchi) | Stagioni migliorate |
|---|---:|---|---|---:|---|---:|
| D — data jul, finestra 240 g, F1 | 0.9798 | +0.00004 [-0.00013, +0.00022] | [-0.00013, +0.00021] | +0.00018 | -0.00006 [-0.00030, +0.00016] | 5/8 |
| D — data jul, finestra 240 g, F2 | 0.9799 | -0.00005 [-0.00031, +0.00021] | [-0.00030, +0.00021] | +0.00012 | -0.00017 [-0.00043, +0.00009] | 4/8 |
| D — data jul, finestra 365 g, F1 | 0.9798 | +0.00004 [-0.00013, +0.00021] | [-0.00013, +0.00021] | +0.00018 | -0.00007 [-0.00030, +0.00016] | 5/8 |
| D — data jul, finestra 365 g, F2 | 0.9799 | -0.00005 [-0.00031, +0.00020] | [-0.00031, +0.00020] | +0.00012 | -0.00018 [-0.00044, +0.00008] | 4/8 |
| D — data aug, finestra 240 g, F1 | 0.9798 | +0.00005 [-0.00015, +0.00026] | [-0.00014, +0.00025] | +0.00023 | -0.00007 [-0.00034, +0.00018] | 5/8 |
| D — data aug, finestra 240 g, F2 | 0.9798 | +0.00000 [-0.00022, +0.00024] | [-0.00022, +0.00023] | +0.00019 | -0.00013 [-0.00043, +0.00016] | 3/8 |
| D — data aug, finestra 365 g, F1 | 0.9798 | +0.00005 [-0.00015, +0.00025] | [-0.00014, +0.00024] | +0.00022 | -0.00008 [-0.00034, +0.00017] | 5/8 |
| D — data aug, finestra 365 g, F2 | 0.9798 | -0.00001 [-0.00023, +0.00022] | [-0.00023, +0.00022] | +0.00018 | -0.00015 [-0.00045, +0.00014] | 4/8 |

Scelta sulle validazione (parità entro 0.0002 → la più semplice): **D — data jul, finestra 240 g, F1** (Δ validazione +0.00018). Verdetto: **non distinguibile dal rumore**.

**D — data jul, finestra 240 g, F1**

| Insieme | N | Δ log-loss | IC 95% per partita | IC 95% a blocchi per settimana |
|---|---:|---:|---|---|
| tutte le stagioni | 12751 | +0.00004 | [-0.00013, +0.00022] | [-0.00013, +0.00021] |
| validazione 2019/20-2021/22 | 5376 | +0.00018 | [-0.00006, +0.00041] | [-0.00007, +0.00042] |
| held-out 2022/23→ | 7375 | -0.00006 | [-0.00031, +0.00018] | [-0.00030, +0.00016] |

Log-loss 0.9798 (baseline 0.9798); Δ RPS +0.00002; Δ Brier +0.00003.

| Stagione | 2019/20 | 2020/21 | 2021/22 | 2022/23 | 2023/24 | 2024/25 | 2025/26 | 2026/27 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Δ log-loss | +0.0001 | +0.0002 | +0.0003 | -0.0003 | -0.0001 | +0.0001 | -0.0000 | +0.0002 |

| Lega | Serie A | Premier League | Bundesliga | La Liga | Ligue 1 |
|---|---:|---:|---:|---:|---:|
| Δ log-loss | -0.0000 | -0.0000 | +0.0000 | +0.0003 | -0.0001 |

### Guadagno per sottoinsieme (variante scelta)

Insiemi disgiunti: (1) partite con almeno una neopromossa (squadra assente dallo stesso campionato nella stagione precedente); (2) restanti partite in cui entrambe le squadre hanno giocato meno di 8 partite nella stagione (prime 8 giornate); (3) resto.

| Sottoinsieme | N | Δ log-loss | IC 95% per partita | IC 95% a blocchi | Δ held-out |
|---|---:|---:|---|---|---:|
| neopromosse (almeno una squadra) | 3410 | -0.00016 | [-0.00065, +0.00032] | [-0.00067, +0.00034] | -0.00030 |
| restanti prime 8 giornate | 2195 | +0.00049 | [+0.00021, +0.00077] | [+0.00028, +0.00070] | +0.00038 |
| resto | 7146 | -0.00000 | [-0.00018, +0.00019] | [-0.00019, +0.00019] | -0.00009 |
