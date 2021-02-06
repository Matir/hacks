wall_thickness = 2;

module glue_stick(dia, height) {
  difference() {
    union() {
      // Main body
      cylinder(d=dia+wall_thickness*2, h=height+wall_thickness, $fs=0.1);
      // Base
      cylinder(d=(dia+wall_thickness*2)*1.8, h=wall_thickness, $fs=0.1);
      // Taper
      translate([0, 0, wall_thickness])
      cylinder(d1=(dia+wall_thickness*2)*1.8, d2=dia+wall_thickness*2, h=wall_thickness*3, $fs=0.1);
    }
    // Opening in top
    translate([0, 0, wall_thickness])
      cylinder(d=dia, h=height, $fs=0.1);
  }
}

glue_stick(18, 32);
