# Kerstkaart 2026 – Rudolf het rendier

Opvolger van de kerstkaarten van 2024 en 2025: een printplaat in de vorm van een rendier (96 × 99 mm) met 49 NeoPixels
(WS2812B-2020), een ATtiny1616 en een knop. Rudolf heeft een rode neus (LED 16), een oog (LED 19) en een gewei van 11 LED's.

| Bestand | Inhoud |
|---|---|
| `kerstkaart2026.kicad_pcb` | KiCad 7+ printplaat: omtrek, 49 LED's, MCU, routering, GND-vlak (boven) en VCC-vlak (onder) |
| `pcb_render.png` | Gerenderd overzicht (nummering = datavolgorde) |
| `firmware/kerstkaart2026/` | Arduino-sketch (megaTinyCore, tinyNeoPixel) + `leds.h` met LED-posities |
| `gen.py`, `shape.py`, `ketting.py` | Generator: wijzig silhouet of LED-volgorde en draai `python3 gen.py` opnieuw |

## Ontwerp
* Boven: LED's, datasporen (0,25 mm), GND-vlak. Onder: VCC-vlak. Elke LED heeft een via naar VCC.
* Batterij: 3×AAA (4,5 V) op `BT+/BT-`; `SW`-pads voor een schuifschakelaar (zonder schakelaar: draadbrug).
* Programmeren: 3-pins UPDI-header (UPDI/VCC/GND) met 470 Ω in serie, zoals in 2025.
* Pinnen: data PC0 (via 330 Ω), knop PA7, buzzerpads PB0 (nog ongebruikt in de code).
* Programma's (korte druk = volgend, lange druk = helderheid): Rudolf, komeet, sneeuwval, noorderlicht, gewei-lichtjes, ademend, neus-alarm.

## Nog controleren vóór bestellen
1. **Footprints**: LED-pinout WS2812B-2020 (1 DO, 2 GND, 3 DI, 4 VDD) en pad-afmetingen komen uit een zoekresultaat, niet uit jouw bibliotheek; de SOIC-20, 0603's en tactschakelaar zijn eenvoudige plaatshouders. Vergelijk met de footprints van de gekozen JLC-onderdelen.
2. **ATtiny1616 pinout (SOIC-20)**: VCC = pin 1, GND = pin 20, UPDI = pin 16, PC0 = pin 12, PA7 = pin 5, PB0 = pin 11 – controleer in de datasheet.
3. Open in KiCad, vul de vlakken (B) en draai de DRC; mijn eigen controle (afstand 0,2 mm, randafstand 0,4 mm) vond geen fouten, maar is geen KiCad-DRC. Er is niet gecompileerd voor de ATtiny (alleen syntaxis gecontroleerd).
4. Aan de top-GND zitten geen stitching-vias; het VCC-vlak onder is één stuk, GND-boven kan eilandjes krijgen (generator controleerde dat alle GND-pads aan het hoofdvlak hangen).
