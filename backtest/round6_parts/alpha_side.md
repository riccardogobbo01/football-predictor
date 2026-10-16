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
