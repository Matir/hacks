#include "pattern.h"
#include "consts.h"
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

const pattern_frame_t ramps[] = {
  {
    .duration = 100,
    .led_states = {RAMP_UP, OFF, OFF, OFF, OFF, RAMP_DN},
  },
  {
    .duration = 100,
    .led_states = {RAMP_DN, RAMP_UP, OFF, OFF, OFF, OFF},
  },
  {
    .duration = 100,
    .led_states = {OFF, RAMP_DN, RAMP_UP, OFF, OFF, OFF},
  },
  {
    .duration = 100,
    .led_states = {OFF, OFF, RAMP_DN, RAMP_UP, OFF, OFF},
  },
  {
    .duration = 100,
    .led_states = {OFF, OFF, OFF, RAMP_DN, RAMP_UP, OFF},
  },
  {
    .duration = 100,
    .led_states = {OFF, OFF, OFF, OFF, RAMP_DN, RAMP_UP},
  },
  {0},
};

const pattern_frame_t ornament[] = {
  // Go through body LEDs
  {
    .duration = RAMP_TIME,
    .led_states = {RAMP_UP, OFF, OFF, OFF, OFF, OFF},
  },
  {
    .duration = RAMP_TIME,
    .led_states = {ON, RAMP_UP, OFF, OFF, OFF, OFF},
  },
  {
    .duration = RAMP_TIME,
    .led_states = {ON, ON, RAMP_UP, OFF, OFF, OFF},
  },
  {
    .duration = 1800,
    .led_states = {ON, ON, ON, OFF, OFF, OFF},
  },
  {
    .duration = RAMP_TIME,
    .led_states = {RAMP_DN, ON, ON, OFF, OFF, OFF},
  },
  {
    .duration = RAMP_TIME,
    .led_states = {OFF, RAMP_DN, ON, OFF, OFF, OFF},
  },
  {
    .duration = RAMP_TIME,
    .led_states = {OFF, OFF, RAMP_DN, OFF, OFF, OFF},
  },
  // Now head
  {
    .duration = RAMP_TIME,
    .led_states = {OFF, OFF, OFF, RAMP_UP, OFF, OFF},
  },
  {
    .duration = RAMP_TIME,
    .led_states = {OFF, OFF, OFF, ON, RAMP_UP, RAMP_UP},
  },
  {
    .duration = 1800,
    .led_states = {OFF, OFF, OFF, ON, ON, ON},
  },
  // Wink
  {
    .duration = 40,
    .led_states = {OFF, OFF, OFF, ON, ON, OFF},
  },
  {
    .duration = 40,
    .led_states = {OFF, OFF, OFF, ON, ON, ON},
  },
  {
    .duration = RAMP_TIME,
    .led_states = {OFF, OFF, OFF, RAMP_DN, ON, ON},
  },
  {
    .duration = RAMP_TIME,
    .led_states = {OFF, OFF, OFF, OFF, RAMP_DN, RAMP_DN},
  },
  {
    .duration = 600,
    .led_states = {OFF},
  },
  {0},
};

const pattern_frame_t all_on[] = {
  {
    .duration = 100,
    .led_states = {ON, ON, ON, ON, ON, ON},
  },
  {0}
};

const pattern_frame_t *patterns[] = {
  test_pattern_frames,
  ramps,
  ornament,
  all_on,
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
