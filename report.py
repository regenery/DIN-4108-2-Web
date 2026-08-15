# -*- coding: utf-8 -*-
"""
PDF-Projektreport für den Nachweis des sommerlichen Wärmeschutzes
nach DIN 4108-2:2013-02 — prüffähig aufbereitet (u. a. für BAFA-Förderanträge).
"""

import glob
import io
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, KeepTogether,
                                PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)

import din4108 as din
from din4108 import de

# ---------------------------------------------------------------------------
# Farben und Schriften
# ---------------------------------------------------------------------------

TINTE = colors.HexColor("#14202e")
GRAU = colors.HexColor("#5b6b7c")
LINIE = colors.HexColor("#c9d2dc")
FEIN = colors.HexColor("#e7ecf2")
KOPF = colors.HexColor("#eef2f6")
AKZENT = colors.HexColor("#0f5f80")
GRUEN = colors.HexColor("#12704a")
GRUEN_BG = colors.HexColor("#e8f4ee")
ROT = colors.HexColor("#a3231c")
ROT_BG = colors.HexColor("#fbeceb")
GELB = colors.HexColor("#8a5a00")
GELB_BG = colors.HexColor("#fdf4e3")

_SCHRIFT_PFADE = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/TTF",
    "/usr/local/share/fonts",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"),
]


def _registriere_schriften():
    """DejaVu für ≤, ², ⊥, Σ. Fällt auf Helvetica zurück, wenn nicht vorhanden."""
    gefunden = {}
    for verzeichnis in _SCHRIFT_PFADE:
        for datei in glob.glob(os.path.join(verzeichnis, "DejaVuSans*.ttf")):
            name = os.path.basename(datei)
            if name == "DejaVuSans.ttf":
                gefunden.setdefault("normal", datei)
            elif name == "DejaVuSans-Bold.ttf":
                gefunden.setdefault("fett", datei)
            elif name == "DejaVuSans-Oblique.ttf":
                gefunden.setdefault("kursiv", datei)
    if "normal" not in gefunden:
        return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"
    pdfmetrics.registerFont(TTFont("NSW", gefunden["normal"]))
    fett = gefunden.get("fett", gefunden["normal"])
    kursiv = gefunden.get("kursiv", gefunden["normal"])
    pdfmetrics.registerFont(TTFont("NSW-Bold", fett))
    pdfmetrics.registerFont(TTFont("NSW-Italic", kursiv))
    pdfmetrics.registerFontFamily("NSW", normal="NSW", bold="NSW-Bold",
                                  italic="NSW-Italic")
    return "NSW", "NSW-Bold", "NSW-Italic"


FONT, FONT_B, FONT_I = _registriere_schriften()

# ---------------------------------------------------------------------------
# Absatzformate
# ---------------------------------------------------------------------------

_basis = getSampleStyleSheet()

S_TITEL = ParagraphStyle("titel", parent=_basis["Normal"], fontName=FONT_B,
                         fontSize=17, leading=21, textColor=TINTE, spaceAfter=2)
S_UNTERTITEL = ParagraphStyle("untertitel", parent=_basis["Normal"], fontName=FONT,
                              fontSize=9.5, leading=13, textColor=GRAU)
S_H = ParagraphStyle("h", parent=_basis["Normal"], fontName=FONT_B, fontSize=10.5,
                     leading=14, textColor=TINTE, spaceBefore=11, spaceAfter=5)
S_T = ParagraphStyle("t", parent=_basis["Normal"], fontName=FONT, fontSize=8.6,
                     leading=12, textColor=TINTE, alignment=TA_LEFT)
S_KLEIN = ParagraphStyle("klein", parent=S_T, fontSize=7.6, leading=10.4,
                         textColor=GRAU)
S_ZELLE = ParagraphStyle("zelle", parent=S_T, fontSize=8.0, leading=10.6)
S_ZELLE_B = ParagraphStyle("zelleb", parent=S_ZELLE, fontName=FONT_B)
S_LABEL = ParagraphStyle("label", parent=S_T, fontSize=7.4, leading=9.5,
                         textColor=GRAU)


