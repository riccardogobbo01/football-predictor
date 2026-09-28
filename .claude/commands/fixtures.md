# /fixtures — Prossime partite

Mostra le prossime partite programmate nel database.

L'utente può specificare:
- `/fixtures` — tutte le partite dei prossimi 7 giorni
- `/fixtures serie_a` — solo Serie A
- `/fixtures premier_league` — solo Premier League
- `/fixtures champions_league` — solo Champions League
- `/fixtures 14` — prossimi 14 giorni (numero = giorni in avanti)

Leghe disponibili: `serie_a`, `premier_league`, `bundesliga`, `la_liga`, `ligue_1`, `champions_league`, `europa_league`, `conference_league`

Esegui il comando appropriato:

```bash
# Tutte le partite, 7 giorni
python main.py fixtures

# Con filtro lega
python main.py fixtures --league <lega>

# Con filtro giorni
python main.py fixtures --days <giorni>

# Con entrambi
python main.py fixtures --league <lega> --days <giorni>
```

Se non ci sono partite, suggerisci di eseguire `/update` per scaricare il calendario aggiornato.
