# NSW-Web — Nachweis sommerlicher Wärmeschutz nach DIN 4108-2:2013-02

Flask-Webanwendung für den vereinfachten Nachweis des sommerlichen Wärmeschutzes
über Sonneneintragskennwerte (DIN 4108-2:2013-02, Abschnitt 8.3).
Nachbau des Excel-Werkzeugs `NSW2013-V2_80-Tool.xlsm` (IWU) als eigenständige
Python-Anwendung mit SQLite-Persistenz und prüffähigem PDF-Report.

## Start

```bash
pip install -r requirements.txt
python3 main.py                    # → http://0.0.0.0:8080
```

Umgebungsvariablen: `NSW_PORT` (Standard 8080), `NSW_DB` (Standard `./nsw.db`).
Die Datenbank wird beim ersten Start automatisch angelegt.

Für den Dauerbetrieb hinter dem Tailnet:

```bash
pip install gunicorn
gunicorn -w 2 -b 0.0.0.0:8080 'main:app'
```

`/healthz` liefert JSON mit Status und Projektanzahl — für das zentrale
Überwachungs-Dashboard.

### Schriften für das PDF

Der Report nutzt DejaVu Sans, damit `≤`, `⊥`, `Σ` und `²` korrekt gesetzt werden.
Falls nicht vorhanden: `apt install fonts-dejavu-core`. Ohne DejaVu fällt der
Report auf Helvetica zurück; Sonderzeichen fehlen dann.

## Aufbau

| Datei | Inhalt |
|---|---|
| `din4108.py` | Rechenkern, alle Normtabellen, keine Abhängigkeit zu Flask |
| `main.py` | Routen, SQLite-Schema, JSON-API |
| `report.py` | PDF-Report (reportlab) |
| `templates/`, `static/` | Oberfläche |

## Umgesetzter Funktionsumfang

Aus dem Excel-Tool übernommen:

* **Tabelle 6** — zulässiger grundflächenbezogener Fensterflächenanteil (7 / 10 / 15 %)
  und die Prüfung, ob ein Nachweis überhaupt erforderlich ist
* **Tabelle 7** — Abminderungsfaktoren FC, spaltenweise nach Glaserzeugnis
  (Sonnenschutzglas g ≤ 0,40 / dreifach / zweifach)
* **Tabelle 8** — S1 (Wohn-/Nichtwohngebäude × 3 Nachtlüftungsstufen ×
  3 Bauarten × 3 Klimaregionen) sowie S2 bis S6
* **Verglasungskataloge** mit g⊥-Werten je Glastyp, zusätzlich benutzerdefiniert
* **Bauartermittlung** nach DIN 4108-2 (Rohdichte plus vier Kriterien) oder
  direkt über Cwirk/AG nach DIN EN ISO 13786
* **Fenstertabelle** mit AW,j = Breite · Höhe · Anzahl, gtot = g⊥ · FC,
  Zuordnung zu Verglasungsart, Neigung, Orientierung und Eigenverschattung
* **Sonderfälle** nach Abschnitt 8.2.2 b) und 8.2.3 (unbeheizter Glasvorbau)
* Annahmen- und Kommentarfeld, beides im Report enthalten

Ergänzt gegenüber dem Original: Felder für Bauvorhaben-Anschrift und
Förderkennzeichen, Warnung bei LT > 3 · LH, Warnung bei S,zul ≤ 0 (dann ist eine
thermische Gebäudesimulation nach Abschnitt 8.4 erforderlich), Plausibilitäts-
prüfung der Sonnenschutzglas-Einstufung, Seite „Rechengrundlagen“, die alle
hinterlegten Werte offenlegt.

## Abgleich mit dem Excel-Tool

Der im Original hinterlegte Beispielfall (Raum 412, Nichtwohngebäude, Region C,
mittlere Bauart, 3 × 1,34 m × 1,71 m Südwest, g = 0,58, FC = 0,25) wird exakt
reproduziert:

| Größe | Excel-Tool | NSW-Web (Excel-Modus) | NSW-Web (Standard) |
|---|---|---|---|
| AG | 23,41 m² | 23,41 m² | 23,41 m² |
| AW,ges | 6,87 m² | 6,87 m² | 6,87 m² |
| fWG | 29,346 % | 29,346 % | 29,362 % |
| S1 | 0,0060 | 0,0060 | 0,0060 |
| S2 | −0,0037 | −0,0037 | −0,0038 |
| S,zul | 0,0023 | 0,0023 | 0,0022 |
| S,vorh | 0,0426 | 0,0426 | 0,0426 |
| Ergebnis | nicht erfüllt | nicht erfüllt | nicht erfüllt |

**Zur Abweichung:** Das Excel-Tool rechnet mit den *angezeigten*, auf zwei bzw.
drei Nachkommastellen gerundeten Zwischenwerten weiter. NSW-Web rechnet
standardmäßig mit voller Genauigkeit. Wer die Excel-Zahlen bitgenau
reproduzieren muss, setzt in `din4108.py`:

```python
RUNDUNG_WIE_EXCEL = True
```

**Zweite Abweichung:** Im Excel-Tool widersprechen sich zwei Blätter beim
FC-Wert für „Jalousie und Raffstore, 10° Lamellenstellung“ in Verbindung mit
Zweifachverglasung (Blatt `Hilfstabellen`: 0,20 / Blatt `Anwendungshinweise`:
0,15). NSW-Web verwendet 0,20 gemäß Tabelle 7. Die Zeile ist ohnehin als
informativ gekennzeichnet und sollte für Nachweise nicht verwendet werden.

## Aktive Kühlung

Eine im Gebäude vorhandene **Anlage zur Kühlung darf im Verfahren der
Sonneneintragskennwerte nicht angerechnet werden** — nur passive Kühlung geht
über S6 ein. Das Feld „Anlage zur Kühlung vorhanden“ dokumentiert die Anlage im
Report, verändert die Rechnung aber nicht. Für Gebäude mit Anlagen zur Kühlung
gilt zusätzlich GEG § 14 Absatz 4, sofern der Nachweis über die Simulation nach
Abschnitt 8.4 geführt wird.

## Rechtliches

Eigenständige Umsetzung des in DIN 4108-2:2013-02 beschriebenen Verfahrens.
Es wurde kein Code und kein Text aus dem Excel-Tool übernommen; die Zahlenwerte
stammen aus der Norm. Maßgebend ist der Wortlaut der Norm — die fachliche
Verantwortung für Eingabewerte und Ergebnis liegt beim Ersteller des Nachweises.
