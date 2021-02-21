module pureconnect_cover() {
  difference() {
    cube([14, 18, 7]);
    translate([(14-11.0)/2, 0, 0])
      union() {
        translate([0, 0, 1.5])
          cube([11.0, 15, 3.5]);
        translate([(11.0-8.8)/2, 0, 0])
          cube([8.8, 15, 2]);
      }
  }
}

pureconnect_cover();
