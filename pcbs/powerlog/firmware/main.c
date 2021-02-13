#include <atmel_start.h>
#include <cdcdf_acm.h>

int main(void)
{
	/* Initializes MCU, drivers and middleware */
	if (atmel_start_init() == 0) {
    cdcd_acm_example();
  }

	/* Replace with your application code */
	while (1) {
	  gpio_set_pin_level(PB30, false);
    delay_ms(5000);
	  gpio_set_pin_level(PB30, true);
    delay_ms(1000);
	}
}
