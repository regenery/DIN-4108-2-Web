# Entscheidungen DIN-4108-2-Web

ADR-light: was, wann, warum, verworfene Alternative. Neueste oben.

## 2026-10-20 — Umzug in Rubus: Datenbank unter `$RUBUS_DATEN/db/`

Was: `main.py` sucht die Datenbank in der Reihenfolge `NSW_DB`,
`$RUBUS_DATEN/db/nsw.db`, `nsw.db` neben dem Code; Vorgabe für Host und Port
`127.0.0.1:20003`. In der rubus.toml `[daten] verzeichnisse = ["db"]`.
Warum: `[daten]` nennt Ordner; ein eigener Ordner hält die Datenbank vom Rest
unter `RUBUS_DATEN` getrennt. Der Code legt ihn bei Bedarf selbst an.
Verworfen: `nsw.db` direkt unter `RUBUS_DATEN` (kein Ordner für `[daten]`);
ProxyFix nachrüsten (die App erzeugt nur relative Links, `durchreichen` braucht
keinen Umbau). Python bleibt 3.12 wie die laufende venv, nicht 3.13.

## 2026-09-13 — Port 20003 ist die Wahrheit, nicht 8080 und nicht 5060

Was: als Port dieses Dienstes gilt 20003, belegt durch `ss -tulnp` (PID 1479)
und `nsw-web.service`. Code-Default 8080 und die README-Angabe sind veraltet.
Die im Setup-Auftrag genannte 5060 kommt im gesamten System nirgends vor.
Warum: der laufende Prozess ist die Wahrheit, nicht die Dokumentation.
Verworfen: den Dienst auf den Code-Default umzustellen. Das Portregister ordnet
20003 diesem Dienst zu, und 8080 wäre eine Rückkehr in die Zeit vor der
Portmigration.
