#include <stddef.h>
#include <stdint.h>
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/power.h>
#include <avr/pgmspace.h>
#include <avr/sleep.h>
#include <util/delay.h>
#include "avr_mcu_section.h"
#include "pattern.h"
#include "consts.h"

#define XSTR(x) STR(x)
#define STR(x) #x

// Settings
#ifndef PWM_RESOLUTION_STEPS
# define PWM_RESOLUTION_STEPS 0x80
#endif
#ifndef AUTO_OFF_TIME_SECS
# define AUTO_OFF_TIME_SECS 3*60*60L
#endif
#define uint24_t __uint24
#define TOUCH_ENABLED
#ifndef MAX_BRIGHTNESS
# define MAX_BRIGHTNESS PWM_RESOLUTION_STEPS
#endif
#define DESIRED_FRAMERATE 60
#define PWM_FRAME_MASK (PWM_RESOLUTION_STEPS-1)
#define TIMER_PRESCALER 8
#define TIMER_INTERVAL (F_CPU/(DESIRED_FRAMERATE*(PWM_FRAME_MASK+1))/TIMER_PRESCALER)
#if (TIMER_INTERVAL > 255)
# error "Unable to use 8-bit timer!"
#endif
#pragma message "TIMER_INTERVAL is " XSTR(TIMER_INTERVAL) "!"

// From gamma.c
extern const uint8_t consts_num_steps;
extern const uint8_t gamma_table[];

pattern_t * volatile current_pattern = NULL;

// Update frame
volatile uint8_t update_frame = 1;
volatile uint24_t frame_id = 0;
#ifdef DEBUG
volatile uint8_t running_brightness = 0;
#endif

// Declarations
void setup(void);
void update_loop_step();
void pwm_frame_update(uint8_t frame_no, uint8_t *brightness);
void update_active_leds(uint8_t off);
static void update_out(uint8_t leds);
static void idle();
static void sleep_until_touch();

// Handle the Timer compare
ISR(TIM0_COMPA_vect) {
  update_frame = 1;
}

// Ignore the overflow we should never see
ISR(TIM0_OVF_vect){}

// Handle touch sensor
#ifdef TOUCH_ENABLED
ISR(EXT_INT0_vect){
  update_out(0);
  // Verify it's low for a bit
  for (volatile int16_t i=0xFEEE;i;i--) {
    if ((PINB & (1 << PINB2)) == 0) {
      return;
    }
    asm("");
  }
  // Restart timer if stopped
  PRR &= ~(1<<PRTIM0);
  if (current_pattern) {
    current_pattern = NULL;
  } else {
    current_pattern = next_pattern();
  }
  frame_id = 0;
}
#endif

static void idle() {
  sleep_mode();
}

static void sleep_until_touch() {
  current_pattern = NULL;
  update_out(0);
  // Disable timer
  PRR |= (1<<PRTIM0);
  sei();
  sleep_mode();
}

void setup(void) {
  // Disable interrupts while setting up
  cli();

  // Do clock setup
#if F_CPU == 4000000
  // Must be done in 2 steps per datasheet!
  CLKPR = (1<<CLKPCE);
  CLKPR = (1<<CLKPS0);
#endif

  // Low 4 pins are output
  DDRA = 0x0F;
  // Low 2 pins here are output
  DDRB = 0x03;

  // Zero values
  PORTA = 0;
  PORTB = 0;

  // Enable timer for next frame
  OCR0A = TIMER_INTERVAL;   // Interval
  TIMSK0 = 0x02;            // Interrupt on compare
  TCCR0A = 0x02;            // CTC Mode
#if TIMER_PRESCALER == 1
  TCCR0B = 1<<CS00;         // No prescaler
#elif TIMER_PRESCALER == 8
  TCCR0B = 1<<CS01;         // Prescale by 8
#else
# error "Unknown prescaler."
#endif

  // Reduce power consumption slightly
  PRR |= (1<<PRTIM1) | (1<<PRUSI) | (1<<PRADC);

  // Enable the touch sensor
#ifdef TOUCH_ENABLED
  // INT0 on rising edge
  MCUCR |= (1 << ISC01) | (1 << ISC00);
  GIMSK |= (1 << INT0);
#endif

  // Setup sleep mode
  set_sleep_mode(SLEEP_MODE_IDLE);

  // Re-enable interrupts
  sei();
}

__attribute__((noreturn))
void main(void) {
  setup();
  current_pattern = next_pattern();
  while (1) {
    if (!current_pattern) {
      sleep_until_touch();
    }
    if (update_frame) {
      cli();
      update_loop_step();
      update_frame = 0;
      sei();
    }
    // Sleep until a wakeup
    idle();
  }
}

