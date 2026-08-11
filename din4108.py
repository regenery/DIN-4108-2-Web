# -*- coding: utf-8 -*-
"""
Rechenkern: Vereinfachter Nachweis des sommerlichen Wärmeschutzes
(Verfahren Sonneneintragskennwerte) nach DIN 4108-2:2013-02, Abschnitt 8.3.

Alle Zahlenwerte stammen aus DIN 4108-2:2013-02:
  Tabelle 6  →  zulässige grundflächenbezogene Fensterflächenanteile fWG
  Tabelle 7  →  Abminderungsfaktoren FC von Sonnenschutzvorrichtungen
  Tabelle 8  →  anteilige Sonneneintragskennwerte S1 … S6

Dieses Modul enthält ausschließlich Berechnung — keine Datenbank, kein Flask.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional

DIN_QUELLE = "DIN 4108-2:2013-02, Abschnitt 8.3 (Verfahren Sonneneintragskennwerte)"

# ---------------------------------------------------------------------------
# Auswahllisten
# ---------------------------------------------------------------------------

KLIMAREGIONEN = [
    "Region A (Sommerkühle Gebiete)",
    "Region B (Durchschnittliche Gebiete)",
    "Region C (Sommerheiße Gebiete)",
]
KLIMAREGION_INDEX = {name: i for i, name in enumerate(KLIMAREGIONEN)}

GEBAEUDETYPEN = ["Wohngebäude", "Nichtwohngebäude"]

NACHTLUEFTUNG = [
    "ohne",
    "erhöhte Nachtlüftung mit n ≥ 2 h⁻¹",
    "hohe Nachtlüftung mit n ≥ 5 h⁻¹",
]

BAUART_METHODEN = ["nach DIN 4108-2", "nach DIN EN ISO 13786"]

BAUARTEN = ["leichte Bauart", "mittlere Bauart", "schwere Bauart"]

WAERMEKAPAZITAET = [
    ("leichte Bauart: Cwirk / AG < 50 Wh/(m²K)", "leichte Bauart"),
    ("mittlere Bauart: 50 Wh/(m²K) ≤ Cwirk / AG ≤ 130 Wh/(m²K)", "mittlere Bauart"),
    ("schwere Bauart: Cwirk / AG > 130 Wh/(m²K)", "schwere Bauart"),
]

ROHDICHTEN = [
    "Rohdichte < 600 kg/m³",
    "600 kg/m³ ≤ Rohdichte < 1600 kg/m³",
    "Rohdichte ≥ 1600 kg/m³",
]

BAUART_KRITERIEN = [
    ("stahlbetondecke", "Stahlbetondecke"),
    ("keine_abgehaengte_decke", "keine abgehängte oder thermisch abgedeckte Decke"),
    ("keine_innendaemmung", "keine innenliegende Wärmedämmung an den Außenbauteilen"),
    ("keine_hohen_raeume", "keine hohen Räume (> 4,5 m) wie z. B. Turnhallen, Museen"),
]

ORIENTIERUNGEN = ["Nord", "Nordost", "Ost", "Südost",
                  "Süd", "Südwest", "West", "Nordwest"]

NEIGUNGEN = ["0° ≤ Neigung ≤ 60°", "60° < Neigung ≤ 90°"]

GLASTYPEN = ["zweifach", "dreifach", "Sonnenschutzglas (g ≤ 0,4)"]

# ---------------------------------------------------------------------------
# Verglasungskataloge: Glaseigenschaft → g-Wert (senkrechter Strahlungseinfall)
# ---------------------------------------------------------------------------

GLASEIGENSCHAFTEN: Dict[str, List[tuple]] = {
    "zweifach": [
        ("benutzerdefiniert", None),
        ("zweifach (Ug = 2,9 / τD65 = 0,82)", 0.78),
        ("i) Wärmedämmglas (Ug = 1,7 / τD65 = 0,74)", 0.72),
        ("ii) Wärmedämmglas (Ug = 1,4 / τD65 = 0,78)", 0.67),
        ("iii) Wärmedämmglas (Ug = 1,1 / τD65 = 0,80)", 0.60),
        ("iiii) Wärmedämmglas (Ug = 1,0 / τD65 = 0,71)", 0.48),
    ],
    "dreifach": [
        ("benutzerdefiniert", None),
        ("dreifach (Ug = 2,0 / τD65 = 0,75)", 0.70),
        ("i) Wärmedämmglas (Ug = 0,8 / τD65 = 0,69)", 0.50),
        ("ii) Wärmedämmglas (Ug = 0,8 / τD65 = 0,74)", 0.60),
        ("iii) Wärmedämmglas (Ug = 0,7 / τD65 = 0,70)", 0.50),
        ("iiii) Wärmedämmglas (Ug = 0,6 / τD65 = 0,69)", 0.50),
    ],
    "Sonnenschutzglas (g ≤ 0,4)": [
        ("benutzerdefiniert", None),
        ("i) zweifach-SSG (Ug = 1,2 / τD65 = 0,67)", 0.37),
        ("ii) zweifach-SSG (Ug = 1,2 / τD65 = 0,40)", 0.25),
        ("i) dreifach-SSG (Ug = 0,7 / τD65 = 0,63)", 0.34),
        ("ii) dreifach-SSG (Ug = 0,7 / τD65 = 0,45)", 0.24),
        ("iii) dreifach-SSG (Ug = 0,7 / τD65 = 0,27)", 0.16),
    ],
}

# ---------------------------------------------------------------------------
# DIN 4108-2:2013-02, Tabelle 7 — Abminderungsfaktoren FC
# Spalten: (Sonnenschutzglas g ≤ 0,40 | dreifach g > 0,40 | zweifach g > 0,40)
# ---------------------------------------------------------------------------

SONNENSCHUTZ_FC: List[tuple] = [
    ("ohne Sonnenschutzvorrichtung", 1.00, 1.00, 1.00),
    ("Innenliegend oder zwischen den Scheiben: weiß oder hoch reflektierende "
     "Oberflächen mit geringer Transparenz", 0.65, 0.70, 0.65),
    ("Innenliegend oder zwischen den Scheiben: helle Farben oder geringe "
     "Transparenz", 0.75, 0.80, 0.75),
    ("Innenliegend oder zwischen den Scheiben: dunkle Farben oder höhere "
     "Transparenz", 0.90, 0.90, 0.85),
    ("Außenliegend: Fensterläden, Rollläden, ¾ geschlossen", 0.35, 0.30, 0.30),
    ("Außenliegend: Fensterläden, Rollläden, geschlossen (informativ, sollte "
     "nicht verwendet werden)", 0.15, 0.10, 0.10),
    ("Außenliegend: Jalousie und Raffstore, drehbare Lamellen, 45° "
     "Lamellenstellung", 0.30, 0.25, 0.25),
    ("Außenliegend: Jalousie und Raffstore, drehbare Lamellen, 10° "
     "Lamellenstellung (informativ, sollte nicht verwendet werden)",
     0.20, 0.15, 0.20),
    ("Außenliegend: Markise, parallel zur Verglasung", 0.30, 0.25, 0.25),
    ("Außenliegend: Vordächer, Markisen allgemein, freistehende Lamellen",
     0.55, 0.50, 0.50),
    ("benutzerdefiniert", None, None, None),
]

_FC_SPALTE = {"Sonnenschutzglas (g ≤ 0,4)": 1, "dreifach": 2, "zweifach": 3}


def fc_wert(sonnenschutzart: str, glastyp: str) -> Optional[float]:
    """FC nach Tabelle 7 für die Kombination Sonnenschutzart / Glaserzeugnis."""
    spalte = _FC_SPALTE.get(glastyp, 3)
    for eintrag in SONNENSCHUTZ_FC:
        if eintrag[0] == sonnenschutzart:
            return eintrag[spalte]
    return None


def g_wert_katalog(glastyp: str, glaseigenschaft: str) -> Optional[float]:
    for name, wert in GLASEIGENSCHAFTEN.get(glastyp, []):
        if name == glaseigenschaft:
            return wert
    return None


# ---------------------------------------------------------------------------
# DIN 4108-2:2013-02, Tabelle 8 — anteilige Sonneneintragskennwerte
# ---------------------------------------------------------------------------

# S1: [Gebäudetyp][Nachtlüftung][Bauart] → [Region A, B, C]
S1_TABELLE = {
    "Wohngebäude": {
        "ohne": {
            "leichte Bauart":  [0.071, 0.056, 0.041],
            "mittlere Bauart": [0.080, 0.067, 0.054],
            "schwere Bauart":  [0.087, 0.074, 0.061],
        },
        "erhöhte Nachtlüftung mit n ≥ 2 h⁻¹": {
            "leichte Bauart":  [0.098, 0.088, 0.078],
            "mittlere Bauart": [0.114, 0.103, 0.092],
            "schwere Bauart":  [0.125, 0.113, 0.101],
        },
        "hohe Nachtlüftung mit n ≥ 5 h⁻¹": {
            "leichte Bauart":  [0.128, 0.117, 0.105],
            "mittlere Bauart": [0.160, 0.152, 0.143],
            "schwere Bauart":  [0.181, 0.171, 0.160],
        },
    },
    "Nichtwohngebäude": {
        "ohne": {
            "leichte Bauart":  [0.013, 0.007, 0.000],
            "mittlere Bauart": [0.020, 0.013, 0.006],
            "schwere Bauart":  [0.025, 0.018, 0.011],
        },
        "erhöhte Nachtlüftung mit n ≥ 2 h⁻¹": {
            "leichte Bauart":  [0.071, 0.060, 0.048],
            "mittlere Bauart": [0.089, 0.081, 0.072],
            "schwere Bauart":  [0.101, 0.092, 0.083],
        },
        "hohe Nachtlüftung mit n ≥ 5 h⁻¹": {
            "leichte Bauart":  [0.090, 0.082, 0.074],
            "mittlere Bauart": [0.135, 0.124, 0.113],
            "schwere Bauart":  [0.170, 0.158, 0.145],
        },
    },
}

# S2 = a − b · fWG  (fWG als Verhältnis, nicht in Prozent)
S2_KOEFFIZIENTEN = {
    "Wohngebäude":      {"a": 0.060, "b": 0.231},
    "Nichtwohngebäude": {"a": 0.030, "b": 0.115},
}

S3_FAKTOR = 0.03     # S3 = 0,03 · (AW,gtot ≤ 0,4 / AW,ges)
S4_FAKTOR = -0.035   # S4 = −0,035 · fneig
S5_FAKTOR = 0.10     # S5 = 0,10 · fnord

S6_PASSIVE_KUEHLUNG = {
    "leichte Bauart": 0.02,
    "mittlere Bauart": 0.04,
    "schwere Bauart": 0.06,
}

# DIN 4108-2:2013-02, Tabelle 6 — zulässiger fWG in %, unterhalb dessen auf
# einen Nachweis verzichtet werden kann
FWG_ZULAESSIG = {"sonst": 10.0, "nord": 15.0, "geneigt": 7.0}

# Das Excel-Original rechnet mit den *angezeigten*, gerundeten Zwischenwerten
# weiter (AG und AW,ges auf 2, fneig und fnord auf 3 Nachkommastellen).
# Standardmäßig wird hier mit voller Genauigkeit gerechnet; mit
# RUNDUNG_WIE_EXCEL = True lassen sich die Zahlen des Excel-Tools exakt
# reproduzieren (Abweichung typisch in der 4. Nachkommastelle von S).
RUNDUNG_WIE_EXCEL = False

TABELLE_6 = [
    ("über 60° bis 90°", "Nordwest über Süd bis Nordost", 10),
    ("über 60° bis 90°", "alle anderen Nordorientierungen", 15),
    ("von 0° bis 60°", "alle Orientierungen", 7),
]


# ---------------------------------------------------------------------------
# Bauart-Ermittlung
# ---------------------------------------------------------------------------

def ermittle_bauart(methode: str, kapazitaet: str, rohdichte: str,
                    stahlbetondecke: bool, keine_abgehaengte_decke: bool,
                    keine_innendaemmung: bool, keine_hohen_raeume: bool) -> str:
    """Bauart nach DIN 4108-2 bzw. direkte Vorgabe über Cwirk/AG (DIN EN ISO 13786)."""
    if methode == "nach DIN EN ISO 13786":
        for label, bauart in WAERMEKAPAZITAET:
            if label == kapazitaet:
                return bauart
        return "leichte Bauart"

    alle_kriterien = (stahlbetondecke and keine_abgehaengte_decke
                      and keine_innendaemmung and keine_hohen_raeume)

    if rohdichte == "Rohdichte < 600 kg/m³":
        return "leichte Bauart"
    if rohdichte == "600 kg/m³ ≤ Rohdichte < 1600 kg/m³":
        return "mittlere Bauart" if alle_kriterien else "leichte Bauart"
    if rohdichte == "Rohdichte ≥ 1600 kg/m³":
        return "schwere Bauart" if alle_kriterien else "leichte Bauart"
    return "leichte Bauart"


# ---------------------------------------------------------------------------
# Fenster
# ---------------------------------------------------------------------------

@dataclass
class Fenster:
    nr: int = 1
    bezeichnung: str = ""
    orientierung: str = "Süd"
    neigung: str = NEIGUNGEN[1]
    breite: float = 0.0
    hoehe: float = 0.0
    anzahl: int = 1
    flaeche_direkt: float = 0.0
    glastyp: str = "zweifach"
    glaseigenschaft: str = "benutzerdefiniert"
    g_wert: float = 0.0
    verschattet: bool = False
    sonnenschutzart: str = "ohne Sonnenschutzvorrichtung"
    fc: float = 1.0

    @property
    def flaeche(self) -> float:
        """AW,j = Breite · Höhe · Anzahl, oder direkt vorgegebene Gesamtfläche."""
        if self.flaeche_direkt > 0:
            return self.flaeche_direkt
        return self.breite * self.hoehe * max(self.anzahl, 0)

    @property
    def gtot(self) -> float:
        """gtot = g⊥ · FC"""
        return self.g_wert * self.fc

    @property
    def solareintrag(self) -> float:
        """AW,j · gtot,j"""
        return self.flaeche * self.gtot

    @property
    def ist_geneigt(self) -> bool:
        return self.neigung == NEIGUNGEN[0]


# ---------------------------------------------------------------------------
# Ergebnis
# ---------------------------------------------------------------------------

@dataclass
class Ergebnis:
    ok: bool = False
    status: str = ""        # erfuellt | nicht_erfuellt | kein_nachweis | fehler
    ueberschrift: str = ""
    anmerkungen: List[str] = field(default_factory=list)
    warnungen: List[str] = field(default_factory=list)
    fehler: List[str] = field(default_factory=list)
    werte: Dict[str, object] = field(default_factory=dict)
    bauart: str = ""
    herleitung: List[dict] = field(default_factory=list)


def de(wert, nk=2) -> str:
    """Zahl im deutschen Format."""
    if wert is None:
        return "—"
    if isinstance(wert, float) and abs(wert) < 0.5 * 10 ** (-nk):
        wert = 0.0   # kein "-0,0000"
    return f"{wert:,.{nk}f}".replace(",", "#").replace(".", ",").replace("#", ".")


# ---------------------------------------------------------------------------
# Hauptberechnung
# ---------------------------------------------------------------------------

def berechne(projekt: dict, fenster: List[Fenster]) -> Ergebnis:
    erg = Ergebnis()
    w = erg.werte

    # --- Raumgeometrie ---------------------------------------------------
    lh = float(projekt.get("raumhoehe") or 0)
    lt = float(projekt.get("raumtiefe") or 0)
    lb = float(projekt.get("raumbreite") or 0)


    ag_direkt = float(projekt.get("ag_direkt") or 0)
    if ag_direkt > 0:
        ag = ag_direkt
        ag_herkunft = "direkt vorgegeben"
    else:
        ag = lt * lb
        ag_herkunft = "AG = LT · LB"
    w.update({"LH": lh, "LT": lt, "LB": lb, "AG": ag, "AG_herkunft": ag_herkunft})

    if ag_direkt <= 0:
        for name, wert in (("Lichte Raumhöhe LH", lh),
                           ("Lichte Raumtiefe LT", lt),
                           ("Lichte Raumbreite LB", lb)):
            if wert <= 0:
                erg.fehler.append(
                    f"{name} muss größer als Null sein — oder die "
                    f"Nettogrundfläche AG direkt vorgeben.")

    if lh > 0 and lt > 3 * lh:
        erg.warnungen.append(
            f"Die lichte Raumtiefe LT = {de(lt)} m überschreitet den Grenzwert "
            f"LT,max = 3 · LH = {de(3 * lh)} m. Nach DIN 4108-2 ist der "
            f"Referenzraum raumtiefenbegrenzt zu betrachten — Raum in "
            f"Raumbereiche unterteilen oder die Nettogrundfläche auf LT,max "
            f"begrenzen.")

    # --- Fensterflächen --------------------------------------------------
    aw_ges = sum(f.flaeche for f in fenster)
    aw_zweifach = sum(f.flaeche for f in fenster if f.glastyp == "zweifach")
    aw_dreifach = sum(f.flaeche for f in fenster if f.glastyp == "dreifach")
    aw_ssg = sum(f.flaeche for f in fenster
                 if f.glastyp == "Sonnenschutzglas (g ≤ 0,4)")

    frei = [f for f in fenster if not f.verschattet]
    aw_neig = sum(f.flaeche for f in frei if f.ist_geneigt)
    aw_no_nw = sum(f.flaeche for f in frei if not f.ist_geneigt
                   and f.orientierung in ("Nordost", "Nordwest"))
    aw_nord = sum(f.flaeche for f in frei if not f.ist_geneigt
                  and f.orientierung == "Nord")
    aw_sonst = sum(f.flaeche for f in frei if not f.ist_geneigt
                   and f.orientierung not in ("Nord", "Nordost", "Nordwest"))
    aw_verschattet = sum(f.flaeche for f in fenster if f.verschattet)

    summenprodukt = sum(f.solareintrag for f in fenster)

    w.update({"AW_ges": aw_ges, "AW1": aw_zweifach, "AW2": aw_dreifach,
              "AW_ssg": aw_ssg, "AW_neig": aw_neig, "AW_no_nw": aw_no_nw,
              "AW_nord": aw_nord, "AW_sonst": aw_sonst,
              "AW_verschattet": aw_verschattet, "summenprodukt": summenprodukt})

    if not fenster:
        erg.fehler.append("Es ist kein Fenster erfasst.")
    if aw_ges <= 0:
        erg.fehler.append("Die Summe aller Fensterflächen AW,ges muss größer "
                          "als Null sein.")
    if ag <= 0:
        erg.fehler.append("Die Nettogrundfläche AG muss größer als Null sein.")
    for f in fenster:
        if f.g_wert <= 0:
            erg.fehler.append(f"Fenster {f.nr}: g-Wert fehlt oder ist Null.")
        if f.glastyp == "Sonnenschutzglas (g ≤ 0,4)" and f.gtot > 0.4:
            erg.warnungen.append(
                f"Fenster {f.nr}: Als Sonnenschutzglas eingestuft, aber "
                f"gtot = {de(f.gtot, 3)} > 0,40. Einstufung prüfen.")

    # --- Bauart ----------------------------------------------------------
    bauart = ermittle_bauart(
        projekt.get("bauart_methode", "nach DIN 4108-2"),
        projekt.get("waermekapazitaet", ""),
        projekt.get("rohdichte", ""),
        bool(projekt.get("stahlbetondecke")),
        bool(projekt.get("keine_abgehaengte_decke")),
        bool(projekt.get("keine_innendaemmung")),
        bool(projekt.get("keine_hohen_raeume")))
    erg.bauart = bauart

    gebaeudetyp = projekt.get("gebaeudetyp", "Wohngebäude")
    nachtlueftung = projekt.get("nachtlueftung", "ohne")
    region = projekt.get("klimaregion", KLIMAREGIONEN[1])

    if gebaeudetyp not in S1_TABELLE:
        erg.fehler.append("Gebäudekategorie ist nicht gewählt.")
    elif nachtlueftung not in S1_TABELLE[gebaeudetyp]:
        erg.fehler.append("Nachtlüftung ist nicht gewählt.")
    elif region not in KLIMAREGION_INDEX:
        erg.fehler.append("Sommerklimaregion ist nicht gewählt.")

    if erg.fehler:
        erg.status = "fehler"
        erg.ueberschrift = "Nachweis nicht durchführbar"
        return erg

    # --- Kennzahlen ------------------------------------------------------
    ag_r, aw_r = (round(ag, 2), round(aw_ges, 2)) if RUNDUNG_WIE_EXCEL else (ag, aw_ges)

    fwg = aw_r / ag_r * 100.0
    fneig = aw_neig / aw_r
    fnord = (aw_nord + aw_no_nw + aw_verschattet) / aw_r
    if RUNDUNG_WIE_EXCEL:
        fneig, fnord = round(fneig, 3), round(fnord, 3)
    w.update({"fWG": fwg, "fneig": fneig, "fnord": fnord})

    # --- S1 … S6 ---------------------------------------------------------
    region_i = KLIMAREGION_INDEX.get(region, 1)
    s1 = S1_TABELLE[gebaeudetyp][nachtlueftung][bauart][region_i]

    koef = S2_KOEFFIZIENTEN[gebaeudetyp]
    s2 = koef["a"] - koef["b"] * (aw_r / ag_r)
    s3 = S3_FAKTOR * (aw_ssg / aw_r)
    s4 = S4_FAKTOR * fneig
    s5 = S5_FAKTOR * fnord
    s6 = S6_PASSIVE_KUEHLUNG[bauart] if projekt.get("passive_kuehlung") else 0.0

    s_zul = s1 + s2 + s3 + s4 + s5 + s6
    s_vorh = summenprodukt / ag_r

    w.update({"S1": s1, "S2": s2, "S3": s3, "S4": s4, "S5": s5, "S6": s6,
              "S_zul": s_zul, "S_vorh": s_vorh,
              "ausnutzung": (s_vorh / s_zul * 100.0) if s_zul > 0 else None})

    erg.herleitung = [
        {"kurz": "S1", "titel": "Nachtlüftung und Bauart",
         "formel": f"Tabelle 8: {gebaeudetyp}, Nachtlüftung „{nachtlueftung}“, "
                   f"{bauart}, {region}", "wert": s1},
        {"kurz": "S2", "titel": "Grundflächenbezogener Fensterflächenanteil",
         "formel": f"S2 = {de(koef['a'], 3)} − {de(koef['b'], 3)} · "
                   f"({de(aw_r)} m² / {de(ag_r)} m²)", "wert": s2},
        {"kurz": "S3", "titel": "Sonnenschutzglas",
         "formel": f"S3 = 0,030 · ({de(aw_ssg)} m² / {de(aw_r)} m²)", "wert": s3},
        {"kurz": "S4", "titel": "Fensterneigung",
         "formel": f"S4 = −0,035 · fneig = −0,035 · {de(fneig, 3)}", "wert": s4},
        {"kurz": "S5", "titel": "Orientierung",
         "formel": f"S5 = 0,100 · fnord = 0,100 · {de(fnord, 3)}", "wert": s5},
        {"kurz": "S6", "titel": "Einsatz passiver Kühlung",
         "formel": (f"Tabelle 8, {bauart}" if projekt.get("passive_kuehlung")
                    else "keine passive Kühlung angesetzt"), "wert": s6},
    ]

    # --- Tabelle 6: Ist ein Nachweis überhaupt erforderlich? -------------
    if aw_neig > 0:
        fwg_zul, fwg_fall = (FWG_ZULAESSIG["geneigt"],
                             "geneigte Fensterflächen 0° bis 60°, alle Orientierungen")
    elif (aw_sonst + aw_no_nw) > 0:
        fwg_zul, fwg_fall = (FWG_ZULAESSIG["sonst"],
                             "Nordwest über Süd bis Nordost, Neigung > 60°")
    elif aw_nord > 0:
        fwg_zul, fwg_fall = (FWG_ZULAESSIG["nord"],
                             "alle anderen Nordorientierungen, Neigung > 60°")
    else:
        fwg_zul, fwg_fall = (FWG_ZULAESSIG["sonst"],
                             "keine unverschatteten Fensterflächen erfasst")
        erg.warnungen.append("Es sind ausschließlich dauerhaft verschattete "
                             "Fensterflächen erfasst — Neigung und Orientierung prüfen.")
    w.update({"fWG_zul": fwg_zul, "fWG_fall": fwg_fall})

    # --- Sonderfälle nach 8.2 -------------------------------------------
    if projekt.get("aktive_kuehlung"):
        erg.anmerkungen.append(
            "Im Gebäude ist eine Anlage zur Kühlung vorhanden. Nach DIN 4108-2 "
            "darf eine aktive Kühlung im Verfahren der Sonneneintragskennwerte "
            "nicht angerechnet werden — nur passive Kühlung geht über S6 ein. "
            "Der Nachweis wurde daher ohne Berücksichtigung der Kühlanlage "
            "geführt. Für Gebäude mit Anlagen zur Kühlung gilt zusätzlich "
            "GEG § 14 Absatz 4, sofern der Nachweis nach Abschnitt 8.4 "
            "(Simulation) geführt wird.")
    if projekt.get("passive_kuehlung") and projekt.get("aktive_kuehlung"):
        erg.warnungen.append(
            "Es sind gleichzeitig passive und aktive Kühlung angegeben. S6 darf "
            "nur für passive Kühlung angesetzt werden (z. B. Erdreichwärme-"
            "übertrager, thermisch aktivierte Bauteile ohne Kältemaschine).")

    if projekt.get("glasvorbau_nur"):
        erg.anmerkungen.append(
            "Raum mit Belüftung nur über den unbeheizten Glasvorbau: Der Nachweis "
            "gilt nach DIN 4108-2:2013-02, Abschnitt 8.2.3 I. a) als erfüllt.")
    if projekt.get("glasvorbau_nicht_nur"):
        erg.anmerkungen.append(
            "Raum mit Belüftung nicht oder nicht nur über den unbeheizten "
            "Glasvorbau: Der Nachweis ist nach DIN 4108-2:2013-02, Abschnitt "
            "8.2.3 II. a) mit diesem Verfahren zu führen.")

    if projekt.get("verzicht_822b"):
        erg.status, erg.ok = "kein_nachweis", True
        erg.ueberschrift = "Kein Nachweis erforderlich"
        erg.anmerkungen.insert(0,
            "Auf einen Nachweis kann verzichtet werden (DIN 4108-2:2013-02, "
            "Abschnitt 8.2.2 b): Bei Wohngebäuden sowie bei Gebäudeteilen zur "
            "Wohnnutzung, bei denen der kritische Raum einen grundflächen-"
            "bezogenen Fensterflächenanteil von 35 % nicht überschreitet und "
            "dessen Fenster in Ost-, Süd- oder Westorientierung (auch die "
            "eines Glasvorbaus) mit außenliegenden Sonnenschutzvorrichtungen "
            "mit einem Abminderungsfaktor FC ≤ 0,30 bei Glas mit g > 0,40 "
            "bzw. FC ≤ 0,35 bei Glas mit g ≤ 0,40 ausgestattet sind, kann auf "
            "einen Nachweis verzichtet werden. Ein Glasvorbau wird nicht als "
            "kritischer Raum herangezogen. Die Berechnung wurde dennoch "
            "vollständig geführt und ist nachfolgend dokumentiert.")

        # Plausibilitätsprüfung der Voraussetzungen — informativ, blockiert
        # den Verzicht nicht (die Einstufung obliegt dem Ersteller).
        if fwg > 35.0:
            erg.warnungen.append(
                f"Voraussetzung für Abschnitt 8.2.2 b) fraglich: Der "
                f"vorhandene Fensterflächenanteil fWG = {de(fwg)} % "
                f"überschreitet die dort geforderte Grenze von 35 %.")
        unzulaessig = [
            f.nr for f in fenster
            if f.orientierung not in ("Ost", "Süd", "West")
            or f.sonnenschutzart == "ohne Sonnenschutzvorrichtung"
            or not f.sonnenschutzart.startswith("Außenliegend")
            or (f.g_wert > 0.4 and f.fc > 0.30)
            or (f.g_wert <= 0.4 and f.fc > 0.35)]
        if unzulaessig:
            erg.warnungen.append(
                "Voraussetzung für Abschnitt 8.2.2 b) fraglich: Fenster Nr. "
                + ", ".join(str(n) for n in unzulaessig) + " erfüllen nicht "
                "Orientierung Ost/Süd/West mit außenliegendem Sonnenschutz "
                "und FC ≤ 0,30 (g > 0,40) bzw. FC ≤ 0,35 (g ≤ 0,40).")
        return erg

    if fwg < fwg_zul:
        erg.status, erg.ok = "kein_nachweis", True
        erg.ueberschrift = "Kein Nachweis erforderlich"
        erg.anmerkungen.insert(0,
            f"Auf einen Nachweis des sommerlichen Wärmeschutzes kann verzichtet "
            f"werden, da der vorhandene grundflächenbezogene Fensterflächenanteil "
            f"fWG = {de(fwg)} % unterhalb des zulässigen Wertes von {de(fwg_zul)} % "
            f"liegt (DIN 4108-2:2013-02, Tabelle 6; maßgebend: {fwg_fall}).")
        erg.anmerkungen.append(
            f"Der Vollständigkeit halber wurde der Nachweis dennoch geführt: "
            f"S,vorh = {de(s_vorh, 4)} gegenüber S,zul = {de(s_zul, 4)}.")
        return erg

    erg.anmerkungen.append(
        f"Ein Nachweis ist erforderlich, da der vorhandene grundflächenbezogene "
        f"Fensterflächenanteil fWG = {de(fwg)} % den zulässigen Wert von "
        f"{de(fwg_zul)} % erreicht bzw. überschreitet (DIN 4108-2:2013-02, "
        f"Tabelle 6; maßgebend: {fwg_fall}).")

    # --- Nachweis --------------------------------------------------------
    if round(s_vorh, 4) > round(s_zul, 4):
        erg.status, erg.ok = "nicht_erfuellt", False
        erg.ueberschrift = "Anforderung nicht erfüllt"
        erg.anmerkungen.append(
            f"Anforderung nicht erfüllt: Der vorhandene Sonneneintragskennwert "
            f"S,vorh = {de(s_vorh, 4)} übersteigt den zulässigen "
            f"Sonneneintragskennwert S,zul = {de(s_zul, 4)}.")
    else:
        erg.status, erg.ok = "erfuellt", True
        erg.ueberschrift = "Anforderung erfüllt"
        erg.anmerkungen.append(
            f"Anforderung erfüllt: Der vorhandene Sonneneintragskennwert "
            f"S,vorh = {de(s_vorh, 4)} übersteigt den zulässigen "
            f"Sonneneintragskennwert S,zul = {de(s_zul, 4)} nicht.")

    if s_zul <= 0:
        erg.warnungen.append(
            "Der zulässige Sonneneintragskennwert S,zul ist kleiner oder gleich "
            "Null. Das vereinfachte Verfahren liefert hier keine belastbare "
            "Aussage — der Nachweis ist über eine thermische Gebäudesimulation "
            "nach DIN 4108-2:2013-02, Abschnitt 8.4 zu führen.")

    return erg
