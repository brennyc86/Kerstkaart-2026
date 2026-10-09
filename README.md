# Kerstkaart 2026 – Rudolf het rendier

Opvolger van de kerstkaarten van 2024 en 2025: een printplaat in de vorm van een rendier (96 × 99 mm) met 49 NeoPixels
(WS2812B-2020), een ATtiny1616 in QFN en een knopje om tussen 7 lichtprogramma's te wisselen.
Op de achterkant staat de kerstboodschap: *Zalig Kerstfeest en een gelukkig 2027*.

| Voorkant | Achterkant |
|---|---|
| ![voor](render_voor.png) | ![achter](render_achter.png) |

## Wat zit er in deze repo

| Pad | Inhoud |
|---|---|
| `kerstkaart_2026_gerber.zip` | Gerbers + boorbestand, direct uploadbaar bij JLCPCB |
| `productie/BOM_kerstkaart_2026.csv`, `productie/CPL_kerstkaart_2026.csv` | Stuklijst met LCSC-nummers en plaatsingsbestand (JLCPCB-assemblage) |
| `kerstkaart2026.kicad_pcb` | KiCad-bord (KiCad 10-formaat, **ongetest**; de Gerbers zijn de leidende bron) |
| `footprints/` | De echte KiCad-bibliotheekfootprints van alle onderdelen |
| `firmware/kerstkaart2026/` | Arduino-sketch (megaTinyCore + tinyNeoPixel) en `leds.h` met LED-posities |
| `gen2.py`, `shape.py`, `ketting.py`, `kunst.py` | Generator: silhouet, LED-volgorde, kunst → Gerbers, BOM, CPL, render, `leds.h` |

## Wijzigingen t.o.v. de eerste versie

* **Echte footprints** uit de officiële KiCad-bibliotheek (WS2812B-2020, VQFN-20, 0603, TS-1187A) met bijbehorende LCSC-onderdelen in BOM/CPL.
* **QFN-ATtiny1616** (ATtiny1616-MNR, VQFN-20 3×3 mm, C507118) met de juiste pinout uit het KiCad-symbool:
  pen 3 GND, 4 VCC, 8 PA7 (knop), 15 PC0 (data), 19 UPDI/PA0, 21 = EP (GND).
* **Configuratiepads op de achterkant** (geen headers): rij `VCC – UPDI – GND` met UPDI in het midden
  (via de **4,7 kΩ**-weerstand R2), plus een aparte pad **`HV`** die **direct** met de UPDI-pen is verbonden (voor hoogspanningsprogrammering).
  `BT+` en `BT-` zijn grote koperpads voor de batterijdraden.
* **Knop** (TS-1187A, pen 8 → GND) om tussen programma's te wisselen; lang indrukken wisselt de helderheid. Keuze blijft bewaard (EEPROM).
* **Beide geweien identiek**: gewei A is een exacte spiegel van gewei B met dezelfde 6 LED's (beide krijgen tip, zijtak en stam), en de firmware gebruikt een spiegelrang (`gewei_rang()`) zodat alle effecten links en rechts gelijk lopen.
* **Kerstboodschap en sneeuwvlokken** als silkscreen (achterkant boodschap, voorkant vlokken en sterren), plus labels bij de pads.

## Kleurkeuze (1 kleur silk)

Een volledig kleuren-silkscreen is een EasyEDA Pro-functie en kan ik hier niet genereren. Het ontwerp is daarom gemaakt voor één silkkleur:

* **PCB: zwart soldeermasker (mat of glans), silk: wit, afwerking ENIG (goud).**
  Zwart laat de LED's het beste oplichten en geeft de witte boodschap en vlokken veel contrast; ENIG maakt de blanke pads (`HV`, `UPDI`, `BT±`, LED-pads) goudkleurig.
* Alternatief: **rood masker + wit silk** (meer kerst, minder contrast).

## Bestellen

1. JLCPCB → PCB + SMT-assemblage, upload `kerstkaart_2026_gerber.zip`, kies zwart masker, wit silk, ENIG, dikte 1,6 mm, 2 lagen.
2. Upload `BOM_kerstkaart_2026.csv` en `CPL_kerstkaart_2026.csv`.
3. **Controleer in de JLC-voorvertoning de rotatie van de LED's, U1 en de knop.** De CPL gebruikt de footprintrotatie uit KiCad; JLC wijkt voor sommige onderdelen 90° of 180° af.
4. Pas indien nodig de ATtiny aan: ATtiny816-M (VQFN-20, zelfde pinout) kan ook, 1616 heeft meer geheugen.

## Nog te controleren

* De Gerbers heb ik gecontroleerd door ze in te lezen met `gerbonara` (alle 8 lagen + boorbestand worden herkend), maar **niet** in KiCad of JLC's viewer; kijk ze daar na.
* Mijn eigen controle (spoor/pad-afstand 0,2 mm, randafstand 0,4 mm, GND en VCC elk één samenhangend vlak) is geen volledige DRC.
* Alle LCSC-nummers komen uit de zoekresultaten (WS2812B-2020 C965555, ATtiny1616-MNR C507118, TS-1187A-B-A-B C318884 bevestigd; de 0603-onderdelen C14663/C23138/C23162 zijn standaardnummers die ik niet afzonderlijk heb geverifieerd).
* Firmware is niet op een echte ATtiny gecompileerd (alleen syntax gecontroleerd).
* Het GND-vlak boven heeft geen thermal reliefs; handsolderen van de LED-GND-pads gaat daardoor iets moeilijker.

## Licentie en bronnen
De footprints in `footprints/` komen uit de KiCad-bibliotheken (CC-BY-SA 4.0 met uitzondering voor het gebruik in ontwerpen). De overige bestanden zijn van Brendan.
