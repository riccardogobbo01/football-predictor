# /predict — Previsioni partite

Genera previsioni statistiche complete per una o più partite.

L'utente può usare:
- `/predict Milan Inter` — previsione per una partita specifica
- `/predict serie_a` — tutto il prossimo turno di Serie A
- `/predict premier_league` — tutto il prossimo turno di Premier League
- `/predict champions_league` — prossime partite di Champions

Leghe disponibili: `serie_a`, `premier_league`, `bundesliga`, `la_liga`, `ligue_1`, `champions_league`, `europa_league`, `conference_league`

Per una partita singola:
```bash
python main.py predict "<squadra_casa>" "<squadra_trasferta>" --league <lega>
```

Per il prossimo turno di una lega:
```bash
python main.py predict --league <lega> --round next
```

La previsione include:
- Gol attesi (xG) per entrambe le squadre
- Probabilità 1X2, Over/Under 0.5 → 3.5, BTTS, clean sheet
- Punteggi più probabili (top 5)
- Tiri, corner, cartellini gialli attesi
- Contesto: ELO, forma recente, giorni di riposo, H2H, meteo, quote mercato

Se il modello non è ancora stato fittato, avvia automaticamente il fitting prima di generare le previsioni.

Se l'utente non specifica squadre né lega, chiedi quale partita o campionato vuole analizzare.
