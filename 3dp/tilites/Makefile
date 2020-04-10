.PHONY: all

all: tilelites-body.stl tilelites-plate.stl

tilelites-body.stl: tilelites.scad
	openscad -Dmode=1 -o $@ $<

tilelites-plate.stl: tilelites.scad
	openscad -Dmode=2 -o $@ $<
