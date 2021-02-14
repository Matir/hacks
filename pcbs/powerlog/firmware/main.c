#include <atmel_start.h>
#include <cdcdf_acm.h>
#include <stdio.h>

#include "ina3221.h"

uint32_t sample_id = 0;

void sample_report_once();

int main(void)
{
	/* Initializes MCU, drivers and middleware */
	atmel_start_init();

	/* Prepare i2c */
	if (setup_i2c() != 0) {
  }

	if (configure_ina3221() != 0) {
  }

	/* Replace with your application code */
	while (1) {
	  sample_report_once();
	}
}

void sample_report_once() {
  int fail = 0;
  char buf[64];
  int used = snprintf(buf, sizeof(buf), "%08lu|", sample_id++);
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
    used = snprintf(buf, sizeof(buf), "%08lu|FAIL\n", (unsigned long)sample_id-1);
  }
  cdcdf_acm_write((uint8_t *)buf, used);
}
