# Round 6 — tiri in porta, miglioramenti dei modelli delle statistiche e nuovi mercati derivati (solo backtest)

**Nulla della produzione è stato toccato** (`stats_model.STATS` non è stato modificato: le statistiche nuove usano specifiche locali di `backtest/round6_lib.py`). Stesse regole dei round 3-5: criteri scritti prima, validazione 2019/20-2021/22, held-out dal 2022/23, IC bootstrap per partita e a blocchi per settimana ISO.

---
## Criteri fissati PRIMA di calcolare i risultati

Questa sezione è stata scritta prima di eseguire qualsiasi variante del round 6. Cosa è stato guardato prima: solo struttura e disponibilità dei dati (colonne HTHG/HTAG, HST/AST, HF/AF nei CSV di football-data.co.uk; moduli esistenti `stats_model`, `stats_baseline`, `refeffect`). Nessuna log-loss e nessun esito sono stati usati per scegliere nulla.

**Regole comuni (come round 3-5).** Validazione = 2019/20, 2020/21, 2021/22; held-out = 2022/23 in poi. I parametri si scelgono solo sulle validazione: configurazione con la metrica primaria più bassa in validazione; parità entro 0.0002 → la più semplice (ordine in tabella). Δ = metrica(baseline) − metrica(variante) per le perdite, variante − baseline per correlazioni e per la copertura quando il confronto è «più alto = meglio»; positivo = variante migliore. IC 95% bootstrap appaiato (5000 ricampionamenti) per partita e a blocchi per settimana ISO; per le correlazioni solo a blocchi (1000 ricampionamenti). Nessuna griglia viene estesa dopo aver visto i risultati.

**Insieme di valutazione.** Tutte le partite di campionato dal 2019/20 con HS, AS, HST, AST, HC, AC, HY, AY, HF, AF presenti e previsioni del baseline disponibili (stesso insieme per ogni statistica e variante; K1 usa le partite con HTHG/HTAG).

**Baseline = modelli attuali (variante with_xg), rifatti in walk-forward per stagione** (training dal 2016/17 sulle stagioni precedenti, test dal 2019/20): tiri (proprie = Poisson attacco/difesa sui tiri, ausiliaria = tiri in porta), corner (ausiliaria = tiri), gialli (ausiliaria = falli) **con l'effetto arbitro già in produzione** (regressore log R, k=20, storico `data/referees/matches.csv`). Due regressioni di Poisson (casa, ospite) con alpha 1e-3 su feature standardizzate; totale = Binomiale Negativa con alpha a momenti.

**Distribuzione per squadra del baseline.** La produzione pubblica oggi solo la distribuzione del totale. Per i conteggi della singola squadra, il baseline usa NB(media della squadra, alpha_squadra) con **un alpha_squadra unico per statistica** (casa e ospite insieme), stimato a momenti sulle partite di training con le medie in campione del fold: alpha = max(Σ((y − m)² − m)/Σ m², 1e-4). Per il totale: NB(mh + ma, alpha_totale) come in produzione.

