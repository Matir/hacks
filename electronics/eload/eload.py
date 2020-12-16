#!/usr/bin/env python3

"""
Constant current load calculator.

Based on TI AppNote SLAA868: https://www.ti.com/lit/an/slaa868/slaa868.pdf
"""

DAC_MAX_VOLTAGE = 0.510
VCC_MAX = 5.0
CURRENT_MAX = 0.100

OHM = "\u03A9"


def calc_rset(dac_max_v, i_out_max):
    """Calculate the minimum resistance for Rset."""
    return dac_max_v / i_out_max


def calc_rset_power(dac_max_v, i_out_max):
    """Calculate power in Rset."""
    return dac_max_v * i_out_max


def calc_rload(vcc_max, i_out_max, r_set):
    """Calculate the maximum Rload value."""
    rset_drop = i_out_max * r_set
    rload_drop = vcc_max - rset_drop
    return rload_drop / i_out_max


def calc_rload_power(i_out_max, r_load):
    """Calculate the maximum power dissipation in Rload."""
    return r_load * i_out_max * i_out_max


def transistor_power(vcc_max, i_out, r_load, r_set):
    """Calculate power loss in the transistor."""
    r_tot = r_load + r_set
    # Find point where power is maximum
    max_pwr_i = vcc_max/(2 * r_tot)
    load_rdrop = max_pwr_i * r_tot
    v_trans = vcc_max - load_rdrop
    return max_pwr_i * v_trans


def print_line(title, value, unit):
    print("%32s %0.3f%s" % (title, value, unit))


def main():
    # Print inputs
    print_line("DAC Max Voltage", DAC_MAX_VOLTAGE, "V")
    print_line("VCC Max", VCC_MAX, "V")
    print_line("Current Max", CURRENT_MAX, "A")
    print("")
    rset = calc_rset(DAC_MAX_VOLTAGE, CURRENT_MAX)
    print_line("RSet", rset, OHM)
    print_line("RSet PWR", calc_rset_power(DAC_MAX_VOLTAGE, CURRENT_MAX), "W")
    rload = calc_rload(VCC_MAX, CURRENT_MAX, rset)
    print_line("Rload", rload, OHM)
    print_line("Rload PWR", calc_rload_power(CURRENT_MAX, rload), "W")
    print_line("Transistor PWR",
            transistor_power(VCC_MAX, CURRENT_MAX, rload, rset), "W")


if __name__ == '__main__':
    main()
