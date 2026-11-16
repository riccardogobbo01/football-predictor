"""JavaScript e CSS di MyCombo per la pagina statica (docs/index.html). Tutto il calcolo avviene nel browser: nessuna quota viene salvata o inviata.
CORE_JS = funzioni pure (etichette, valutazione delle giocate sugli scenari, probabilita' congiunta, valore atteso), collaudabili con Node;
UI_JS = sezione «MyCombo» del pannello di dettaglio (combo proposte con calcolo sulla quota Sisal, modalita' «componi tu»)."""

CORE_JS = r'''
var MCCORE = (function () {
  "use strict";
  var NCOL = 10;
  var COL = { hg: 0, ag: 1, hth: 2, ath: 3, tiri_c: 4, tiri_o: 5, sot_c: 6, sot_o: 7, corner_t: 8, gialli_t: 9 };
  var STAT = { tiri: "tiri", sot: "tiri in porta", corner: "corner", gialli: "gialli" };
  var RES = { "0": "1", "1": "X", "2": "2", "0,1": "1X", "0,2": "12", "1,2": "X2" };
  function n1(x) { return x.toFixed(1).replace(".", ","); }

  function label(s, h, a) {
    var k = s[0];
    if (k === "res") { return RES[s[1].join(",")]; }
    if (k === "htres") { return "1T: " + RES[s[1].join(",")]; }
    if (k === "gtot") { return (s[1] === "over" ? "Over " : "Under ") + n1(s[2]) + " gol"; }
    if (k === "btts") { return s[1] ? "Gol" : "No Gol"; }
    if (k === "htou") { return "1T Over " + n1(s[1]) + " gol"; }
    if (k === "team") { return (s[2] === "c" ? h : a) + (s[3] === "over" ? " Over " : " Under ") + n1(s[4]) + " " + STAT[s[1]]; }
    if (k === "tot") { return (s[2] === "over" ? "Over " : "Under ") + n1(s[3]) + " " + STAT[s[1]] + " totali" + (s[1] === "corner" ? " (indicativo)" : ""); }
    return "";
  }

  // funzione (dati, offset della riga) -> bool, per una giocata; i dati sono righe di NCOL byte (uno scenario per riga)
  function legFn(s) {
    var k = s[0], set, col;
    if (k === "res" || k === "htres") {
      set = s[1];
      var o1 = (k === "res") ? 0 : 2;
      return function (d, o) { var x = d[o + o1], y = d[o + o1 + 1]; return set.indexOf(x > y ? 0 : (x === y ? 1 : 2)) >= 0; };
    }
    if (k === "gtot") {
      return function (d, o) { var t = d[o] + d[o + 1]; return s[1] === "over" ? t > s[2] : t < s[2]; };
    }
    if (k === "btts") {
      return function (d, o) { var b = d[o] > 0 && d[o + 1] > 0; return s[1] ? b : !b; };
    }
    if (k === "htou") {
      return function (d, o) { return d[o + 2] + d[o + 3] > s[1]; };
    }
    if (k === "team") {
      col = COL[s[1] + "_" + s[2]];
      return function (d, o) { var x = d[o + col]; return s[3] === "over" ? x > s[4] : x < s[4]; };
    }
    if (k === "tot") {
      col = COL[s[1] + "_t"];
      return function (d, o) { var x = d[o + col]; return s[2] === "over" ? x > s[3] : x < s[3]; };
    }
    return function () { return false; };
  }

  function decode(b64) {
    var bin = atob(b64), u = new Uint8Array(bin.length), i;
    for (i = 0; i < bin.length; i++) { u[i] = bin.charCodeAt(i); }
    return u;
  }

  // probabilita' congiunta di una lista di giocate sugli stessi scenari; coppie che non si verificano mai insieme (incompatibili)
  function stats(specs, data, n) {
    var fns = specs.map(legFn), L = specs.length, per = [], pair = [], cnt = 0, i, j, k, o, all, t = [];
    for (j = 0; j < L; j++) { per.push(0); t.push(false); pair.push(new Array(L).fill(0)); }
    for (i = 0; i < n; i++) {
      o = i * NCOL; all = true;
      for (j = 0; j < L; j++) { t[j] = fns[j](data, o); if (t[j]) { per[j]++; } else { all = false; } }
      if (all) { cnt++; }
      for (j = 0; j < L; j++) { if (t[j]) { for (k = j + 1; k < L; k++) { if (t[k]) { pair[j][k]++; } } } }
    }
    var minp = Math.max(0.005 * n, 5), indep = 1, bad = [];
    for (j = 0; j < L; j++) { indep *= per[j] / n; }
    for (j = 0; j < L; j++) { for (k = j + 1; k < L; k++) { if (pair[j][k] === 0 && per[j] >= minp && per[k] >= minp) { bad.push([j, k]); } } }
    return { n: n, cnt: cnt, p: cnt / n, per: per.map(function (x) { return x / n; }), indep: indep, bad: bad };
  }

  function parseOdds(txt) {
    var v = parseFloat(String(txt === null || txt === undefined ? "" : txt).replace(",", ".").trim());
    return isFinite(v) ? v : NaN;
  }

  // valore atteso per 1 di puntata e margine implicito = quota equa / quota proposta - 1 (positivo = margine a favore del banco)
  function ev(p, odds) {
    if (!(p > 0) || !(odds > 1)) { return null; }
    return { ev: p * odds - 1, margin: (1 / p) / odds - 1, fair: 1 / p };
  }

  return { NCOL: NCOL, COL: COL, label: label, legFn: legFn, decode: decode, stats: stats, parseOdds: parseOdds, ev: ev, n1: n1 };
})();
if (typeof module !== "undefined") { module.exports = MCCORE; }
'''

