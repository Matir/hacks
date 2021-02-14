#include <atmel_start.h>
#include <cdcdf_acm.h>
#include <stdio.h>

#include "ina3221.h"

#define LED_STATUS  PA00
#define LED_READING PA01
#define LED_ERROR   PA02

#define LED_ON(x)  gpio_set_pin_level((x), false)
#define LED_OFF(x) gpio_set_pin_level((x), true);

uint32_t sample_id = 0;
uint8_t run_sample = 1;
static struct timer_task TIMER_0_task;

static void sample_report_once();
static void setup_timer();
static void TIMER0_callback(const struct timer_task *const timer_task);
static void led_error_code(int n);
static void led_error_code_forever(int n);

int main(void)
{
	/* Initializes MCU, drivers and middleware */
	if (atmel_start_init() != 0) {
	  led_error_code_forever(3);
  }
	LED_OFF(LED_STATUS);
	LED_OFF(LED_READING);
	LED_OFF(LED_ERROR);

	/* Prepare i2c */
	if (setup_i2c() != 0) {
	  led_error_code_forever(4);
  }

	if (configure_ina3221() != 0) {
	  led_error_code_forever(5);
  }

  setup_timer();

	/* Replace with your application code */
	while (1) {
	  // Busy wait for interrupt
	  while (!run_sample) {}
	  sample_report_once();
	  run_sample = 0;
	}
}

static void led_error_code_forever(int n) {
  while(1) {
    led_error_code(n);
    delay_ms(1000);
  }
}

static void led_error_code(int n) {
  while(n--) {
    LED_ON(LED_ERROR);
    delay_ms(200);
    LED_OFF(LED_ERROR);
    if(n)
      delay_ms(200);
  }
}

static void setup_timer() {
  TIMER_0_task.interval = 100;
  TIMER_0_task.mode = TIMER_TASK_REPEAT;
  TIMER_0_task.cb = TIMER0_callback;
  timer_add_task(&TIMER_0, &TIMER_0_task);
  timer_start(&TIMER_0);
}

static void TIMER0_callback(const struct timer_task *const timer_task) {
  if (!run_sample) {
    run_sample = 1;
    return;
  }
}

static void sample_report_once() {
  int fail = 0;
  char buf[64];
  int used = snprintf(buf, sizeof(buf), "%08lu|", (unsigned long)sample_id++);
  for(int i=0; i<3; i++) {
    int16_t bus, shunt;
    if (get_channel_voltages(i, &shunt, &bus) != 0) {
      fail=1;
      continue;
    }
    shunt = shunt_voltage_to_current(shunt);
    used += snprintf(buf, sizeof(buf)-used, "%05d|%05d|", bus, shunt);
  }
  if (!fail) {
    buf[used]='\n';
    buf[used+1]='\0';
  } else {
    led_error_code(1);
    used = snprintf(buf, sizeof(buf), "%08lu|FAIL\n", (unsigned long)sample_id-1);
  }
  cdcdf_acm_write((uint8_t *)buf, used);
}
