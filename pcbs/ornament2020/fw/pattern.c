#include "pattern.h"
#include <stddef.h>

// TODO: investigate switching to PROGMEM

const pattern_frame_t test_pattern_frames[] = {
    {
      .duration = 100,
      .led_states = {OFF, OFF, OFF, OFF, OFF, OFF},
    },
    {
      .duration = 100,
      .led_states = {ON, OFF, OFF, OFF, OFF, OFF},
    },
    {
      .duration = 100,
      .led_states = {OFF, ON, OFF, OFF, OFF, OFF},
    },
    {
      .duration = 100,
      .led_states = {OFF, OFF, ON, OFF, OFF, OFF},
    },
    {
      .duration = 100,
      .led_states = {OFF, OFF, OFF, ON, OFF, OFF},
    },
    {
      .duration = 100,
      .led_states = {OFF, OFF, OFF, OFF, ON, OFF},
    },
    {
      .duration = 100,
      .led_states = {OFF, OFF, OFF, OFF, OFF, ON},
    },
    {
      .duration = 100,
      .led_states = {OFF, OFF, OFF, OFF, OFF, RAMP_DN},
    },
    {0}
};

const pattern_frame_t *patterns[] = {
  test_pattern_frames,
  NULL,
};

static pattern_t *new_pattern(const pattern_frame_t *frames) {
  static pattern_t master;
  master.frames = frames;
  master.frame_id = 0;
  master.frame_timer = 0;
  return &master;
};

pattern_t *next_pattern() {
  static int pattern_id = 0;
  const pattern_frame_t *p = patterns[++pattern_id];
  if (p == NULL){
    pattern_id = 0;
    p = patterns[0];
  }
  return new_pattern(p);
}