// Compute the next frame, returns 1 on wrap around
void get_brightness_from_pattern(uint8_t *brightness, pattern_t *p) {
  if (p == NULL) {
    for(uint8_t i = 0; i<NUM_LEDS; i++) {
      brightness[i] = 0;
    }
  }
  pattern_frame_t *frame = &p->frames[p->frame_id];
  uint16_t frame_timer = (++(p->frame_timer));

  // Check if we need to advance the frame
  if (frame_timer == frame->duration) {
    p->frame_timer = 0;
    frame_timer = 0;
    frame = &p->frames[++(p->frame_id)];
    if (frame->duration == 0) {
      p->frame_id = 0;
      frame = &p->frames[0];
    }
    return;
  }

  // Linear interpolation
  uint8_t *led_states = &frame->led_states[0];
  for(uint8_t i = 0; i<NUM_LEDS; i++) {
    switch(led_states[i]) {
      case OFF:
        brightness[i] = 0;
        break;
      case ON:
        brightness[i] = MAX_BRIGHTNESS;
        break;
      case RAMP_UP:
        if (frame_timer < RAMP_TIME) {
          uint24_t prop = MAX_BRIGHTNESS * (uint24_t)frame_timer;
          prop /= RAMP_TIME;
          brightness[i] = (uint8_t)(prop);
        } else {
          brightness[i] = MAX_BRIGHTNESS;
        }
        break;
      case RAMP_DN:
        if (frame_timer < RAMP_TIME) {
          uint24_t prop = MAX_BRIGHTNESS * (uint24_t)frame_timer;
          prop /= RAMP_TIME;
          brightness[i] = MAX_BRIGHTNESS-(uint8_t)(prop);
        } else {
          brightness[i] = 0;
        }
        break;
    }
  }
}

void update_loop_step() {
  static uint8_t pwm_frame = 0;
  static uint8_t brightness[NUM_LEDS] = {0};
  pwm_frame &= PWM_FRAME_MASK;
  if (!pwm_frame) {
    // Check auto-off
#if AUTO_OFF_TIME_SECS > 0
      if (frame_id >= (uint24_t)(AUTO_OFF_TIME_SECS * DESIRED_FRAMERATE)) {
        frame_id = 0;
        sleep_until_touch();
        return;
      }
#endif
    // Generate next frame
    frame_id++;
#ifdef DEBUG
    running_brightness = 1;
#endif
    get_brightness_from_pattern(brightness, current_pattern);
#ifdef DEBUG
    running_brightness = 0;
#endif
  }
  pwm_frame_update(pwm_frame++, brightness);
}

__attribute__((optimize("unroll-loops")))
void pwm_frame_update(uint8_t frame_no, uint8_t *brightness) {
  uint8_t out = 0;
  uint8_t bright;
  for(int8_t i=0; i<NUM_LEDS; i++) {
    if (brightness[i] == 0)
      continue;
    // Convert via gamma table
    bright = pgm_read_byte(&(gamma_table[brightness[i]]));
    if(bright > frame_no)
      out |= (1<<i);
  }
  update_out(out);
}

#ifdef DEBUG
volatile uint8_t global_leds = 0;
#endif

// LEDS are on PA0-3 and PB0-1
static void update_out(uint8_t leds) {
#ifdef DEBUG
  global_leds = leds;
#endif
#define PORTA_MASK 0x0F
#define PORTB_MASK 0x3
  PORTA = (PORTA & ~PORTA_MASK) | (leds & PORTA_MASK);
  PORTB = (PORTB & ~PORTB_MASK) | ((leds >> 4) & PORTB_MASK);
}


// simavr stuff
AVR_MCU_VCD_FILE("gtkwave_trace.vcd", 300000);
const struct avr_mmcu_vcd_trace_t _mytrace[]  _MMCU_ = {
  {AVR_MCU_VCD_SYMBOL("PORTA"), .what = (void *)&PORTA},
  {AVR_MCU_VCD_SYMBOL("PORTB"), .what = (void *)&PORTB},
  {AVR_MCU_VCD_SYMBOL("update_frame"), .mask=1, .what = (uint8_t *)(&update_frame)},
  {AVR_MCU_VCD_SYMBOL("frame_id"), .what = &frame_id},
#ifdef DEBUG
  {AVR_MCU_VCD_SYMBOL("global_leds"), .what = (uint8_t *)&global_leds},
  {AVR_MCU_VCD_SYMBOL("running_bright"), .mask=1, .what = (uint8_t *)&running_brightness},
#endif
};
