"""
Arbitri designati della Serie A da fonti che li pubblicano prima di football-data.org.

football-data.org pubblica l'arbitro solo la mattina della partita; l'AIA (Commissione Arbitri Nazionale) rende note le designazioni
il mercoledì per le partite da venerdì a lunedì. Ordine delle fonti (solo Serie A):

  1. AIA     https://www.aia-figc.it/designazioni/can/  (elenco) + la pagina «SERIE A ... DESIGNAZIONI Na GIORNATA» piu' recente: 2 richieste
  2. fantacalcio.it  l'articolo «Serie A: le designazioni arbitrali della Na giornata» (stessa tabella dell'AIA); l'URL contiene un numero
     non prevedibile, quindi si cerca nelle prime pagine dell'elenco delle notizie di Serie A (solo se l'AIA non e' utilizzabile)
  3. football-data.org (campo `referees`, gia' in `fixtures` da get_fixtures)

Se la pagina AIA non risponde o cambia struttura (nessuna partita riconosciuta) il parser non solleva eccezioni: scrive un avviso nel log
(`log.warning`, visibile nel workflow) e si passa alla fonte successiva. Il nome dell'arbitro diventa il nome «alla football-data.org»
(es. «Marco Di Bello») cosi' da usare gli alias e l'effetto arbitro gia' esistenti (backtest/referee_aliases.py); un arbitro senza storico
ha come chiave il proprio nome (effetto zero). Per ogni partita si registra la fonte (`referee_source`).
"""
import html as htmllib
import logging
import re
import unicodedata

import requests

from backtest import referees as RF
from backtest.referee_aliases import AIA_ALIASES, REFEREE_ALIASES

log = logging.getLogger(__name__)

AIA_BASE = "https://www.aia-figc.it"
AIA_LIST = AIA_BASE + "/designazioni/can/"
FANTA_LISTS = ["https://www.fantacalcio.it/news/calcio-italia/serie-a", "https://www.fantacalcio.it/news/calcio-italia"]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; football-predictor/1.0; +https://github.com/riccardogobbo01/football-predictor)"}
TIMEOUT = 20
SOURCE_AIA, SOURCE_FANTA, SOURCE_FDO = "aia", "fantacalcio", "football-data.org"

_DASH = r"[–\-—]"
_TEAMS = re.compile(rf"^(?P<h>[A-ZÀ-ÝÇ0-9][A-ZÀ-ÝÇ0-9'. ]*?)\s+{_DASH}\s+(?P<a>[A-ZÀ-ÝÇ0-9][A-ZÀ-ÝÇ0-9'. ]*?)(?P<rest>\s{{2,}}.*|\s+(?:Luned|Marted|Mercoled|Gioved|Venerd|Sabato|Domenica).*)?$")
_DATE = re.compile(r"(\d{1,2})/(\d{1,2})")
_TIME = re.compile(r"h\.?\s*(\d{1,2})[.:](\d{2})")
_ASSIST = re.compile(r"^(IV|VAR|AVAR)\s*:", re.I)


# ───────────────────────────── testo -> token ─────────────────────────────
def tokens_from_html(raw: str, start_marker: str | None = None, end_marker: str | None = None) -> list[str]:
    """Pezzi di testo del documento (un token per blocco: p, td, tr, li, br, h*), con spazi normalizzati, senza i vuoti."""
    if start_marker and start_marker in raw:
        raw = raw[raw.index(start_marker):]
    if end_marker and end_marker in raw:
        raw = raw[:raw.index(end_marker)]
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    raw = re.sub(r"(?i)</?(p|div|tr|td|th|li|ul|ol|br|h[1-6]|table|tbody|thead|section|article)\b[^>]*>", "\n", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    text = htmllib.unescape(raw).replace("\xa0", " ").replace("﻿", "")
    out = []
    for line in text.split("\n"):
        t = re.sub(r"\s+", " ", line).strip()
        if t:
            out.append(t)
    return out


def parse_designations(tokens: list[str]) -> list[dict]:
    """Partite con arbitro: [{home, away, day, month, hour, minute, referee}] (nomi in maiuscolo come pubblicati).
    Una partita inizia con «CASA – OSPITE» seguito (nello stesso token o nei successivi 3) dalla data «gg/mm» e dall'ora «h. hh.mm»;
    l'arbitro e' il primo token alfabetico dopo l'ora (non «IV:», «VAR:», «AVAR:» e non una coppia di assistenti «A – B»)."""
    out = []
    n = len(tokens)
    i = 0
    while i < n:
        m = _TEAMS.match(tokens[i])
        if not m:
            i += 1
            continue
        window = " ".join(tokens[i:i + 4])
        d, t = _DATE.search(window), _TIME.search(window)
        if not d or not t:
            i += 1
            continue
        # il token dell'arbitro e' il primo dopo quello che contiene l'ora
        j = i
        while j < min(n, i + 4) and not _TIME.search(tokens[j]):
            j += 1
        k = j + 1
        referee = None
        while k < min(n, j + 4):
            tk = tokens[k]
            if _ASSIST.match(tk) or re.search(_DASH, tk):
                break
            tk = re.sub(r"\(.*$", "", tk).strip()
            if re.fullmatch(r"[A-ZÀ-ÝÇ' .]{2,}", tk):
                referee = tk
                break
            k += 1
        if referee:
            out.append(dict(home=m.group("h").strip(), away=m.group("a").strip(), day=int(d.group(1)), month=int(d.group(2)),
                            hour=int(t.group(1)), minute=int(t.group(2)), referee=referee))
            i = k + 1
            if i < n and re.search(_DASH, tokens[i]) and not _DATE.search(tokens[i]):      # riga degli assistenti («A – B»): non e' una partita
                i += 1
        else:
            i += 1
    return out


# ───────────────────────────── nomi ─────────────────────────────
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]+", " ", s)


