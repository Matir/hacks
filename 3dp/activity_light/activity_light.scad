// For 8 LED ring
// 32mm dia
// two 1.8mm dia holes spaced 29.6mm-1.8mm (27.8mm centers) apart (across)
// 1/16 of a ring off from 90deg locations (22.5deg)

module diffuser(ring_dia=34, wall_thick=0.5, height=32, taper=3) {
  union() {
    difference() {
      cylinder(d1=ring_dia+wall_thick*2, d2=ring_dia+wall_thick*2-taper, h=height, $fa=3, $fs=0.5);
      cylinder(d1=ring_dia, d2=ring_dia-taper, h=height-wall_thick, $fa=3, $fs=0.5);
    }
    // screw supports
    intersection() {
      union() {
        for(i = [0, 90, 180, 270]) {
          rotate([0, 0, i+22.5])
            translate([0, 27.8/2, 3])
              difference() {
                hull() {
                  cylinder(d=4, h=height, $fn=24);
                  translate([0, (ring_dia-27.8)/2, 0])
                    cylinder(d=4, h=height, $fn=24);
                }
                cylinder(d=1.8, h=4, $fn=24);
              }
            }
          } // union
      // this keeps the screw supports inside the wall
      cylinder(d1=ring_dia+wall_thick, d2=ring_dia-taper+wall_thick, h=height, $fa=3, $fs=0.5);
    } // end screw supports
  }
}

diffuser();
