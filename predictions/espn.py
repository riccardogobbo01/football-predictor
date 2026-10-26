"""
Risultati e statistiche delle partite finite dall'API pubblica di ESPN (site.api.espn.com, scoreboard per data), usata come ripiego quando
football-data.co.uk non e' ancora aggiornato (campionati) e come unica fonte per l'Europa League / Conference League (football-data.org: 403) e per le
statistiche delle coppe. Verificata identica a football-data.co.uk per tiri in porta, falli, corner e gol (round 8: backtest/results_round8.md).

Per ogni partita finita: gol dei 90 minuti, gol del primo tempo, tiri, tiri in porta, corner, falli, gialli (squadra di casa e ospite). I gialli non
sono tra le statistiche di squadra dello scoreboard: si contano dagli eventi della partita (`details`, cartellini gialli; il secondo giallo vale uno).
Nessuna chiave; una richiesta per (competizione, giorno). Se l'API non risponde le funzioni restituiscono [] e scrivono un avviso nel log.
Differenze note rispetto al CSV (308 partite 2026/27 confrontate): gol e gol del primo tempo identici; tiri in porta 99,7%, tiri totali 97,7%,
corner 98,5%, falli 98,9% uguali; gialli di una squadra uguali nell'87% delle partite (±1 nel resto): i valori ESPN restano provvisori (`result_source`
= "espn") e vengono sostituiti dal CSV appena football-data.co.uk lo aggiorna.
"""
import logging
import re
import time
from datetime import date, datetime, timedelta

import requests

log = logging.getLogger(__name__)

BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard"
CODES = {"serie_a": "ita.1", "premier_league": "eng.1", "bundesliga": "ger.1", "la_liga": "esp.1", "ligue_1": "fra.1",
         "ucl": "uefa.champions", "uel": "uefa.europa", "uecl": "uefa.europa.conf"}
# nomi ESPN -> nome usato dai CSV di football-data.co.uk (solo dove la somiglianza dei token non basta)
ALIASES = {"FC Cologne": "FC Koln", "Atlético Madrid": "Ath Madrid", "Athletic Club": "Ath Bilbao", "Deportivo": "La Coruna",
           "Stade Rennais": "Rennes", "Espanyol": "Espanol", "Real Sociedad": "Sociedad", "Paris Saint-Germain": "Paris SG",
           "Borussia Mönchengladbach": "M'gladbach", "Hamburg SV": "Hamburg", "Eintracht Frankfurt": "Ein Frankfurt",
           "Real Betis": "Betis", "Celta Vigo": "Celta", "Inter Milan": "Inter", "AC Milan": "Milan", "Manchester United": "Man United",
           "Manchester City": "Man City", "Newcastle United": "Newcastle", "Nottingham Forest": "Nott'm Forest", "Leeds United": "Leeds",
           "Wolverhampton Wanderers": "Wolves", "Hull City": "Hull", "Ipswich Town": "Ipswich", "1899 Hoffenheim": "Hoffenheim",
           "Slavia Prague": "Slavia Praha", "Hapoel Be'er": "Beer-Sheva", "Hapoel Be'er Sheva": "Beer-Sheva", "Union St.-Gilloise": "St Gillis"}



HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; football-predictor/1.0)"}
STAT_KEYS = {"totalShots": "shots", "shotsOnTarget": "sot", "wonCorners": "corners", "foulsCommitted": "fouls"}

_MIN = re.compile(r"^(\d+)'(?:\+(\d+)')?$")


def _minute(display: str):
    """(minuto, recupero) da «45'+2'» -> (45, 2); None se non riconosciuto."""
    m = _MIN.match((display or "").strip())
    return (int(m.group(1)), int(m.group(2) or 0)) if m else None


