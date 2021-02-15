#include <stdint.h>
#include <atmel_start.h>

#include "ina3221.h"

#define INA3221_ADDR 0b1000000
// TODO: store in nvram
#define SHUNT_MILLIS 20

/* Note that this macro evaluates the target more than once. */
#define bswap16(x) \
  ((((x) >> 8) & 0xffu) | (((x) & 0xffu) << 8))

struct io_descriptor *i2c_io;

int32_t setup_i2c() {
  int32_t rv;
  if ((rv = i2c_m_sync_get_io_descriptor(&I2C_0, &i2c_io)) != 0)
    return rv;
  if ((rv = i2c_m_sync_enable(&I2C_0)) != 0)
    return rv;
  /* if i2c is ever a shared bus, each function will need to set its own address */
  i2c_m_sync_set_slaveaddr(&I2C_0, INA3221_ADDR, I2C_M_SEVEN);
  return 0;
}

int32_t configure_ina3221() {
  int32_t rv;
  int16_t cfg = 0;
  /* Enable all channels */
  cfg |= (1 << 14) | (1 << 13) | (1 << 12);
  /* Average 16 samples */
  cfg |= (0b010 << 9);
  /* Conversion time = 1.1ms */
  cfg |= (0b100 << 6);
  cfg |= (0b100 << 3);
  /* Continuous shunt and bus mode */
  cfg |= 0b111;
#define INA_CONFIG_REG 0
  if ((rv = i2c_m_sync_cmd_write(&I2C_0, INA_CONFIG_REG, (uint8_t *)&cfg, sizeof(cfg))) != 0)
    return rv;
  return 0;
}

/*
 * Stores the bus voltage in mv and the shunt voltage in *uv*.
 * Returns 0 on success, non-zero on failure.
 */
int32_t get_channel_voltages (const uint8_t channel, int32_t *shunt_voltage, int16_t *bus_voltage) {
  uint8_t shunt_reg = 2*channel - 1;
  uint8_t bus_reg = 2*channel;
  if (channel < 1 || channel > 3) {
    return -1;
  }
  int16_t tmp;
  int32_t rv;
  if ((rv = i2c_m_sync_cmd_read(&I2C_0, shunt_reg, (uint8_t *)&tmp, sizeof(tmp))) != 0)
    return rv;
  /*
   * 40uV/bit
   * Can potentially overflow 16 bits in uV
   */
  *shunt_voltage = (int32_t)(bswap16(tmp)) * 5;
  if ((rv = i2c_m_sync_cmd_read(&I2C_0, bus_reg, (uint8_t *)&tmp, sizeof(tmp))) != 0)
    return rv;
  /* 3 LSB are insignificant *but* we need to scale by 8mv, so this does not
   * need to be scaled at all. */
  *bus_voltage = bswap16(tmp);
  return 0;
}

/* Converts microvolts to milliamps.
 * TODO: consider if this can overflow?
 */
int32_t shunt_voltage_to_current(int32_t uvolts) {
  /* v = i * shunt_ohms
   * i = v / shunt_ohms
   * i = v / (shunt_millis * 1000)
   * ma = (uv) / shunt_millis
   */
  return (uvolts / SHUNT_MILLIS);
}
