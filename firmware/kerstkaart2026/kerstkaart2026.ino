// Kerstkaart 2026 - Rudolf het rendier
// ATtiny1616 @ 16 MHz (megaTinyCore), 49x WS2812B-2020 aan PC0, knop op PA7 (naar GND)
// Korte druk = volgend programma, lang (>0,8 s) = helderheid wisselen.
#include <tinyNeoPixel.h>
#include <EEPROM.h>
#include "leds.h"

#define PIN_LEDS  PIN_PC0
#define PIN_KNOP  PIN_PA7
#define PIN_BUZ   PIN_PB0
#define N_MODUS   7

tinyNeoPixel pix = tinyNeoPixel(N_LED, PIN_LEDS, NEO_GRB + NEO_KHZ800);

const uint8_t HELDER[3] = {40, 100, 220};
uint8_t helderheid = 0;
uint8_t modus = 0;
unsigned long t_vorig = 0;

uint8_t lx(uint8_t i) { return pgm_read_byte(&LED_X[i]); }
uint8_t ly(uint8_t i) { return pgm_read_byte(&LED_Y[i]); }

// kleur met factor f (0..255)
uint32_t kleur(uint8_t r, uint8_t g, uint8_t b, uint8_t f = 255) {
  return pix.Color((uint16_t)r * f / 255, (uint16_t)g * f / 255, (uint16_t)b * f / 255);
}
// zachte golf 0..255
uint8_t golf(uint16_t t, uint16_t periode) {
  uint16_t x = (t % periode) * 512UL / periode;
  return x < 256 ? x : 511 - x;
}
void wis() { pix.clear(); }

void toon() {
  pix.setBrightness(HELDER[helderheid]);
  pix.show();
}

