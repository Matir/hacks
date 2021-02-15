#include <stdint.h>

#ifndef INA3221_H
#define INA3211_H

int32_t setup_i2c();
int32_t configure_ina3221();
int32_t get_channel_voltages (const uint8_t channel, int32_t *shunt_voltage, int16_t *bus_voltage);
int32_t shunt_voltage_to_current(int32_t volts);

#endif
