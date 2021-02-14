#include <atmel_start.h>
#include <cdcdf_acm.h>

int main(void)
{
  char hw[] = "hello world\r\n";
	/* Initializes MCU, drivers and middleware */
	atmel_start_init();
  

	/* Replace with your application code */
	while (1) {
	  gpio_set_pin_level(PB30, false);
    delay_ms(5000);
	  gpio_set_pin_level(PB30, true);
    delay_ms(1000);
    cdcdf_acm_write(hw, strlen(hw));
	}
}
