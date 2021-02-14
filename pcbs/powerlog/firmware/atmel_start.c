#include <atmel_start.h>

/**
 * Initializes MCU, drivers and middleware in the project
 **/
int atmel_start_init(void)
{
	system_init();
	return usb_init();
}
