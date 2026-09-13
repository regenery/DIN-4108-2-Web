# Entscheidungen DIN-4108-2-Web

ADR-light: was, wann, warum, verworfene Alternative. Neueste oben.

## 2026-09-13 — Port 20003 ist die Wahrheit, nicht 8080 und nicht 5060

Was: als Port dieses Dienstes gilt 20003, belegt durch `ss -tulnp` (PID 1479)
und `nsw-web.service`. Code-Default 8080 und die README-Angabe sind veraltet.
Die im Setup-Auftrag genannte 5060 kommt im gesamten System nirgends vor.
Warum: der laufende Prozess ist die Wahrheit, nicht die Dokumentation.
Verworfen: den Dienst auf den Code-Default umzustellen. Das Portregister ordnet
20003 diesem Dienst zu, und 8080 wäre eine Rückkehr in die Zeit vor der
Portmigration.