**Metriche, per ogni statistica, sia PER SQUADRA sia sul TOTALE:**
1. log-loss della distribuzione del conteggio (−log p(y); per squadra, media tra i conteggi della squadra di casa e dell'ospite della stessa partita);
2. MAE della media prevista;
3. correlazione tra media prevista e osservato (per squadra: casa e ospite insieme);
4. copertura degli intervalli centrali all'80% e al 90% (estremi = quantili 0.10/0.90 e 0.05/0.95 della distribuzione; con conteggi discreti la copertura effettiva è ≥ nominale: si riporta lo scarto dal nominale);
5. calibrazione delle probabilità Over/Under: log-loss medio sulle linee, errore di calibrazione atteso (ECE, 10 classi di pari numerosità sulle probabilità di tutte le linee) e scarto medio (probabilità media prevista − frequenza osservata).
Linee fissate: tiri totale 23.5/25.5/27.5, squadra 10.5/12.5/14.5; tiri in porta totale 7.5/8.5/9.5/10.5, squadra 3.5/4.5/5.5; corner totale 8.5/9.5/10.5/11.5, squadra 3.5/4.5/5.5/6.5; gialli totale 2.5/3.5/4.5/5.5, squadra 1.5/2.5; falli totale 22.5/24.5/26.5, squadra 10.5/12.5/14.5.

**Metrica primaria dei miglioramenti J**: log-loss del conteggio TOTALE (la metrica del sito); secondaria: log-loss per squadra. **Verdetto «migliora»**: Δ primario held-out > 0 con IC a blocchi che esclude lo zero **e** Δ secondario held-out non negativo (punto); «peggiora» se il Δ primario è negativo con IC che esclude lo zero; altrimenti «non distinguibile dal rumore». Per J3 la secondaria è la log-loss 1X2 di «chi ha più» (P casa > ospite, pareggio, P ospite > casa).

---

### I — Modello dei tiri in porta per squadra

Stessa struttura degli altri: Poisson attacco/difesa sui tiri in porta (HST/AST, xi 0.0018, finestra 5 anni, ridge 1, senza tau — nuove colonne `sot_lh/sot_la`, stesse impostazioni di `build_stat_features`), ausiliaria = Poisson sui tiri (tiri_lh/la), feature comuni (DC gol, xG, pi-ratings, |pi|, gol attesi e |gol attesi|, dummy di lega), Binomiale Negativa. **Baseline semplice**: tiri previsti dal modello dei tiri attuale × quota storica in porta della squadra = (Σ HST + 100·p_L)/(Σ HS + 100) sulle ultime 20 partite della squadra (tiri propri, qualsiasi campo), con p_L = quota in porta media del campionato nelle partite precedenti (100 = tiri equivalenti di shrinkage); stessa distribuzione NB con alpha a momenti. Una sola configurazione, nessun parametro da scegliere.

### J — Miglioramenti di tiri, tiri in porta e corner (uno alla volta, ciascuno vs il baseline della statistica; per i tiri in porta il baseline è il modello I)

- **J1**: si aggiungono tre feature di stato di gara: `eo_diff` (Elo-Odds di produzione) e log dei gol attesi di casa e ospite del modello 1X2 v6 (previsioni walk-forward per stagione dal 2019/20; per il 2016/17-2018/19 le previsioni in campione del primo fold, come per l'arbitro).
- **J2a**: alpha della Binomiale Negativa per lega (stimato a momenti sulle partite di training di quella lega nel fold), per il totale e per squadra. **J2b**: alpha per squadra con shrinkage: alpha_squadra = (n·alpha_squadra_stimata + 30·alpha_lega)/(n + 30), n = partite della squadra nel training; per il totale dell'alpha di una partita è la media dei due alpha delle squadre calcolati sul totale; si riporta sempre, anche se J2a non migliora.
- **J3**: modello congiunto delle due squadre con copula gaussiana: marginali NB(media, alpha_squadra), correlazione ρ stimata sul passato come correlazione tra i due punteggi normali di una trasformazione integrale di probabilità randomizzata (seme fisso) dei residui sulle partite di training del fold. Griglia: ρ unica per statistica oppure ρ per lega (ordine di semplicità: unica prima). Si calcolano esattamente (integrazione numerica deterministica, nessun Monte Carlo) la distribuzione del totale e la distribuzione di casa − ospite. Il totale è confrontato con la NB sul totale del baseline; «chi ha più» con l'indipendenza (ρ = 0). 
- **J4**: GAP ratings (Wheatcroft) per statistica: quattro rating per squadra (attacco e difesa in casa e in trasferta) aggiornati partita dopo partita: previsione casa = μ_casa + A^casa_i + D^trasf_j, previsione ospite = μ_trasf + A^trasf_j + D^casa_i (μ = media di lega del campo, previsione minima 0.5); errore e = osservato − previsto, aggiornamento A_i^casa += η e_c, D_j^trasf += η e_c, A_j^trasf += η e_o, D_i^casa += η e_o, e una frazione γ degli stessi aggiornamenti sui rating dell'altro campo; rating per campionato, nessun azzeramento tra le stagioni, squadre nuove a 0. Le feature (log previsione casa e ospite) **sostituiscono** le forze attuali della statistica; l'ausiliaria resta com'è. Griglia η ∈ {0.02, 0.05} × γ ∈ {0, 0.5} (4 configurazioni; ordine: γ=0 prima, η crescente), scelta per statistica sulle validazione.

### K — Nuovi mercati derivati

- **K1 — primo tempo** (punteggi HTHG/HTAG). Gol attesi dal modello 1X2 v6 (μ casa, ν ospite, stesse previsioni di J1). Tre varianti (ordine di semplicità): **(a)** quota di gol del primo tempo unica per lega s_L = Σ gol 1T/Σ gol FT nelle partite di training; **(b)** quote separate casa/ospite per lega; **(c)** regressione di Poisson sui gol del primo tempo di ciascuna squadra con esposizione = gol attesi FT di quella squadra, dummy di lega e log dei gol attesi totali (μ + ν) come covariata (verifica se la quota dipende dai gol attesi totali). Gol del primo tempo: Poisson indipendenti (nessuna correzione Dixon-Coles). Mercati: 1X2 al riposo, Over 0.5 e Over 1.5 del primo tempo (gol totali 1T). Riferimento: «climatologia» = medie di lega dei gol del primo tempo di casa e ospite, senza informazioni sulla partita. Valutazione: log-loss dei tre mercati (1X2 / O0.5 / O1.5), ECE e scarto medio; scelta tra (a)-(c) sulle validazione per log-loss media dei tre mercati.
- **K2 — «chi fa più», handicap**: dai modelli congiunti di J3 (copula con la ρ scelta; per i gialli la stessa struttura con baseline gialli e arbitro): «chi fa più corner» e «chi prende più gialli» (tre esiti: casa, pareggio, ospite) e handicap ±1.5 sui corner (casa − ospite > 1.5, e ospite − casa > 1.5). Confronto con l'indipendenza (ρ = 0, stesse marginali). Metriche: log-loss e ECE.
- **K3 — falli** per squadra e totali: stessa struttura (Poisson attacco/difesa sui falli HF/AF, ausiliaria = gialli, feature comuni, NB). **K3a** senza arbitro; **K3b** con effetto arbitro sui falli (log R_f calcolato come per i gialli con falli osservati e attesi, k = 20, regressore). Baseline semplice = metodo «a medie» di `stats_baseline` applicato ai falli.

### Proposte per il pannello
Per le varianti che migliorano si propone come mostrarle. Per tiri e tiri in porta il pannello mostrerà valore atteso e intervallo all'80% per ciascuna squadra e per il totale (come richiesto), con le linee Over/Under dei totali.


## Esperimenti I e J — tiri in porta (nuovo modello) e miglioramenti di tiri, tiri in porta e corner

Insieme di valutazione: 12751 partite di campionato dal 2019/20 (stesso insieme per tutte le statistiche e varianti). Validazione 5377 partite, held-out 7374.

Controllo: la matrice delle feature del baseline dei tiri coincide con `stats_model.design` di produzione.

### I — Modello dei tiri in porta per squadra (HST/AST)

**Baseline semplice: tiri previsti × quota in porta storica**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.1811 | 1.7773 | 0.440 | 0.873 | 0.941 | 0.5929 | 0.0056 | -0.0049 |
| Totale | 2.5410 | 2.4758 | 0.278 | 0.854 | 0.931 | 0.6300 | 0.0069 | -0.0065 |

**Nuovo modello dei tiri in porta (struttura degli altri modelli)**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.1777 | 1.7803 | 0.447 | 0.870 | 0.940 | 0.5910 | 0.0133 | +0.0116 |
| Totale | 2.5436 | 2.4949 | 0.271 | 0.851 | 0.928 | 0.6313 | 0.0186 | +0.0186 |

Δ del nuovo modello rispetto al baseline semplice (positivo = nuovo modello migliore):

| Variante | Δ log-loss totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ log-loss per squadra (tutte) [IC a blocchi] | Δ per squadra held-out | Δ MAE tot. | Δ corr. tot. [IC] | Δ corr. squadra [IC] | Copertura 80% tot. (var.) | Copertura 90% tot. (var.) | ECE O/U tot. (base → var.) | Verdetto |
|---|---|---|---|---:|---:|---|---|---:|---:|---|---|
| I — modello dei tiri in porta vs baseline semplice | -0.00264 [-0.00700, +0.00152] | -0.00600 [-0.01022, -0.00164] | +0.00340 [+0.00101, +0.00563] | +0.00126 | -0.0191 | -0.0067 [-0.0191, +0.0059] | +0.0068 [+0.0026, +0.0110] | 0.851 | 0.928 | 0.0069 → 0.0186 | peggiora |

### J — tiri: modello dei tiri attuale come baseline

**Baseline**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.8867 | 3.5105 | 0.505 | 0.821 | 0.908 | 0.5738 | 0.0102 | -0.0096 |
| Totale | 3.1506 | 4.4924 | 0.302 | 0.818 | 0.907 | 0.6343 | 0.0152 | -0.0151 |

Δ = baseline − variante (positivo = variante migliore); IC 95% a blocchi per settimana.

| Variante | Δ log-loss totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ log-loss per squadra (tutte) [IC a blocchi] | Δ per squadra held-out | Δ MAE tot. | Δ corr. tot. [IC] | Δ corr. squadra [IC] | Copertura 80% tot. (var.) | Copertura 90% tot. (var.) | ECE O/U tot. (base → var.) | Verdetto |
|---|---|---|---|---:|---:|---|---|---:|---:|---|---|
| J1 — + eo_diff e gol attesi v6 | -0.00300 [-0.00530, -0.00071] | +0.00223 [-0.00005, +0.00456] | -0.00031 [-0.00197, +0.00134] | +0.00423 | -0.0121 | -0.0053 [-0.0103, -0.0005] | -0.0001 [-0.0025, +0.0022] | 0.818 | 0.907 | 0.0152 → 0.0139 | non distinguibile dal rumore |
| J2a — alpha per lega | +0.00021 [-0.00058, +0.00100] | -0.00113 [-0.00218, -0.00003] | -0.00029 [-0.00060, +0.00001] | -0.00049 | +0.0000 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0.818 | 0.906 | 0.0152 → 0.0151 | peggiora |
| J2b — alpha per squadra con shrinkage (30) | -0.00131 [-0.00250, -0.00011] | -0.00221 [-0.00373, -0.00069] | -0.00299 [-0.00409, -0.00191] | -0.00280 | +0.0000 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0.819 | 0.906 | 0.0152 → 0.0151 | peggiora |
| J4 — GAP η=0.02, γ=0.0 | -0.00453 [-0.00888, +0.00029] | -0.00020 [-0.00532, +0.00658] | -0.00505 [-0.00807, -0.00166] | -0.00335 | -0.0273 | -0.0155 [-0.0238, -0.0066] | -0.0091 [-0.0124, -0.0060] | 0.817 | 0.910 | 0.0152 → 0.0162 | non distinguibile dal rumore |
| J4 — GAP η=0.05, γ=0.0 | +0.00617 [+0.00167, +0.01099] | +0.00446 [-0.00092, +0.01108] | +0.00307 [+0.00005, +0.00635] | +0.00245 | +0.0094 | +0.0107 [+0.0016, +0.0202] | +0.0017 [-0.0017, +0.0047] | 0.819 | 0.909 | 0.0152 → 0.0127 | non distinguibile dal rumore |
| J4 — GAP η=0.02, γ=0.5 | +0.00236 [-0.00184, +0.00687] | +0.00458 [-0.00042, +0.01097] | -0.00056 [-0.00352, +0.00271] | +0.00030 | +0.0050 | +0.0039 [-0.0040, +0.0125] | -0.0025 [-0.0056, +0.0004] | 0.818 | 0.907 | 0.0152 → 0.0151 | non distinguibile dal rumore |
| J4 — GAP η=0.05, γ=0.5 (scelta in validazione) | +0.01477 [+0.01009, +0.01967] | +0.01061 [+0.00511, +0.01730] | +0.00982 [+0.00671, +0.01312] | +0.00834 | +0.0489 | +0.0338 [+0.0245, +0.0434] | +0.0115 [+0.0081, +0.0144] | 0.819 | 0.907 | 0.0152 → 0.0131 | migliora |
| J3 — copula gaussiana, ρ unica | -0.00033 [-0.00096, +0.00029] | -0.00010 [-0.00080, +0.00062] | +0.00000 [+0.00000, +0.00000] | +0.00000 | +0.0002 | -0.0000 [-0.0001, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0.819 | 0.908 | 0.0152 → 0.0213 | non distinguibile dal rumore |
| J3 — copula gaussiana, ρ per lega (scelta in validazione) | -0.00002 [-0.00101, +0.00094] | -0.00102 [-0.00218, +0.00017] | +0.00000 [+0.00000, +0.00000] | +0.00000 | +0.0002 | -0.0000 [-0.0001, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0.819 | 0.907 | 0.0152 → 0.0206 | non distinguibile dal rumore |

**J3, «chi ha più tiri»** (esito casa / pari / ospite) con ρ per lega: log-loss 0.7232 contro 0.7251 con l'indipendenza (ρ = 0): Δ +0.00185, IC a blocchi [+0.00091, +0.00280], held-out +0.00147 [+0.00021, +0.00274]. Probabilità medie previste casa/pari/ospite 0.584/0.050/0.366, frequenze osservate 0.592/0.049/0.359.

ρ stimata (ultimo fold): D1 -0.189, E0 -0.248, F1 -0.213, I1 -0.129, SP1 -0.208.

### J — sot: modello I dei tiri in porta come baseline

**Baseline**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.1777 | 1.7803 | 0.447 | 0.870 | 0.940 | 0.5910 | 0.0133 | +0.0116 |
| Totale | 2.5436 | 2.4949 | 0.271 | 0.851 | 0.928 | 0.6313 | 0.0186 | +0.0186 |

Δ = baseline − variante (positivo = variante migliore); IC 95% a blocchi per settimana.

| Variante | Δ log-loss totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ log-loss per squadra (tutte) [IC a blocchi] | Δ per squadra held-out | Δ MAE tot. | Δ corr. tot. [IC] | Δ corr. squadra [IC] | Copertura 80% tot. (var.) | Copertura 90% tot. (var.) | ECE O/U tot. (base → var.) | Verdetto |
|---|---|---|---|---:|---:|---|---|---:|---:|---|---|
| J1 — + eo_diff e gol attesi v6 | +0.00126 [-0.00006, +0.00263] | +0.00077 [-0.00111, +0.00255] | +0.00327 [+0.00216, +0.00441] | +0.00390 | +0.0103 | +0.0015 [-0.0015, +0.0046] | +0.0056 [+0.0035, +0.0077] | 0.850 | 0.927 | 0.0186 → 0.0080 | non distinguibile dal rumore |
| J2a — alpha per lega | +0.00011 [-0.00023, +0.00045] | +0.00004 [-0.00039, +0.00048] | -0.00007 [-0.00031, +0.00017] | -0.00019 | +0.0000 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0.850 | 0.927 | 0.0186 → 0.0183 | non distinguibile dal rumore |
| J2b — alpha per squadra con shrinkage (30) | -0.00084 [-0.00160, -0.00008] | -0.00052 [-0.00152, +0.00050] | -0.00158 [-0.00234, -0.00077] | -0.00173 | +0.0000 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0.852 | 0.929 | 0.0186 → 0.0177 | non distinguibile dal rumore |
| J4 — GAP η=0.02, γ=0.0 | -0.00213 [-0.00386, -0.00045] | -0.00157 [-0.00385, +0.00079] | -0.00111 [-0.00200, -0.00023] | -0.00104 | -0.0077 | -0.0042 [-0.0090, +0.0008] | -0.0014 [-0.0028, +0.0000] | 0.852 | 0.927 | 0.0186 → 0.0231 | non distinguibile dal rumore |
| J4 — GAP η=0.05, γ=0.0 | +0.00186 [-0.00000, +0.00369] | +0.00254 [+0.00021, +0.00488] | +0.00113 [+0.00016, +0.00209] | +0.00137 | +0.0047 | +0.0054 [+0.0001, +0.0111] | +0.0018 [+0.0002, +0.0036] | 0.852 | 0.928 | 0.0186 → 0.0181 | migliora |
| J4 — GAP η=0.02, γ=0.5 | +0.00202 [+0.00045, +0.00357] | +0.00285 [+0.00077, +0.00510] | +0.00087 [+0.00002, +0.00169] | +0.00115 | +0.0049 | +0.0067 [+0.0024, +0.0116] | +0.0017 [+0.0003, +0.0031] | 0.852 | 0.928 | 0.0186 → 0.0185 | migliora |
| J4 — GAP η=0.05, γ=0.5 (scelta in validazione) | +0.00523 [+0.00343, +0.00706] | +0.00605 [+0.00374, +0.00832] | +0.00314 [+0.00217, +0.00416] | +0.00368 | +0.0150 | +0.0148 [+0.0096, +0.0205] | +0.0052 [+0.0035, +0.0069] | 0.854 | 0.929 | 0.0186 → 0.0141 | migliora |
| J3 — copula gaussiana, ρ unica | +0.00031 [+0.00008, +0.00056] | +0.00026 [-0.00005, +0.00056] | +0.00000 [+0.00000, +0.00000] | +0.00000 | +0.0024 | -0.0000 [-0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0.851 | 0.927 | 0.0186 → 0.0147 | non distinguibile dal rumore |
| J3 — copula gaussiana, ρ per lega (scelta in validazione) | +0.00055 [+0.00010, +0.00102] | +0.00045 [-0.00012, +0.00102] | +0.00000 [+0.00000, +0.00000] | +0.00000 | +0.0024 | -0.0000 [-0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0.851 | 0.928 | 0.0186 → 0.0147 | non distinguibile dal rumore |

**J3, «chi ha più sot»** (esito casa / pari / ospite) con ρ per lega: log-loss 0.8506 contro 0.8507 con l'indipendenza (ρ = 0): Δ +0.00009, IC a blocchi [-0.00017, +0.00036], held-out -0.00011 [-0.00045, +0.00023]. Probabilità medie previste casa/pari/ospite 0.526/0.109/0.365, frequenze osservate 0.531/0.112/0.357.

ρ stimata (ultimo fold): D1 -0.068, E0 -0.071, F1 -0.044, I1 +0.011, SP1 +0.009.

### J — corner: modello dei corner attuale come baseline

**Baseline**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.3299 | 2.0909 | 0.360 | 0.858 | 0.933 | 0.5995 | 0.0098 | +0.0093 |
| Totale | 2.6157 | 2.6820 | 0.154 | 0.841 | 0.921 | 0.6472 | 0.0174 | +0.0174 |

Δ = baseline − variante (positivo = variante migliore); IC 95% a blocchi per settimana.

| Variante | Δ log-loss totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ log-loss per squadra (tutte) [IC a blocchi] | Δ per squadra held-out | Δ MAE tot. | Δ corr. tot. [IC] | Δ corr. squadra [IC] | Copertura 80% tot. (var.) | Copertura 90% tot. (var.) | ECE O/U tot. (base → var.) | Verdetto |
|---|---|---|---|---:|---:|---|---|---:|---:|---|---|
| J1 — + eo_diff e gol attesi v6 | -0.00056 [-0.00116, +0.00005] | +0.00023 [-0.00047, +0.00092] | +0.00024 [-0.00039, +0.00088] | +0.00094 | +0.0007 | -0.0048 [-0.0076, -0.0020] | +0.0002 [-0.0013, +0.0018] | 0.841 | 0.920 | 0.0174 → 0.0128 | non distinguibile dal rumore |
| J2a — alpha per lega | +0.00004 [-0.00041, +0.00048] | +0.00027 [-0.00025, +0.00081] | -0.00002 [-0.00021, +0.00016] | -0.00004 | +0.0000 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0.841 | 0.920 | 0.0174 → 0.0173 | non distinguibile dal rumore |
| J2b — alpha per squadra con shrinkage (30) | -0.00050 [-0.00117, +0.00018] | -0.00037 [-0.00118, +0.00048] | -0.00245 [-0.00334, -0.00152] | -0.00189 | +0.0000 | +0.0000 [+0.0000, +0.0000] | +0.0000 [+0.0000, +0.0000] | 0.842 | 0.921 | 0.0174 → 0.0171 | non distinguibile dal rumore |
| J4 — GAP η=0.02, γ=0.0 | -0.00131 [-0.00279, +0.00025] | -0.00117 [-0.00323, +0.00109] | -0.00070 [-0.00159, +0.00025] | -0.00099 | -0.0036 | -0.0102 [-0.0174, -0.0029] | -0.0032 [-0.0051, -0.0013] | 0.841 | 0.922 | 0.0174 → 0.0177 | non distinguibile dal rumore |
| J4 — GAP η=0.05, γ=0.0 | -0.00077 [-0.00217, +0.00073] | -0.00111 [-0.00305, +0.00109] | +0.00025 [-0.00065, +0.00119] | +0.00002 | -0.0039 | -0.0060 [-0.0127, +0.0009] | -0.0008 [-0.0027, +0.0011] | 0.841 | 0.921 | 0.0174 → 0.0194 | non distinguibile dal rumore |
| J4 — GAP η=0.02, γ=0.5 | +0.00070 [-0.00072, +0.00223] | +0.00112 [-0.00085, +0.00334] | +0.00022 [-0.00066, +0.00115] | +0.00003 | +0.0028 | -0.0000 [-0.0068, +0.0070] | -0.0012 [-0.0031, +0.0006] | 0.842 | 0.922 | 0.0174 → 0.0149 | non distinguibile dal rumore |
| J4 — GAP η=0.05, γ=0.5 (scelta in validazione) | +0.00082 [-0.00058, +0.00234] | +0.00050 [-0.00148, +0.00269] | +0.00119 [+0.00023, +0.00219] | +0.00139 | +0.0011 | +0.0020 [-0.0045, +0.0091] | +0.0014 [-0.0006, +0.0032] | 0.841 | 0.921 | 0.0174 → 0.0174 | non distinguibile dal rumore |
| J3 — copula gaussiana, ρ unica (scelta in validazione) | +0.00021 [-0.00032, +0.00075] | -0.00019 [-0.00091, +0.00056] | +0.00000 [+0.00000, +0.00000] | +0.00000 | +0.0027 | +0.0000 [-0.0001, +0.0001] | +0.0000 [+0.0000, +0.0000] | 0.842 | 0.921 | 0.0174 → 0.0101 | non distinguibile dal rumore |
| J3 — copula gaussiana, ρ per lega | +0.00017 [-0.00044, +0.00077] | -0.00005 [-0.00082, +0.00074] | +0.00000 [+0.00000, +0.00000] | +0.00000 | +0.0027 | +0.0000 [-0.0001, +0.0001] | +0.0000 [+0.0000, +0.0000] | 0.842 | 0.921 | 0.0174 → 0.0104 | non distinguibile dal rumore |

**J3, «chi ha più corner»** (esito casa / pari / ospite) con ρ unica: log-loss 0.8713 contro 0.8724 con l'indipendenza (ρ = 0): Δ +0.00114, IC a blocchi [+0.00038, +0.00194], held-out +0.00032 [-0.00068, +0.00129]. Probabilità medie previste casa/pari/ospite 0.524/0.094/0.381, frequenze osservate 0.535/0.094/0.370.

ρ stimata (ultimo fold): -0.195.


## Esperimento K — Nuovi mercati derivati

### K1 — Primo tempo

12751 partite di test con punteggio al riposo (dal 2019/20). Frequenze osservate: 1X2 al riposo 0.338/0.400/0.262, Over 0.5 0.716, Over 1.5 0.357; gol medi del primo tempo casa 0.690, ospite 0.565; quota media dei gol nel primo tempo 0.446.

| Variante | Log-loss 1X2 | Log-loss Over 0.5 | Log-loss Over 1.5 | Media dei tre | ECE 1X2 | ECE O0.5 | ECE O1.5 | Scarto O0.5 | Scarto O1.5 | Scarto 1/X/2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Riferimento: medie di lega (nessuna informazione sulla partita) | 1.0843 | 0.5953 | 0.6499 | 0.7765 | 0.0128 | 0.0177 | 0.0181 | -0.0143 | -0.0149 | -0.000/+0.015/-0.015 |
| K1a — quota 1T per lega | 1.0343 | 0.5895 | 0.6422 | 0.7553 | 0.0089 | 0.0129 | 0.0111 | -0.0068 | -0.0026 | +0.004/-0.000/-0.004 |
| K1b — quote 1T casa/ospite per lega | 1.0346 | 0.5895 | 0.6423 | 0.7555 | 0.0078 | 0.0121 | 0.0118 | -0.0068 | -0.0026 | +0.005/-0.000/-0.005 |
| K1c — regressione con gol attesi totali | 1.0344 | 0.5893 | 0.6420 | 0.7552 | 0.0082 | 0.0143 | 0.0109 | -0.0101 | -0.0058 | -0.001/+0.002/-0.002 |

Scelta sulle validazione tra (a), (b), (c) (log-loss media dei tre mercati; parità entro 0.0002 → la più semplice): **K1a**.

Δ log-loss rispetto al riferimento (medie di lega) e rispetto a K1a (positivo = migliore; IC 95% a blocchi per settimana):

| Variante | Mercato | Δ vs riferimento [IC a blocchi] | Δ held-out vs riferimento [IC a blocchi] | Δ vs K1a [IC a blocchi] |
|---|---|---|---|---|
| K1a — quota 1T per lega (scelta) | 1X2 al riposo | +0.05004 [+0.04504, +0.05500] | +0.04969 [+0.04332, +0.05610] | — |
| K1a — quota 1T per lega (scelta) | Over 0.5 1T | +0.00581 [+0.00435, +0.00722] | +0.00543 [+0.00353, +0.00735] | — |
| K1a — quota 1T per lega (scelta) | Over 1.5 1T | +0.00766 [+0.00576, +0.00965] | +0.00773 [+0.00512, +0.01039] | — |
| K1a — quota 1T per lega (scelta) | media dei tre | +0.02117 [+0.01912, +0.02323] | +0.02095 [+0.01833, +0.02356] | — |
| K1b — quote 1T casa/ospite per lega | 1X2 al riposo | +0.04966 [+0.04465, +0.05463] | +0.04962 [+0.04327, +0.05604] | -0.00038 [-0.00056, -0.00020] |
| K1b — quote 1T casa/ospite per lega | Over 0.5 1T | +0.00580 [+0.00434, +0.00721] | +0.00543 [+0.00352, +0.00736] | -0.00002 [-0.00006, +0.00003] |
| K1b — quote 1T casa/ospite per lega | Over 1.5 1T | +0.00764 [+0.00574, +0.00963] | +0.00773 [+0.00512, +0.01039] | -0.00002 [-0.00008, +0.00003] |
| K1b — quote 1T casa/ospite per lega | media dei tre | +0.02103 [+0.01900, +0.02309] | +0.02093 [+0.01829, +0.02355] | -0.00014 [-0.00020, -0.00008] |
| K1c — regressione con gol attesi totali | 1X2 al riposo | +0.04989 [+0.04490, +0.05487] | +0.04990 [+0.04351, +0.05634] | -0.00015 [-0.00062, +0.00031] |
| K1c — regressione con gol attesi totali | Over 0.5 1T | +0.00604 [+0.00451, +0.00751] | +0.00567 [+0.00376, +0.00761] | +0.00022 [-0.00011, +0.00055] |
| K1c — regressione con gol attesi totali | Over 1.5 1T | +0.00789 [+0.00579, +0.01007] | +0.00819 [+0.00540, +0.01105] | +0.00023 [-0.00017, +0.00063] |
| K1c — regressione con gol attesi totali | media dei tre | +0.02127 [+0.01920, +0.02331] | +0.02125 [+0.01867, +0.02388] | +0.00010 [-0.00017, +0.00037] |

K1c: coefficiente di log(μ+ν) sulla quota del primo tempo (ultimo fold; negativo = quota minore quando ci si aspettano più gol): casa +0.077, ospite +0.021.

Quota media dei gol nel primo tempo per lega (tutte le stagioni dal 2016/17): I1 0.435, E0 0.445, D1 0.447, SP1 0.435, F1 0.443.

Per K2 e K3 l'insieme di valutazione è quello dei campionati: 12751 partite dal 2019/20.

### K2 — «Chi fa più» e handicap ±1,5 dai modelli congiunti

**corner**: ρ unica (ultimo fold -0.195).

| Mercato | Log-loss copula | Log-loss indipendenza | Δ [IC a blocchi] | Δ held-out [IC a blocchi] | ECE copula / indip. | Scarto medio copula (casa/pari/ospite) | Frequenze osservate |
|---|---:|---:|---|---|---|---|---|
| Chi ha più corner (casa / pari / ospite) | 0.8713 | 0.8724 | +0.00114 [+0.00038, +0.00194] | +0.00032 [-0.00068, +0.00129] | 0.0043 / 0.0118 | -0.011/+0.000/+0.011 | 0.535/0.094/0.370 |
| Handicap Casa −1,5 (casa vince di almeno 2 corner) | 0.6381 | 0.6393 | +0.00123 [+0.00071, +0.00174] | +0.00084 [+0.00019, +0.00150] | 0.0141 / 0.0238 | -0.0102 (indip. -0.0127) | frequenza 0.439 |
| Handicap Ospite −1,5 (ospite vince di almeno 2 corner) | 0.5531 | 0.5539 | +0.00080 [-0.00006, +0.00168] | +0.00003 [-0.00103, +0.00113] | 0.0116 / 0.0191 | +0.0079 (indip. -0.0087) | frequenza 0.286 |

**gialli**: ρ unica (ultimo fold +0.171).

| Mercato | Log-loss copula | Log-loss indipendenza | Δ [IC a blocchi] | Δ held-out [IC a blocchi] | ECE copula / indip. | Scarto medio copula (casa/pari/ospite) | Frequenze osservate |
|---|---:|---:|---|---|---|---|---|
| Chi ha più gialli (casa / pari / ospite) | 1.0564 | 1.0601 | +0.00367 [+0.00255, +0.00473] | +0.00374 [+0.00230, +0.00524] | 0.0112 / 0.0222 | +0.009/-0.015/+0.006 | 0.330/0.240/0.430 |

### K3 — Falli per squadra e totali

**Baseline semplice: metodo «a medie» sui falli**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.6992 | 2.8971 | 0.370 | 0.846 | 0.924 | 0.5936 | 0.0054 | +0.0042 |
| Totale | 3.0924 | 4.2700 | 0.416 | 0.834 | 0.921 | 0.6110 | 0.0063 | +0.0040 |

**K3a — modello dei falli (struttura degli altri, senza arbitro)**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.6918 | 2.8709 | 0.389 | 0.846 | 0.925 | 0.5892 | 0.0085 | +0.0067 |
| Totale | 3.0853 | 4.2313 | 0.432 | 0.839 | 0.923 | 0.6082 | 0.0126 | +0.0077 |

**K3b — modello dei falli con effetto arbitro**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.6842 | 2.8487 | 0.405 | 0.844 | 0.923 | 0.5851 | 0.0071 | +0.0047 |
| Totale | 3.0711 | 4.1673 | 0.458 | 0.838 | 0.920 | 0.6001 | 0.0102 | +0.0049 |

Δ = baseline − variante (positivo = variante migliore); IC 95% a blocchi per settimana.

| Variante | Δ log-loss totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ log-loss per squadra (tutte) [IC a blocchi] | Δ per squadra held-out | Δ MAE tot. | Δ corr. tot. [IC] | Δ corr. squadra [IC] | Copertura 80% tot. (var.) | Copertura 90% tot. (var.) | ECE O/U tot. (base → var.) | Verdetto |
|---|---|---|---|---:|---:|---|---|---:|---:|---|---|
| K3a vs baseline a medie | +0.00711 [+0.00177, +0.01212] | +0.00801 [+0.00188, +0.01381] | +0.00734 [+0.00396, +0.01056] | +0.00954 | +0.0387 | +0.0168 [+0.0076, +0.0263] | +0.0187 [+0.0118, +0.0253] | 0.839 | 0.923 | 0.0063 → 0.0126 | migliora |
| K3b (con arbitro) vs K3a | +0.01424 [+0.01051, +0.01793] | +0.01187 [+0.00747, +0.01628] | +0.00761 [+0.00554, +0.00966] | +0.00633 | +0.0640 | +0.0250 [+0.0191, +0.0315] | +0.0158 [+0.0117, +0.0199] | 0.838 | 0.920 | 0.0126 → 0.0102 | migliora |
| K3b vs baseline a medie | +0.02134 [+0.01494, +0.02741] | +0.01988 [+0.01296, +0.02645] | +0.01495 [+0.01108, +0.01871] | +0.01586 | +0.1027 | +0.0418 [+0.0310, +0.0528] | +0.0345 [+0.0269, +0.0418] | 0.838 | 0.920 | 0.0063 → 0.0102 | migliora |


### Analisi aggiuntive (NON previste dal prereg)

Stesso insieme di valutazione dei campionati (12751 partite).

**Baseline dei gialli (modello attuale con effetto arbitro): metriche per squadra e totale**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 1.6618 | 1.0639 | 0.282 | 0.932 | 0.978 | 0.6259 | 0.0111 | -0.0093 |
| Totale | 2.1082 | 1.6171 | 0.316 | 0.870 | 0.934 | 0.5822 | 0.0073 | -0.0015 |

**Tiri in porta: modello con GAP ratings (η=0.05, γ=0.5, scelto in validazione per J4)**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.1746 | 1.7739 | 0.452 | 0.872 | 0.941 | 0.5891 | 0.0103 | +0.0088 |
| Totale | 2.5384 | 2.4799 | 0.286 | 0.854 | 0.929 | 0.6285 | 0.0141 | +0.0141 |

Tiri in porta, GAP vs baseline semplice «tiri previsti × quota in porta» (Δ positivo = GAP migliore):

| Variante | Δ log-loss totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ log-loss per squadra (tutte) [IC a blocchi] | Δ per squadra held-out | Δ MAE tot. | Δ corr. tot. [IC] | Δ corr. squadra [IC] | Copertura 80% tot. (var.) | Copertura 90% tot. (var.) | ECE O/U tot. (base → var.) | Verdetto |
|---|---|---|---|---:|---:|---|---|---:|---:|---|---|
| Tiri in porta — J4 GAP vs baseline semplice | +0.00260 [-0.00141, +0.00640] | +0.00005 [-0.00422, +0.00458] | +0.00654 [+0.00429, +0.00871] | +0.00494 | -0.0041 | +0.0081 [-0.0032, +0.0194] | +0.0121 [+0.0083, +0.0158] | 0.854 | 0.929 | 0.0069 → 0.0141 | non distinguibile dal rumore |


## Tabella riassuntiva

Δ = baseline − variante (positivo = variante migliore); IC 95% a blocchi per settimana; validazione 2019/20-2021/22, held-out dal 2022/23. Primaria = log-loss del conteggio totale; secondaria = log-loss per squadra. Per le statistiche non esiste un riferimento di mercato nei dati: la colonna «distanza dalle quote di chiusura» non si applica.

### Miglioramenti di tiri, tiri in porta e corner, e modello dei tiri in porta

| Statistica | Variante | Δ totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ per squadra (tutte) [IC a blocchi] | Δ per squadra held-out | Δ corr. totale | Copertura 80% / 90% tot. | ECE O/U tot. (base → var.) | Verdetto |
|---|---|---|---|---|---:|---:|---|---|---|
| Tiri in porta | I — nuovo modello vs baseline semplice (tiri × quota in porta) | -0.00264 [-0.00700, +0.00152] | -0.00600 [-0.01022, -0.00164] | +0.00340 [+0.00101, +0.00563] | +0.00126 | -0.0067 | 0.851 / 0.928 | 0.0069 → 0.0186 | peggiora (totale) / migliora per squadra |
| Tiri | J1 — + eo_diff e gol attesi v6 | -0.00300 [-0.00530, -0.00071] | +0.00223 [-0.00005, +0.00456] | -0.00031 [-0.00197, +0.00134] | +0.00423 | -0.0053 | 0.818 / 0.907 | 0.0152 → 0.0139 | non distinguibile dal rumore |
| Tiri | J2a — alpha per lega | +0.00021 [-0.00058, +0.00100] | -0.00113 [-0.00218, -0.00003] | -0.00029 [-0.00060, +0.00001] | -0.00049 | +0.0000 | 0.818 / 0.906 | 0.0152 → 0.0151 | peggiora |
| Tiri | J2b — alpha per squadra con shrinkage (30) | -0.00131 [-0.00250, -0.00011] | -0.00221 [-0.00373, -0.00069] | -0.00299 [-0.00409, -0.00191] | -0.00280 | +0.0000 | 0.819 / 0.906 | 0.0152 → 0.0151 | peggiora |
| Tiri | J4 — GAP η=0.02, γ=0.0 | -0.00453 [-0.00888, +0.00029] | -0.00020 [-0.00532, +0.00658] | -0.00505 [-0.00807, -0.00166] | -0.00335 | -0.0155 | 0.817 / 0.910 | 0.0152 → 0.0162 | non distinguibile dal rumore |
| Tiri | J4 — GAP η=0.05, γ=0.0 | +0.00617 [+0.00167, +0.01099] | +0.00446 [-0.00092, +0.01108] | +0.00307 [+0.00005, +0.00635] | +0.00245 | +0.0107 | 0.819 / 0.909 | 0.0152 → 0.0127 | non distinguibile dal rumore |
| Tiri | J4 — GAP η=0.02, γ=0.5 | +0.00236 [-0.00184, +0.00687] | +0.00458 [-0.00042, +0.01097] | -0.00056 [-0.00352, +0.00271] | +0.00030 | +0.0039 | 0.818 / 0.907 | 0.0152 → 0.0151 | non distinguibile dal rumore |
| Tiri | J4 — GAP η=0.05, γ=0.5 (scelta in validazione) | +0.01477 [+0.01009, +0.01967] | +0.01061 [+0.00511, +0.01730] | +0.00982 [+0.00671, +0.01312] | +0.00834 | +0.0338 | 0.819 / 0.907 | 0.0152 → 0.0131 | migliora |
| Tiri | J3 — copula gaussiana, ρ unica | -0.00033 [-0.00096, +0.00029] | -0.00010 [-0.00080, +0.00062] | +0.00000 [+0.00000, +0.00000] | +0.00000 | -0.0000 | 0.819 / 0.908 | 0.0152 → 0.0213 | non distinguibile dal rumore |
| Tiri | J3 — copula gaussiana, ρ per lega (scelta in validazione) | -0.00002 [-0.00101, +0.00094] | -0.00102 [-0.00218, +0.00017] | +0.00000 [+0.00000, +0.00000] | +0.00000 | -0.0000 | 0.819 / 0.907 | 0.0152 → 0.0206 | non distinguibile dal rumore |
| Tiri in porta | J1 — + eo_diff e gol attesi v6 | +0.00126 [-0.00006, +0.00263] | +0.00077 [-0.00111, +0.00255] | +0.00327 [+0.00216, +0.00441] | +0.00390 | +0.0015 | 0.850 / 0.927 | 0.0186 → 0.0080 | non distinguibile dal rumore |
| Tiri in porta | J2a — alpha per lega | +0.00011 [-0.00023, +0.00045] | +0.00004 [-0.00039, +0.00048] | -0.00007 [-0.00031, +0.00017] | -0.00019 | +0.0000 | 0.850 / 0.927 | 0.0186 → 0.0183 | non distinguibile dal rumore |
| Tiri in porta | J2b — alpha per squadra con shrinkage (30) | -0.00084 [-0.00160, -0.00008] | -0.00052 [-0.00152, +0.00050] | -0.00158 [-0.00234, -0.00077] | -0.00173 | +0.0000 | 0.852 / 0.929 | 0.0186 → 0.0177 | non distinguibile dal rumore |
| Tiri in porta | J4 — GAP η=0.02, γ=0.0 | -0.00213 [-0.00386, -0.00045] | -0.00157 [-0.00385, +0.00079] | -0.00111 [-0.00200, -0.00023] | -0.00104 | -0.0042 | 0.852 / 0.927 | 0.0186 → 0.0231 | non distinguibile dal rumore |
| Tiri in porta | J4 — GAP η=0.05, γ=0.0 | +0.00186 [-0.00000, +0.00369] | +0.00254 [+0.00021, +0.00488] | +0.00113 [+0.00016, +0.00209] | +0.00137 | +0.0054 | 0.852 / 0.928 | 0.0186 → 0.0181 | migliora |
| Tiri in porta | J4 — GAP η=0.02, γ=0.5 | +0.00202 [+0.00045, +0.00357] | +0.00285 [+0.00077, +0.00510] | +0.00087 [+0.00002, +0.00169] | +0.00115 | +0.0067 | 0.852 / 0.928 | 0.0186 → 0.0185 | migliora |
| Tiri in porta | J4 — GAP η=0.05, γ=0.5 (scelta in validazione) | +0.00523 [+0.00343, +0.00706] | +0.00605 [+0.00374, +0.00832] | +0.00314 [+0.00217, +0.00416] | +0.00368 | +0.0148 | 0.854 / 0.929 | 0.0186 → 0.0141 | migliora |
| Tiri in porta | J3 — copula gaussiana, ρ unica | +0.00031 [+0.00008, +0.00056] | +0.00026 [-0.00005, +0.00056] | +0.00000 [+0.00000, +0.00000] | +0.00000 | -0.0000 | 0.851 / 0.927 | 0.0186 → 0.0147 | non distinguibile dal rumore |
| Tiri in porta | J3 — copula gaussiana, ρ per lega (scelta in validazione) | +0.00055 [+0.00010, +0.00102] | +0.00045 [-0.00012, +0.00102] | +0.00000 [+0.00000, +0.00000] | +0.00000 | -0.0000 | 0.851 / 0.928 | 0.0186 → 0.0147 | non distinguibile dal rumore |
| Corner | J1 — + eo_diff e gol attesi v6 | -0.00056 [-0.00116, +0.00005] | +0.00023 [-0.00047, +0.00092] | +0.00024 [-0.00039, +0.00088] | +0.00094 | -0.0048 | 0.841 / 0.920 | 0.0174 → 0.0128 | non distinguibile dal rumore |
| Corner | J2a — alpha per lega | +0.00004 [-0.00041, +0.00048] | +0.00027 [-0.00025, +0.00081] | -0.00002 [-0.00021, +0.00016] | -0.00004 | +0.0000 | 0.841 / 0.920 | 0.0174 → 0.0173 | non distinguibile dal rumore |
| Corner | J2b — alpha per squadra con shrinkage (30) | -0.00050 [-0.00117, +0.00018] | -0.00037 [-0.00118, +0.00048] | -0.00245 [-0.00334, -0.00152] | -0.00189 | +0.0000 | 0.842 / 0.921 | 0.0174 → 0.0171 | non distinguibile dal rumore |
| Corner | J4 — GAP η=0.02, γ=0.0 | -0.00131 [-0.00279, +0.00025] | -0.00117 [-0.00323, +0.00109] | -0.00070 [-0.00159, +0.00025] | -0.00099 | -0.0102 | 0.841 / 0.922 | 0.0174 → 0.0177 | non distinguibile dal rumore |
| Corner | J4 — GAP η=0.05, γ=0.0 | -0.00077 [-0.00217, +0.00073] | -0.00111 [-0.00305, +0.00109] | +0.00025 [-0.00065, +0.00119] | +0.00002 | -0.0060 | 0.841 / 0.921 | 0.0174 → 0.0194 | non distinguibile dal rumore |
| Corner | J4 — GAP η=0.02, γ=0.5 | +0.00070 [-0.00072, +0.00223] | +0.00112 [-0.00085, +0.00334] | +0.00022 [-0.00066, +0.00115] | +0.00003 | -0.0000 | 0.842 / 0.922 | 0.0174 → 0.0149 | non distinguibile dal rumore |
| Corner | J4 — GAP η=0.05, γ=0.5 (scelta in validazione) | +0.00082 [-0.00058, +0.00234] | +0.00050 [-0.00148, +0.00269] | +0.00119 [+0.00023, +0.00219] | +0.00139 | +0.0020 | 0.841 / 0.921 | 0.0174 → 0.0174 | non distinguibile dal rumore |
| Corner | J3 — copula gaussiana, ρ unica (scelta in validazione) | +0.00021 [-0.00032, +0.00075] | -0.00019 [-0.00091, +0.00056] | +0.00000 [+0.00000, +0.00000] | +0.00000 | +0.0000 | 0.842 / 0.921 | 0.0174 → 0.0101 | non distinguibile dal rumore |
| Corner | J3 — copula gaussiana, ρ per lega | +0.00017 [-0.00044, +0.00077] | -0.00005 [-0.00082, +0.00074] | +0.00000 [+0.00000, +0.00000] | +0.00000 | +0.0000 | 0.842 / 0.921 | 0.0174 → 0.0104 | non distinguibile dal rumore |
| Tiri in porta | (extra) J4 GAP vs baseline semplice | +0.00260 [-0.00141, +0.00640] | +0.00005 [-0.00422, +0.00458] | +0.00654 [+0.00429, +0.00871] | +0.00494 | +0.0081 | 0.854 / 0.929 | 0.0069 → 0.0141 | non distinguibile (totale); migliora per squadra |

### Nuovi mercati

| Mercato | Confronto | Δ log-loss [IC a blocchi] | Δ held-out [IC a blocchi] | Note |
|---|---|---|---|---|
| K1a — 1X2 al riposo | vs medie di lega | +0.05004 [+0.04504, +0.05500] | +0.04969 [+0.04332, +0.05610] | quota 1T per lega |
| K1a — Over 0.5 primo tempo | vs medie di lega | +0.00581 [+0.00435, +0.00722] | +0.00543 [+0.00353, +0.00735] | quota 1T per lega |
| K1a — Over 1.5 primo tempo | vs medie di lega | +0.00766 [+0.00576, +0.00965] | +0.00773 [+0.00512, +0.01039] | quota 1T per lega |
| K1a — media dei tre | vs medie di lega | +0.02117 [+0.01912, +0.02323] | +0.02095 [+0.01833, +0.02356] | quota 1T per lega |
| K2 — chi ha più corner | copula vs indipendenza | +0.00114 [+0.00038, +0.00194] | +0.00032 [-0.00068, +0.00129] | ρ -0.195 |
| K2 — chi ha più gialli | copula vs indipendenza | +0.00367 [+0.00255, +0.00473] | +0.00374 [+0.00230, +0.00524] | ρ +0.171 |
| K2 — handicap Casa −1,5 sui corner | copula vs indipendenza | +0.00123 [+0.00071, +0.00174] | +0.00084 [+0.00019, +0.00150] | |
| K2 — handicap Ospite −1,5 sui corner | copula vs indipendenza | +0.00080 [-0.00006, +0.00168] | +0.00003 [-0.00103, +0.00113] | |
| K3 — falli totali | K3a vs metodo a medie | +0.00711 [+0.00177, +0.01212] | +0.00801 [+0.00188, +0.01381] | per squadra +0.00734; migliora |
| K3 — falli totali | K3b (con arbitro) vs K3a | +0.01424 [+0.01051, +0.01793] | +0.01187 [+0.00747, +0.01628] | per squadra +0.00761; migliora |
| K3 — falli totali | K3b vs metodo a medie | +0.02134 [+0.01494, +0.02741] | +0.01988 [+0.01296, +0.02645] | per squadra +0.01495; migliora |

## Proposte per il pannello (non implementate)

Solo le varianti che «migliorano» secondo la regola scritta prima, più due mercati nuovi che non hanno un modello attuale con cui confrontarsi.

**1. Tiri** (nella sezione «Statistiche attese»): valore atteso e **intervallo all'80%** per la squadra di casa, per l'ospite e per il totale, più le linee Over/Under del totale già mostrate. Modello: J4 (GAP ratings, η = 0.05, γ = 0.5) al posto delle forze attuali dei tiri; intervalli dalla Binomiale Negativa con alpha per squadra unico (stima a momenti sul training). L'intervallo per squadra del baseline copre già 0.82 (nominale 0.80), quindi si può mostrare così com'è. Dopo il passaggio a GAP la copertura resta in linea (totale 0.819 all'80%, 0.907 al 90%).
**2. Tiri in porta**: stesso layout dei tiri (squadra, squadra, totale, intervallo all'80%, Over/Under del totale 7.5-10.5). Modello: struttura del modello I con le feature GAP al posto delle forze (J4, η = 0.05, γ = 0.5). Avvertenze da mostrare nel testo del pannello: l'intervallo per squadra è prudente (copre 0.87 all'80% e 0.94 al 90%, per la natura discreta di conteggi piccoli) e rispetto al semplice «tiri previsti × quota in porta» il guadagno è sul singolo conteggio (+0.0065) ma non sul totale (+0.0026, IC che include lo zero).
**3. Corner**: nessuna variante di J migliora; resta il modello attuale. Si possono aggiungere, calcolati con la copula (ρ ≈ −0.2), «Chi fa più corner» (tre probabilità casa/pari/ospite) e l'handicap «Casa −1,5»: calibrati meglio dell'indipendenza (ECE 0.004 contro 0.012 per «chi fa più»).
**4. Gialli**: si aggiunge «Chi prende più gialli» (tre probabilità) dalla copula con ρ ≈ +0.17: è il miglioramento più netto tra i mercati derivati (+0.0037 di log-loss, ECE 0.011 contro 0.022). La riga dell'arbitro resta com'è. Gli intervalli per squadra dei gialli sono molto prudenti (copertura 0.93 all'80% con conteggi di 0-5): conviene non mostrarli per squadra ma solo l'intervallo del totale.
**5. Falli** (blocco nuovo): valore atteso e intervallo all'80% per squadra e totale, Over/Under 22.5/24.5/26.5 del totale. Modello K3b (con l'effetto arbitro sui falli, stessa designazione dei gialli; se l'arbitro non è noto si usa K3a). Migliora di 0.0213 di log-loss del totale rispetto al metodo a medie (0.0071 dal modello, 0.0142 dall'arbitro).
**6. Primo tempo** (nuova sezione accanto a «Over / Under»): 1X2 al riposo, Over 0.5 e Over 1.5 del primo tempo, ottenuti da una quota fissa per lega (≈ 44.6% dei gol attesi dal modello 1X2) applicata ai gol attesi della partita: K1a. Rispetto alle sole medie di lega la log-loss migliora molto sul 1X2 al riposo (+0.050) e un po' sugli Over (+0.006 e +0.008); regressioni più elaborate (quote separate casa/ospite, dipendenza dai gol attesi totali) non aggiungono nulla.

**Cosa servirebbe per implementarle** (stima del lavoro, non fatto): i GAP ratings sono uno stato per squadra e per statistica che si ricostruisce ogni giorno dallo storico (come gli Elo-Odds), quindi niente da salvare nel modello; η e γ sono costanti; il training salverebbe le nuove regressioni (tiri in porta, falli), la quota del primo tempo per lega e le ρ per statistica in `models/stack.json`; `STATS_VERSION` cambierebbe e `history.csv` registrerebbe valori previsti e reali anche per tiri, tiri in porta e falli.


## Commento

1. **J4 (GAP ratings di Wheatcroft) è il miglioramento più grande: tiri e tiri in porta.** Con η = 0.05 e γ = 0.5 (scelti in validazione) la log-loss del totale dei tiri scende di 0.0148 (IC a blocchi [+0.0101, +0.0197]; held-out +0.0106), quella per squadra di 0.0098, la correlazione del totale sale di 0.034 e la MAE scende di 0.049 tiri. Per i tiri in porta +0.0052 sul totale (held-out +0.0061) e +0.0031 per squadra. Sui corner il guadagno non è distinguibile dal rumore (+0.0008). Il segnale sembra essere l'adattamento rapido (η alto: mezza vita di circa 14 partite contro oltre un anno dei rating attuali) più l'aggiornamento incrociato casa/trasferta (γ = 0.5). **Attenzione**: la configurazione scelta è l'angolo della griglia dichiarata (η massimo e γ massimo, e il guadagno cresce con entrambi): l'ottimo potrebbe stare oltre; la regola scritta prima non permette di estendere la griglia in questo round.
2. **Per i tiri in porta il nuovo modello (I) non batte il baseline semplice sul totale**: rispetto a «tiri previsti × quota in porta» la log-loss del totale peggiora (−0.0026 su tutte le stagioni, −0.0060 fuori campione, verdetto scritto «peggiora») mentre quella per squadra migliora (+0.0034, IC [+0.0010, +0.0056]). Con le feature GAP il modello I recupera: +0.0026 sul totale (IC che include lo zero) e +0.0065 per squadra rispetto al baseline semplice (analisi aggiuntiva, non prevista dal prereg).
3. **J1, J2, J3 non migliorano il totale.** J1 (eo_diff e gol attesi v6): nessun guadagno distinguibile sul totale; sui tiri in porta migliora la log-loss per squadra (+0.0033) ma non il totale. J2a (alpha per lega) non cambia nulla; J2b (alpha per squadra con shrinkage) peggiora i tiri (anche fuori campione) e la log-loss per squadra dei tiri in porta. J3 (copula): la distribuzione del totale resta equivalente alla Binomiale Negativa sul totale (Δ tra −0.0003 e +0.0006; fuori campione sempre non distinguibile da zero); le correlazioni tra le due squadre sono negative per tiri (da −0.13 a −0.25 a seconda della lega) e corner (−0.20), quasi nulle per i tiri in porta, positive per i gialli (+0.17). Per la regola scritta («migliora» se il totale migliora) J3 non migliora; il suo valore sta nei mercati «chi ha più».
4. **K2: i mercati «chi ha più» migliorano con la copula.** «Chi prende più gialli»: log-loss −0.0037 (IC a blocchi [+0.0026, +0.0047], held-out +0.0037), calibrazione molto migliore (ECE 0.011 contro 0.022). «Chi ha più tiri»: +0.0019 ([+0.0009, +0.0028]). «Chi fa più corner»: +0.0011 su tutte le stagioni ma non fuori campione (+0.0003, IC che include lo zero); handicap «casa −1,5» sui corner +0.0012 (held-out +0.0008, significativo), «ospite −1,5» non distinguibile. Le probabilità dell'indipendenza sono invece mal calibrate (es. «chi fa più corner» ECE 0.012).
5. **K1, primo tempo: una quota fissa per lega basta.** I gol del primo tempo sono il 44.6% dei gol (da 43.5% a 44.7% per lega). Applicata ai gol attesi del modello 1X2 batte le sole medie di lega di 0.050 sul 1X2 al riposo e di 0.006/0.008 su Over 0.5/1.5, con buona calibrazione (ECE 0.009/0.013/0.011). Quote separate casa/ospite (K1b) o dipendenti dai gol attesi totali (K1c) non aggiungono nulla (K1c vs K1a +0.0001, IC [−0.0002, +0.0004]); il coefficiente sui gol attesi totali è positivo ma piccolo (casa +0.08, ospite +0.02). Il campione di partite è tutto il periodo 2019/20-2026/27.
6. **K3, falli: il modello e l'arbitro migliorano.** La struttura degli altri modelli batte il metodo a medie (+0.0071 sul totale, per squadra +0.0073); aggiungere l'effetto arbitro dà +0.0142 (IC [+0.0105, +0.0179]), la correlazione del totale sale da 0.416 a 0.458. Il guadagno complessivo sul totale è 0.0213 (IC [+0.0149, +0.0274]).
7. **Copertura degli intervalli** (nominale 80%/90%): per squadra sono vicine al nominale solo per i tiri (0.82/0.91); per tiri in porta (0.87/0.94), corner (0.86/0.93), falli (0.85/0.93) e soprattutto gialli (0.93/0.98) sono sopra, perché con conteggi piccoli e discreti l'intervallo [quantile 10%, quantile 90%] contiene per costruzione più massa; per il totale: tiri 0.82/0.91, tiri in porta 0.85/0.93, corner 0.84/0.92, gialli 0.87/0.93, falli 0.84/0.92. Non è un difetto di calibrazione della media ma della discretizzazione; per i gialli per squadra si suggerisce di non mostrare l'intervallo.
8. **Calibrazione Over/Under**: l'ECE dei totali è tra 0.007 (gialli, falli del metodo a medie) e 0.019 (tiri in porta); gli scarti medi sono sotto 2 punti percentuali. I miglioramenti J4 abbassano l'ECE dei tiri da 0.015 a 0.013 e dei tiri in porta da 0.019 a 0.014.
9. **Cosa non c'è**: nessun riferimento di mercato per queste statistiche nei dati, quindi niente «distanza dalle quote di chiusura». Produzione intatta.


---

## Fase 1 — Estensione della griglia dei GAP ratings: criteri fissati PRIMA di guardare i risultati

Nel round 6 la configurazione scelta per i GAP (η = 0.05, γ = 0.5) stava sul bordo della griglia dichiarata e il guadagno cresceva con entrambi i parametri. Questa sezione è stata scritta prima di eseguire qualsiasi configurazione nuova; nessun risultato con η > 0.05 o γ > 0.5 era stato visto (γ = 0.75 e 1.0 e η = 0.10-0.20 non erano mai stati calcolati). Definizioni, metriche, insieme di valutazione, validazione (2019/20-2021/22), held-out (dal 2022/23) e IC (a blocchi per settimana ISO, 5000 ricampionamenti; per partita anche) sono quelli del prereg del round 6.

**Griglia 1** (12 configurazioni): η ∈ {0.05, 0.10, 0.15, 0.20} × γ ∈ {0.5, 0.75, 1.0}. γ = 1 significa che l'aggiornamento dei rating dell'altro campo vale quanto quello del campo giocato; γ > 1 non ha senso e non si prova.

**Scelta**, separatamente per tiri e per tiri in porta (baseline del tiri = modello dei tiri attuale; baseline dei tiri in porta = modello I senza GAP, come nel round 6): configurazione con il Δ della log-loss del totale più alto sulle sole stagioni di validazione; parità entro 0.0002 → la più semplice (η più basso, poi γ più basso).

**Bordo e seconda (ultima) estensione.** Se per una statistica la configurazione scelta ha η = 0.20, si aggiunge UNA volta η ∈ {0.30, 0.40} (con γ ∈ {0.5, 0.75, 1.0}) e si sceglie di nuovo sull'unione delle griglie con la stessa regola; poi ci si ferma, anche se l'ottimo fosse ancora sul bordo. Un ottimo con γ = 1.0 non porta ad alcuna estensione (γ ha il limite naturale 1). Il passaggio a una seconda estensione vale per ogni statistica separatamente.

**Verifica fuori campione.** Per la configurazione scelta si riportano Δ della log-loss del totale e per squadra (tutte le stagioni, validazione, held-out) con IC a blocchi, correlazioni, MAE, copertura 80%/90%, ECE O/U. Verdetto come nel round 6: «migliora» se Δ totale held-out > 0 con IC a blocchi che esclude lo zero e Δ per squadra held-out ≥ 0. Si riporta anche la differenza rispetto alla configurazione del round 6 (η = 0.05, γ = 0.5), con IC.

I parametri scelti qui sono quelli della fase 2 (messa in produzione).

## Fase 1 — Estensione della griglia dei GAP ratings (tiri e tiri in porta)

### Tiri

**Baseline (modello dei tiri attuale)**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.8867 | 3.5105 | 0.505 | 0.821 | 0.908 | 0.5738 | 0.0102 | -0.0096 |
| Totale | 3.1506 | 4.4924 | 0.302 | 0.818 | 0.907 | 0.6343 | 0.0152 | -0.0151 |

**Griglia 1** (η ∈ [0.05, 0.1, 0.15, 0.2] × γ ∈ [0.5, 0.75, 1.0]): scelta sulle validazione η = 0.1, γ = 1.0; l'ottimo non è al bordo di η (nessuna estensione).

| η | γ | Δ totale (tutte) [IC a blocchi] | Δ totale validazione | Δ totale held-out [IC a blocchi] | Δ per squadra (tutte) | Δ per squadra held-out | Verdetto |
|---:|---:|---|---:|---|---:|---:|---|
| 0.05 | 0.5 | +0.01477 [+0.01009, +0.01967] | +0.02047 | +0.01061 [+0.00511, +0.01730] | +0.00982 | +0.00834 | migliora (round 6) |
| 0.05 | 0.75 | +0.01834 [+0.01351, +0.02326] | +0.02531 | +0.01326 [+0.00760, +0.01996] | +0.01257 | +0.01060 | migliora |
| 0.05 | 1.0 | +0.02002 [+0.01514, +0.02490] | +0.02859 | +0.01378 [+0.00818, +0.02041] | +0.01416 | +0.01119 | migliora |
| 0.1 | 0.5 | +0.01677 [+0.01150, +0.02207] | +0.02382 | +0.01163 [+0.00556, +0.01854] | +0.01231 | +0.01053 | migliora |
| 0.1 | 0.75 | +0.01966 [+0.01428, +0.02497] | +0.02765 | +0.01384 [+0.00762, +0.02071] | +0.01425 | +0.01216 | migliora |
| 0.1 | 1.0 | +0.02073 [+0.01523, +0.02607] | +0.03039 | +0.01368 [+0.00744, +0.02065] | +0.01495 | +0.01181 | migliora ← scelta |
| 0.15 | 0.5 | +0.01391 [+0.00841, +0.01943] | +0.01958 | +0.00978 [+0.00358, +0.01660] | +0.01067 | +0.00937 | migliora |
| 0.15 | 0.75 | +0.01622 [+0.01064, +0.02169] | +0.02261 | +0.01156 [+0.00529, +0.01845] | +0.01204 | +0.01050 | migliora |
| 0.15 | 1.0 | +0.01687 [+0.01122, +0.02245] | +0.02497 | +0.01097 [+0.00454, +0.01796] | +0.01223 | +0.00961 | migliora |
| 0.2 | 0.5 | +0.01030 [+0.00488, +0.01594] | +0.01412 | +0.00752 [+0.00137, +0.01425] | +0.00843 | +0.00766 | migliora |
| 0.2 | 0.75 | +0.01215 [+0.00654, +0.01775] | +0.01657 | +0.00893 [+0.00265, +0.01576] | +0.00938 | +0.00841 | migliora |
| 0.2 | 1.0 | +0.01246 [+0.00672, +0.01826] | +0.01843 | +0.00810 [+0.00160, +0.01515] | +0.00912 | +0.00718 | migliora |

**Scelta finale sulle sole validazione: η = 0.1, γ = 1.0** — η è interno alla griglia (nessuna estensione prevista); γ = 1.0 è il limite naturale del parametro, quindi nessuna estensione ulteriore.

| Variante | Δ log-loss totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ log-loss per squadra (tutte) [IC a blocchi] | Δ per squadra held-out | Δ MAE tot. | Δ corr. tot. [IC] | Δ corr. squadra [IC] | Copertura 80% tot. (var.) | Copertura 90% tot. (var.) | ECE O/U tot. (base → var.) | Verdetto |
|---|---|---|---|---:|---:|---|---|---:|---:|---|---|
| GAP η=0.1, γ=1.0 vs baseline | +0.02073 [+0.01523, +0.02607] | +0.01368 [+0.00744, +0.02065] | +0.01495 [+0.01131, +0.01866] | +0.01181 | +0.0688 | +0.0487 [+0.0374, +0.0597] | +0.0192 [+0.0154, +0.0227] | 0.821 | 0.906 | 0.0152 → 0.0132 | migliora |

Rispetto alla configurazione del round 6 (η=0.05, γ=0.5): Δ totale +0.00596 [IC a blocchi +0.00276, +0.00891], held-out +0.00307 [-0.00065, +0.00678]; per squadra +0.00513 [+0.00293, +0.00737].

**Metriche della configurazione scelta (η=0.1, γ=1.0)**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.8717 | 3.4627 | 0.525 | 0.821 | 0.908 | 0.5667 | 0.0087 | -0.0071 |
| Totale | 3.1299 | 4.4236 | 0.351 | 0.821 | 0.906 | 0.6218 | 0.0132 | -0.0132 |

### Tiri in porta

**Baseline (modello I dei tiri in porta, senza GAP)**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.1777 | 1.7803 | 0.447 | 0.870 | 0.940 | 0.5910 | 0.0133 | +0.0116 |
| Totale | 2.5436 | 2.4949 | 0.271 | 0.851 | 0.928 | 0.6313 | 0.0186 | +0.0186 |

**Griglia 1** (η ∈ [0.05, 0.1, 0.15, 0.2] × γ ∈ [0.5, 0.75, 1.0]): scelta sulle validazione η = 0.05, γ = 1.0; l'ottimo non è al bordo di η (nessuna estensione).

| η | γ | Δ totale (tutte) [IC a blocchi] | Δ totale validazione | Δ totale held-out [IC a blocchi] | Δ per squadra (tutte) | Δ per squadra held-out | Verdetto |
|---:|---:|---|---:|---|---:|---:|---|
| 0.05 | 0.5 | +0.00523 [+0.00343, +0.00706] | +0.00411 | +0.00605 [+0.00374, +0.00832] | +0.00314 | +0.00368 | migliora (round 6) |
| 0.05 | 0.75 | +0.00649 [+0.00472, +0.00831] | +0.00522 | +0.00741 [+0.00511, +0.00969] | +0.00398 | +0.00467 | migliora |
| 0.05 | 1.0 | +0.00679 [+0.00494, +0.00868] | +0.00570 | +0.00759 [+0.00518, +0.00997] | +0.00445 | +0.00499 | migliora ← scelta |
| 0.1 | 0.5 | +0.00270 [+0.00064, +0.00482] | +0.00151 | +0.00358 [+0.00096, +0.00615] | +0.00254 | +0.00318 | migliora |
| 0.1 | 0.75 | +0.00318 [+0.00115, +0.00528] | +0.00189 | +0.00412 [+0.00152, +0.00668] | +0.00288 | +0.00363 | migliora |
| 0.1 | 1.0 | +0.00300 [+0.00096, +0.00509] | +0.00181 | +0.00387 [+0.00126, +0.00649] | +0.00296 | +0.00357 | migliora |
| 0.15 | 0.5 | +0.00006 [-0.00216, +0.00235] | -0.00098 | +0.00082 [-0.00199, +0.00358] | +0.00134 | +0.00188 | non distinguibile dal rumore |
| 0.15 | 0.75 | +0.00014 [-0.00200, +0.00240] | -0.00089 | +0.00090 [-0.00186, +0.00363] | +0.00137 | +0.00195 | non distinguibile dal rumore |
| 0.15 | 1.0 | -0.00019 [-0.00231, +0.00198] | -0.00114 | +0.00050 [-0.00221, +0.00318] | +0.00126 | +0.00167 | non distinguibile dal rumore |
| 0.2 | 0.5 | -0.00201 [-0.00433, +0.00032] | -0.00290 | -0.00136 [-0.00426, +0.00148] | +0.00028 | +0.00068 | non distinguibile dal rumore |
| 0.2 | 0.75 | -0.00215 [-0.00437, +0.00015] | -0.00300 | -0.00152 [-0.00429, +0.00118] | +0.00016 | +0.00053 | non distinguibile dal rumore |
| 0.2 | 1.0 | -0.00256 [-0.00474, -0.00038] | -0.00333 | -0.00201 [-0.00473, +0.00067] | -0.00007 | +0.00017 | non distinguibile dal rumore |

**Scelta finale sulle sole validazione: η = 0.05, γ = 1.0** — η = 0.05 è interno all'unione delle griglie (round 6: 0.02 e 0.05; fase 1: da 0.05 a 0.20) e il guadagno scende per η più alti; γ = 1.0 è il limite naturale del parametro, quindi nessuna estensione.

| Variante | Δ log-loss totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Δ log-loss per squadra (tutte) [IC a blocchi] | Δ per squadra held-out | Δ MAE tot. | Δ corr. tot. [IC] | Δ corr. squadra [IC] | Copertura 80% tot. (var.) | Copertura 90% tot. (var.) | ECE O/U tot. (base → var.) | Verdetto |
|---|---|---|---|---:|---:|---|---|---:|---:|---|---|
| GAP η=0.05, γ=1.0 vs baseline | +0.00679 [+0.00494, +0.00868] | +0.00759 [+0.00518, +0.00997] | +0.00445 [+0.00335, +0.00562] | +0.00499 | +0.0203 | +0.0187 [+0.0136, +0.0244] | +0.0072 [+0.0053, +0.0091] | 0.853 | 0.930 | 0.0186 → 0.0113 | migliora |

Rispetto alla configurazione del round 6 (η=0.05, γ=0.5): Δ totale +0.00156 [IC a blocchi +0.00050, +0.00262], held-out +0.00154 [+0.00009, +0.00293]; per squadra +0.00131 [+0.00065, +0.00198].

**Metriche della configurazione scelta (η=0.05, γ=1.0)**

| Livello | Log-loss | MAE | Correlazione | Copertura 80% | Copertura 90% | Log-loss Over/Under | ECE O/U | Scarto medio O/U |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Per squadra | 2.1733 | 1.7703 | 0.454 | 0.871 | 0.940 | 0.5884 | 0.0088 | +0.0072 |
| Totale | 2.5368 | 2.4746 | 0.290 | 0.853 | 0.930 | 0.6274 | 0.0113 | +0.0113 |


### Conclusione della fase 1 e parametri per la produzione

| Statistica | η | γ | Δ log-loss totale (tutte) [IC a blocchi] | Δ totale held-out [IC a blocchi] | Verdetto |
|---|---:|---:|---|---|---|
| Tiri | 0.10 | 1.0 | +0.02073 [+0.01523, +0.02607] | +0.01368 [+0.00744, +0.02065] | migliora |
| Tiri in porta (modello I con GAP) | 0.05 | 1.0 | +0.00679 [+0.00494, +0.00868] | +0.00759 [+0.00518, +0.00997] | migliora |

Il γ ottimo è il limite naturale 1.0 per entrambe le statistiche (l'aggiornamento dei rating dell'altro campo vale quanto quello del campo giocato). L'η ottimo è interno alla griglia esplorata (0.10 per i tiri, 0.05 per i tiri in porta, con il guadagno che scende per η più alti): la regola dell'estensione (solo se η = 0.20) non è scattata e non c'è stata alcuna seconda estensione. Rispetto alla configurazione del round 6 (η = 0.05, γ = 0.5) il guadagno sul totale aumenta di +0.00596 per i tiri e +0.00156 per i tiri in porta (IC a blocchi esclude lo zero in entrambi i casi sulle stagioni complessive; sull'held-out dei tiri l'IC della differenza include lo zero: +0.00307 [-0.00065, +0.00678]). Questi sono i parametri messi in produzione (`config.GAP_PARAMS`).


---

## Fase 2 — Verifica di produzione: il codice messo in produzione riproduce la fase 1

Parametri di produzione (`config.GAP_PARAMS`): tiri η=0.1, γ=1.0; tiri in porta η=0.05, γ=1.0. Il walk-forward usa `backtest/gap.py` (rating), `backtest/stats_v3.py` (matrice di progetto) e gli stessi stimatori di `backtest/stats_model.py` del training; il baseline è lo stesso della fase 1.

| Statistica | Δ log-loss totale (produzione) | Δ totale fase 1 | Δ per squadra (produzione) | Δ per squadra fase 1 | Differenza massima | Esito |
|---|---:|---:|---:|---:|---:|---|
| Tiri | +0.02073 | +0.02073 | +0.01495 | +0.01495 | 0.00e+00 | riprodotto |
| Tiri in porta | +0.00679 | +0.00679 | +0.00445 | +0.00445 | 0.00e+00 | riprodotto |

**Coerenza del serving** (stato GAP ricostruito dallo storico e `gap.predict`, contro la previsione pre-partita del backtest per l'ultima partita giocata di ogni campionato):

| Campionato | Statistica | Scarto massimo (casa, ospite) |
|---|---|---:|
| D1 | tiri | 0.0e+00 |
| E0 | tiri | 0.0e+00 |
| F1 | tiri | 0.0e+00 |
| I1 | tiri | 0.0e+00 |
| SP1 | tiri | 0.0e+00 |
| D1 | sot | 0.0e+00 |
| E0 | sot | 0.0e+00 |
| F1 | sot | 0.0e+00 |
| I1 | sot | 0.0e+00 |
| SP1 | sot | 0.0e+00 |

**Esito complessivo: tutto riprodotto**
