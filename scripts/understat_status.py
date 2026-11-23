#!/usr/bin/env python3
"""Controllo di Understat: risponde con JSON o con la pagina di manutenzione («We will come back soon»)? Una sola richiesta leggera (getLeagueData della Serie A 2026).
Uscita: 0 = online (JSON con `dates`), 3 = manutenzione o risposta non JSON, 4 = errore di rete. Stampa una riga.
Usato dall'attivita' pianificata `understat-controllo`; quando risulta online si lancia scripts/understat_match_probe.py."""
import re
import sys

import requests

URL = "https://understat.com/getLeagueData/Serie%20A/2026"
HEAD = {"X-Requested-With": "XMLHttpRequest", "User-Agent": "Mozilla/5.0 (football-predictor status check)"}


def main() -> int:
    try:
        r = requests.get(URL, headers=HEAD, timeout=30)
    except requests.RequestException as e:
        print(f"ERRORE DI RETE: {type(e).__name__}")
        return 4
    try:
        d = r.json()
    except ValueError:
        t = re.sub(r"<(svg|style|script).*?</\1>", "", r.text, flags=re.S)
        txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)).strip()[:80]
        print(f"MANUTENZIONE: HTTP {r.status_code}, non JSON: «{txt}» (Last-Modified {r.headers.get('Last-Modified')})")
        return 3
    if isinstance(d, dict) and d.get("dates"):
        played = sum(1 for m in d["dates"] if m.get("isResult"))
        print(f"ONLINE: getLeagueData Serie A 2026 risponde, {played} partite giocate")
        return 0
    print(f"RISPOSTA INATTESA: JSON senza `dates` ({str(d)[:80]})")
    return 3


if __name__ == "__main__":
    sys.exit(main())
