#!/bin/bash

openocd -f board/atmel_samd21_xplained_pro.cfg \
  -c 'init' \
  -c 'program gcc/firmware.bin 0 verify reset' \
  -c 'shutdown'
