# DIN-4108-2-Web

NSW-Web: Nachweis des sommerlichen Wärmeschutzes über Sonneneintragskennwerte
nach DIN 4108-2:2013-02, Nachbau des IWU-Excelwerkzeugs mit prüffähigem PDF.

@tasks/STATUS.md

- Klasse: eigenes Werkzeug, freie Hand.
- Dienst `nsw-web.service` auf `127.0.0.1:20003`. Code-Default und README nennen
  8080 — das ist veraltet, der Port ist 20003. Dienst nicht neu starten.
- Rechenergebnisse müssen gegen das Originalwerkzeug prüfbar bleiben; Formeln
  nicht ohne Testfall ändern.
