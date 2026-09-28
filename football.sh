#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
#  football.sh — Script di automazione Football Predictor
#  Uso: ./football.sh <comando> [opzioni]
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

BOLD="\033[1m"
GREEN="\033[92m"
BLUE="\033[94m"
YELL="\033[93m"
RED="\033[91m"
CYAN="\033[96m"
GRAY="\033[90m"
RST="\033[0m"

# ── Funzioni di supporto ──────────────────────────────────────────────────────

log()   { echo -e "${GRAY}[football]${RST} $*"; }
ok()    { echo -e "${GREEN}✓${RST} $*"; }
warn()  { echo -e "${YELL}⚠${RST}  $*"; }
err()   { echo -e "${RED}✗${RST}  $*" >&2; }
title() { echo -e "\n${BOLD}${CYAN}$*${RST}\n"; }

check_python() {
    if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
        err "Python non trovato. Installa Python 3.9+ e riprova."
        exit 1
    fi
    PYTHON=$(command -v python3 || command -v python)
}

PYTHON=""
check_python

# ── Comandi ───────────────────────────────────────────────────────────────────

cmd_setup() {
    title "⚙  Setup Football Predictor"

    # 1. Dipendenze
    log "Installo dipendenze Python..."
    $PYTHON -m pip install -r requirements.txt -q --break-system-packages 2>/dev/null \
        || $PYTHON -m pip install -r requirements.txt -q
    ok "Dipendenze installate"

    # 2. File .env
    if [[ ! -f ".env" ]]; then
        cp .env.example .env
        warn "File .env creato. Apri .env e incolla la tua chiave API:"
        echo -e "  ${BLUE}https://www.football-data.org/client/register${RST}  (gratuita)"
        echo ""
        read -rp "  Premi Invio quando hai inserito la chiave in .env, oppure Ctrl+C per farlo dopo... "
    else
        ok "File .env già presente"
    fi

    # 3. Init DB
    log "Inizializzo il database..."
    $PYTHON main.py init
    ok "Database pronto"

    # 4. Dati storici
    echo ""
    echo -e "  ${BOLD}Scarico i dati storici${RST} (CSV Football-Data.co.uk — può richiedere 3-5 minuti)"
    $PYTHON main.py update --source historical
    ok "Dati storici scaricati"

    # 5. Dati recenti completi
    echo ""
    log "Aggiornamento dati recenti..."
    $PYTHON main.py update
    ok "Dati aggiornati"

    # 6. Fitting modello per Serie A
    echo ""
    log "Fitting modello Dixon-Coles (Serie A)..."
    $PYTHON main.py fit --league serie_a && ok "Modello Serie A pronto" || warn "Dati insufficienti per il modello"

    echo ""
    echo -e "${BOLD}${GREEN}════════════════════════════════════════${RST}"
    echo -e "${BOLD}${GREEN}  ✓ Setup completato!${RST}"
    echo -e "${BOLD}${GREEN}════════════════════════════════════════${RST}"
    echo ""
    echo -e "  Comandi disponibili:"
    echo -e "  ${CYAN}./football.sh update${RST}                # aggiorna tutti i dati"
    echo -e "  ${CYAN}./football.sh fixtures${RST}              # prossime partite"
    echo -e "  ${CYAN}./football.sh predict-all serie_a${RST}   # tutte le previsioni Serie A"
    echo -e "  ${CYAN}./football.sh predict Milan Inter${RST}   # previsione singola"
    echo -e "  ${CYAN}./football.sh daily${RST}                 # aggiornamento + previsioni giornaliero"
    echo ""
}

cmd_update() {
    local source="${1:-all}"
    local league="${2:-}"

    title "🔄  Aggiornamento dati — source: $source"

    local args=("--source" "$source")
    [[ -n "$league" ]] && args+=("--league" "$league")

    $PYTHON main.py update "${args[@]}"
    ok "Aggiornamento completato"
}

cmd_fixtures() {
    local league="${1:-}"
    local days="${2:-7}"

    title "📅  Prossime partite"

    local args=("--days" "$days")
    [[ -n "$league" ]] && args+=("--league" "$league")

    $PYTHON main.py fixtures "${args[@]}"
}

cmd_predict() {
    local home="${1:-}"
    local away="${2:-}"
    local league="${3:-serie_a}"

    if [[ -z "$home" || -z "$away" ]]; then
        err "Specifica le due squadre: ./football.sh predict \"Milan\" \"Inter\" [lega]"
        exit 1
    fi

    title "🔮  Previsione: $home vs $away"
    $PYTHON main.py predict "$home" "$away" --league "$league"
}

cmd_predict_all() {
    local league="${1:-serie_a}"

    title "🔮  Previsioni prossimo turno — $league"
    $PYTHON main.py predict --league "$league" --round next
}

cmd_team() {
    local team="${1:-}"
    local league="${2:-serie_a}"

    if [[ -z "$team" ]]; then
        err "Specifica il nome della squadra: ./football.sh team \"Juventus\" [lega]"
        exit 1
    fi

    title "🏟  Profilo: $team"
    $PYTHON main.py team "$team" --league "$league"
}

