## Controlli anti-leakage (esperimento 2)

**1a. DC sui lambda impliciti (Premier League, xi=0.005).** Lambda impliciti sostituiti con numeri casuali per tutte le partite dal 2024-02-03; primo rifit successivo: 2024-02-05. Differenza massima delle feature (log-gol attesi) per le 227 partite precedenti a quel rifit: casa 0.00e+00, ospite 0.00e+00 (deve essere 0). Per le 972 partite successive la differenza massima è 0.936 (il test non è vuoto).

**1b. Elo-Odds (K=200).** Quote di chiusura permutate a caso tra tutte le partite dal 2024-02-03 in poi. Rating pre-partita diversi per le partite fino al 2024-02-03 compreso: 0 su 21005 (deve essere 0); dopo quella data cambiano 4509 su 4533 (il test non è vuoto).

**2. Placebo.** Lambda impliciti permutati a caso tra le partite dello stesso campionato e stagione, stessa pipeline (xi=0.005): Δ log-loss vs baseline -0.00012 [-0.00045, +0.00021] (con i lambda veri: +0.00146). Il guadagno sparisce, quindi non viene da un artefatto della pipeline.

Esito dei controlli: perturbazione DC OK, perturbazione Elo-Odds OK, placebo OK.
