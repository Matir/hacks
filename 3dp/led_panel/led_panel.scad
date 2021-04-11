use <../library/hex.scad>


module puzzle_notch(w, l, d) {
  translate([0, w/4, 0])
  hull() {
    translate([w/4, 0, 0])
      cylinder(r=w/4, h=d, $fn=20);
    translate([-w/4, 0, 0])
      cylinder(r=w/4, h=d, $fn=20);
    translate([-w/4, 0, 0])
      cube([w/2, l-w/4, d]);
  }
}

module finger_joint(width=12, hole_dia=3, length=18, depth=14, n_fingers=3, tol=0.15) {
  union() {
    intersection() {
      difference() {
        union() {
          finger_depth = depth/n_fingers/2;
          for(i=[0:n_fingers-1]) {
            translate([0, i*finger_depth*2, 0])
              cube([length, finger_depth-tol, width]);
          }
        }
        translate([length-width/2, depth, width/2])
          rotate([90, 0, 0])
          cylinder(d=hole_dia+2*tol, h=depth*2, $fn=32);
      }
      union() {
        cube([length-width/2, depth, width]);
        translate([length-width/2, depth, width/2])
          rotate([90, 0, 0])
          cylinder(d=width, h=depth, $fn=32);
      }
    }
    // Hex nut holder
    translate([length-width/2, 0, width/2]) {
      rotate([90, 0, 0])
      difference() {
        cylinder(d=hole_dia*3, h=hole_dia, $fn=32);
        linear_extrude(hole_dia)
          hexagon(hole_dia);
      }
    }
  }
}

width=60;
rib_width=12;

module panel_piece() {
  height=75;
  thickness=2;
  rib_thickness=10;
  rib_offset=width/4;

  difference() {
    union() {
      cube([width, height, thickness]);
      translate([width/4, -10, 0])
        puzzle_notch(rib_width*.75, 10, rib_thickness);
      // ribs
      for (o = [1/4, 3/4])
        translate([width*o-rib_width/2, 0, 0])
          cube([rib_width, height, rib_thickness]);
    }
    union() {
      // rib notch
      translate([width*3/4, 10.2, 0])
        rotate([180, 180, 0])
          puzzle_notch(rib_width*.75+0.2, 10.2, rib_thickness);
      // screw holes
      for (o=[1/4, 3/4]) {
        for (l=[16, 22])
          translate([width*o, l, rib_thickness/2])
            cylinder(d=2.5, h=rib_thickness, $fn=20);
      };
      // taper on end
      translate([width/2, height, rib_thickness*1.41+thickness])
        rotate([45, 0, 0])
          cube([width, rib_thickness*2, rib_thickness*2], center=true);
    }
  }
}

module back_bracket() {
  bracket_len = 60;
  difference() {
    union() {
      // ribs
      for (o = [1/4, 3/4]) {
        translate([o*width-rib_width/2, 0, 0])
          cube([rib_width, bracket_len, 3]);
      }
      // crossbar
      translate([width/4, rib_width/2, 0])
        cube([width/2, rib_width, 3]);
      // joint support
      translate([width/2-7, rib_width/2, 0])
        difference() {
          translate([0, 0, 3])
            rotate([0, 15, 0])
            cube([12, 12, 6]);
          translate([-2, -2, 0])
            cube([20, 20, 3]);
        }
      // joint
      translate([width/2-6, rib_width/2, 6])
        rotate([0, 15, 0])
        rotate([0, -90, -90])
          finger_joint();
    }
    union() {
      // screw holes
      for (o = [1/4, 3/4]) {
        for (d = [16, 22]) {
          for (s = [-1, 1]) {
            translate([o*width, 30+d*s, 0])
              cylinder(d=3, h=10, $fn=20);
          }
        }
      }
    }
  }
}

module 45_bracket() {
  module end() {
    translate([0, 30, 12])
      rotate([180, 0, 90])
      finger_joint();
    cube([14, 30, 12]);
  }
  union() {
    translate([14, 0, 0])
      rotate([0, 0, -135])
      end();
    end();
    #intersection() {
      translate([14, 0, 0])
        cylinder(r=14, h=24, center=true, $fn=48);
      translate([0, -15, 0])
        cube([14, 20, 12]);
    }
  }
}

module tower_bracket() {
  module screwholes() {
    module sh() {
      translate([0, 0, 6.5])
        cylinder(d=6.6, h=10, center=true, $fn=20);
      cylinder(d=3.2, h=10, center=true, $fn=20);
    }
    union() {
      translate([-38.5, 12.6, 0]) sh();
      translate([-32, 5.6, 0]) sh();
      translate([-8, 24, 0]) sh();
    }
  }
  difference() {
    translate([-45, 0, 0])
      union() {
        cube([45, 30, 3]);
        translate([41, -4, 10])
          rotate([0, -45, -45])
            union() {
              translate([-24, 0, 0])
                cube([24, 12, 12]);
              finger_joint();
            }
      }
    union() {
      screwholes();
      // corner cut
      rotate([0, 0, -45])
        cube([14, 14, 7], center=true);
      // remove anything beneath the bottom
      translate([-50, 0, -20])
        cube([50, 50, 20]);
    }
  }
}

module single_panel() {
  p_width=80;
  height=75;
  thickness=2;
  rib_thickness=10;
  rib_offset=width/4;

  difference() {
    union() {
      cube([p_width, p_width, thickness]);
      // ribs
      for (o = [1/4, 3/4])
        translate([width*o-rib_width/2+10, 0, 0])
          cube([rib_width, p_width, rib_thickness]);
    }
    union() {
      // screw holes for back
      for (o=[1/4, 3/4]) {
        for (l=[16, 22])
          for (d=[-1, 1])
            translate([width*o+10, l*d+(p_width/2), rib_thickness/2])
              cylinder(d=2.5, h=rib_thickness, $fn=20);
      };
      // taper on end
      for(o=[0, 1])
        translate([width/2+10, o*p_width, rib_thickness*1.41+thickness])
          rotate([45, 0, 0])
            cube([width, rib_thickness*2, rib_thickness*2], center=true);
      // Cutout for connector
      translate([p_width/2-5, 0, -thickness])
        cube([10, 9, thickness*3]);
      // Screw holes, m3 at 70mm spacing
      for(x_pos=[1, -1])
        for(y_pos=[1, -1])
          translate([p_width/2-x_pos*35, p_width/2-y_pos*35, -thickness])
            cylinder(d=3.2, h=thickness*3, $fn=20);
    }
  }
}

module single_panel_lens() {
  p_width=80;
  thickness=0.6;
  depth=5;

  union() {
    difference() {
      // Main Body
      cube([p_width, p_width, depth]);
      // Make it hollow
      translate([thickness*2, thickness*2, thickness])
        cube([p_width-thickness*4, p_width-thickness*4, depth]);
      // Cut out for screw terminal
      translate([p_width/2-5, 0, -thickness])
        cube([10, 9, 15]);
    }
    // Screw supports, self-tapping M3
    for(x_pos=[1, -1])
      for(y_pos=[1, -1])
        translate([p_width/2-x_pos*35, p_width/2-y_pos*35, 0]) {
          difference() {
            cylinder(d=6, h=depth, $fn=20);
            cylinder(d=2.6, h=depth, $fn=20);
          }
        }
  }
}

//panel_piece();

//translate([0, -30, 10])
//back_bracket();
//translate([0, 0, 30])
//  single_panel();

//
//45_bracket();

//tower_bracket();

single_panel_lens();
