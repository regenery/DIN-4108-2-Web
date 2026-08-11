/* NSW-Web — Eingaben speichern sich selbst, das Ergebnis rechnet der Server. */

(function () {
  "use strict";

  const cfg = window.NSW;
  if (!cfg) return;

  const $ = (sel, wurzel) => (wurzel || document).querySelector(sel);
  const $$ = (sel, wurzel) => Array.from((wurzel || document).querySelectorAll(sel));

  // ---------------------------------------------------------------- Zahlen
  function zahlDe(wert, nk) {
    if (wert === null || wert === undefined || wert === "" || isNaN(wert)) return "—";
    return Number(wert).toLocaleString("de-DE", {
      minimumFractionDigits: nk, maximumFractionDigits: nk
    });
  }

  function zahlEin(text) {
    const n = parseFloat(String(text).replace(",", ".").replace(/\s/g, ""));
    return isNaN(n) ? 0 : n;
  }

  const NACHKOMMA = {
    S_vorh: 4, S_zul: 4, S1: 4, S2: 4, S3: 4, S4: 4, S5: 4, S6: 4,
    fneig: 3, fnord: 3, fWG: 2, fWG_zul: 2, AG: 2, AW_ges: 2, summenprodukt: 3
  };

  // -------------------------------------------------------------- Statusanzeige
  const stand = $("#speicherstand");
  let standTimer = null;

  function melde(text, aktiv) {
    if (!stand) return;
    stand.textContent = text;
    stand.classList.toggle("aktiv", !!aktiv);
    clearTimeout(standTimer);
    standTimer = setTimeout(() => {
      stand.textContent = "Alle Eingaben werden sofort gespeichert.";
      stand.classList.remove("aktiv");
    }, 2200);
  }

  // ------------------------------------------------------------------ Server
  async function sende(pfad, daten, methode) {
    const antwort = await fetch(pfad, {
      method: methode || "POST",
      headers: { "Content-Type": "application/json" },
      body: daten === undefined ? undefined : JSON.stringify(daten)
    });
    if (!antwort.ok) {
      const fehler = await antwort.json().catch(() => ({}));
      throw new Error(fehler.fehler || "Speichern fehlgeschlagen");
    }
    return antwort.json();
  }

  // -------------------------------------------------------------- Ergebnis
  function zeichneErgebnis(erg) {
    cfg.ergebnis = erg;

    const plakette = $("#status-plakette");
    plakette.textContent = erg.ueberschrift || "—";
    plakette.className = "plakette-gross " + (erg.status || "");

    $("#bauart").textContent = erg.bauart || "—";

    $$("[data-wert]").forEach((el) => {
      const schluessel = el.dataset.wert;
      const wert = erg.werte[schluessel];
      el.textContent = zahlDe(wert, NACHKOMMA[schluessel] !== undefined ? NACHKOMMA[schluessel] : 2);
    });

    // Kennwert-Waage
    const sVorh = erg.werte.S_vorh, sZul = erg.werte.S_zul;
    const fuellung = $("#waage-fuellung");
    const ausnutzung = $("#ausnutzung");
    if (typeof sVorh === "number" && typeof sZul === "number" && sZul > 0) {
      const anteil = sVorh / sZul;
      // S,zul liegt bei 75 % der Bahn — Überschreitungen bleiben sichtbar
      fuellung.style.width = Math.min(anteil * 75, 100) + "%";
      fuellung.classList.toggle("ueber", anteil > 1);
      ausnutzung.textContent = zahlDe(anteil * 100, 1) + " %";
    } else {
      fuellung.style.width = "0%";
      fuellung.classList.remove("ueber");
      ausnutzung.textContent = "—";
    }

    // S1 … S6
    const koerper = $("#kennwerte-koerper");
    koerper.innerHTML = "";
    (erg.herleitung || []).forEach((h) => {
      const tr = document.createElement("tr");
      const th = document.createElement("th");
      th.textContent = h.kurz + " · " + h.titel;
      th.title = h.formel;
      const td = document.createElement("td");
      td.className = "r zahl";
      td.textContent = zahlDe(h.wert, 4);
      tr.append(th, td);
      koerper.append(tr);
    });
    if ((erg.herleitung || []).length) {
      const tr = document.createElement("tr");
      tr.className = "summe";
      const th = document.createElement("th");
      th.textContent = "S,zul";
      const td = document.createElement("td");
      td.className = "r zahl";
      td.textContent = zahlDe(erg.werte.S_zul, 4);
      tr.append(th, td);
      koerper.append(tr);
    }

    // Meldungen
    const kasten = $("#meldungen");
    kasten.innerHTML = "";
    const gruppen = [
      ["fehler", erg.fehler], ["warnung", erg.warnungen], ["info", erg.anmerkungen]
    ];
    gruppen.forEach(([art, liste]) => {
      (liste || []).forEach((text) => {
        const div = document.createElement("div");
        div.className = "meldung " + art;
        div.textContent = text;
        kasten.append(div);
      });
    });
  }

  // ------------------------------------------------------- Projektfelder
  const editor = $(".editor");
  if (!editor) return;
  const pid = cfg.pid;

  function bauartBloeckeSchalten() {
    const methode = $('[data-feld="bauart_methode"]').value;
    $$("[data-zeigen-bei]").forEach((block) => {
      block.hidden = block.dataset.zeigenBei !== methode;
    });
  }

  const wartend = new Map();
  let sendeTimer = null;

  function projektFeld(name, wert, sofort) {
    wartend.set(name, wert);
    clearTimeout(sendeTimer);
    sendeTimer = setTimeout(projektSenden, sofort ? 0 : 400);
  }

  async function projektSenden() {
    if (!wartend.size) return;
    const nutzlast = Object.fromEntries(wartend);
    wartend.clear();
    melde("Speichern …", true);
    try {
      zeichneErgebnis(await sende("/api/projekt/" + pid, nutzlast));
      melde("Gespeichert");
    } catch (e) {
      melde(e.message);
    }
  }

  $$("[data-feld]").forEach((el) => {
    const name = el.dataset.feld;
    if (el.type === "checkbox") {
      el.addEventListener("change", () => projektFeld(name, el.checked, true));
    } else if (el.tagName === "SELECT") {
      el.addEventListener("change", () => {
        projektFeld(name, el.value, true);
        if (name === "bauart_methode") bauartBloeckeSchalten();
      });
    } else {
      el.addEventListener("input", () => {
        projektFeld(name, el.value);
        if (name === "referenzraum") $("#kopf-raum").textContent = el.value || "—";
      });
      el.addEventListener("blur", () => {
        if (["raumhoehe", "raumtiefe", "raumbreite", "ag_direkt"].includes(name)) {
          el.value = zahlDe(zahlEin(el.value), 2);
          projektFeld(name, el.value, true);
        }
      });
    }
  });

  bauartBloeckeSchalten();

  // ------------------------------------------------------------- Fenster
  const koerper = $("#fensterkoerper");

  function option(wert, gewaehlt) {
    const o = document.createElement("option");
    o.value = wert;
    o.textContent = wert;
    if (wert === gewaehlt) o.selected = true;
    return o;
  }

  function auswahlFeld(feld, optionen, wert, klasse) {
    const s = document.createElement("select");
    s.dataset.ffeld = feld;
    if (klasse) s.className = klasse;
    optionen.forEach((o) => s.append(option(o, wert)));
    return s;
  }

  function textFeld(feld, wert, klasse) {
    const i = document.createElement("input");
    i.type = "text";
    i.dataset.ffeld = feld;
    i.value = wert;
    if (klasse) i.className = klasse;
    return i;
  }

  function glasOptionen(glastyp) {
    return Object.keys(cfg.glas[glastyp] || {});
  }

  function zelle(inhalt, klasse) {
    const td = document.createElement("td");
    if (klasse) td.className = klasse;
    if (inhalt) td.append(inhalt);
    return td;
  }

  function baueZeile(f) {
    const tr = document.createElement("tr");
    tr.dataset.fid = f.id;

    const nr = document.createElement("td");
    nr.className = "zeilennr";
    nr.textContent = f.nr;
    tr.append(nr);

    tr.append(zelle(textFeld("bezeichnung", f.bezeichnung), "sp-mittel"));
    tr.append(zelle(auswahlFeld("orientierung", cfg.orientierungen, f.orientierung), "sp-mittel"));
    tr.append(zelle(auswahlFeld("neigung", cfg.neigungen, f.neigung), "sp-breit"));
    tr.append(zelle(textFeld("breite", zahlDe(f.breite, 2), "zahl"), "sp-schmal"));
    tr.append(zelle(textFeld("hoehe", zahlDe(f.hoehe, 2), "zahl"), "sp-schmal"));
    tr.append(zelle(textFeld("anzahl", f.anzahl, "zahl"), "sp-schmal"));
    tr.append(zelle(textFeld("flaeche_direkt", zahlDe(f.flaeche_direkt, 2), "zahl"), "sp-schmal"));
    tr.append(zelle(auswahlFeld("glastyp", cfg.glastypen, f.glastyp), "sp-mittel"));
    tr.append(zelle(auswahlFeld("glaseigenschaft", glasOptionen(f.glastyp), f.glaseigenschaft), "sp-breit"));
    tr.append(zelle(textFeld("g_wert", zahlDe(f.g_wert, 2), "zahl"), "sp-schmal"));
    tr.append(zelle(auswahlFeld("sonnenschutzart", cfg.sonnenschutz, f.sonnenschutzart), "sp-breit"));
    tr.append(zelle(textFeld("fc", zahlDe(f.fc, 2), "zahl"), "sp-schmal"));

    const haken = document.createElement("input");
    haken.type = "checkbox";
    haken.dataset.ffeld = "verschattet";
    haken.checked = !!f.verschattet;
    haken.title = "dauerhaft vom Gebäude selbst verschattet";
    const hakenZelle = zelle(haken, "r");
    hakenZelle.style.width = "48px";
    tr.append(hakenZelle);

    const gtot = zelle(null, "abgeleitet");
    gtot.dataset.abgeleitet = "gtot";
    tr.append(gtot);

    const flaeche = zelle(null, "abgeleitet");
    flaeche.dataset.abgeleitet = "flaeche";
    tr.append(flaeche);

    const weg = document.createElement("button");
    weg.type = "button";
    weg.className = "zeile-loeschen";
    weg.textContent = "×";
    weg.title = "Fenster entfernen";
    weg.addEventListener("click", () => fensterLoeschen(f.id, tr));
    tr.append(zelle(weg, "r"));

    zeileAbleiten(tr);
    return tr;
  }

  function zeileAbleiten(tr) {
    const lies = (feld) => zahlEin($(`[data-ffeld="${feld}"]`, tr).value);
    const gtot = lies("g_wert") * lies("fc");
    const direkt = lies("flaeche_direkt");
    const flaeche = direkt > 0 ? direkt : lies("breite") * lies("hoehe") * lies("anzahl");
    $('[data-abgeleitet="gtot"]', tr).textContent = zahlDe(gtot, 3);
    $('[data-abgeleitet="flaeche"]', tr).textContent = zahlDe(flaeche, 2);
  }

  const fensterWartend = new Map();
  let fensterTimer = null;

  function fensterFeld(fid, name, wert, sofort) {
    if (!fensterWartend.has(fid)) fensterWartend.set(fid, {});
    fensterWartend.get(fid)[name] = wert;
    clearTimeout(fensterTimer);
    fensterTimer = setTimeout(fensterSenden, sofort ? 0 : 400);
  }

  async function fensterSenden() {
    if (!fensterWartend.size) return;
    const stapel = Array.from(fensterWartend.entries());
    fensterWartend.clear();
    melde("Speichern …", true);
    try {
      let letztes = null;
      for (const [fid, daten] of stapel) {
        letztes = await sende("/api/fenster/" + fid, daten);
      }
      if (letztes) zeichneErgebnis(letztes.ergebnis);
      melde("Gespeichert");
    } catch (e) {
      melde(e.message);
    }
  }

  koerper.addEventListener("input", (ereignis) => {
    const el = ereignis.target;
    if (!el.dataset.ffeld) return;
    const tr = el.closest("tr");
    zeileAbleiten(tr);
    fensterFeld(tr.dataset.fid, el.dataset.ffeld,
                el.type === "checkbox" ? el.checked : el.value);
  });

  koerper.addEventListener("change", (ereignis) => {
    const el = ereignis.target;
    const feld = el.dataset.ffeld;
    if (!feld) return;
    const tr = el.closest("tr");
    const fid = tr.dataset.fid;

    if (feld === "glastyp") {
      fensterFeld(fid, "glastyp", el.value, true);
      // Glaseigenschaften und FC hängen am Glaserzeugnis (Tabelle 7)
      const eigenschaft = $('[data-ffeld="glaseigenschaft"]', tr);
      eigenschaft.innerHTML = "";
      glasOptionen(el.value).forEach((o) => eigenschaft.append(option(o, "benutzerdefiniert")));
      fensterFeld(fid, "glaseigenschaft", "benutzerdefiniert", true);
      uebernehmeFc(tr, fid);
    }
    if (feld === "glaseigenschaft") {
      const glastyp = $('[data-ffeld="glastyp"]', tr).value;
      const g = (cfg.glas[glastyp] || {})[el.value];
      if (g !== null && g !== undefined) {
        $('[data-ffeld="g_wert"]', tr).value = zahlDe(g, 2);
        fensterFeld(fid, "g_wert", g, true);
      }
    }
    if (feld === "sonnenschutzart") uebernehmeFc(tr, fid);
    if (feld === "verschattet") fensterFeld(fid, "verschattet", el.checked, true);
    if (["orientierung", "neigung"].includes(feld)) fensterFeld(fid, feld, el.value, true);

    zeileAbleiten(tr);
  });

  function uebernehmeFc(tr, fid) {
    const art = $('[data-ffeld="sonnenschutzart"]', tr).value;
    const glastyp = $('[data-ffeld="glastyp"]', tr).value;
    const fc = (cfg.fc[art] || {})[glastyp];
    if (fc !== null && fc !== undefined) {
      $('[data-ffeld="fc"]', tr).value = zahlDe(fc, 2);
      fensterFeld(fid, "fc", fc, true);
    }
    fensterFeld(fid, "sonnenschutzart", art, true);
    zeileAbleiten(tr);
  }

  koerper.addEventListener("blur", (ereignis) => {
    const el = ereignis.target;
    if (!el.dataset.ffeld || !el.classList.contains("zahl")) return;
    const nk = el.dataset.ffeld === "anzahl" ? 0 : 2;
    el.value = zahlDe(zahlEin(el.value), nk);
    zeileAbleiten(el.closest("tr"));
  }, true);

  async function fensterLoeschen(fid, tr) {
    if (!confirm("Dieses Fenster aus dem Nachweis entfernen?")) return;
    try {
      const antwort = await sende("/api/fenster/" + fid, undefined, "DELETE");
      tr.remove();
      zeichneErgebnis(antwort.ergebnis);
      leerhinweis();
      melde("Fenster entfernt");
    } catch (e) {
      melde(e.message);
    }
  }

  function leerhinweis() {
    $("#kein-fenster").hidden = koerper.children.length > 0;
  }

  $("#fenster-hinzu").addEventListener("click", async () => {
    if (koerper.children.length >= cfg.maxFenster) {
      melde("Maximal " + cfg.maxFenster + " Fenster je Nachweis");
      return;
    }
    try {
      const antwort = await sende("/api/projekt/" + pid + "/fenster", {});
      const tr = baueZeile(antwort.fenster);
      koerper.append(tr);
      leerhinweis();
      $('[data-ffeld="bezeichnung"]', tr).focus();
      zeichneErgebnis(await sende("/api/projekt/" + pid, {}));
    } catch (e) {
      melde(e.message);
    }
  });

  // ------------------------------------------------------------ Startzustand
  (cfg.fenster || []).forEach((f) => koerper.append(baueZeile(f)));
  leerhinweis();
  zeichneErgebnis(cfg.ergebnis);
  window.addEventListener("beforeunload", () => {
    projektSenden();
    fensterSenden();
  });
})();
