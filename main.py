# -*- coding: utf-8 -*-
"""
NSW-Web — Nachweis sommerlicher Wärmeschutz nach DIN 4108-2:2013-02
Flask-Anwendung, SQLite-Persistenz, PDF-Projektreport.

Start:  python3 main.py      →  http://127.0.0.1:20003
"""

import os
import sqlite3
from datetime import date, datetime

from flask import (Flask, g, jsonify, redirect, render_template, request,
                   send_file, url_for, abort)

import din4108 as din
from din4108 import Fenster, berechne, de
from report import erzeuge_pdf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _db_pfad():
    """NSW_DB vor RUBUS_DATEN/db/nsw.db vor nsw.db neben dem Code."""
    if os.environ.get("NSW_DB"):
        return os.environ["NSW_DB"]
    if os.environ.get("RUBUS_DATEN"):
        ordner = os.path.join(os.environ["RUBUS_DATEN"], "db")
        os.makedirs(ordner, exist_ok=True)
        return os.path.join(ordner, "nsw.db")
    return os.path.join(BASE_DIR, "nsw.db")


DB_PFAD = _db_pfad()
PORT = int(os.environ.get("NSW_PORT", 20003))
HOST = os.environ.get("NSW_HOST", "127.0.0.1")

app = Flask(__name__)
app.jinja_env.filters["de"] = lambda wert, nk=2: de(wert, nk)

MAX_FENSTER = 40