S_ZELLE_R = ParagraphStyle("zeller", parent=S_ZELLE, alignment=TA_RIGHT)
S_MINI = ParagraphStyle("mini", parent=S_ZELLE, fontSize=7.2, leading=9.2)
S_MINI_B = ParagraphStyle("minib", parent=S_MINI, fontName=FONT_B)


def p(text, stil=S_T, leer="—"):
    return Paragraph(str(text) if text not in (None, "") else leer, stil)


def _rechts(zelle):
    """Paragraph rechtsbündig ausrichten (TableStyle-ALIGN greift dort nicht)."""
    if isinstance(zelle, Paragraph):
        stil = ParagraphStyle("r_" + zelle.style.name, parent=zelle.style,
                              alignment=TA_RIGHT)
        return Paragraph(zelle.text, stil)
    return zelle


# ---------------------------------------------------------------------------
# Seitenrahmen
# ---------------------------------------------------------------------------

RAND_L = RAND_R = 18 * mm
RAND_O = 26 * mm
RAND_U = 20 * mm


class Dokument(BaseDocTemplate):
    def __init__(self, puffer, projekt, **kw):
        super().__init__(puffer, pagesize=A4, leftMargin=RAND_L,
                         rightMargin=RAND_R, topMargin=RAND_O,
                         bottomMargin=RAND_U,
                         title=f"Nachweis sommerlicher Wärmeschutz — "
                               f"{projekt.get('projekt', '')}",
                         author=projekt.get("ersteller", "") or "NSW-Web",
                         subject="DIN 4108-2:2013-02, Verfahren "
                                 "Sonneneintragskennwerte", **kw)
        self.projekt = projekt
        rahmen = Frame(RAND_L, RAND_U, A4[0] - RAND_L - RAND_R,
                       A4[1] - RAND_O - RAND_U, id="haupt",
                       leftPadding=0, rightPadding=0, topPadding=0,
                       bottomPadding=0)
        self.addPageTemplates([PageTemplate(id="std", frames=[rahmen],
                                            onPage=self._rahmen)])

    def _rahmen(self, cv, doc):
        breite, hoehe = A4
        cv.saveState()

        cv.setFont(FONT_B, 7.6)
        cv.setFillColor(AKZENT)
        cv.drawString(RAND_L, hoehe - 15 * mm,
                      "NACHWEIS SOMMERLICHER WÄRMESCHUTZ")
        cv.setFont(FONT, 7.6)
        cv.setFillColor(GRAU)
        cv.drawRightString(breite - RAND_R, hoehe - 15 * mm,
                           "DIN 4108-2:2013-02 · Verfahren Sonneneintragskennwerte")
        cv.setStrokeColor(LINIE)
        cv.setLineWidth(0.6)
        cv.line(RAND_L, hoehe - 17.5 * mm, breite - RAND_R, hoehe - 17.5 * mm)

        cv.line(RAND_L, 14 * mm, breite - RAND_R, 14 * mm)
        cv.setFont(FONT, 7.2)
        cv.setFillColor(GRAU)
        links = " · ".join(x for x in [self.projekt.get("projekt"),
                                       self.projekt.get("referenzraum")] if x)
        cv.drawString(RAND_L, 10 * mm, links[:95])
        cv.drawRightString(breite - RAND_R, 10 * mm, f"Seite {doc.page}")
        cv.restoreState()


# ---------------------------------------------------------------------------
# Tabellenbausteine
# ---------------------------------------------------------------------------

NUTZBREITE = A4[0] - RAND_L - RAND_R


