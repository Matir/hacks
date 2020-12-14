import math
import sys

gamma = 2.5

template = '''
#include <stdint.h>
#include <avr/pgmspace.h>

const uint8_t consts_num_steps = %(nsteps)d;
const uint8_t gamma_table[] PROGMEM = {%(gamma_table)s};
'''

nsteps = int(sys.argv[1], 0)
maxval = int(sys.argv[2], 0)
outfile = sys.argv[3]

# Gamma adjustment table per Adafruit
gamma_vals = [int(math.pow(i/float(nsteps), gamma) * float(maxval) + 0.75)
              for i in range(nsteps)]

# Render them
templ = {}
templ['nsteps'] = nsteps - 1
templ['gamma_table'] = ', '.join('%d' % x for x in gamma_vals)

with open(outfile, 'w') as fp:
    fp.write(template % templ)