_STOP = {"fc", "ac", "as", "us", "ss", "ssc", "afc", "calcio", "1907", "1913", "1909", "1927", "hellas", "sc", "cfc", "bc"}


def _team_tokens(s: str) -> set:
    return {w for w in _norm(s).split() if w not in _STOP}


def same_team(aia_name: str, fixture_name: str) -> bool:
    a, b = _team_tokens(aia_name), _team_tokens(fixture_name)
    return bool(a) and bool(b) and (a <= b or b <= a)


def _canonical_keys(division: str = "I1", extra_keys=()) -> dict:
    """{chiave canonica: nome «alla football-data.org» (titolo)} per gli arbitri noti della lega: quelli con alias (indicati da
    football-data.org) e quelli con storico (`extra_keys`, chiavi canoniche di models/stack.json["referees"])."""
    names = {}
    for alias, key in REFEREE_ALIASES.get(division, {}).items():
        names.setdefault(key, alias)
    out = {k: v.title() for k, v in names.items()}
    for k in extra_keys:
        out.setdefault(k, k.title())
    return out


def display_name(aia_referee: str, division: str = "I1", extra_keys=()) -> tuple:
    """(nome «alla football-data.org», noto) per un cognome AIA («DI BELLO», «SACCHI J.L.»). Alias esplicito (AIA_ALIASES) per i cognomi
    ambigui; altrimenti l'unico arbitro noto con quel cognome; senza corrispondenza il cognome in maiuscole/minuscole (effetto zero)."""
    sur = re.sub(r"\b[A-Z]\.", " ", aia_referee)                  # toglie le iniziali («J.L.»)
    sur = _norm(sur).strip()
    known = _canonical_keys(division, extra_keys)
    key = AIA_ALIASES.get(division, {}).get(sur)
    if key is None:
        cand = [k for k in known if k == sur or k.endswith(" " + sur)]
        if len(cand) == 1:
            key = cand[0]
        elif len(cand) > 1:
            log.warning("  Arbitro AIA «%s»: cognome ambiguo tra %s, serve un alias in AIA_ALIASES (effetto zero finche' non c'e')", aia_referee, cand)
    if key is not None and key in known:
        return known[key], True
    return sur.title(), False


# ───────────────────────────── fonti ─────────────────────────────
def _get(url: str, session=None) -> str:
    r = (session or requests).get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.content.decode("utf-8", "replace")


def aia_latest_page_url(list_html: str) -> str | None:
    """Link della pagina «SERIE A ... DESIGNAZIONI Na GIORNATA» con N piu' alto nell'elenco CAN."""
    best, best_n = None, -1
    for href, text in re.findall(r'<a[^>]+href="([^"]*dettaglio\.asp\?ID=\d+)"[^>]*>(.*?)</a>', list_html, flags=re.S | re.I):
        t = re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", text))).strip().upper()
        m = re.search(r"DESIGNAZIONI\s+(\d+)\s*[AaªA^]?\s*GIORNATA", t)
        if "SERIE A" in t and "SERIE B" not in t and "BKT" not in t and m and int(m.group(1)) > best_n:
            best, best_n = href, int(m.group(1))
    if best is None:
        return None
    return best if best.startswith("http") else AIA_BASE + (best if best.startswith("/") else "/" + best)


