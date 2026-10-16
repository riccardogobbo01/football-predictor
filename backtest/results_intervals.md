# Intervalli delle statistiche attese — verifica in walk-forward

**Metodo (uguale per tutte le statistiche).** Dalla distribuzione prevista dal modello (Binomiale Negativa; per i gialli la dispersione stimata è quasi nulla, quindi di fatto Poisson) si prende l'intervallo di valori interi consecutivi centrato sui valori più probabili (per ogni ampiezza la finestra di probabilità massima) la cui probabilità reale è la più vicina all'80%, a parità quella maggiore (`stats_v3.nb_interval`). Nel pannello compare con la probabilità arrotondata, ad es. «1–3 (78%)».

**Verifica.** Walk-forward per stagione (training dal 2016/17 sulle sole stagioni precedenti, test dal 2019/20; variante with_xg, parametri e dispersioni stimati nel training di ogni fold come in produzione). Per ogni partita e livello si confronta la probabilità dichiarata dall'intervallo con l'esito reale (1 se il valore osservato cade nell'intervallo). **Criterio: scarto massimo 3 punti** tra probabilità media dichiarata e frequenza reale, per squadra e totale. IC 95% dello scarto a blocchi per settimana ISO (2000 ricampionamenti).

## Tutte le stagioni di test (2019/20–2025/26)

| Statistica | Livello | N | Prob. media dichiarata | Frequenza reale | Scarto (reale − dichiarata) [IC a blocchi] | Ampiezza media | Esito |
|---|---|---:|---:|---:|---|---:|---|
| Tiri | Casa | 12751 | 80.1% | 78.3% | -1.7 [-2.5, -1.0] pp | 11.0 | ok |
| Tiri | Ospite | 12751 | 80.1% | 78.0% | -2.1 [-2.8, -1.4] pp | 10.1 | ok |
| Tiri | Squadra (casa+ospite) | 25502 | 80.1% | 78.2% | -1.9 [-2.4, -1.4] pp | 10.6 | ok |
| Tiri | Totale | 12751 | 80.0% | 78.8% | -1.2 [-1.9, -0.5] pp | 13.7 | ok |
| Tiri in porta | Casa | 12751 | 80.2% | 80.5% | +0.3 [-0.4, +0.9] pp | 5.9 | ok |
| Tiri in porta | Ospite | 12751 | 80.2% | 80.1% | -0.1 [-0.8, +0.6] pp | 5.3 | ok |
| Tiri in porta | Squadra (casa+ospite) | 25502 | 80.2% | 80.3% | +0.1 [-0.4, +0.6] pp | 5.6 | ok |
| Tiri in porta | Totale | 12751 | 80.1% | 80.3% | +0.2 [-0.5, +0.9] pp | 7.9 | ok |
| Corner | Casa | 12751 | 80.1% | 79.5% | -0.6 [-1.4, +0.2] pp | 6.7 | ok |
| Corner | Ospite | 12751 | 80.2% | 79.9% | -0.3 [-0.9, +0.5] pp | 6.0 | ok |
| Corner | Squadra (casa+ospite) | 25502 | 80.1% | 79.7% | -0.4 [-0.9, +0.1] pp | 6.4 | ok |
| Corner | Totale | 12751 | 79.9% | 79.6% | -0.3 [-1.0, +0.4] pp | 8.4 | ok |
| Gialli | Casa | 12751 | 80.3% | 82.1% | +1.8 [+1.1, +2.5] pp | 3.5 | ok |
| Gialli | Ospite | 12751 | 80.6% | 82.5% | +1.9 [+1.3, +2.6] pp | 3.7 | ok |
| Gialli | Squadra (casa+ospite) | 25502 | 80.4% | 82.3% | +1.9 [+1.3, +2.4] pp | 3.6 | ok |
| Gialli | Totale | 12751 | 80.4% | 79.6% | -0.8 [-1.5, -0.0] pp | 5.1 | ok |
| Falli | Casa | 12751 | 80.0% | 80.6% | +0.6 [-0.1, +1.3] pp | 9.1 | ok |
| Falli | Ospite | 12751 | 80.1% | 79.9% | -0.1 [-1.0, +0.7] pp | 9.2 | ok |
| Falli | Squadra (casa+ospite) | 25502 | 80.0% | 80.3% | +0.2 [-0.3, +0.7] pp | 9.2 | ok |
| Falli | Totale | 12751 | 80.0% | 80.7% | +0.7 [-0.1, +1.4] pp | 13.5 | ok |

Scarto massimo per statistica: Tiri 2.1 pp; Tiri in porta 0.3 pp; Corner 0.6 pp; Gialli 1.9 pp; Falli 0.7 pp

## Solo held-out (dal 2022/23)

| Statistica | Livello | N | Prob. media dichiarata | Frequenza reale | Scarto (reale − dichiarata) [IC a blocchi] | Ampiezza media | Esito |
|---|---|---:|---:|---:|---|---:|---|
| Tiri | Casa | 7374 | 80.1% | 77.9% | -2.2 [-3.1, -1.2] pp | 11.2 | ok |
| Tiri | Ospite | 7374 | 80.1% | 77.8% | -2.3 [-3.4, -1.4] pp | 10.3 | ok |
| Tiri | Squadra (casa+ospite) | 14748 | 80.1% | 77.8% | -2.3 [-3.0, -1.5] pp | 10.8 | ok |
| Tiri | Totale | 7374 | 80.0% | 78.9% | -1.2 [-2.2, -0.3] pp | 14.0 | ok |
| Tiri in porta | Casa | 7374 | 80.3% | 81.4% | +1.1 [+0.2, +2.1] pp | 5.9 | ok |
| Tiri in porta | Ospite | 7374 | 80.2% | 80.3% | +0.1 [-0.8, +1.0] pp | 5.3 | ok |
| Tiri in porta | Squadra (casa+ospite) | 14748 | 80.2% | 80.9% | +0.6 [-0.0, +1.3] pp | 5.6 | ok |
| Tiri in porta | Totale | 7374 | 80.1% | 81.5% | +1.3 [+0.3, +2.3] pp | 8.0 | ok |
| Corner | Casa | 7374 | 80.1% | 79.6% | -0.5 [-1.6, +0.6] pp | 6.8 | ok |
| Corner | Ospite | 7374 | 80.1% | 80.5% | +0.3 [-0.6, +1.2] pp | 6.0 | ok |
| Corner | Squadra (casa+ospite) | 14748 | 80.1% | 80.1% | -0.1 [-0.8, +0.6] pp | 6.4 | ok |
| Corner | Totale | 7374 | 79.8% | 79.8% | -0.1 [-1.0, +0.8] pp | 8.4 | ok |
| Gialli | Casa | 7374 | 80.4% | 82.4% | +2.0 [+1.1, +3.0] pp | 3.5 | ok |
| Gialli | Ospite | 7374 | 80.7% | 82.7% | +1.9 [+1.1, +2.8] pp | 3.8 | ok |
| Gialli | Squadra (casa+ospite) | 14748 | 80.5% | 82.5% | +2.0 [+1.2, +2.7] pp | 3.6 | ok |
| Gialli | Totale | 7374 | 80.3% | 79.0% | -1.3 [-2.3, -0.4] pp | 5.2 | ok |
| Falli | Casa | 7374 | 80.0% | 80.7% | +0.7 [-0.2, +1.6] pp | 9.0 | ok |
| Falli | Ospite | 7374 | 80.1% | 79.5% | -0.6 [-1.6, +0.4] pp | 9.1 | ok |
| Falli | Squadra (casa+ospite) | 14748 | 80.0% | 80.1% | +0.0 [-0.6, +0.7] pp | 9.1 | ok |
| Falli | Totale | 7374 | 80.1% | 80.4% | +0.4 [-0.6, +1.3] pp | 13.4 | ok |

Scarto massimo per statistica: Tiri 2.3 pp; Tiri in porta 1.3 pp; Corner 0.5 pp; Gialli 2.0 pp; Falli 0.7 pp

## Tiri: alpha unico per squadra (prima versione) contro alpha separato per casa e ospite (versione finale)

Con un solo alpha per squadra l'ospite stava a −3,0 punti (tutte le stagioni) e −3,4 (held-out), fuori dal criterio dei 3 punti; la causa era la varianza reale dei tiri dell'ospite, circa il 13% sopra quella del modello. Con alpha separati (momenti sul training del fold) tutti i livelli rientrano. Le tabelle sopra sono quelle finali (alpha separato).

| Insieme | Livello | Alpha unico: dichiarata → reale (scarto) | Alpha separato: dichiarata → reale (scarto) |
|---|---|---|---|
| Tutte le stagioni | Casa | 80.1% → 79.1% (-1.0 pp) | 80.1% → 78.3% (-1.7 pp) |
| Tutte le stagioni | Ospite | 80.1% → 77.0% (-3.0 pp) | 80.1% → 78.0% (-2.1 pp) |
| Tutte le stagioni | Squadra (casa+ospite) | 80.1% → 78.1% (-2.0 pp) | 80.1% → 78.2% (-1.9 pp) |
| Tutte le stagioni | Totale | 80.0% → 78.8% (-1.2 pp) | 80.0% → 78.8% (-1.2 pp) |
| Held-out (dal 2022/23) | Casa | 80.0% → 78.8% (-1.3 pp) | 80.1% → 77.9% (-2.2 pp) |
| Held-out (dal 2022/23) | Ospite | 80.1% → 76.7% (-3.4 pp) | 80.1% → 77.8% (-2.3 pp) |
| Held-out (dal 2022/23) | Squadra (casa+ospite) | 80.1% → 77.7% (-2.3 pp) | 80.1% → 77.8% (-2.3 pp) |
| Held-out (dal 2022/23) | Totale | 80.0% → 78.9% (-1.2 pp) | 80.0% → 78.9% (-1.2 pp) |

## Tiri: alpha separato per casa e ospite — verifica che non peggiori il modello attuale

12751 partite di test (dal 2019/20). Alpha medi del training (ultimo fold): attuale per squadra 0.0397; casa 0.0360, ospite 0.0453. L'alpha del totale non cambia (0.0086).

Δ = attuale − alpha separato (positivo = migliora), IC 95% a blocchi per settimana ISO.

| Metrica | Attuale | Alpha separato | Δ tutte [IC a blocchi] | Δ held-out (dal 2022/23) [IC a blocchi] |
|---|---:|---:|---|---|
| Log-loss per squadra | 2.87173 | 2.87117 | +0.00056 [+0.00022, +0.00090] | +0.00059 [+0.00012, +0.00106] |
| Log-loss del totale | 3.12988 | 3.12988 | +0.00000 [+0.00000, +0.00000] | +0.00000 [+0.00000, +0.00000] |
| Log-loss Over/Under per squadra (linee 10.5/12.5/14.5) | 0.56667 | 0.56654 | +0.00013 [+0.00005, +0.00021] | +0.00020 [+0.00008, +0.00031] |
| Log-loss Over/Under del totale (linee 22.5/24.5/26.5) | 0.62185 | 0.62185 | +0.00000 [+0.00000, +0.00000] | +0.00000 [+0.00000, +0.00000] |
| Copertura nominale 80% per squadra (quantili, riferimento) | 0.8210 | 0.8223 | +0.0013 [+0.0004, +0.0023] | |
| Copertura nominale 80% del totale (quantili, riferimento) | 0.8206 | 0.8206 | +0.0000 [+0.0000, +0.0000] | |
| Log-loss «chi fa più tiri» (copula, ρ per lega ristimato) | 0.71821 | 0.71812 | +0.00009 [+0.00000, +0.00018] | +0.00023 [+0.00011, +0.00035] |

**Esito:** nessuna metrica peggiora con IC a blocchi che esclude lo zero.


## Dettaglio per campionato (tutte le stagioni di test)

| Statistica | D1 | E0 | F1 | I1 | SP1 |
|---|---:|---:|---:|---:|---:|
| Tiri (squadra / totale, pp) | -1.0 / -1.1 | -2.5 / -1.3 | -2.3 / -1.0 | -1.7 / -2.0 | -1.9 / -0.6 |
| Tiri in porta (squadra / totale, pp) | -0.2 / +0.7 | +0.2 / +0.6 | -0.4 / -1.0 | +0.4 / -0.0 | +0.4 / +0.6 |
| Corner (squadra / totale, pp) | -0.6 / -1.4 | -0.9 / +0.1 | +0.3 / +0.5 | +0.0 / -1.3 | -0.9 / +0.4 |
| Gialli (squadra / totale, pp) | -0.2 / -3.1 | -0.1 / -3.4 | +2.1 / +0.9 | +5.2 / +2.6 | +2.0 / -1.2 |
| Falli (squadra / totale, pp) | +0.1 / -0.6 | +0.4 / +0.6 | -0.1 / +0.0 | +0.7 / +1.6 | -0.0 / +1.5 |

## Dettaglio per stagione (scarto in pp, squadra / totale)

| Statistica | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Tiri | +0.2 / -0.7 | -2.4 / -1.8 | -1.9 / -1.2 | -1.5 / -0.6 | -3.0 / -0.8 | -1.3 / -1.2 | -2.4 / -0.8 | -7.6 / -8.8 |
| Tiri in porta | -1.2 / -0.9 | +0.5 / -0.7 | -1.2 / -2.4 | +0.7 / +2.0 | +0.4 / +1.1 | +1.0 / +1.2 | +0.8 / +1.9 | -1.5 / -4.3 |
| Corner | -2.7 / -2.5 | -0.1 / +0.1 | +0.1 / +0.1 | +0.7 / +1.6 | -0.9 / +1.1 | -0.1 / -1.3 | +0.3 / -1.1 | -1.3 / -3.8 |
| Gialli | +0.4 / -1.8 | +3.3 / +2.6 | +1.4 / -1.1 | +1.3 / -2.3 | +0.1 / -2.3 | +2.2 / -2.7 | +4.1 / +1.7 | +3.2 / +0.7 |
| Falli | +0.6 / -0.1 | +1.1 / +1.6 | -0.2 / +1.8 | +0.2 / +0.8 | +1.4 / +1.3 | -0.8 / -0.7 | +0.1 / +0.7 | -4.1 / -3.5 |
