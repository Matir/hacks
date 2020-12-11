#ifndef _PATTERN_H_
#define _PATTERN_H_

#include <stdint.h>

#define NUM_LEDS 6

#define OFF      0
#define ON       1
#define RAMP_UP  2
#define RAMP_DN  3

#define BOT_BTN  0
#define MID_BTN  1
#define TOP_BTN  2
#define NOSE     3
#define RT_EYE   4
#define LEFT_EYE 5

/*
 * Note: duration is in units of ~16.67ms. (16.25 when tested)
 */
typedef struct {
  uint16_t duration;
  uint8_t led_states[NUM_LEDS];
} pattern_frame_t;

typedef struct {
  const pattern_frame_t *frames;
  uint8_t frame_id;
  uint16_t frame_timer;
} pattern_t;

pattern_t *next_pattern();

#endif /* _PATTERN_H_ */