def fetch_aia(session=None) -> list | None:
    """Designazioni AIA della giornata piu' recente (2 richieste). None se la pagina non risponde o la struttura non e' riconosciuta."""
    try:
        url = aia_latest_page_url(_get(AIA_LIST, session))
        if not url:
            log.warning("  Arbitri AIA: nessuna pagina «SERIE A ... DESIGNAZIONI» riconosciuta nell'elenco %s (struttura cambiata?)", AIA_LIST)
            return None
        toks = tokens_from_html(_get(url, session), start_marker='id="content"', end_marker="Supplemento on-line")
        ds = parse_designations(toks)
        if not ds:
            log.warning("  Arbitri AIA: nessuna partita riconosciuta in %s (struttura cambiata?)", url)
            return None
        log.info("  Arbitri AIA: %d partite con arbitro (%s)", len(ds), url)
        return ds
    except Exception as e:                                          # rete, HTTP, parsing: mai bloccare la generazione
        log.warning("  Arbitri AIA non disponibili (%s: %s): si passa al ripiego", type(e).__name__, e)
        return None


def fetch_fantacalcio(session=None) -> list | None:
    """Designazioni dall'articolo di fantacalcio.it piu' recente trovato nell'elenco delle notizie di Serie A (solo ripiego)."""
    try:
        for lst in FANTA_LISTS:
            links = re.findall(r'href="((?:https://www\.fantacalcio\.it)?/news/calcio-italia/\d{2}_\d{2}_\d{4}/serie-a-le-designazioni-arbitrali[^"]*)"', _get(lst, session))
            if links:
                url = links[0] if links[0].startswith("http") else "https://www.fantacalcio.it" + links[0]
                ds = parse_designations(tokens_from_html(_get(url, session), start_marker="article-body"))
                if ds:
                    log.info("  Arbitri fantacalcio.it: %d partite con arbitro (%s)", len(ds), url)
                    return ds
                log.warning("  Arbitri fantacalcio.it: nessuna partita riconosciuta in %s (struttura cambiata?)", url)
                return None
        log.warning("  Arbitri fantacalcio.it: articolo delle designazioni non trovato nell'elenco delle notizie")
    except Exception as e:
        log.warning("  Arbitri fantacalcio.it non disponibili (%s: %s)", type(e).__name__, e)
    return None


def _year_for(day: int, month: int, today) -> int:
    import datetime as dt
    t = today.date() if hasattr(today, "date") else today
    best = min((t.year - 1, t.year, t.year + 1), key=lambda y: abs((dt.date(y, month, day) - t).days))
    return best


def apply_serie_a(fixtures: list[dict], today, session=None, fetchers=None, known_keys=()) -> dict:
    """Imposta `referee` e `referee_source` (aia | fantacalcio | football-data.org) sulle fixture di Serie A (in place).
    football-data.org e' la fonte di ripiego ma, se pubblica un arbitro diverso da quello AIA per la stessa partita (cambio dell'ultimo momento),
    prevale perche' e' piu' recente (il conflitto e' scritto nel log). Restituisce {"aia": n, "fantacalcio": n, "football-data.org": n}."""
    counts = {SOURCE_AIA: 0, SOURCE_FANTA: 0, SOURCE_FDO: 0}
    fetchers = fetchers or [(SOURCE_AIA, fetch_aia), (SOURCE_FANTA, fetch_fantacalcio)]
    ds, src = None, None
    for name, fn in fetchers:
        ds = fn(session)
        if ds:
            src = name
            break
    for fix in fixtures:
        fdo = fix.get("referee")
        found = None
        if ds:
            for d in ds:
                year = _year_for(d["day"], d["month"], today)
                if (f"{year}-{d['month']:02d}-{d['day']:02d}" == fix["date"] or abs((_to_date(fix["date"]) - _to_date(f"{year}-{d['month']:02d}-{d['day']:02d}")).days) <= 1) \
                        and same_team(d["home"], fix["home"]) and same_team(d["away"], fix["away"]):
                    found = d
                    break
        if found is not None:
            name, _known = display_name(found["referee"], "I1", known_keys)
            if fdo and RF.normalize(fdo) != RF.normalize(name) and _norm(fdo.split()[-1]) != _norm(name.split()[-1]):
                log.warning("  Arbitro %s - %s: %s indica %s, football-data.org %s: si usa football-data.org (piu' recente)", fix["home"], fix["away"], src, name, fdo)
                fix["referee_source"] = SOURCE_FDO
                counts[SOURCE_FDO] += 1
            else:
                fix["referee"] = fdo or name
                fix["referee_source"] = src
                counts[src] += 1
        elif fdo:
            fix["referee_source"] = SOURCE_FDO
            counts[SOURCE_FDO] += 1
    return counts


def _to_date(s: str):
    import datetime as dt
    return dt.date.fromisoformat(s)
