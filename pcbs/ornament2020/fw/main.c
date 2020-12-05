#include <stdint.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/power.h>
#include <avr/pgmspace.h>
#include "avr_mcu_section.h"

// Settings
#define DESIRED_FRAMERATE 60
#define NUM_LEDS 6
#define PWM_FRAME_MASK PWM_RESOLUTION_STEPS
#define TIMER_PRESCALER 8
#define TIMER_INTERVAL (F_CPU/(DESIRED_FRAMERATE*(PWM_FRAME_MASK+1))/TIMER_PRESCALER)
#if (TIMER_INTERVAL > 255)
# error "Unable to use 8-bit timer!"
#endif

// From gamma.c
extern const uint8_t consts_num_steps;
extern const uint8_t gamma_table[];

// Brightness divisors
const uint8_t MAX_BRIGHTNESS_SCALE[NUM_LEDS] = {0, 0, 0, 0, 0, 0};
// Scaling factors
const uint8_t RAMP_UP_SPEED[NUM_LEDS] =   {0x2F, 0x4F, 0x3F, 0x1F, 0x04, 0x12};
const uint8_t RAMP_DOWN_SPEED[NUM_LEDS] = {0x20, 0x40, 0x10, 0x20, 0x30, 0x40};
// INTERVAL is 2x as long as ramp up/down time
const uint8_t OFF_SPEED[NUM_LEDS] =       {0x40, 0x00, 0x20, 0x00, 0x40, 0x00};

// Current brightness
uint8_t brightness[NUM_LEDS]     = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
// Current frame
uint16_t px_frame_no[NUM_LEDS]   = {0};

// Limit to 3 active LEDs at any given time
uint8_t active_leds = 0b010101;

// Update frame
volatile uint8_t update_frame = 1;
#ifdef DEBUG
volatile uint32_t frame_id = 0;
volatile uint8_t running_brightness = 0;
#endif

// Declarations
void setup(void);
void update_loop_step();
void pwm_frame_update(uint8_t frame_no);
uint8_t calc_brightness(uint8_t which);
void update_active_leds(uint8_t off);
static void update_out(uint8_t leds);

// Handle the Timer compare
ISR(TIMER0_COMPA_vect) {
  update_frame = 1;
}

void setup(void) {
  // Disable interrupts while setting up
  cli();

  // Low 4 pins are output
  DDRA = 0x0F;
  DDRB = 0x02;

  // Enable timer for next frame
  OCR0A = TIMER_INTERVAL;   // Interval
  TIMSK0 = 0x01;            // Interrupt on compare
  TCCR0A = 0x02;            // CTC Mode
#if TIMER_PRESCALER == 1
  TCCR0B = 1<<CS00;         // No prescaler
#elif TIMER_PRESCALER == 8
  TCCR0B = 1<<CS01;         // Prescale by 8
#else
# error "Unknown prescaler."
#endif

  // Reduce power consumption slightly
  PRR |= (1<<PRTIM1) | (1<<PRUSI);

  // Re-enable interrupts
  sei();
}

__attribute__((noreturn))
void main(void) {
  setup();
  while (1) {
    // TODO: sleep?
    if (update_frame) {
      cli();
      update_loop_step();
#ifdef DEBUG
      frame_id++;
#endif
      update_frame = 0;
      sei();
    }
  }
}

__attribute__((optimize("unroll-loops")))
void update_loop_step() {
  static uint8_t pwm_frame = 0;
  pwm_frame &= PWM_FRAME_MASK;
  if (!pwm_frame) {
    for(uint8_t i=0; i<NUM_LEDS; i++) {
      if (active_leds & (1 << i)) {
        if (calc_brightness(i)) {
          update_active_leds(i);
        }
      }
    }
  }
  pwm_frame_update(pwm_frame++);
}

uint8_t calc_brightness(uint8_t which) {
  // Returns 1 on overflow (cycle around), 0 otherwise
#ifdef DEBUG
  running_brightness = 1;
#endif
  uint8_t brightness_tmp = 0;
  uint16_t cur_frame = px_frame_no[which];
  uint16_t init_frame = cur_frame;

  // Ramp up phase
  if (cur_frame <= 0x3FFF) {
    // Scales to [0-255]
    brightness_tmp = (uint8_t)(cur_frame >> 6);
    cur_frame += RAMP_UP_SPEED[which];
  } else if (cur_frame <= 0x7FFF) {
    if (!RAMP_DOWN_SPEED[which]) {
      cur_frame = 0x8000;
    } else {
      brightness_tmp = 255 - (uint8_t)(cur_frame >> 6);
      cur_frame += RAMP_DOWN_SPEED[which];
    }
  } else {
    // Waiting INTERVAL
    if (!OFF_SPEED[which]) {
      cur_frame = 0;
    } else {
      cur_frame += ((uint16_t)OFF_SPEED[which]) << 1;
    }
  }
  if (MAX_BRIGHTNESS_SCALE[which])
    brightness_tmp >>= MAX_BRIGHTNESS_SCALE[which];
  brightness[which] = brightness_tmp;
  px_frame_no[which] = cur_frame;
#ifdef DEBUG
  running_brightness = 0;
#endif
  return (cur_frame < init_frame) ? 1 : 0;
}

void update_active_leds(uint8_t off) {
  static uint8_t next = 1;
  while(active_leds & (1 << next)) {
    next = (next == 5) ? 0 : next + 1;
  }
  px_frame_no[next] = 0;
  active_leds |= (1 << next);
  active_leds &= ~(1 << off);
}

__attribute__((optimize("unroll-loops")))
void pwm_frame_update(uint8_t frame_no) {
  uint8_t out = 0;
  uint8_t bright;
  for(int8_t i=0; i<NUM_LEDS; i++) {
    if(!(active_leds & (1 << i)))
      continue;
    // Convert via gamma table
    bright = pgm_read_byte(&(gamma_table[brightness[i]]));
    if(bright > frame_no)
      out |= (1<<i);
    // Stagger the pwm cycles
    frame_no = (frame_no + PWM_FRAME_MASK/3) & PWM_FRAME_MASK;
  }
  update_out(out);
}

// LEDS are on PA0-3 and PB0-1
static void update_out(uint8_t leds) {
#define PORTA_MASK 0x0F
#define PORTB_MASK 0x2
  PORTA &= (0xFF ^ PORTA_MASK);
  PORTA |= (leds & PORTA_MASK);
  leds = leds >> 4;  // 4 bits used
  PORTB &= (0xFF ^ PORTB_MASK);
  PORTB |= (leds & PORTB_MASK);
}

// simavr stuff
AVR_MCU_VCD_FILE("gtkwave_trace.vcd", 300000);
const struct avr_mmcu_vcd_trace_t _mytrace[]  _MMCU_ = {
  {AVR_MCU_VCD_SYMBOL("update_frame"), .what = (uint8_t *)(&update_frame)},
#ifdef DEBUG
  {AVR_MCU_VCD_SYMBOL("frame_id"), .what = &frame_id},
  {AVR_MCU_VCD_SYMBOL("running_bright"), .what = &running_brightness},
#endif
};