cmd_fit() {
    local league="${1:-all}"

    title "⚙  Fitting modello Dixon-Coles"

    if [[ "$league" == "all" ]]; then
        for l in serie_a premier_league bundesliga la_liga ligue_1; do
            echo -e "\n  ${BOLD}$l${RST}"
            $PYTHON main.py fit --league "$l" && ok "$l" || warn "$l — dati insufficienti, skip"
        done
    else
        $PYTHON main.py fit --league "$league"
    fi
}

cmd_daily() {
    # Routine giornaliera: update + fit + previsioni per tutte le leghe
    title "🗓  Aggiornamento giornaliero automatico"

    local leagues=("serie_a" "premier_league" "bundesliga" "la_liga" "ligue_1" "champions_league")

    # 1. Aggiorna dati (escludi historical per velocità)
    log "Aggiornamento dati recenti..."
    $PYTHON main.py update --source fixtures      && ok "Fixtures"
    $PYTHON main.py update --source results       && ok "Results"
    $PYTHON main.py update --source xg            && ok "xG (Understat)"
    $PYTHON main.py update --source elo           && ok "ELO (ClubElo)"
    $PYTHON main.py update --source weather       && ok "Meteo"
    $PYTHON main.py update --source stats         && ok "Stats aggregate"
    $PYTHON main.py update --source fbref         && ok "Stats avanzate (FBref)" || warn "FBref: skip"
    $PYTHON main.py update --source transfermarkt && ok "Infortuni (Transfermarkt)" || warn "Transfermarkt: skip"

    # 2. Ri-fitta il modello per ogni lega (aggiornamento settimanale: solo se lunedì)
    local dow
    dow=$(date +%u)   # 1=lun … 7=dom
    if [[ "$dow" == "1" ]]; then
        log "Lunedì: ri-fitting modelli..."
        for l in "${leagues[@]}"; do
            $PYTHON main.py fit --league "$l" 2>/dev/null && ok "Fit $l" || true
        done
    fi

    # 3. Mostra prossime partite
    echo ""
    $PYTHON main.py fixtures --days 3

    # 4. Previsioni per i prossimi 3 giorni
    echo ""
    title "🔮  Previsioni prossimi match"
    for l in "${leagues[@]}"; do
        $PYTHON main.py predict --league "$l" --round next 2>/dev/null || true
    done

    ok "Routine giornaliera completata — $(date '+%Y-%m-%d %H:%M')"
}

cmd_serve() {
    local port="${1:-5000}"
    title "🌐  Avvio Web Dashboard"
    echo -e "  Apri nel browser: ${CYAN}http://localhost:${port}${RST}"
    echo -e "  ${GRAY}(Ctrl+C per fermare)${RST}\n"
    $PYTHON app.py
}

cmd_help() {
    echo ""
    echo -e "${BOLD}Football Predictor${RST} — Script di automazione"
    echo ""
    echo -e "  ${BOLD}Uso:${RST} ./football.sh <comando> [argomenti]"
    echo ""
    echo -e "  ${CYAN}serve${RST}                              🌐 Avvia la web dashboard (http://localhost:5000)"
    echo -e "  ${CYAN}setup${RST}                              Prima installazione completa"
    echo -e "  ${CYAN}update [fonte] [lega]${RST}              Aggiorna dati (default: tutte le fonti)"
    echo -e "  ${CYAN}fixtures [lega] [giorni]${RST}           Prossime partite"
    echo -e "  ${CYAN}predict <casa> <ospite> [lega]${RST}     Previsione partita singola"
    echo -e "  ${CYAN}predict-all [lega]${RST}                 Previsioni prossimo turno"
    echo -e "  ${CYAN}team <squadra> [lega]${RST}              Profilo squadra"
    echo -e "  ${CYAN}fit [lega|all]${RST}                     Ri-fitta il modello (default: all)"
    echo -e "  ${CYAN}daily${RST}                              Routine giornaliera automatica"
    echo ""
    echo -e "  ${BOLD}Leghe:${RST} serie_a  premier_league  bundesliga  la_liga  ligue_1"
    echo -e "         champions_league  europa_league  conference_league"
    echo ""
    echo -e "  ${BOLD}Esempi:${RST}"
    echo -e "  ${GRAY}./football.sh setup${RST}               ← prima installazione"
    echo -e "  ${GRAY}./football.sh serve${RST}               ← apri il browser su localhost:5000"
    echo -e "  ${GRAY}./football.sh daily${RST}               ← aggiornamento quotidiano"
    echo ""
}

# ── Dispatch ──────────────────────────────────────────────────────────────────

COMMAND="${1:-help}"
shift 2>/dev/null || true

case "$COMMAND" in
    serve)        cmd_serve "$@" ;;
    setup)        cmd_setup "$@" ;;
    update)       cmd_update "$@" ;;
    fixtures)     cmd_fixtures "$@" ;;
    predict)      cmd_predict "$@" ;;
    predict-all)  cmd_predict_all "$@" ;;
    team)         cmd_team "$@" ;;
    fit)          cmd_fit "$@" ;;
    daily)        cmd_daily "$@" ;;
    help|--help|-h) cmd_help ;;
    *)
        err "Comando sconosciuto: $COMMAND"
        cmd_help
        exit 1
        ;;
esac