def parse_event(ev: dict) -> dict | None:
    """Partita finita (stato `post`) dal JSON di un evento dello scoreboard; None se non finita o senza squadre."""
    try:
        comp = ev["competitions"][0]
        if ev["status"]["type"]["state"] != "post":
            return None
        teams = {t["homeAway"]: t for t in comp["competitors"]}
        h, a = teams["home"], teams["away"]
        ids = {h["team"]["id"]: "h", a["team"]["id"]: "a"}
        hg90, ag90 = int(h["score"]), int(a["score"])
        ht = {"h": 0, "a": 0}
        yel = {"h": 0, "a": 0}
        reg = {"h": 0, "a": 0}
        any_goal_detail = False
        ys = {"h": [], "a": []}                  # atleti ammoniti per squadra (per riconoscere i rossi per doppia ammonizione)
        reds = {"h": [], "a": []}
        for d in comp.get("details", []) or []:
            side = ids.get((d.get("team") or {}).get("id"))
            if side is None:
                continue
            mn = _minute((d.get("clock") or {}).get("displayValue"))
            if d.get("scoringPlay") and not d.get("shootout"):
                any_goal_detail = True
                if mn is not None and mn[0] <= 90:                       # tempi regolamentari (compreso il recupero), esclusi supplementari
                    reg[side] += 1
                    if mn[0] < 45 or (mn[0] == 45):
                        ht[side] += 1
            if d.get("yellowCard"):
                yel[side] += 1
                ys[side] += [a.get("id") for a in d.get("athletesInvolved", []) or []]
            elif d.get("redCard"):
                reds[side].append([a.get("id") for a in d.get("athletesInvolved", []) or []])
        for side in ("h", "a"):                  # un rosso dello stesso giocatore già ammonito = secondo giallo: football-data.co.uk lo conta come rosso
            yel[side] -= sum(1 for r in reds[side] if r and any(x in ys[side] for x in r))
        # supplementari / rigori: il punteggio dei 90 minuti viene dagli eventi
        stype = ev["status"]["type"]["name"]
        if stype in ("STATUS_FINAL_AET", "STATUS_FINAL_PEN") and any_goal_detail:
            hg90, ag90 = reg["h"], reg["a"]
        st = {"h": {}, "a": {}}
        for side, t in (("h", h), ("a", a)):
            for s in t.get("statistics", []) or []:
                k = STAT_KEYS.get(s.get("name"))
                if k is not None:
                    try:
                        st[side][k] = float(s["displayValue"])
                    except (TypeError, ValueError):
                        pass
        out = {"espn_id": ev["id"], "date": ev["date"][:10], "kickoff": ev["date"][:10] + " " + ev["date"][11:16], "status": stype,
               "home": h["team"]["displayName"], "away": a["team"]["displayName"],
               "home_short": h["team"].get("shortDisplayName") or h["team"]["displayName"], "away_short": a["team"].get("shortDisplayName") or a["team"]["displayName"],
               "hg": hg90, "ag": ag90, "ht_goals": (ht["h"] + ht["a"]) if any_goal_detail else (0 if hg90 + ag90 == 0 else None), "yellow_h": yel["h"], "yellow_a": yel["a"]}
        for k in STAT_KEYS.values():
            out[f"{k}_h"], out[f"{k}_a"] = st["h"].get(k), st["a"].get(k)
        return out
    except Exception as e:                                               # un evento con struttura inattesa non deve bloccare gli altri
        log.warning("  ESPN: evento non leggibile (%s: %s)", type(e).__name__, e)
        return None


def fetch_day(code: str, day, session=None, retries: int = 2) -> list:
    """Partite finite del giorno (UTC) per il codice ESPN (es. «ita.1»). [] e un avviso nel log se l'API non risponde."""
    d = day.strftime("%Y%m%d") if hasattr(day, "strftime") else str(day).replace("-", "")
    url = BASE.format(code=code)
    for attempt in range(retries + 1):
        try:
            r = (session or requests).get(url, params={"dates": d}, headers=HEADERS, timeout=30)
            r.raise_for_status()
            evs = r.json().get("events", [])
            return [m for m in (parse_event(e) for e in evs) if m]
        except (requests.RequestException, ValueError) as e:
            if attempt == retries:
                log.warning("  ESPN %s %s non disponibile (%s: %s)", code, d, type(e).__name__, e)
                return []
            time.sleep(3 * (attempt + 1))
    return []


def fetch_range(code: str, first, last, session=None) -> list:
    """Partite finite tra due date incluse (una richiesta per giorno)."""
    d0 = datetime.strptime(str(first)[:10], "%Y-%m-%d").date()
    d1 = datetime.strptime(str(last)[:10], "%Y-%m-%d").date()
    out = []
    d = d0
    while d <= d1:
        out += fetch_day(code, d, session)
        d += timedelta(days=1)
    return out


def as_finished(matches: list, cup_key: str) -> list:
    """Formato di `cups.apply_results` / `cups.match_to_fdo` (stesse chiavi di get_finished + le statistiche)."""
    return [{"cup": cup_key, "date": m["date"], "home": ALIASES.get(m["home_short"], m["home_short"]), "away": ALIASES.get(m["away_short"], m["away_short"]),
             "home_full": ALIASES.get(m["home"], m["home"]), "away_full": ALIASES.get(m["away"], m["away"]),
             "hg": m["hg"], "ag": m["ag"], "espn": m} for m in matches]


# ───────────────────────────── abbinamento con le righe dello storico ─────────────────────────────
def _sim(a, b) -> float:
    from predictions.cups import name_similarity
    return name_similarity(a, b)


def _names_for(ev_name: str, ev_short: str) -> list:
    out = [ev_name, ev_short]
    for n in (ev_name, ev_short):
        if n in ALIASES:
            out.append(ALIASES[n])
    return out


def match_event(row: dict, events: list, threshold: float = 0.8, max_days: int = 1):
    """Evento ESPN corrispondente a una riga dello storico (dict con match_date, home, away, home_dc, away_dc): data ±max_days e nomi simili per
    entrambe le squadre (confronto con home/away di football-data.org e con i nomi del CSV). None se non c'e'."""
    d0 = datetime.strptime(str(row["match_date"])[:10], "%Y-%m-%d")
    best, best_s = None, threshold
    mine_h = [x for x in (row.get("home"), row.get("home_dc")) if isinstance(x, str)]
    mine_a = [x for x in (row.get("away"), row.get("away_dc")) if isinstance(x, str)]
    for ev in events:
        if abs((datetime.strptime(ev["date"], "%Y-%m-%d") - d0).days) > max_days:
            continue
        sh = max(_sim(m, n) for m in mine_h for n in _names_for(ev["home"], ev["home_short"]))
        sa = max(_sim(m, n) for m in mine_a for n in _names_for(ev["away"], ev["away_short"]))
        if min(sh, sa) > best_s:
            best, best_s = ev, min(sh, sa)
    return best
