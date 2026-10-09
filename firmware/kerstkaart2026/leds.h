// Automatisch gegenereerd door gen2.py - niet handmatig aanpassen
#pragma once
#include <avr/pgmspace.h>

#define N_LED 42

// positie in 0,5 mm, oorsprong linksonder van de kaart
const uint8_t LED_X[N_LED] PROGMEM = {161, 166, 182, 175, 162, 155, 139, 132, 120, 112, 128, 127, 113, 99, 84, 67, 50, 36, 22, 22, 29, 29, 37, 46, 45, 53, 53, 59, 72, 90, 90, 97, 98, 112, 112, 120, 119, 117, 127, 138, 162, 186};
const uint8_t LED_Y[N_LED] PROGMEM = {141, 154, 161, 173, 163, 149, 149, 163, 173, 161, 154, 116, 101, 90, 95, 95, 93, 90, 42, 14, 14, 42, 61, 42, 14, 14, 42, 54, 54, 42, 14, 14, 42, 42, 14, 14, 42, 74, 90, 103, 108, 110};

#define GEWEI_B_VAN 1
#define GEWEI_B_TOT 5
#define GEWEI_A_VAN 6
#define GEWEI_A_TOT 10
#define NEUS 41
#define KOP 0
#define KIN 40

// Beide geweien hebben evenveel LED's; A loopt in de keten omgekeerd t.o.v. B.
// gewei_rang(i) geeft de spiegel-positie binnen het gewei (0..GEWEI_N-1) zodat beide geweien identiek reageren.
#define GEWEI_N (GEWEI_B_TOT - GEWEI_B_VAN + 1)
static inline uint8_t gewei_rang(uint8_t i) { return i <= GEWEI_B_TOT ? (uint8_t)(i - GEWEI_B_VAN) : (uint8_t)(GEWEI_N - 1 - (i - GEWEI_A_VAN)); }
