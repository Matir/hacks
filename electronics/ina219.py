#!/usr/bin/env python3

OHM = "\u2126"
MICRO = "\u03BC"


class INA219B(object):

    def __init__(self, resistor):
        self.resistor = resistor

    def calc(self, pga=1):
        """Return Max Scale Current"""
        assert(pga in (1, 2, 4, 8))
        # v = ir
        max_v = pga * .04  # 40 mA ADC Max
        max_i = max_v / self.resistor
        return max_i

    def __str__(self):
        grid = []
        for p in (1, 2, 4, 8):
            max_i = self.calc(p)
            res = max_i/(2**12)
            rv = '{:>6s}A Max, {:>6s}A/bit'.format(
                    format_small_float(max_i),
                    format_small_float(res))
            grid.append(rv)
        return '{:12s}{}'.format(
                format_small_float(self.resistor) + OHM,
                '  '.join(grid))


def format_small_float(f):
    if f < 1/1000:
        return '{:3.3f}{}'.format(f*1000000, MICRO)
    if f < 1:
        return '{:3.3f}{}'.format(f*1000, "m")
    return '{:3.3f}'.format(f)


def main():
    for r in (0.1, 0.05, 0.02):
        setup = INA219B(r)
        print(str(setup))


if __name__ == '__main__':
    main()