UI_JS = r'''
var MCUI = (function () {
  "use strict";
  var M = MCCORE;
  var S = { f: null, data: null, n: 0, legs: [], loading: false };
  var NOTE = "Le combo hanno margini alti: una quota Sisal sotto la quota equa ha valore atteso negativo.";

  function esc(s) {
    return String(s === null || s === undefined ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function pc(v) { return (v * 100).toFixed(1).replace(".", ",") + "%"; }
  function od(v) { return v.toFixed(2).replace(".", ","); }
  function sg(v, d) { return (v >= 0 ? "+" : "−") + Math.abs(v * 100).toFixed(d === undefined ? 1 : d).replace(".", ",") + "%"; }

  function evHtml(p, txt) {
    var r = M.ev(p, M.parseOdds(txt));
    if (!r) { return ""; }
    return '<span class="' + (r.ev < 0 ? "mc-neg" : "mc-pos") + '"><b>Valore atteso</b> ' + sg(r.ev) + ' della puntata</span> · <b>Margine implicito</b> ' + sg(r.margin) +
      (r.margin < 0 ? ' (quota sopra la quota equa)' : '');
  }

  function lab(s, h, a) {
    var l = M.label(s, h, a), r = s[0] === "res" || s[0] === "htres" ? s[1] : null;
    if (r && r.length === 1) { l = l + (r[0] === 0 ? " · " + h : r[0] === 2 ? " · " + a : " · pareggio"); }
    return l;
  }
  function refNote(c) {
    return c.referee ? 'Gialli: la media attesa include l\'effetto dell\'arbitro designato (' + esc(c.referee) + ').' :
      'Gialli: arbitro non ancora designato, la media attesa non include l\'effetto arbitro (si aggiorna alla designazione).';
  }
  function html(f) {
    var c = f.combo, h = f.home, a = f.away, out = "";
    out += '<div class="pn-note">Combo costruite da ' + c.n.toLocaleString("it-IT") + ' scenari simulati della partita (punteggio, primo tempo, tiri, tiri in porta, corner, gialli e falli con le loro correlazioni). ' +
      'Ogni giocata è un evento sullo stesso scenario, quindi la probabilità congiunta tiene conto delle dipendenze. Quota equa = 1 / probabilità congiunta. Corner e gialli sono <b>indicativi</b> (stime meno precise). ' +
      'Validazione walk-forward 2022/23-2025/26 su 21.243 combo: probabilità prevista 36,7%, frequenza reale 36,9%.</div>';
    if (!c.combos.length) {
      return out + '<div class="pn-note">Nessuna combo con quota equa tra 2,00 e 3,00 per questa partita.</div>' + composeHtml(f);
    }
    c.combos.forEach(function (x, i) {
      var legs = x.specs.map(function (s) { return '<li>' + esc(lab(s, h, a)) + '</li>'; }).join("");
      out += '<div class="mc-combo" data-p="' + x.p + '"><div class="mc-title">Combo ' + (i + 1) + ' · ' + x.k + ' giocate</div><ul class="mc-legs">' + legs + '</ul>' +
        '<div class="mc-nums"><div><span>Probabilità congiunta</span><b>' + pc(x.p) + '</b></div><div><span>Quota equa</span><b>' + od(x.fair) + '</b></div>' +
        '<div><span>Come se fossero indipendenti</span><b>' + pc(x.p_indep) + '</b> <small>(quota ' + od(1 / x.p_indep) + ')</small></div></div>' +
        '<label class="mc-in">Quota Sisal <input class="mc-sisal" type="text" inputmode="decimal" placeholder="es. 3,10" autocomplete="off"></label><div class="mc-ev"></div></div>';
    });
    out += '<div class="pn-note warn">' + NOTE + '</div>';
    if (c.combos.some(function (x) { return x.specs.some(function (s) { return s[0] === "tot" && s[1] === "gialli"; }); })) { out += '<div class="pn-note">' + refNote(c) + '</div>'; }
    return out + composeHtml(f);
  }

  // ───────── componi tu ─────────
  var OU = [["over", "Over"], ["under", "Under"]];
  function range(a, b) { var r = [], x; for (x = a; x <= b + 1e-9; x += 1) { r.push([String(x), M.n1(x)]); } return r; }
  function markets(f) {
    return [
      { id: "res", name: "1X2", fields: [["v", "Esito", [["0", "1"], ["1", "X"], ["2", "2"]]]], spec: function (v) { return ["res", [+v.v]]; } },
      { id: "dc", name: "Doppia chance", fields: [["v", "Esito", [["0,1", "1X"], ["0,2", "12"], ["1,2", "X2"]]]], spec: function (v) { return ["res", v.v.split(",").map(Number)]; } },
      { id: "gtot", name: "Over/Under gol", fields: [["d", "", OU], ["l", "Linea", [["1.5", "1,5"], ["2.5", "2,5"], ["3.5", "3,5"]]]], spec: function (v) { return ["gtot", v.d, +v.l]; } },
      { id: "btts", name: "Gol / No Gol", fields: [["v", "", [["1", "Gol"], ["0", "No Gol"]]]], spec: function (v) { return ["btts", v.v === "1"]; } },
      { id: "htres", name: "Primo tempo: 1X2", fields: [["v", "Esito", [["0", "1"], ["1", "X"], ["2", "2"]]]], spec: function (v) { return ["htres", [+v.v]]; } },
      { id: "htou", name: "Primo tempo: Over gol", fields: [["l", "Linea", [["0.5", "0,5"], ["1.5", "1,5"]]]], spec: function (v) { return ["htou", +v.l]; } },
      { id: "tiri", name: "Tiri (squadra)", fields: [["s", "Squadra", [["c", f.home], ["o", f.away]]], ["d", "", OU], ["l", "Linea", range(3.5, 25.5)]], spec: function (v) { return ["team", "tiri", v.s, v.d, +v.l]; } },
      { id: "sot", name: "Tiri in porta (squadra)", fields: [["s", "Squadra", [["c", f.home], ["o", f.away]]], ["d", "", OU], ["l", "Linea", range(0.5, 12.5)]], spec: function (v) { return ["team", "sot", v.s, v.d, +v.l]; } },
      { id: "gialli", name: "Gialli totali", fields: [["d", "", OU], ["l", "Linea", range(0.5, 8.5)]], spec: function (v) { return ["tot", "gialli", v.d, +v.l]; } },
      { id: "corner", name: "Corner totali (indicativo)", fields: [["d", "", OU], ["l", "Linea", range(4.5, 16.5)]], spec: function (v) { return ["tot", "corner", v.d, +v.l]; } }
    ];
  }
  function sel(cls, key, opts, val) {
    return '<select class="' + cls + '" data-k="' + key + '">' + opts.map(function (o) {
      return '<option value="' + esc(o[0]) + '"' + (val !== undefined && String(val) === String(o[0]) ? ' selected' : '') + '>' + esc(o[1]) + '</option>';
    }).join("") + '</select>';
  }
  function fieldsHtml(mk, mid) {
    var m = mk.filter(function (x) { return x.id === mid; })[0];
    return m.fields.map(function (fl) {
      var def = null;
      if (fl[0] === "l") { def = (mid === "tiri") ? "11.5" : (mid === "sot") ? "3.5" : (mid === "gialli") ? "3.5" : (mid === "corner") ? "9.5" : (mid === "gtot") ? "2.5" : undefined; }
      return sel("mc-fld", fl[0], fl[2], def);
    }).join("");
  }
  function composeHtml(f) {
    var mk = markets(f);
    return '<div class="mc-compose"><div class="stat-cap">Componi tu · da 2 a 6 giocate</div>' +
      '<div class="pn-note">Scegli le giocate e inserisci la quota totale Sisal: la probabilità congiunta si calcola qui, nel tuo browser, sugli scenari simulati di questa partita (nulla viene salvato o inviato).</div>' +
      (f.combo.file ? '<button type="button" class="mc-load">Carica gli scenari della partita</button>' :
        '<div class="pn-note warn">Gli scenari di questa partita saranno disponibili da ' + f.combo.web_days + ' giorni prima del calcio d\'inizio.</div>') +
      '<div class="mc-ui" hidden><div class="mc-add">' + sel("mc-mkt", "m", mk.map(function (x) { return [x.id, x.name]; })) +
      '<span class="mc-fields">' + fieldsHtml(mk, "res") + '</span><button type="button" class="mc-addbtn">Aggiungi</button></div>' +
      '<div class="mc-chips"></div>' +
      '<label class="mc-in">Quota totale Sisal <input class="mc-odds" type="text" inputmode="decimal" placeholder="es. 5,40" autocomplete="off"></label>' +
      '<div class="mc-out"></div></div><div class="mc-msg pn-note"></div><div class="pn-note">' + refNote(f.combo) + '</div><div class="pn-note warn">' + NOTE + '</div></div>';
  }

  function recalc(box) {
    var chips = box.querySelector(".mc-chips"), out = box.querySelector(".mc-out"), f = S.f, h = f.home, a = f.away;
    chips.innerHTML = S.legs.map(function (s, i) {
      return '<span class="mc-chip">' + esc(lab(s, h, a)) + ' <button type="button" class="mc-del" data-i="' + i + '" aria-label="Rimuovi">×</button></span>';
    }).join("");
    if (S.legs.length < 2) { out.innerHTML = '<div class="pn-note">Aggiungi almeno 2 giocate (massimo 6).</div>'; return; }
    var st = M.stats(S.legs, S.data, S.n), html = "";
    if (st.bad.length) {
      html += '<div class="mc-bad"><b>Giocate incompatibili: probabilità zero.</b> ' + st.bad.map(function (b) {
        return '«' + esc(lab(S.legs[b[0]], h, a)) + '» e «' + esc(lab(S.legs[b[1]], h, a)) + '» non possono verificarsi insieme';
      }).join("; ") + '.</div>';
    } else if (st.cnt === 0) {
      html += '<div class="mc-bad"><b>Probabilità praticamente zero</b>: nessuno scenario su ' + S.n.toLocaleString("it-IT") + ' le soddisfa tutte (meno dello 0,02%).</div>';
    }
    html += '<div class="mc-nums"><div><span>Probabilità congiunta</span><b>' + pc(st.p) + '</b></div><div><span>Quota equa</span><b>' + (st.cnt ? od(1 / st.p) : "∞") + '</b></div>' +
      '<div><span>Come se fossero indipendenti</span><b>' + pc(st.indep) + '</b></div></div>';
    if (st.cnt > 0 && st.cnt < 30) { html += '<div class="pn-note warn">Evento molto raro: stima su soli ' + st.cnt + ' scenari su ' + S.n.toLocaleString("it-IT") + ', molto incerta.</div>'; }
    html += '<div class="pn-note">Singole: ' + st.per.map(function (p, i) { return esc(lab(S.legs[i], h, a)) + ' ' + pc(p); }).join(" · ") +
      '. Stima su ' + S.n.toLocaleString("it-IT") + ' scenari (errore standard fino a ±' + (50 / Math.sqrt(S.n)).toFixed(1).replace(".", ",") + ' punti).</div>';
    html += '<div class="mc-ev">' + (st.cnt ? evHtml(st.p, box.querySelector(".mc-odds").value) : "") + '</div>';
    out.innerHTML = html;
  }

  function load(box, btn) {
    var msg = box.querySelector(".mc-msg");
    if (S.data || S.loading) { return; }
    S.loading = true;
    btn.disabled = true;
    msg.textContent = "Caricamento degli scenari…";
    fetch(S.f.combo.file).then(function (r) {
      if (!r.ok) { throw new Error("HTTP " + r.status); }
      return r.arrayBuffer();
    }).then(function (buf) {
      S.data = new Uint8Array(buf); S.n = Math.floor(buf.byteLength / M.NCOL); S.loading = false;
      msg.textContent = "";
      btn.hidden = true;
      box.querySelector(".mc-ui").hidden = false;
      recalc(box);
    }).catch(function (e) {
      S.loading = false; btn.disabled = false;
      msg.textContent = "Scenari non disponibili (" + e.message + "). La modalità «componi tu» funziona dal sito pubblicato, non aprendo il file in locale.";
    });
  }

  function onClick(e) {
    var t = e.target, box = t.closest ? t.closest(".mc-compose") : null;
    if (!box) { return; }
    if (t.classList.contains("mc-load")) { load(box, t); return; }
    if (t.classList.contains("mc-addbtn")) {
      var mk = markets(S.f), mid = box.querySelector(".mc-mkt").value, v = {};
      Array.prototype.forEach.call(box.querySelectorAll(".mc-fld"), function (s) { v[s.getAttribute("data-k")] = s.value; });
      var spec = mk.filter(function (x) { return x.id === mid; })[0].spec(v), key = JSON.stringify(spec);
      if (S.legs.length >= 6) { box.querySelector(".mc-msg").textContent = "Massimo 6 giocate."; return; }
      if (S.legs.some(function (x) { return JSON.stringify(x) === key; })) { box.querySelector(".mc-msg").textContent = "Giocata già presente."; return; }
      box.querySelector(".mc-msg").textContent = "";
      S.legs.push(spec);
      recalc(box);
      return;
    }
    if (t.classList.contains("mc-del")) { S.legs.splice(+t.getAttribute("data-i"), 1); box.querySelector(".mc-msg").textContent = ""; recalc(box); }
  }
  function onChange(e) {
    var t = e.target, box = t.closest ? t.closest(".mc-compose") : null;
    if (box && t.classList.contains("mc-mkt")) { box.querySelector(".mc-fields").innerHTML = fieldsHtml(markets(S.f), t.value); }
  }
  function onInput(e) {
    var t = e.target;
    if (t.classList && t.classList.contains("mc-sisal")) {
      var c = t.closest(".mc-combo");
      c.querySelector(".mc-ev").innerHTML = evHtml(parseFloat(c.getAttribute("data-p")), t.value);
    } else if (t.classList && t.classList.contains("mc-odds")) {
      var box = t.closest(".mc-compose");
      if (S.data && S.legs.length >= 2) { recalc(box); }
    }
  }
  function bind(root) {
    root.addEventListener("click", onClick);
    root.addEventListener("change", onChange);
    root.addEventListener("input", onInput);
  }
  function reset(f) { S = { f: f, data: null, n: 0, legs: [], loading: false }; }
  return { html: html, bind: bind, reset: reset, _state: function () { return S; } };
})();
'''

