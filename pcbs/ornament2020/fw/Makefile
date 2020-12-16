DEVICE     = attiny84
CLOCK      = 4000000
PWM_RESOLUTION_STEPS = 0x80
MAX_BRIGHTNESS = 0x10
CC         = avr-gcc
CFLAGS     = -Wall -Wno-main -Wextra -O2 -DF_CPU=$(CLOCK) -mmcu=$(DEVICE) \
						 -DPWM_RESOLUTION_STEPS=$(PWM_RESOLUTION_STEPS) \
						 -g #-DDEBUG=1
#SIMAVR		 = /home/david/tmp/simavr/simavr/run_avr
SIMAVR		 = /usr/bin/simavr
AVRDUDE_DEVICE = t84
AVRDUDE_PROG = tigard
AVRDUDE_FLAGS = -C +tigard.avrdude.conf -c $(AVRDUDE_PROG) -p $(AVRDUDE_DEVICE)
# Fusebits for avrdude
# 4MHz, no CKDIV8, no CKOUT
FUSEBITS	 = -U lfuse:w:0xe2:m -U hfuse:w:0xdf:m -U efuse:w:0xff:m


OBJS = gamma.o pattern.o main.o

main.hex: main.elf
	avr-objcopy -j .text -j .data -O ihex ${@:.hex=.elf} $@

main.elf: ${OBJS}
	${CC} ${CFLAGS} -Wl,--undefined=_mmcu,--section-start=.mmcu=0x910000 $^ -o $@
	avr-size --mcu=${DEVICE} -C $@

%.o: %.c Makefile
	${CC} ${CFLAGS} -c $<

%.s: %.c
	${CC} ${CFLAGS} -S -fverbose-asm -o $@ $<

gamma.c: gentable.py Makefile
	python3 gentable.py $(PWM_RESOLUTION_STEPS) $(MAX_BRIGHTNESS) $@

simavr: main.elf
	${SIMAVR} -f ${CLOCK} -m ${DEVICE} ${SIMAVR_FLAGS} $^

.PHONY: avrdude

avrdude: main.hex
	avrdude ${AVRDUDE_FLAGS} -U flash:w:$< ${FUSEBITS}

clean:
	rm -f *.o *.hex *.elf gamma.c
