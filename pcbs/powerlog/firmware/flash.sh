#!/bin/bash

#openocd -f board/atmel_samd21_xplained_pro.cfg \
#  -c 'init' \
#  -c 'program gcc/firmware.bin 0 verify reset' \
#  -c 'shutdown'

set -ue

gdb-multiarch ./gcc/firmware.elf <<EOF
  target extended-remote ${1}
  monitor swdp_scan
  attach 1
  load ./gcc/firmware.hex
  monitor hard_srst
EOF