# ---------------------------------------------------------------------------
# Datenbank
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS projekte (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    projekt                 TEXT    NOT NULL DEFAULT '',
    gebaeudebereich         TEXT    NOT NULL DEFAULT '',
    referenzraum            TEXT    NOT NULL DEFAULT '',
    datum                   TEXT    NOT NULL DEFAULT '',
    buero                   TEXT    NOT NULL DEFAULT '',
    ersteller               TEXT    NOT NULL DEFAULT '',
    bauvorhaben_adresse     TEXT    NOT NULL DEFAULT '',
    foerderkennzeichen      TEXT    NOT NULL DEFAULT '',
    gebaeudetyp             TEXT    NOT NULL DEFAULT 'Wohngebäude',
    klimaregion             TEXT    NOT NULL DEFAULT '',
    nachtlueftung           TEXT    NOT NULL DEFAULT 'ohne',
    bauart_methode          TEXT    NOT NULL DEFAULT 'nach DIN 4108-2',
    waermekapazitaet        TEXT    NOT NULL DEFAULT '',
    rohdichte               TEXT    NOT NULL DEFAULT '',
    stahlbetondecke         INTEGER NOT NULL DEFAULT 0,
    keine_abgehaengte_decke INTEGER NOT NULL DEFAULT 0,
    keine_innendaemmung     INTEGER NOT NULL DEFAULT 0,
    keine_hohen_raeume      INTEGER NOT NULL DEFAULT 0,
    passive_kuehlung        INTEGER NOT NULL DEFAULT 0,
    aktive_kuehlung         INTEGER NOT NULL DEFAULT 0,
    verzicht_822b           INTEGER NOT NULL DEFAULT 0,
    glasvorbau_nur          INTEGER NOT NULL DEFAULT 0,
    glasvorbau_nicht_nur    INTEGER NOT NULL DEFAULT 0,
    raumhoehe               REAL    NOT NULL DEFAULT 0,
    raumtiefe               REAL    NOT NULL DEFAULT 0,
    raumbreite              REAL    NOT NULL DEFAULT 0,
    ag_direkt               REAL    NOT NULL DEFAULT 0,
    kommentare              TEXT    NOT NULL DEFAULT '',
    annahmen                TEXT    NOT NULL DEFAULT '',
    erstellt_am             TEXT    NOT NULL DEFAULT '',
    geaendert_am            TEXT    NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS fenster (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    projekt_id      INTEGER NOT NULL REFERENCES projekte(id) ON DELETE CASCADE,
    nr              INTEGER NOT NULL DEFAULT 1,
    bezeichnung     TEXT    NOT NULL DEFAULT '',
    orientierung    TEXT    NOT NULL DEFAULT 'Süd',
    neigung         TEXT    NOT NULL DEFAULT '',
    breite          REAL    NOT NULL DEFAULT 0,
    hoehe           REAL    NOT NULL DEFAULT 0,
    anzahl          INTEGER NOT NULL DEFAULT 1,
    flaeche_direkt  REAL    NOT NULL DEFAULT 0,
    glastyp         TEXT    NOT NULL DEFAULT 'zweifach',
    glaseigenschaft TEXT    NOT NULL DEFAULT 'benutzerdefiniert',
    g_wert          REAL    NOT NULL DEFAULT 0,
    verschattet     INTEGER NOT NULL DEFAULT 0,
    sonnenschutzart TEXT    NOT NULL DEFAULT 'ohne Sonnenschutzvorrichtung',
    fc              REAL    NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_fenster_projekt ON fenster(projekt_id, nr);
"""

TEXTFELDER = ["projekt", "gebaeudebereich", "referenzraum", "datum", "buero",
              "ersteller", "bauvorhaben_adresse", "foerderkennzeichen",
              "gebaeudetyp", "klimaregion", "nachtlueftung", "bauart_methode",
              "waermekapazitaet", "rohdichte", "kommentare", "annahmen"]
FLAGS = ["stahlbetondecke", "keine_abgehaengte_decke", "keine_innendaemmung",
         "keine_hohen_raeume", "passive_kuehlung", "aktive_kuehlung",
         "verzicht_822b", "glasvorbau_nur", "glasvorbau_nicht_nur"]
ZAHLEN = ["raumhoehe", "raumtiefe", "raumbreite", "ag_direkt"]


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PFAD)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def db_schliessen(_exc):
    verbindung = g.pop("db", None)
    if verbindung is not None:
        verbindung.close()


NACHTRAEGLICHE_SPALTEN = [
    ("projekte", "aktive_kuehlung", "INTEGER NOT NULL DEFAULT 0"),
    ("projekte", "ag_direkt", "REAL NOT NULL DEFAULT 0"),
    ("projekte", "bauvorhaben_adresse", "TEXT NOT NULL DEFAULT ''"),
    ("projekte", "foerderkennzeichen", "TEXT NOT NULL DEFAULT ''"),
    ("fenster", "flaeche_direkt", "REAL NOT NULL DEFAULT 0"),
]


def init_db():
    verbindung = sqlite3.connect(DB_PFAD)
    verbindung.executescript(SCHEMA)
    for tabelle, spalte, typ in NACHTRAEGLICHE_SPALTEN:
        vorhanden = [z[1] for z in
                     verbindung.execute(f"PRAGMA table_info({tabelle})")]
        if spalte not in vorhanden:
            verbindung.execute(f"ALTER TABLE {tabelle} ADD COLUMN {spalte} {typ}")
    verbindung.commit()
    verbindung.close()


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def zahl(wert, standard=0.0):
    """Nimmt '1,34' genauso wie '1.34' entgegen."""
    if wert is None:
        return standard
    if isinstance(wert, (int, float)):
        return float(wert)
    text = str(wert).strip().replace(" ", "").replace(",", ".")
    if not text:
        return standard
    try:
        return float(text)
    except ValueError:
        return standard


def jetzt():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def projekt_laden(pid):
    zeile = db().execute("SELECT * FROM projekte WHERE id = ?", (pid,)).fetchone()
    if zeile is None:
        abort(404)
    return dict(zeile)


def fenster_laden(pid):
    zeilen = db().execute(
        "SELECT * FROM fenster WHERE projekt_id = ? ORDER BY nr, id", (pid,)).fetchall()
    return [dict(z) for z in zeilen]


def zu_fenster(zeilen):
    return [Fenster(nr=z["nr"], bezeichnung=z["bezeichnung"],
                    orientierung=z["orientierung"], neigung=z["neigung"],
                    breite=z["breite"], hoehe=z["hoehe"], anzahl=z["anzahl"],
                    flaeche_direkt=z["flaeche_direkt"],
                    glastyp=z["glastyp"], glaseigenschaft=z["glaseigenschaft"],
                    g_wert=z["g_wert"], verschattet=bool(z["verschattet"]),
                    sonnenschutzart=z["sonnenschutzart"], fc=z["fc"])
            for z in zeilen]


def ergebnis_json(erg):
    return {
        "ok": erg.ok, "status": erg.status, "ueberschrift": erg.ueberschrift,
        "bauart": erg.bauart, "anmerkungen": erg.anmerkungen,
        "warnungen": erg.warnungen, "fehler": erg.fehler,
        "herleitung": [{**h, "wert_text": de(h["wert"], 4)} for h in erg.herleitung],
        "werte": erg.werte,
        "text": {k: de(v, 4) if isinstance(v, float) else v
                 for k, v in erg.werte.items()},
    }


# ---------------------------------------------------------------------------
# Routen — Seiten
# ---------------------------------------------------------------------------

@app.route("/")
def uebersicht():
    zeilen = db().execute(
        "SELECT p.*, (SELECT COUNT(*) FROM fenster f WHERE f.projekt_id = p.id) "
        "AS fensteranzahl FROM projekte p ORDER BY datetime(p.geaendert_am) DESC"
    ).fetchall()

    projekte = []
    for zeile in zeilen:
        daten = dict(zeile)
        erg = berechne(daten, zu_fenster(fenster_laden(daten["id"])))
        daten["status"] = erg.status
        daten["ueberschrift"] = erg.ueberschrift
        daten["s_vorh"] = erg.werte.get("S_vorh")
        daten["s_zul"] = erg.werte.get("S_zul")
        projekte.append(daten)
    return render_template("uebersicht.html", projekte=projekte)


@app.route("/projekt/neu", methods=["POST"])
def projekt_neu():
    heute = date.today().strftime("%d.%m.%Y")
    cur = db().execute(
        "INSERT INTO projekte (projekt, referenzraum, datum, klimaregion, "
        "nachtlueftung, gebaeudetyp, bauart_methode, rohdichte, erstellt_am, "
        "geaendert_am) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (request.form.get("projekt", "").strip() or "Neuer Nachweis",
         "Referenzraum 1", heute, din.KLIMAREGIONEN[1], din.NACHTLUEFTUNG[0],
         "Wohngebäude", "nach DIN 4108-2", din.ROHDICHTEN[1], jetzt(), jetzt()))
    db().commit()
    return redirect(url_for("projekt", pid=cur.lastrowid))


@app.route("/projekt/<int:pid>")
def projekt(pid):
    daten = projekt_laden(pid)
    fenster = fenster_laden(pid)
    erg = berechne(daten, zu_fenster(fenster))
    return render_template("projekt.html", p=daten, fenster=fenster,
                           erg=ergebnis_json(erg), din=din,
                           fc_json={e[0]: {"Sonnenschutzglas (g ≤ 0,4)": e[1],
                                           "dreifach": e[2], "zweifach": e[3]}
                                    for e in din.SONNENSCHUTZ_FC},
                           g_json={t: dict(v) for t, v in
                                   din.GLASEIGENSCHAFTEN.items()},
                           max_fenster=MAX_FENSTER)


@app.route("/projekt/<int:pid>/kopieren", methods=["POST"])
def projekt_kopieren(pid):
    quelle = projekt_laden(pid)
    spalten = [s for s in quelle if s not in ("id", "erstellt_am", "geaendert_am")]
    werte = [quelle[s] for s in spalten]
    werte[spalten.index("projekt")] = f"{quelle['projekt']} (Kopie)"
    cur = db().execute(
        f"INSERT INTO projekte ({','.join(spalten)}, erstellt_am, geaendert_am) "
        f"VALUES ({','.join('?' * len(spalten))}, ?, ?)", (*werte, jetzt(), jetzt()))
    neu = cur.lastrowid
    for f in fenster_laden(pid):
        db().execute(
            "INSERT INTO fenster (projekt_id, nr, bezeichnung, orientierung, "
            "neigung, breite, hoehe, anzahl, flaeche_direkt, glastyp, "
            "glaseigenschaft, g_wert, verschattet, sonnenschutzart, fc) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (neu, f["nr"], f["bezeichnung"], f["orientierung"], f["neigung"],
             f["breite"], f["hoehe"], f["anzahl"], f["flaeche_direkt"],
             f["glastyp"], f["glaseigenschaft"], f["g_wert"], f["verschattet"],
             f["sonnenschutzart"], f["fc"]))
    db().commit()
    return redirect(url_for("projekt", pid=neu))


@app.route("/projekt/<int:pid>/loeschen", methods=["POST"])
def projekt_loeschen(pid):
    db().execute("DELETE FROM fenster WHERE projekt_id = ?", (pid,))
    db().execute("DELETE FROM projekte WHERE id = ?", (pid,))
    db().commit()
    return redirect(url_for("uebersicht"))


@app.route("/grundlagen")
def grundlagen():
    return render_template("grundlagen.html", din=din)


# ---------------------------------------------------------------------------
# Routen — API
# ---------------------------------------------------------------------------

@app.route("/api/projekt/<int:pid>", methods=["POST"])
def api_projekt_speichern(pid):
    projekt_laden(pid)
    daten = request.get_json(force=True) or {}

    felder, werte = [], []
    for name in TEXTFELDER:
        if name in daten:
            felder.append(name)
            werte.append(str(daten[name]))
    for name in FLAGS:
        if name in daten:
            felder.append(name)
            werte.append(1 if daten[name] else 0)
    for name in ZAHLEN:
        if name in daten:
            felder.append(name)
            werte.append(zahl(daten[name]))

    if felder:
        db().execute(
            f"UPDATE projekte SET {', '.join(f + ' = ?' for f in felder)}, "
            f"geaendert_am = ? WHERE id = ?", (*werte, jetzt(), pid))
        db().commit()

    aktuell = projekt_laden(pid)
    erg = berechne(aktuell, zu_fenster(fenster_laden(pid)))
    return jsonify(ergebnis_json(erg))


@app.route("/api/projekt/<int:pid>/fenster", methods=["POST"])
def api_fenster_neu(pid):
    projekt_laden(pid)
    vorhanden = fenster_laden(pid)
    if len(vorhanden) >= MAX_FENSTER:
        return jsonify({"fehler": f"Maximal {MAX_FENSTER} Fenster je Nachweis."}), 400

    nr = max([f["nr"] for f in vorhanden], default=0) + 1
    vorlage = vorhanden[-1] if vorhanden else None
    cur = db().execute(
        "INSERT INTO fenster (projekt_id, nr, bezeichnung, orientierung, neigung, "
        "breite, hoehe, anzahl, flaeche_direkt, glastyp, glaseigenschaft, g_wert, "
        "verschattet, sonnenschutzart, fc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (pid, nr, f"F{nr}",
         vorlage["orientierung"] if vorlage else "Süd",
         vorlage["neigung"] if vorlage else din.NEIGUNGEN[1],
         0, 0, 1, 0,
         vorlage["glastyp"] if vorlage else "zweifach",
         "benutzerdefiniert", 0, 0,
         "ohne Sonnenschutzvorrichtung", 1.0))
    db().execute("UPDATE projekte SET geaendert_am = ? WHERE id = ?", (jetzt(), pid))
    db().commit()
    zeile = db().execute("SELECT * FROM fenster WHERE id = ?",
                         (cur.lastrowid,)).fetchone()
    return jsonify({"fenster": dict(zeile)})


@app.route("/api/fenster/<int:fid>", methods=["POST", "DELETE"])
def api_fenster(fid):
    zeile = db().execute("SELECT * FROM fenster WHERE id = ?", (fid,)).fetchone()
    if zeile is None:
        abort(404)
    pid = zeile["projekt_id"]

    if request.method == "DELETE":
        db().execute("DELETE FROM fenster WHERE id = ?", (fid,))
    else:
        daten = request.get_json(force=True) or {}
        felder, werte = [], []
        for name in ("bezeichnung", "orientierung", "neigung", "glastyp",
                     "glaseigenschaft", "sonnenschutzart"):
            if name in daten:
                felder.append(name)
                werte.append(str(daten[name]))
        for name in ("breite", "hoehe", "flaeche_direkt", "g_wert", "fc"):
            if name in daten:
                felder.append(name)
                werte.append(zahl(daten[name]))
        if "anzahl" in daten:
            felder.append("anzahl")
            werte.append(max(int(zahl(daten["anzahl"], 1)), 0))
        if "verschattet" in daten:
            felder.append("verschattet")
            werte.append(1 if daten["verschattet"] else 0)
        if felder:
            db().execute(f"UPDATE fenster SET "
                         f"{', '.join(f + ' = ?' for f in felder)} WHERE id = ?",
                         (*werte, fid))

    db().execute("UPDATE projekte SET geaendert_am = ? WHERE id = ?", (jetzt(), pid))
    db().commit()

    fenster = fenster_laden(pid)
    erg = berechne(projekt_laden(pid), zu_fenster(fenster))
    return jsonify({"ergebnis": ergebnis_json(erg), "fenster": fenster})


@app.route("/api/projekt/<int:pid>/ergebnis")
def api_ergebnis(pid):
    erg = berechne(projekt_laden(pid), zu_fenster(fenster_laden(pid)))
    return jsonify(ergebnis_json(erg))


# ---------------------------------------------------------------------------
# PDF-Report
# ---------------------------------------------------------------------------

@app.route("/projekt/<int:pid>/report.pdf")
def report(pid):
    daten = projekt_laden(pid)
    fenster_zeilen = fenster_laden(pid)
    objekte = zu_fenster(fenster_zeilen)
    erg = berechne(daten, objekte)
    puffer = erzeuge_pdf(daten, objekte, erg)

    sicher = "".join(c if c.isalnum() or c in "-_" else "_"
                     for c in (daten["projekt"] or "Nachweis"))[:60]
    name = f"NSW_DIN4108-2_{sicher}_{date.today():%Y-%m-%d}.pdf"
    return send_file(puffer, mimetype="application/pdf",
                     as_attachment=True, download_name=name)


# ---------------------------------------------------------------------------

@app.route("/healthz")
def healthz():
    anzahl = db().execute("SELECT COUNT(*) AS n FROM projekte").fetchone()["n"]
    return jsonify({"status": "ok", "projekte": anzahl,
                    "version": "1.0", "port": PORT})


if __name__ == "__main__":
    init_db()
    app.run(host=HOST, port=PORT, debug=False)
