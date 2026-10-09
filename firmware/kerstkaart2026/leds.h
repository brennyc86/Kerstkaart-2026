// Automatisch gegenereerd door gen2.py - niet handmatig aanpassen
#pragma once
#include <avr/pgmspace.h>

#define N_LED 49

// positie in 0,5 mm, oorsprong linksonder van de kaart
const uint8_t LED_X[N_LED] PROGMEM = {81, 90, 90, 97, 98, 112, 113, 120, 119, 117, 127, 138, 155, 171, 183, 173, 162, 158, 166, 182, 175, 168, 162, 155, 139, 132, 126, 120, 112, 128, 127, 113, 99, 84, 67, 50, 36, 13, 24, 22, 22, 29, 29, 37, 46, 45, 52, 53, 59};
const uint8_t LED_Y[N_LED] PROGMEM = {55, 42, 14, 14, 42, 42, 14, 14, 42, 74, 90, 103, 115, 111, 113, 122, 126, 133, 155, 161, 171, 186, 163, 149, 149, 163, 186, 171, 161, 155, 116, 101, 90, 95, 95, 93, 90, 92, 72, 42, 14, 14, 42, 61, 42, 14, 14, 42, 54};

#define GEWEI_B_VAN 18
#define GEWEI_B_TOT 23
#define GEWEI_A_VAN 24
#define GEWEI_A_TOT 29
#define NEUS 14
#define OOG 17
#define KOP_VAN 12
#define KOP_TOT 16
#define STAART 37

// Beide geweien hebben evenveel LED's; A loopt in de keten omgekeerd t.o.v. B.
// gewei_rang(i) geeft de spiegel-positie binnen het gewei (0..GEWEI_N-1) zodat beide geweien identiek reageren.
#define GEWEI_N (GEWEI_B_TOT - GEWEI_B_VAN + 1)
static inline uint8_t gewei_rang(uint8_t i) { return i <= GEWEI_B_TOT ? (uint8_t)(i - GEWEI_B_VAN) : (uint8_t)(GEWEI_N - 1 - (i - GEWEI_A_VAN)); }
