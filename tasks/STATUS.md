# Status DIN-4108-2-Web (NSW-Web)

Stand 13.09.2026, erhoben aus Code und `~/projekte/tasks/INVENTUR.md`.

## Aktueller Stand

Letzter Commit `2ddb479`, 17.08.2026, Branch `main`, Arbeitsbaum sauber.
1.643 Zeilen Python in drei Dateien, keine Tests, kein Linter.
Modul-globale App (`main.py:25`), keine Blueprints, SQLite über `g`-Objekt mit
`teardown_appcontext` (`main.py:100-109`) und `foreign_keys=ON`.
Läuft als `nsw-web.service` auf `127.0.0.1:20003`.

## Offene Punkte

1. Portwiderspruch: laufend 20003 (Unit), Code-Default `0.0.0.0:8080`
   (`main.py:22-23`), README nennt 8080 (`README.md:12,15,22`). Beim Handstart
   bindet die Anwendung damit im ganzen LAN. Code-Default und README auf
   `127.0.0.1:20003` ziehen.
2. Kein `PRAGMA journal_mode=WAL` (`main.py:100-105`), als eines von zwei
   Projekten.
3. Kein Logging eingerichtet.
4. Keine Tests, obwohl das Projekt ein Excelwerkzeug nachbaut und damit
   vergleichbare Ergebnisse liefern muss.
5. Ausgeliefert wird über den Flask-Entwicklungsserver (`main.py:421`); der
   README nennt gunicorn, eingesetzt wird keines von beidem.

## Nächster Schritt

Punkt 4 vor Punkt 1: Testfälle aus dem Originalwerkzeug `NSW2013-V2_80-Tool.xlsm`
als Vergleichsdaten anlegen, solange niemand an den Formeln arbeitet. Danach ist
Punkt 1 eine Änderung von drei Zeilen mit Absicherung.

## Umzug in Rubus, 2026-10-20 (Teil B im Workspace)

Erledigt: `rubus.toml` (Dienst `nsw-web` auf `127.0.0.1:20003`, Health
`/healthz`, `[daten] verzeichnisse = ["db"]`, Anzeige `dashboard` mit
`durchreichen`, nur prod auf homeserver), `requirements.txt` exakt gepinnt
(10 Pakete, `pip check` mit `--no-deps` sauber), Datenbankpfad über
`RUBUS_DATEN` mit Rückfall, Vorgabe `127.0.0.1:20003` (damit Punkt 1 im Code
und README erledigt). Start- und Seitentest in Test-venv bestanden.
Offen für Teil A: `nsw.db` nach `/opt/rubus/din-4108-2-web/data/db/nsw.db`
kopieren, prod einrichten, umschalten. Punkte 2 bis 5 oben bleiben offen.

## Nachtrag 2026-09-13: geänderte Betriebsregeln

Der Neustart produktiver Dienste und `git push` sind seit dem 2026-09-13 erlaubt.
Die Projektdatei `CLAUDE.md` nannte den Neustart zuvor als verboten; diese
Angabe ist entfernt. Inhaltlich am Projekt selbst wurde dabei nichts geändert.