// 0: Rudolf - gloeiende neus, twinkelend goud, knipperend oog
void m_rudolf(unsigned long t) {
  for (uint8_t i = 0; i < N_LED; i++) {
    uint8_t f = 40 + golf(t / 8 + i * 37, 1500) / 4;
    pix.setPixelColor(i, kleur(255, 150, 20, f / 2));
  }
  for (uint8_t i = GEWEI_B_VAN; i <= GEWEI_B_TOT; i++) pix.setPixelColor(i, kleur(255, 240, 200, 60 + golf(t / 6 + i * 50, 2000) / 3));
  for (uint8_t i = GEWEI_A_VAN; i <= GEWEI_A_TOT; i++) pix.setPixelColor(i, kleur(255, 240, 200, 60 + golf(t / 6 + i * 50, 2000) / 3));
  pix.setPixelColor(NEUS, kleur(255, 0, 0, 60 + golf(t / 3, 1600) * 3 / 4));
  bool knip = (t % 4000) > 3850;
  pix.setPixelColor(OOG, knip ? 0 : kleur(255, 255, 255, 140));
}
// 1: Vliegende komeet langs de hele keten
void m_komeet(unsigned long t) {
  wis();
  int kop = (t / 55) % (N_LED + 10);
  for (uint8_t s = 0; s < 10; s++) {
    int i = kop - s;
    if (i >= 0 && i < N_LED) pix.setPixelColor(i, kleur(200, 220, 255, 255 >> (s / 2 + (s > 0))));
  }
  pix.setPixelColor(NEUS, kleur(255, 0, 0, 200));
}
// 2: Sneeuwval
void m_sneeuw(unsigned long t) {
  static uint8_t vlok[N_LED];
  static unsigned long last = 0;
  if (t - last > 90) {
    last = t;
    for (uint8_t i = 0; i < N_LED; i++) vlok[i] = vlok[i] > 24 ? vlok[i] - 24 : 0;
    vlok[random(N_LED)] = 255; vlok[random(N_LED)] = 180;
  }
  for (uint8_t i = 0; i < N_LED; i++) { uint8_t w = vlok[i] > 60 ? vlok[i] / 2 : 0; uint8_t b = 25 + vlok[i] / 4; pix.setPixelColor(i, pix.Color(w, w + b / 2, min(255, w + b + 40))); }
  pix.setPixelColor(NEUS, kleur(255, 0, 0, 80));
}
// 3: Noorderlicht - kleurgolf over de x-positie
void m_noorder(unsigned long t) {
  for (uint8_t i = 0; i < N_LED; i++) {
    uint8_t a = golf(t / 10 + lx(i) * 5 + ly(i) * 2, 2400);
    uint8_t b = golf(t / 14 + lx(i) * 3, 3200);
    pix.setPixelColor(i, kleur(a / 3, 40 + a / 2, 255 - b / 2, 140));
  }
  pix.setPixelColor(NEUS, kleur(255, 0, 0, 90 + golf(t / 3, 1600) / 2));
}
// 4: Gewei-kerstlichtjes loopverlicht, lijf warm
void m_gewei(unsigned long t) {
  const uint8_t kl[4][3] = {{255, 0, 0}, {0, 255, 0}, {255, 180, 0}, {0, 80, 255}};
  for (uint8_t i = 0; i < N_LED; i++) pix.setPixelColor(i, kleur(255, 120, 10, 35));
  uint8_t stap = (t / 350) % 4;
  for (uint8_t i = GEWEI_B_VAN; i <= GEWEI_A_TOT; i++) {
    const uint8_t *c = kl[(i + stap) % 4];
    pix.setPixelColor(i, kleur(c[0], c[1], c[2], 220));
  }
  pix.setPixelColor(NEUS, kleur(255, 0, 0, 255));
}
// 5: Ademend warm-wit (rustig)
void m_adem(unsigned long t) {
  uint8_t f = 20 + golf(t / 6, 4000) * 3 / 4;
  for (uint8_t i = 0; i < N_LED; i++) pix.setPixelColor(i, kleur(255, 170, 70, f));
  pix.setPixelColor(NEUS, kleur(255, 0, 0, 40 + f));
}
// 6: Neus-alarm: neus pulseert, kop volgt, rest dim - Rudolf leidt de slee
void m_neus(unsigned long t) {
  wis();
  uint8_t f = golf(t / 2, 1200);
  for (uint8_t i = KOP_VAN; i <= KOP_TOT; i++) pix.setPixelColor(i, kleur(255, 40, 0, f / 6));
  pix.setPixelColor(NEUS, kleur(255, 0, 0, 30 + f * 7 / 8));
  pix.setPixelColor(OOG, kleur(255, 255, 255, 100));
  for (uint8_t i = GEWEI_B_VAN; i <= GEWEI_A_TOT; i++) if (random(40) == 0) pix.setPixelColor(i, kleur(255, 255, 255, 200));
}

void knop_wacht_los() { while (digitalRead(PIN_KNOP) == LOW) delay(10); }

void setup() {
  pix.begin();
  pinMode(PIN_KNOP, INPUT_PULLUP);
  pinMode(PIN_BUZ, OUTPUT);
  modus = EEPROM.read(0) % N_MODUS;
  helderheid = EEPROM.read(1) % 3;
  randomSeed(analogRead(PIN_PA4));
}

void loop() {
  if (digitalRead(PIN_KNOP) == LOW) {
    unsigned long start = millis();
    while (digitalRead(PIN_KNOP) == LOW && millis() - start < 800) delay(10);
    if (digitalRead(PIN_KNOP) == LOW) {          // lang
      helderheid = (helderheid + 1) % 3;
      EEPROM.update(1, helderheid);
    } else {                                      // kort
      modus = (modus + 1) % N_MODUS;
      EEPROM.update(0, modus);
    }
    knop_wacht_los(); delay(30);
  }
  unsigned long t = millis();
  if (t - t_vorig < 20) return;                   // ~50 beelden/s
  t_vorig = t;
  switch (modus) {
    case 0: m_rudolf(t); break;
    case 1: m_komeet(t); break;
    case 2: m_sneeuw(t); break;
    case 3: m_noorder(t); break;
    case 4: m_gewei(t); break;
    case 5: m_adem(t); break;
    default: m_neus(t); break;
  }
  toon();
}
