BUILDS = switchplate piplate frame top bottom switchcover
SRC_FILE = picluster.scad
DEPS = ../library/hex.scad ../library/rounded.scad
OUT_PREFIX = picluster_

all: $(addsuffix .stl, $(addprefix ${OUT_PREFIX}, ${BUILDS}))
	@echo Built $^

%.stl: ${SRC_FILE} ${DEPS}
	@echo Building $@
	openscad -o $@ -D build_target=\"$(subst ${OUT_PREFIX},,$(basename $@))\" $<
