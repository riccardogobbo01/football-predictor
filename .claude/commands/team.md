# /team — Profilo squadra

Mostra il profilo completo di una squadra: ELO, forma recente, statistiche di stagione.

Uso:
- `/team Juventus` — profilo Juventus (default: Serie A)
- `/team Arsenal premier_league` — profilo Arsenal in Premier League
- `/team Bayern bundesliga`

Esegui:
```bash
python main.py team "<nome_squadra>" --league <lega>
```

Il profilo include:
- ELO corrente (da ClubElo)
- Forma recente 0-1 (media ponderata EMA ultimi 5 match)
- Partite giocate in stagione
- Gol fatti/subiti per partita
- xG for/against (se disponibili da Understat)

Se il nome squadra non viene trovato, prova varianti del nome (es. "Inter Milan" invece di "Inter", "Man City" invece di "Manchester City").
