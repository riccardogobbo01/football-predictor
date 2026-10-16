### Conclusione della fase 1 e parametri per la produzione

| Statistica | η | γ | Δ log-loss totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Verdetto |
|---|---:|---:|---|---|---|
| Tiri | 0.10 | 1.0 | +0.02073 [+0.01523, +0.02607] | +0.01368 [+0.00744, +0.02065] | migliora |
| Tiri in porta (modello I con GAP) | 0.05 | 1.0 | +0.00679 [+0.00494, +0.00868] | +0.00759 [+0.00518, +0.00997] | migliora |

Il γ ottimo è il limite naturale 1.0 per entrambe le statistiche (l'aggiornamento dei rating dell'altro campo vale quanto quello del campo giocato). L'η ottimo è interno alla griglia esplorata (0.10 per i tiri, 0.05 per i tiri in porta, con il guadagno che scende per η più alti): la regola dell'estensione (solo se η = 0.20) non è scattata e non c'è stata alcuna seconda estensione. Rispetto alla configurazione del round 6 (η = 0.05, γ = 0.5) il guadagno sul totale aumenta di +0.00596 per i tiri e +0.00156 per i tiri in porta (IC a blocchi esclude lo zero in entrambi i casi sulle stagioni complessive; sull'held-out dei tiri l'IC della differenza include lo zero: +0.00307 [-0.00065, +0.00678]). Questi sono i parametri messi in produzione (`config.GAP_PARAMS`).
