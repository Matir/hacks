use <../library/hex.scad>;
use <../library/threads.scad>;


module hex_flask(r, h, cap_thick=10, wall=1) {

  module hex_flask_cap(thick, cutout=false) {
    cap_r = r - wall;
    cap_inner_r = cap_r * .9;
    difference() {
      union() {
        cylinder(r2=cap_inner_r, r1=cap_r*.8, h=thick*.2);
        translate([0, 0, thick*.2]) {
          // Slightly thinner for fit
          thread_d = cutout ? cap_r*2 : cap_r*2-0.3;
          cylinder(r=cap_inner_r, h=thick*.8);
          metric_thread(thread_d, thick/3, thick*.8, internal=cutout, leadin=3);
        }
      }
      if (!cutout) {
        translate([0, 0, thick*.4])
        difference() {
          cylinder(r2=cap_inner_r*0.8, r1=cap_inner_r*0.6, h=thick*.6);
          cube([cap_inner_r*0.2, cap_inner_r*2, thick*1.2], center=true);
        }
      }
    }
  }

  // bottle
  difference() {
    linear_extrude(h) {
      hexagon(r);
    }
    translate([0, 0, wall*2])
    difference() {
      in_height = h-2*wall-cap_thick;
      linear_extrude(in_height)
        hexagon(r-wall);
      translate([0, 0, in_height-cap_thick])
        difference() {
          cylinder(r=r*1.155, h=cap_thick);
          cylinder(r1=r*1.155, r2=(r-wall)*.8, h=cap_thick);
        }
    }
    translate([0, 0, h-cap_thick])
      hex_flask_cap(cap_thick, cutout=true);
  }

  // standalone cap
  translate([r*3, 0, cap_thick])
    rotate([180, 0, 0])
      hex_flask_cap(cap_thick);
}

module hex_flask_preview() {
  intersection() {
    hex_flask(r=25, h=80);
    cube([200, 200, 200]);
  }
}

hex_flask(r=25, h=80);
//hex_flask_preview();
