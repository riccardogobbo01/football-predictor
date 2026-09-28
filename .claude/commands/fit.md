# /fit — Ri-fitta il modello predittivo

Ri-addestra il modello Dixon-Coles per un campionato specifico.

Da usare quando:
- Sono stati caricati molti nuovi dati (aggiornamento stagionale)
- Le previsioni sembrano meno accurate del solito
- Si vuole aggiornare i parametri del modello

Uso:
- `/fit` — ri-fitta Serie A (default)
- `/fit serie_a`
- `/fit premier_league`
- `/fit all` — ri-fitta tutti i campionati

Per un singolo campionato:
```bash
python main.py fit --league <lega>
```

Per tutti i campionati, eseguili in sequenza:
```bash
python main.py fit --league serie_a
python main.py fit --league premier_league
python main.py fit --league bundesliga
python main.py fit --league la_liga
python main.py fit --league ligue_1
```

Il fitting mostra: numero di squadre, home advantage (λ), correlazione (ρ).
Il modello è pronto quando mostra "✓ Modello fittato".

Nota: il fitting richiede almeno 5 partite con risultati nel database. Se i dati sono insufficienti, esegui prima `/update`.
