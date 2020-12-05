DEVICE     = attiny84
CLOCK      = 8000000
PROGRAMMER = um232h
FILENAME   = main
PWM_RESOLUTION_STEPS = 0x7F
CC         = avr-gcc
CFLAGS     = -Wall -Wno-main -O2 -DF_CPU=$(CLOCK) -mmcu=$(DEVICE) \
						 -DPWM_RESOLUTION_STEPS=$(PWM_RESOLUTION_STEPS) -g
SIMAVR		 = /home/david/tmp/simavr/simavr/run_avr
AVRDUDE_DEVICE = t84
AVRDUDE_PROG = c232hm
# Fusebits for avrdude
# 4MHz, no CKDIV8, no CKOUT
FUSEBITS	 = -U lfuse:w:0xe2:m -U hfuse:w:0xdf:m -U efuse:w:0xff:m


OBJS = main.o gamma.o

main.hex: main.elf
	avr-objcopy -j .text -j .data -O ihex ${@:.hex=.elf} $@

main.elf: ${OBJS}
	${CC} ${CFLAGS} $^ -o $@
	avr-size --mcu=${DEVICE} -C $@

%.o: %.c
	${CC} ${CFLAGS} -c $<

gamma.c: gentable.py
	python3 gentable.py 256 $(PWM_RESOLUTION_STEPS) $@

simavr: main.elf
	${SIMAVR} -f ${CLOCK} -m ${DEVICE} main.elf

.PHONY: avrdude

avrdude: main.hex
	avrdude -c ${AVRDUDE_PROG} -p ${AVRDUDE_DEVICE} -U flash:w:$< ${FUSEBITS}

clean:
	rm -f *.o *.hex *.elf