def _gitter(extra=None):
    stil = [
        ("GRID", (0, 0), (-1, -1), 0.4, FEIN),
        ("BOX", (0, 0), (-1, -1), 0.6, LINIE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    return TableStyle(stil + (extra or []))


def kopftabelle(kopf, zeilen, breiten, ausrichtung_rechts=(), extra=None,
                kopfstil=None):
    daten = [[p(t, kopfstil or S_ZELLE_B, leer="") for t in kopf]] + [list(z) for z in zeilen]
    for zeile in daten:
        for spalte in ausrichtung_rechts:
            if spalte < len(zeile):
                zeile[spalte] = _rechts(zeile[spalte])
    stil = [("BACKGROUND", (0, 0), (-1, 0), KOPF),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, LINIE)]
    tab = Table(daten, colWidths=breiten, repeatRows=1, hAlign="LEFT")
    tab.setStyle(_gitter(stil + (extra or [])))
    return tab


def feldpaare(paare, spalten=2):
    """Kompaktes Label/Wert-Raster."""
    zeilen, puffer = [], []
    for label, wert in paare:
        puffer.append(Table([[p(label, S_LABEL)], [p(wert, S_ZELLE)]],
                            colWidths=[NUTZBREITE / spalten - 6],
                            style=TableStyle([
                                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                ("TOPPADDING", (0, 0), (-1, -1), 0),
                                ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
                                ("BOTTOMPADDING", (0, 1), (-1, 1), 0)])))
        if len(puffer) == spalten:
            zeilen.append(puffer)
            puffer = []
    if puffer:
        puffer += [""] * (spalten - len(puffer))
        zeilen.append(puffer)

    tab = Table(zeilen, colWidths=[NUTZBREITE / spalten] * spalten, hAlign="LEFT")
    tab.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, FEIN)]))
    return tab


def ja_nein(flag):
    return "ja" if flag else "nein"


# ---------------------------------------------------------------------------
# Ergebnisblock
# ---------------------------------------------------------------------------

def _ausnutzungstext(ausn):
    if ausn is None:
        return "—"
    if ausn > 999:
        return "> 999 %"
    return de(ausn, 1) + " %"


def ergebnisblock(erg):
    if erg.status == "erfuellt":
        vg, hg, note = GRUEN, GRUEN_BG, "Anforderung erfüllt"
    elif erg.status == "kein_nachweis":
        vg, hg, note = GRUEN, GRUEN_BG, "Kein Nachweis erforderlich"
    elif erg.status == "nicht_erfuellt":
        vg, hg, note = ROT, ROT_BG, "Anforderung nicht erfüllt"
    else:
        vg, hg, note = GELB, GELB_BG, "Nachweis nicht durchführbar"

    s_vorh = erg.werte.get("S_vorh")
    s_zul = erg.werte.get("S_zul")
    ausn = erg.werte.get("ausnutzung")

    gross = ParagraphStyle("gross", parent=S_T, fontName=FONT_B, fontSize=15,
                           leading=18, textColor=vg)
    zahl = ParagraphStyle("zahl", parent=S_T, fontName=FONT_B, fontSize=13,
                          leading=16, textColor=TINTE)

    rechts = Table([
        [p("S,vorh", S_LABEL), p("S,zul", S_LABEL), p("Ausnutzung", S_LABEL)],
        [p(de(s_vorh, 4), zahl), p(de(s_zul, 4), zahl),
         p(_ausnutzungstext(ausn), zahl)],
    ], colWidths=[30 * mm, 30 * mm, 30 * mm])
    rechts.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 1)]))

    tab = Table([[p(note, gross), rechts]],
                colWidths=[NUTZBREITE - 96 * mm, 96 * mm])
    tab.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), hg),
        ("BOX", (0, 0), (-1, -1), 0.8, vg),
        ("LINEBEFORE", (0, 0), (0, -1), 3.2, vg),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (0, -1), 9),
        ("RIGHTPADDING", (1, 0), (1, -1), 9)]))
    return tab


def hinweisblock(titel, eintraege, vg, hg):
    if not eintraege:
        return None
    inhalt = [[p(titel, ParagraphStyle("hb", parent=S_ZELLE_B, textColor=vg))]]
    for text in eintraege:
        inhalt.append([p("– " + text, S_ZELLE)])
    tab = Table(inhalt, colWidths=[NUTZBREITE])
    tab.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), hg),
        ("BOX", (0, 0), (-1, -1), 0.5, vg),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return tab


# ---------------------------------------------------------------------------
# Hauptfunktion
# ---------------------------------------------------------------------------

