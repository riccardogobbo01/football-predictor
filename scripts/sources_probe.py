#!/usr/bin/env python3
"""Sonda delle fonti alternative per tiri e giocatori (round 13): FotMob e Sofascore. SOLO sonda: poche richieste, pausa di 1,5 s, nessun download massivo.

FotMob: pagine pubbliche (consentite dal robots.txt, che vieta solo /api/* ai crawler generici): la pagina di una lega elenca le partite (`pageProps.fixtures.allMatches`)
e la pagina di una partita incorpora i dati in `__NEXT_DATA__` (`content.shotmap`, `content.playerStats`, `content.lineup`, `content.matchFacts.events`).
Sofascore: API `https://api.sofascore.com/api/v1/event/{id}/shotmap|lineups|statistics`; da un client normale risponde 403 (nessun tentativo di aggirare la protezione).

Modalita':
  python scripts/sources_probe.py depth     # FotMob, una partita per stagione dal 2016/17 e per lega, e ricerca di un rigore (circa 70 pagine da 1 MB, ~5 minuti)
  python scripts/sources_probe.py ci        # UNA partita per fonte (usata dal workflow di prova di GitHub Actions)
I riepiloghi vanno in data/cache/sources_probe/ (ignorata da git) e in stdout."""
import json
import os
import re
import sys
import time

import requests

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO_ROOT, "data", "cache", "sources_probe")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
PAUSE = 1.5
LEAGUES = {"I1": (55, "serie"), "E0": (47, "premier-league"), "D1": (54, "bundesliga"), "SP1": (87, "laliga"), "F1": (53, "ligue-1")}
NEXT = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


def session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    return s


def fm_page(s, path):
    """(status, byte, __NEXT_DATA__ | None)."""
    r = s.get("https://www.fotmob.com" + path, timeout=40)
    m = NEXT.search(r.text) if r.status_code == 200 else None
    return r.status_code, len(r.content), (json.loads(m.group(1)) if m else None)


def fm_league(s, lid, slug, season=None):
    q = f"?season={season.replace('/', '%2F')}" if season else ""
    st, n, d = fm_page(s, f"/leagues/{lid}/overview/{slug}{q}")
    if d is None:
        return st, None, []
    pp = d["props"]["pageProps"]
    am = [m for m in (pp.get("fixtures") or {}).get("allMatches", []) if m.get("status", {}).get("finished") and not m["status"].get("cancelled")]
    return st, pp.get("details", {}).get("selectedSeason"), am


def fm_summary(d):
    """Riepilogo dei dati utili di una pagina partita FotMob."""
    c = (d["props"]["pageProps"].get("content") or {})
    shots = ((c.get("shotmap") or {}).get("shots")) or []
    ps = c.get("playerStats") or {}
    names = set()
    for p in ps.values():
        for g in p.get("stats") or []:
            names |= set((g.get("stats") or {}).keys())
    evs = ((c.get("matchFacts") or {}).get("events") or {}).get("events") or []
    out = {"shots": len(shots), "xg_shots": sum(1 for x in shots if x.get("expectedGoals") is not None), "penalties": sum(1 for x in shots if x.get("situation") == "Penalty"),
           "own_goals": sum(1 for x in shots if x.get("isOwnGoal")), "situations": sorted({x.get("situation") for x in shots if x.get("situation")}),
           "players_with_stats": len(ps), "fouls_committed": "Fouls committed" in names, "was_fouled": "Was fouled" in names, "total_shots": "Total shots" in names,
           "shots_on_target": "Shots on target" in names, "saves": "Saves" in names, "minutes": "Minutes played" in names, "xg_player": "Expected goals (xG)" in names,
           "cards": sum(1 for e in evs if e.get("type") == "Card"), "subs": sum(1 for e in evs if e.get("type") == "Substitution"),
           "starters_h": len(((c.get("lineup") or {}).get("homeTeam") or {}).get("starters") or [])}
    return out


