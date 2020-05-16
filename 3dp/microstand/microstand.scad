use <../library/hex.scad>
use <../library/shapes.scad>

module finger_joint(width=20, hole_dia=3, length=30, depth=20, n_fingers=3, tol=0) {
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

module finger_joint_bar(width=12, depth=14, length=80, tol=0) {
  joint_length = 1.5*width;
  bar_length = length-2*joint_length;
  translate([joint_length, 0, 0]) {
    translate([bar_length, 0, 0])
      finger_joint(width=width, depth=depth, length=joint_length, tol=tol);
    translate([0, depth, 0])
      rotate([0, 0, 180])
      finger_joint(width=width, depth=depth, length=joint_length, tol=tol);
    cube([bar_length, depth, width]);
  }
}

module microscope_end(holder_dia=30, depth=14, tol=0, hole_dia=3) {
  wall_thick = 6;
  outer_dia = holder_dia+wall_thick;
  thickness = hole_dia*3+1;
  difference() {
    union() {
      cylinder(d=outer_dia, h=thickness, $fn=32);
      translate([holder_dia/2, -depth/2, 0])
        cube([wall_thick, depth, thickness]);
      translate([holder_dia/2+wall_thick, -depth/2, 0])
        finger_joint(width=thickness, depth=depth, length=1.5*thickness, hole_dia=hole_dia, tol=tol);
      translate([-holder_dia+wall_thick/2, -wall_thick/2, 0]) {
        union() {
          cube([hole_dia*3+wall_thick/2, wall_thick, thickness]);
          // Hex nut holder
          translate([hole_dia*1.5, 0, thickness/2]) {
            rotate([90, 0, 0])
            difference() {
              cylinder(d=hole_dia*3, h=hole_dia, $fn=32);
              linear_extrude(hole_dia)
                hexagon(hole_dia);
            }
          }
        }
      }
    } // end union
    cylinder(d=holder_dia+2*tol, h=thickness, $fn=32);
    translate([-holder_dia, -1/2, 0])
      cube([hole_dia*6, 1, thickness]);
    #translate([-holder_dia+wall_thick/2+hole_dia*1.5, wall_thick/2, thickness/2])
      rotate([90, 0, 0])
      cylinder(d=hole_dia+tol, h=wall_thick, $fn=32);
  }
}

module microscope_base(base_length=50, base_depth=30, base_height=10, bracket_width=12, bracket_depth=14, hole_dia=3, tol=0) {
  translate([base_length*cos(30), 0, 0])
  difference() {
    union() {
      truncated_pyramid(bottom=[base_length, base_depth], top=[base_length, base_depth-5], height=base_height);
      translate([base_length/2-bracket_depth/2, base_depth/2-bracket_width/2, base_height])
        rotate([0, -90, -90])
        finger_joint(width=bracket_width, depth=bracket_depth, length=bracket_width*1.5, hole_dia=hole_dia, tol=tol);

      // Wings
      translate([-base_length/2+base_depth/2*cos(30), base_depth*sin(30)/3, 0]) {
        rotate([0, 0, 30])
        difference() {
          translate([-base_length/2, -base_depth/2, 0])
            truncated_pyramid(bottom=[base_length, base_depth], top=[base_length, base_depth-5], height=base_height);
          translate([-base_length/2, 4, 0])
            cube([10, 5+tol, 5]);
          translate([-base_length/2, -9, 0])
            cube([10, 5+tol, 5]);
        }
      }
      translate([base_length*3/2-base_depth/2*cos(30), base_depth*sin(30)/3, 0]) {
        rotate([0, 0, -30])
        difference() {
          translate([-base_length/2, -base_depth/2, 0])
            truncated_pyramid(bottom=[base_length, base_depth], top=[base_length, base_depth-5], height=base_height);
          translate([base_length/2-10, 4, 0])
            cube([10, 5+tol, 5]);
          translate([base_length/2-10, -9, 0])
            cube([10, 5+tol, 5]);
        }
      }
    }
    // These cleanup the edges of the overlaps oops
    translate([0, base_depth*2-5/2, base_height])
      rotate([180, 0, 0])
      truncated_pyramid(bottom=[base_length, base_depth], top=[base_length, base_depth-5], height=base_height);
    translate([base_length*3/2-base_depth/2*cos(30), base_depth*sin(30)/3, base_height]) {
      rotate([0, 0, -30])
      translate([0, base_depth-5/2, 0])
      rotate([180, 0, 0])
      translate([-base_length/2, -base_depth/2, 0])
      truncated_pyramid(bottom=[base_length, base_depth], top=[base_length, base_depth-5], height=base_height);
    }
    translate([-base_length/2+base_depth/2*cos(30), base_depth*sin(30)/3, base_height]) {
      rotate([0, 0, 30])
      translate([0, base_depth-5/2, 0])
      rotate([180, 0, 0])
      translate([-base_length/2, -base_depth/2, 0])
      truncated_pyramid(bottom=[base_length, base_depth], top=[base_length, base_depth-5], height=base_height);
    }
  }
}

module microscope_leg(length=80, width=60, depth=30, height=10, tol=0) {
  // tied to some values in microscope_base
  difference() {
    union() {
      truncated_pyramid(bottom=[width, depth], top=[width, depth-5], height=height);
      translate([width, -length*cos(60)/4, 0])
        rotate([0, 0, -60])
        translate([-length/2, -depth/2, 0])
        truncated_pyramid(bottom=[length, depth], top=[length-5, depth-5], height=height);
      // pins
      translate([0, depth/2, 0]) {
        translate([-8, 4, 0])
          cube([10, 5-tol, 5]);
        translate([-8, -9, 0])
          cube([10, 5-tol, 5]);
      }
    }
    translate([0, 2*depth-5/2, height])
      rotate([180, 0, 0])
      truncated_pyramid(bottom=[width, depth], top=[width, depth-5], height=height);
    #translate([width, -length*cos(60)/4, 0])
      rotate([0, 0, -60])
      translate([0, depth-5/2, height])
      rotate([180, 0, 0])
      translate([-length/2, -depth/2, 0])
      truncated_pyramid(bottom=[width, depth], top=[width, depth-5], height=height);
  }
}

//finger_joint_bar(length=100, tol=0.15);
//microscope_end(tol=0.15);
//microscope_base(tol=0.15);
microscope_leg();