class Zaehler:
    """Fortlaufende Abschnittsnummern — kein Sprung, wenn ein Teil entfällt."""

    def __init__(self):
        self.stand = 0

    def __call__(self, titel):
        self.stand += 1
        return p(f"{self.stand} {titel}", S_H)


def erzeuge_pdf(projekt, fenster, erg):
    puffer = io.BytesIO()
    doc = Dokument(puffer, projekt)
    w = erg.werte
    e = []
    abschnitt = Zaehler()

    # --- Kopf ----------------------------------------------------------
    e.append(p("Nachweis des sommerlichen Wärmeschutzes", S_TITEL))
    e.append(p("Vereinfachtes Verfahren über Sonneneintragskennwerte nach "
               "DIN 4108-2:2013-02, Abschnitt 8.3", S_UNTERTITEL))
    e.append(Spacer(1, 9))

    e.append(feldpaare([
        ("Projekt / Gebäude", projekt.get("projekt")),
        ("Datum", projekt.get("datum")),
        ("Gebäudebereich", projekt.get("gebaeudebereich")),
        ("Büro / Firma", projekt.get("buero")),
        ("Referenzraum", projekt.get("referenzraum")),
        ("Ersteller", projekt.get("ersteller")),
        ("Bauvorhaben / Anschrift", projekt.get("bauvorhaben_adresse")),
        ("Förder-/Vorhabenkennzeichen", projekt.get("foerderkennzeichen")),
    ]))
    e.append(Spacer(1, 11))

    # --- Ergebnis ------------------------------------------------------
    e.append(p("Ergebnis", S_H))
    e.append(ergebnisblock(erg))
    e.append(Spacer(1, 4))
    e.append(p("Anforderung nach DIN 4108-2:2013-02, Abschnitt 8.3: "
               "S,vorh ≤ S,zul.", S_KLEIN))

    for titel, liste, vg, hg in (
            ("Anmerkungen", erg.anmerkungen, AKZENT, KOPF),
            ("Hinweise", erg.warnungen, GELB, GELB_BG),
            ("Fehlende oder unzulässige Eingaben", erg.fehler, ROT, ROT_BG)):
        block = hinweisblock(titel, liste, vg, hg)
        if block is not None:
            e.append(Spacer(1, 6))
            e.append(block)

    # --- 1 Randbedingungen --------------------------------------------
    e.append(abschnitt("Randbedingungen des Nachweises"))
    bauart_herleitung = (projekt.get("waermekapazitaet")
                         if projekt.get("bauart_methode") == "nach DIN EN ISO 13786"
                         else projekt.get("rohdichte"))
    e.append(feldpaare([
        ("Gebäudekategorie", projekt.get("gebaeudetyp")),
        ("Sommerklimaregion (Bild 1)", projekt.get("klimaregion")),
        ("Nachtlüftung", projekt.get("nachtlueftung")),
        ("Einsatz passiver Kühlung (S6)", ja_nein(projekt.get("passive_kuehlung"))),
        ("Anlage zur Kühlung vorhanden", ja_nein(projekt.get("aktive_kuehlung"))
         + (" — nach DIN 4108-2 nicht anrechenbar"
            if projekt.get("aktive_kuehlung") else "")),
        ("Bestimmung der Bauart", projekt.get("bauart_methode")),
        ("Eingangsgröße Bauart", bauart_herleitung),
        ("Ermittelte Bauart", erg.bauart),
        ("Verzicht nach 8.2.2 b) angesetzt",
         ja_nein(projekt.get("verzicht_822b"))),
    ]))

    if projekt.get("bauart_methode") == "nach DIN 4108-2":
        zeilen = [[p(bez, S_ZELLE), p(ja_nein(projekt.get(schluessel)), S_ZELLE)]
                  for schluessel, bez in din.BAUART_KRITERIEN]
        e.append(Spacer(1, 5))
        e.append(kopftabelle(["Kriterium zur Bauartbestimmung", "erfüllt"], zeilen,
                             [NUTZBREITE - 28 * mm, 28 * mm],
                             ausrichtung_rechts=(1,)))

    if projekt.get("glasvorbau_nur") or projekt.get("glasvorbau_nicht_nur"):
        e.append(Spacer(1, 5))
        e.append(p("Unbeheizter Glasvorbau: "
                   + ("Belüftung nur über den Glasvorbau (8.2.3 I. a)."
                      if projekt.get("glasvorbau_nur")
                      else "Belüftung nicht oder nicht nur über den Glasvorbau "
                           "(8.2.3 II. a)."), S_KLEIN))

    # --- 2 Referenzraum ------------------------------------------------
    e.append(abschnitt("Betrachteter Raum bzw. Raumbereich"))
    raumzeilen = []
    if w.get("LH", 0) > 0:
        raumzeilen.append([p("Lichte Raumhöhe", S_ZELLE), p("LH", S_ZELLE),
                           p(de(w.get("LH")), S_ZELLE), p("m", S_ZELLE)])
    if w.get("LT", 0) > 0:
        raumzeilen.append([p("Lichte Raumtiefe (LT,max ≤ 3 · LH)", S_ZELLE),
                           p("LT", S_ZELLE), p(de(w.get("LT")), S_ZELLE),
                           p("m", S_ZELLE)])
    if w.get("LB", 0) > 0:
        raumzeilen.append([p("Lichte Raumbreite", S_ZELLE), p("LB", S_ZELLE),
                           p(de(w.get("LB")), S_ZELLE), p("m", S_ZELLE)])
    raumzeilen.append([p("Nettogrundfläche (" + str(w.get("AG_herkunft", "AG = LT · LB"))
                        + ")", S_ZELLE_B), p("AG", S_ZELLE_B),
                       p(de(w.get("AG")), S_ZELLE_B), p("m²", S_ZELLE_B)])
    e.append(kopftabelle(
        ["Größe", "Kurzzeichen", "Wert", "Einheit"], raumzeilen,
        [NUTZBREITE - 76 * mm, 26 * mm, 26 * mm, 24 * mm],
        ausrichtung_rechts=(2,)))

    # --- 3 Fenster -----------------------------------------------------
    e.append(abschnitt("Kennwerte der Fenster im betrachteten Raum"))
    zeilen = []
    direkt_vorhanden = False
    for f in fenster:
        direkt = f.flaeche_direkt > 0
        direkt_vorhanden = direkt_vorhanden or direkt
        zeilen.append([
            p(f.nr, S_MINI), p(f.bezeichnung, S_MINI),
            p(f.orientierung, S_MINI),
            p("0°–60°" if f.ist_geneigt else "60°–90°", S_MINI),
            p(de(f.breite) if not direkt and f.breite > 0 else "—", S_MINI),
            p(de(f.hoehe) if not direkt and f.hoehe > 0 else "—", S_MINI),
            p(f.anzahl, S_MINI), p(f.glastyp, S_MINI),
            p(de(f.g_wert, 2), S_MINI), p(de(f.fc, 2), S_MINI),
            p(de(f.gtot, 3), S_MINI),
            p(de(f.flaeche, 2) + ("*" if direkt else ""), S_MINI),
            p(de(f.solareintrag, 3), S_MINI)])
    zeilen.append([p("", S_MINI_B, leer=""), p("Summe", S_MINI_B)]
                  + [p("", S_MINI_B, leer="")] * 9
                  + [p(de(w.get("AW_ges")), S_MINI_B),
                     p(de(w.get("summenprodukt"), 3), S_MINI_B)])

    breiten = [5, 16, 12, 10, 7, 7, 7, 14, 7, 7, 8, 10, 11]
    faktor = NUTZBREITE / sum(breiten)
    e.append(kopftabelle(
        ["Nr.", "Fenster", "Orient.", "Neigung", "B [m]", "H [m]", "Anz.",
         "Glastyp", "g⊥", "FC", "gtot", "AW,j [m²]", "AW·gtot [m²]"],
        zeilen, [b * faktor for b in breiten], kopfstil=S_MINI_B,
        ausrichtung_rechts=(4, 5, 6, 8, 9, 10, 11, 12),
        extra=[("BACKGROUND", (0, len(zeilen)), (-1, len(zeilen)), KOPF),
               ("LINEABOVE", (0, len(zeilen)), (-1, len(zeilen)), 0.8, LINIE),
               ("LEFTPADDING", (0, 0), (-1, -1), 3),
               ("RIGHTPADDING", (0, 0), (-1, -1), 3)]))
    e.append(Spacer(1, 3))
    hinweistext = ("AW,j = Breite · Höhe · Anzahl, ermittelt aus dem lichten "
                   "Rohbaumaß der Fensteröffnung. gtot = g⊥ · FC. Die "
                   "Abminderungsfaktoren FC sind DIN 4108-2:2013-02, Tabelle 7 "
                   "entnommen.")
    if direkt_vorhanden:
        hinweistext += (" * Bei diesen Fenstern wurde die Fensterfläche AW,j "
                        "direkt vorgegeben, nicht aus Breite und Höhe "
                        "ermittelt.")
    e.append(p(hinweistext, S_KLEIN))

    zeilen_ss = [[p(f.nr, S_ZELLE), p(f.sonnenschutzart, S_ZELLE),
                  p(de(f.fc, 2), S_ZELLE),
                  p("ja" if f.verschattet else "nein", S_ZELLE)]
                 for f in fenster]
    e.append(Spacer(1, 6))
    e.append(kopftabelle(
        ["Nr.", "Sonnenschutzvorrichtung", "FC", "dauerhaft eigenverschattet"],
        zeilen_ss, [10 * mm, NUTZBREITE - 68 * mm, 16 * mm, 42 * mm],
        ausrichtung_rechts=(2, 3)))

    # --- 4 Flächenzusammenstellung -------------------------------------
    e.append(abschnitt("Zusammenstellung der Fensterflächen"))
    flaechen = [
        ("Summe aller Fensterflächen mit Zweifachverglasung (g > 0,4)",
         "ΣAW1", w.get("AW1")),
        ("Summe aller Fensterflächen mit Dreifachverglasung (g > 0,4)",
         "ΣAW2", w.get("AW2")),
        ("Summe aller Fensterflächen mit Sonnenschutzverglasung (g ≤ 0,4)",
         "ΣAW,g≤0,4", w.get("AW_ssg")),
        ("Summe aller geneigten Fensterflächen 0° ≤ Neigung ≤ 60°, "
         "alle Orientierungen", "ΣAW,neig≤60", w.get("AW_neig")),
        ("Summe aller nordost- und nordwest-orientierten Fensterflächen "
         "(60° < Neigung ≤ 90°)", "ΣAW,no.nw>60", w.get("AW_no_nw")),
        ("Summe aller anderen nordorientierten Fensterflächen "
         "(60° < Neigung ≤ 90°)", "ΣAW,nord>60", w.get("AW_nord")),
        ("Summe aller anderen Orientierungen, Nordwest über Süd bis Nordost "
         "(60° < Neigung ≤ 90°)", "ΣAW,sonst>60", w.get("AW_sonst")),
        ("Summe aller dauerhaft vom Gebäude selbst verschatteten Fensterflächen",
         "ΣAW,verschattet", w.get("AW_verschattet")),
        ("Summe aller Fensterflächen, auch Dachfenster",
         "AW,ges", w.get("AW_ges")),
    ]
    zeilen = [[p(t, S_ZELLE_B if k == "AW,ges" else S_ZELLE),
               p(k, S_ZELLE_B if k == "AW,ges" else S_ZELLE),
               p(de(v), S_ZELLE_B if k == "AW,ges" else S_ZELLE),
               p("m²", S_ZELLE)] for t, k, v in flaechen]
    e.append(kopftabelle(["Fensterfläche", "Kurzzeichen", "Wert", "Einheit"],
                         zeilen, [NUTZBREITE - 84 * mm, 34 * mm, 26 * mm, 24 * mm],
                         ausrichtung_rechts=(2,)))

    # --- 5 Prüfung Tabelle 6 -------------------------------------------
    e.append(abschnitt("Prüfung, ob ein Nachweis erforderlich ist (Tabelle 6)"))
    fwg, fwg_zul = w.get("fWG"), w.get("fWG_zul")
    notwendig = fwg is not None and fwg_zul is not None and fwg >= fwg_zul
    e.append(kopftabelle(
        ["Größe", "Berechnung", "Wert", "Einheit"],
        [[p("Grundflächenbezogener Fensterflächenanteil", S_ZELLE),
          p("fWG = 100 · AW,ges / AG", S_ZELLE), p(de(fwg), S_ZELLE),
          p("%", S_ZELLE)],
         [p(f"Zulässiger Fensterflächenanteil ({w.get('fWG_fall', '')})", S_ZELLE),
          p("DIN 4108-2, Tabelle 6", S_ZELLE), p(de(fwg_zul), S_ZELLE),
          p("%", S_ZELLE)],
         [p("Ergebnis der Prüfung", S_ZELLE_B),
          p("fWG ≥ fWG,zul" if notwendig else "fWG < fWG,zul", S_ZELLE_B),
          p("Nachweis erforderlich" if notwendig
            else "kein Nachweis erforderlich", S_ZELLE_B),
          p("", S_ZELLE, leer="")]],
        [NUTZBREITE - 96 * mm, 54 * mm, 26 * mm, 16 * mm],
        ausrichtung_rechts=(2,)))

    # --- 6 S,zul -------------------------------------------------------
    e.append(abschnitt("Ermittlung des zulässigen Sonneneintragskennwertes S,zul"))
    zeilen = [[p(h["kurz"], S_ZELLE_B), p(h["titel"], S_ZELLE),
               p(h["formel"], S_ZELLE), p(de(h["wert"], 4), S_ZELLE)]
              for h in erg.herleitung]
    zeilen.append([p("S,zul", S_ZELLE_B),
                   p("Maximal zulässiger Sonneneintragskennwert", S_ZELLE_B),
                   p("S,zul = S1 + S2 + S3 + S4 + S5 + S6", S_ZELLE_B),
                   p(de(w.get("S_zul"), 4), S_ZELLE_B)])
    e.append(kopftabelle(
        ["", "Anteiliger Kennwert", "Herleitung", "Wert [–]"], zeilen,
        [12 * mm, 52 * mm, NUTZBREITE - 86 * mm, 22 * mm],
        ausrichtung_rechts=(3,),
        extra=[("BACKGROUND", (0, len(zeilen)), (-1, len(zeilen)), KOPF),
               ("LINEABOVE", (0, len(zeilen)), (-1, len(zeilen)), 0.8, LINIE)]))
    e.append(Spacer(1, 3))
    e.append(p("Anteilige Sonneneintragskennwerte nach DIN 4108-2:2013-02, "
               "Tabelle 8. fneig = ΣAW,neig≤60 / AW,ges = "
               f"{de(w.get('fneig'), 3)}; fnord = (ΣAW,nord + ΣAW,no.nw + "
               f"ΣAW,verschattet) / AW,ges = {de(w.get('fnord'), 3)}.", S_KLEIN))

    # --- 7 S,vorh ------------------------------------------------------
    e.append(abschnitt("Ermittlung des vorhandenen Sonneneintragskennwertes S,vorh"))
    e.append(kopftabelle(
        ["Größe", "Berechnung", "Wert", "Einheit"],
        [[p("Summenprodukt aus Fensterflächen und Gesamtenergiedurchlassgraden",
            S_ZELLE), p("Σ (AW,j · gtot,j)", S_ZELLE),
          p(de(w.get("summenprodukt"), 3), S_ZELLE), p("m²", S_ZELLE)],
         [p("Nettogrundfläche des Referenzraumes", S_ZELLE), p("AG", S_ZELLE),
          p(de(w.get("AG")), S_ZELLE), p("m²", S_ZELLE)],
         [p("Vorhandener Sonneneintragskennwert", S_ZELLE_B),
          p("S,vorh = Σ (AW,j · gtot,j) / AG", S_ZELLE_B),
          p(de(w.get("S_vorh"), 4), S_ZELLE_B), p("–", S_ZELLE_B)]],
        [NUTZBREITE - 96 * mm, 54 * mm, 26 * mm, 16 * mm],
        ausrichtung_rechts=(2,)))

    # --- 8 Bewertung ---------------------------------------------------
    e.append(abschnitt("Bewertung"))
    e.append(ergebnisblock(erg))

    # --- 9 Annahmen ----------------------------------------------------
    if (projekt.get("annahmen") or "").strip() or (projekt.get("kommentare") or "").strip():
        e.append(abschnitt("Annahmen und Kommentare des Erstellers"))
        if (projekt.get("annahmen") or "").strip():
            e.append(p("Annahmen und sonstige Überlegungen zur Nachweisführung",
                       S_ZELLE_B))
            for zeile in projekt["annahmen"].splitlines():
                e.append(p(zeile or " ", S_ZELLE))
            e.append(Spacer(1, 5))
        if (projekt.get("kommentare") or "").strip():
            e.append(p("Kommentare", S_ZELLE_B))
            for zeile in projekt["kommentare"].splitlines():
                e.append(p(zeile or " ", S_ZELLE))

    # --- 10 Verfahren --------------------------------------------------
    e.append(abschnitt("Angewendetes Verfahren und Grundlagen"))
    e.append(p(
        "Der Nachweis wurde nach dem vereinfachten Verfahren über "
        "Sonneneintragskennwerte gemäß DIN 4108-2:2013-02, Abschnitt 8.3 "
        "geführt. Die Anforderung gilt als erfüllt, wenn der vorhandene "
        "Sonneneintragskennwert des betrachteten Raumes den maximal zulässigen "
        "Sonneneintragskennwert nicht übersteigt (S,vorh ≤ S,zul). Der "
        "zulässige Kennwert setzt sich aus den anteiligen Kennwerten S1 bis S6 "
        "nach Tabelle 8 zusammen; die Abminderungsfaktoren FC der "
        "Sonnenschutzvorrichtungen sind Tabelle 7 entnommen. Die Prüfung, ob "
        "auf einen Nachweis verzichtet werden kann, erfolgt über den "
        "grundflächenbezogenen Fensterflächenanteil nach Tabelle 6.", S_T))
    e.append(Spacer(1, 5))
    e.append(kopftabelle(
        ["Formelzeichen", "Bedeutung"],
        [[p(k, S_ZELLE), p(t, S_ZELLE)] for k, t in [
            ("S,vorh", "vorhandener Sonneneintragskennwert = Σ (AW,j · gtot,j) / AG"),
            ("S,zul", "maximal zulässiger Sonneneintragskennwert = S1 + … + S6"),
            ("AW,j", "Fensterfläche j (lichtes Rohbaumaß der Fensteröffnung)"),
            ("gtot,j", "Gesamtenergiedurchlassgrad des Fensters j inkl. "
                       "Sonnenschutz, gtot = g⊥ · FC"),
            ("g⊥", "Gesamtenergiedurchlassgrad der Verglasung bei senkrechtem "
                   "Strahlungseinfall"),
            ("FC", "Abminderungsfaktor der Sonnenschutzvorrichtung (Tabelle 7)"),
            ("AG", "Nettogrundfläche des Raumes bzw. Raumbereiches"),
            ("fWG", "grundflächenbezogener Fensterflächenanteil in %"),
            ("fneig", "Anteil geneigter Fensterflächen an der Gesamtfensterfläche"),
            ("fnord", "Anteil der Nordfensterflächen und der dauerhaft "
                      "verschatteten Flächen an der Gesamtfensterfläche")]],
        [30 * mm, NUTZBREITE - 30 * mm]))

    # --- Unterschrift --------------------------------------------------
    unterschrift = Table(
        [[p(" ", S_T), p(" ", S_T)],
         [p("Ort, Datum", S_LABEL),
          p("Unterschrift / Stempel des Erstellers", S_LABEL)]],
        colWidths=[NUTZBREITE * 0.45, NUTZBREITE * 0.55], rowHeights=[16 * mm, None])
    unterschrift.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, TINTE),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 1), (-1, 1), 2)]))
    e.append(Spacer(1, 14))
    e.append(KeepTogether([abschnitt("Bestätigung"), unterschrift]))

    doc.build(e)
    puffer.seek(0)
    return puffer
