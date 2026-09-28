"""
Formattazione dell'output nel terminale.
Produce schede predittive leggibili senza dipendenze extra (solo testo ANSI).
"""
from predictions.dixon_coles import Prediction

# Codici ANSI (compatibili con la maggior parte dei terminali moderni)
BOLD = "\033[1m"
DIM  = "\033[2m"
GREEN= "\033[92m"
BLUE = "\033[94m"
YELL = "\033[93m"
RED  = "\033[91m"
CYAN = "\033[96m"
GRAY = "\033[90m"
RST  = "\033[0m"


def _bar(value: float, width: int = 20, color: str = GREEN) -> str:
    filled = max(0, min(int(value * width), width))
    return color + "█" * filled + DIM + "░" * (width - filled) + RST


def _pct(v: float) -> str:
    return f"{v*100:5.1f}%"


def _prob_line(label: str, p: float, width: int = 16) -> str:
    color = GREEN if p > 0.50 else (YELL if p > 0.33 else RED)
    return f"  {label:<22} {_bar(p, width, color)} {color}{_pct(p)}{RST}"


def print_prediction(pred: Prediction):
    """Stampa la scheda predittiva completa per una partita."""
    f = pred.features

    # ── Header ────────────────────────────────────────────────────────────────
    sep = "─" * 60
    print()
    print(f"{BOLD}{sep}{RST}")
    print(f"  {BOLD}{CYAN}{pred.home_team:<24}{RST}  vs  "
          f"  {BOLD}{CYAN}{pred.away_team}{RST}")
    if f and f.league_key:
        league_name = f.league_key.replace("_", " ").title()
        print(f"  {GRAY}{league_name}  ·  {f.match_date}{RST}")
    print(f"{sep}")

    # ── Gol attesi ────────────────────────────────────────────────────────────
    print(f"\n  {BOLD}⚽ Gol attesi{RST}")
    print(f"  {pred.home_team:<24}  {BOLD}{GREEN}{pred.home_xg:.2f}{RST}"
          f"  {DIM}xG{RST}")
    print(f"  {pred.away_team:<24}  {BOLD}{BLUE}{pred.away_xg:.2f}{RST}"
          f"  {DIM}xG{RST}")

    # ── Probabilità 1X2 ───────────────────────────────────────────────────────
    print(f"\n  {BOLD}📊 Probabilità risultato{RST}")
    print(_prob_line(f"1 – {pred.home_team[:18]}", pred.prob_home, 18))
    print(_prob_line("X – Pareggio", pred.prob_draw, 18))
    print(_prob_line(f"2 – {pred.away_team[:18]}", pred.prob_away, 18))

    # ── Over/Under e BTTS ─────────────────────────────────────────────────────
    print(f"\n  {BOLD}📈 Totale gol{RST}")
    for label, p in [
        ("Over 0.5", pred.prob_o05),
        ("Over 1.5", pred.prob_o15),
        ("Over 2.5", pred.prob_o25),
        ("Over 3.5", pred.prob_o35),
    ]:
        print(_prob_line(label, p, 16))

    print(f"\n  {BOLD}🎯 Speciali{RST}")
    print(_prob_line("BTTS (entrambi segnano)", pred.prob_btts, 16))
    print(_prob_line(f"Clean sheet {pred.home_team[:12]}", pred.prob_cs_home, 16))
    print(_prob_line(f"Clean sheet {pred.away_team[:12]}", pred.prob_cs_away, 16))

    # ── Punteggi più probabili ────────────────────────────────────────────────
    print(f"\n  {BOLD}🏆 Punteggi più probabili{RST}")
    for i, (hg, ag, p) in enumerate(pred.top_scores[:5]):
        marker = f"{GREEN}►{RST}" if i == 0 else " "
        print(f"  {marker} {hg}–{ag}   {_bar(p * 3, 12, CYAN)}  {CYAN}{_pct(p)}{RST}")

    # ── Statistiche secondarie ────────────────────────────────────────────────
    print(f"\n  {BOLD}📋 Statistiche attese{RST}")
    print(f"  {'Tiri totali':<24}  {BOLD}{pred.exp_shots:.1f}{RST}")
    print(f"  {'Corner totali':<24}  {BOLD}{pred.exp_corners:.1f}{RST}")
    print(f"  {'Cartellini gialli':<24}  {BOLD}{pred.exp_yellow:.1f}{RST}")

    # ── Feature context ───────────────────────────────────────────────────────
    if f:
        print(f"\n  {DIM}Context{RST}")
        if f.home_elo != 1500.0 or f.away_elo != 1500.0:
            print(f"  {GRAY}ELO  {pred.home_team[:12]}: {f.home_elo:.0f}"
                  f"  ·  {pred.away_team[:12]}: {f.away_elo:.0f}"
                  f"  (diff: {f.elo_diff:+.0f}){RST}")
        print(f"  {GRAY}Forma [0-1]  casa: {f.home_form_5:.2f}"
              f"  ·  trasferta: {f.away_form_5:.2f}{RST}")
        print(f"  {GRAY}Riposo  casa: {f.home_rest_days}g"
              f"  ·  trasferta: {f.away_rest_days}g{RST}")
        if f.weather_impact > 0.05:
            print(f"  {YELL}☁ Meteo: impatto {f.weather_impact*100:.0f}%"
                  f" (pioggia/vento){RST}")
        if f.market_ph > 0:
            print(f"  {GRAY}Quote mercato: {_pct(f.market_ph)} · "
                  f"{_pct(f.market_pd)} · {_pct(f.market_pa)}{RST}")
        if f.h2h_advantage != 0:
            sign = ">" if f.h2h_advantage > 0 else "<"
            print(f"  {GRAY}H2H: vantaggio {'casa' if f.h2h_advantage > 0 else 'trasferta'}"
                  f" ({abs(f.h2h_advantage):.2f}){RST}")

    print(f"\n{DIM}{sep}{RST}\n")