CSS = r'''
.mc-combo { background: var(--bg); border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; margin: 10px 0; }
.mc-title { font-weight: 700; font-size: .84rem; margin-bottom: 4px; }
.mc-legs { margin: 4px 0 8px 18px; padding: 0; font-size: .82rem; line-height: 1.5; }
.mc-nums { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; margin: 6px 0 8px; }
.mc-nums > div { background: var(--card); border-radius: 8px; padding: 6px 8px; display: flex; flex-direction: column; min-width: 0; }
.mc-nums span { font-size: .62rem; color: var(--muted); text-transform: uppercase; letter-spacing: .03em; }
.mc-nums b { font-size: .95rem; font-variant-numeric: tabular-nums; }
.mc-nums small { color: var(--muted); font-size: .66rem; }
.mc-in { display: flex; align-items: center; gap: 8px; font-size: .78rem; color: var(--muted); margin: 6px 0; }
.mc-in input, .mc-add select, .mc-fields select { background: var(--card); border: 1px solid var(--border); color: var(--text); border-radius: 8px; padding: 6px 8px; font-size: .82rem; }
.mc-in input { width: 7.5em; }
.mc-ev { font-size: .8rem; margin-top: 4px; min-height: 1.2em; }
.mc-neg { color: var(--red); }
.mc-pos { color: var(--green); }
.mc-bad { border-left: 4px solid var(--red); background: var(--card); border-radius: 8px; padding: 8px 12px; margin: 8px 0; font-size: .82rem; }
.mc-compose { margin-top: 16px; padding-top: 6px; border-top: 1px solid var(--border); }
.mc-load, .mc-addbtn { background: var(--accent); color: #0d1117; border: 0; border-radius: 8px; padding: 7px 12px; font-weight: 700; font-size: .8rem; cursor: pointer; }
.mc-load:disabled { opacity: .6; cursor: default; }
.mc-add { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin: 8px 0; }
.mc-fields { display: inline-flex; flex-wrap: wrap; gap: 6px; }
.mc-chips { display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0; }
.mc-chip { background: var(--card); border: 1px solid var(--border); border-radius: 14px; padding: 3px 4px 3px 10px; font-size: .78rem; }
.mc-del { background: none; border: 0; color: var(--muted); cursor: pointer; font-size: 1rem; line-height: 1; padding: 0 6px; }
@media (max-width: 600px) { .mc-nums { grid-template-columns: 1fr; } }
'''
