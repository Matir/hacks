use <rounded.scad>

module nr200_slotcover() {
  width=75.25;
  height=27.5;
  depth=13.75;
  difference() {
    union() {
      // back
      translate([0, 2, 0])
        rotate([90, 0, 0])
        rounded_flat_cube([width, height, 2], 4, $fn=20);
      cube([width, 2, height/2]);
      // bottom
      rounded_flat_cube([width, depth, 5], 4, $fn=20);
      cube([width, 5, 5]);
    }
    union() {
      // screw head space
      translate([2, 0, 0])
        cube([width-4, depth-3, 4]);
      // top center bulge
      translate([width/2-10, 0, height/3*2])
        cube([20, 3, height/3]);
      // screw holes
      for (dir = [-1, 1]) {
        translate([width/2+(dir*65/2), 0, height-6])
          rotate([90, 0, 0])
          cylinder(d=4, h=8, center=true, $fn=20);
      }
    }
  }
}

nr200_slotcover();