def print_fixtures_table(rows: list[dict]):
    """Stampa la tabella delle prossime partite."""
    if not rows:
        print("  Nessuna partita trovata.")
        return

    print(f"\n  {BOLD}📅 Prossime partite{RST}")
    print(f"  {'Data':<12} {'Ora':<6} {'Casa':<22} {'Ospite':<22} {'Campionato'}")
    print("  " + "─" * 80)

    for r in rows:
        dt  = r.get("match_date", "")
        day = dt[:10] if dt else "?"
        hour = dt[11:16] if len(dt) > 10 else "?"
        home = r.get("home_team", "?")[:20]
        away = r.get("away_team", "?")[:20]
        league = r.get("league_key", "").replace("_", " ").title()[:18]
        print(f"  {day:<12} {hour:<6} {home:<22} {away:<22} {GRAY}{league}{RST}")

    print()


def print_team_info(team_name: str, stats: dict):
    """Stampa il profilo di una squadra."""
    sep = "─" * 50
    print(f"\n{BOLD}{sep}{RST}")
    print(f"  {BOLD}{CYAN}{team_name}{RST}")
    print(sep)

    if stats.get("elo"):
        print(f"  ELO corrente:    {BOLD}{stats['elo']:.0f}{RST}")
    if stats.get("form"):
        print(f"  Forma recente:   {BOLD}{stats['form']:.2f}{RST}/1.0")
    if stats.get("matches"):
        mp = stats["matches"]
        gf = stats.get("goals_for", 0)
        ga = stats.get("goals_against", 0)
        print(f"  Partite giocate: {mp}")
        print(f"  Gol fatti/subiti: {gf:.1f} / {ga:.1f} per partita")
    if stats.get("xg_for"):
        print(f"  xG for/against:  {stats['xg_for']:.2f} / {stats['xg_against']:.2f}")

    print(f"{sep}\n")