def depth():
    os.makedirs(OUT, exist_ok=True)
    s = session()
    res = {}
    seasons = [f"{y}/{y + 1}" for y in range(2016, 2026)]
    plan = [(dv, se) for dv in ("I1", "E0") for se in seasons] + [(dv, se) for dv in ("D1", "SP1", "F1") for se in ("2016/2017", "2018/2019", "2020/2021", "2022/2023", "2025/2026")]
    for dv, se in plan:
        lid, slug = LEAGUES[dv]
        try:
            st, sel, am = fm_league(s, lid, slug, se)
            time.sleep(PAUSE)
            if not am:
                print(f"{dv} {se}: elenco partite non disponibile (HTTP {st})")
                res[f"{dv}|{se}"] = {"error": f"league HTTP {st}"}
                continue
            m = [x for x in am if str(x.get("roundName")) == "10"] or am
            m = m[len(m) // 2]
            st2, n, d = fm_page(s, m["pageUrl"])
            time.sleep(PAUSE)
            if d is None:
                print(f"{dv} {se}: pagina partita HTTP {st2}")
                res[f"{dv}|{se}"] = {"error": f"match HTTP {st2}", "id": m["id"]}
                continue
            sm = fm_summary(d)
            sm.update(id=m["id"], page_bytes=n, date=m["status"]["utcTime"][:10], match=f"{m['home']['name']}-{m['away']['name']} {m['status'].get('scoreStr')}", season_shown=sel)
            res[f"{dv}|{se}"] = sm
            print(f"{dv} {se}: {sm['match']} ({sm['date']}) tiri {sm['shots']} (xG {sm['xg_shots']}), giocatori {sm['players_with_stats']}, falli {sm['fouls_committed']}/{sm['was_fouled']}, "
                  f"tiri/porta/parate {sm['total_shots']}/{sm['shots_on_target']}/{sm['saves']}, minuti {sm['minutes']}, cartellini {sm['cards']}, cambi {sm['subs']}")
        except Exception as e:                                                      # una pagina che fallisce non ferma la sonda
            print(f"{dv} {se}: ERRORE {type(e).__name__} {str(e)[:80]}")
            res[f"{dv}|{se}"] = {"error": f"{type(e).__name__}"}
    json.dump(res, open(os.path.join(OUT, "fotmob_depth.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # ricerca di un rigore: partite di Serie A 2025/26 (al massimo 14 pagine)
    st, sel, am = fm_league(s, *LEAGUES["I1"], "2025/2026")
    time.sleep(PAUSE)
    found = None
    for m in am[10:60:3][:14]:
        st2, n, d = fm_page(s, m["pageUrl"])
        time.sleep(PAUSE)
        if d is None:
            continue
        sm = fm_summary(d)
        if sm["penalties"]:
            found = (m, d, sm)
            break
    if found:
        m, d, sm = found
        pen = [x for x in d["props"]["pageProps"]["content"]["shotmap"]["shots"] if x.get("situation") == "Penalty"]
        print(f"\nRIGORE: {m['home']['name']}-{m['away']['name']} {m['status'].get('scoreStr')} ({m['status']['utcTime'][:10]}), id {m['id']}")
        print(json.dumps(pen[0], ensure_ascii=False)[:900])
        json.dump(d, open(os.path.join(OUT, f"fotmob_penalty_{m['id']}.json"), "w", encoding="utf-8"), ensure_ascii=False)
    else:
        print("\nNessun rigore nelle partite provate")


def ci():
    """Una partita per fonte; esce con 0 anche se una fonte e' bloccata (serve il rapporto, non il successo)."""
    s = session()
    print("== FotMob (pagine pubbliche)")
    try:
        st, sel, am = fm_league(s, *LEAGUES["I1"], "2025/2026")
        print(f"pagina lega Serie A: HTTP {st}, stagione {sel}, partite finite {len(am)}")
        time.sleep(PAUSE)
        if am:
            m = am[9]
            st2, n, d = fm_page(s, m["pageUrl"])
            print(f"pagina partita {m['home']['name']}-{m['away']['name']} ({m['id']}): HTTP {st2}, {n} byte, NEXT_DATA {'si' if d else 'NO'}")
            if d:
                print("riepilogo:", json.dumps(fm_summary(d)))
    except Exception as e:
        print("FotMob ERRORE:", type(e).__name__, str(e)[:120])
    print("== Sofascore (API, client normale)")
    for u in ("https://api.sofascore.com/api/v1/unique-tournament/23/seasons", "https://api.sofascore.com/api/v1/event/12436900/shotmap"):
        try:
            r = s.get(u, timeout=30)
            print(f"HTTP {r.status_code} {r.headers.get('content-type')} {len(r.content)} byte server={r.headers.get('server')} cf-ray={r.headers.get('cf-ray')} | {r.text[:100]!r} | {u}")
        except Exception as e:
            print("Sofascore ERRORE:", type(e).__name__, str(e)[:120])
        time.sleep(PAUSE)
    try:
        ip = requests.get("https://api.ipify.org", timeout=15).text
        print("IP uscente:", ip[:3] + "...")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "ci"
    sys.exit(ci() if mode == "ci" else depth() or 0)
