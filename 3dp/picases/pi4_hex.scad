include <bases/pis.scad>

RENDER_MODE = 2;

wall_thick = 1.5;
base_thick = wall_thick;
bottom_clearance = 2;
case_open_height = 28;
case_height = case_open_height+wall_thick+base_thick;
bottom_height = base_thick + 1.6 + 3.2 + bottom_clearance;
lip_height = 1;
lip_depth = wall_thick/3;
// tolerance on edges
tol = 0.1;
// clip positions
clips = [3.5+7.7+14.8/2, 72];
clip_width = 5;
clip_height = base_thick + 3;
clip_depth = 1;

module hexagon(r){
    polygon(points=[
                [r,(r*(tan(30)))],
                [0,(r*(2/sqrt(3)))],
                [-r,(r*(tan(30)))],
                [-r,-(r*(tan(30)))],
                [0,-(r*(2/sqrt(3)))],
                [r,-(r*(tan(30)))]
    ]);
}

module hexagon_tiles(hex_r, hex_sep, width, length, height) {
	tile_spacing = 2*hex_r + 2*hex_sep*2/sqrt(3);
	tile_row_spacing = 2*hex_r + hex_sep;
	num_cols = floor(width/tile_spacing);
	num_rows = floor(length/tile_row_spacing);
	translate([0, -(hex_r*sqrt(3)/2), 0])
	for (i = [1:num_rows]) {
    row_offset = (tile_spacing / 2) * (i % 2);
	  translate([row_offset, i*tile_row_spacing, 0]) {
      for (k = [1-(i%2):num_cols]) {
        translate([k*tile_spacing, 0, 0]) {
          linear_extrude(height=height) {
            hexagon(hex_r);
          }
        }
      }
	  }
	}
}

module pi_hex_tiles() {
  hexagon_tiles(2.5, .5, pi4_length, pi4_width, wall_thick);
}

module pi4_inplace() {
  translate([wall_thick+2*tol, wall_thick+2*tol, base_thick+bottom_clearance])
    pi4(tol=tol);
}

module innerhollow() {
  translate([wall_thick+tol, wall_thick+tol, base_thick])
    cube([pi4_length+2*tol, pi4_width+2*tol, case_open_height+2*tol]);
}

module picase_lip() {
  translate([wall_thick-lip_depth, wall_thick-lip_depth, bottom_height-lip_height])
  difference() {
    cube([pi4_length+2*lip_depth, pi4_width+2*lip_depth, lip_height]);
    translate([lip_depth, lip_depth, 0])
      cube([pi4_length, pi4_width, lip_height]);
  }
}

// Expand the hdmi ports vertically just a touch
module port_fix() {
  translate([wall_thick+3.5+7.7+14.8+2*tol, 1.75+wall_thick+tol, base_thick+0.2+bottom_clearance]) {
    micro_hdmi(tol=tol);
    translate([13.5, 0, 0])
      micro_hdmi(tol=tol);
  }
}

// Feet under pi
module pi_feet() {
  module single_foot() {
    cylinder(d=4, h=bottom_clearance, $fn=20);
    translate([0, 0, bottom_clearance])
      cylinder(d=2, h=2, $fn=20);
  }
  translate([wall_thick+tol, wall_thick+tol, base_thick]) {
    translate([3.5, 3.5, 0])
      single_foot();
    translate([3.5, 3.5+49, 0])
      single_foot();
    translate([3.5+58, 3.5, 0])
      single_foot();
    translate([3.5+58, 3.5+49, 0])
      single_foot();
  }
}

module sd_slot() {
  translate([-4, 22, base_thick])
    union() {
      cube([12+2*tol, 12+2*tol, bottom_clearance+tol]);
      // Extra depth to grab end of sd
      translate([0, 0, -base_thick-tol])
        cube([4+wall_thick*2, 12+2*tol, base_thick+tol]);
    }
}

module clip_female() {
  #union() {
    for(i=[0:1]) {
      translate([clips[i], wall_thick-clip_depth+tol, clip_height])
        cube([clip_width, clip_depth, clip_depth]);
      translate([clips[i], wall_thick+pi4_width+2*tol, clip_height])
        cube([clip_width, clip_depth, clip_depth]);
    }
  }
}

module clip_male() {
  union() {
    for(i=[0:1]) {
      translate([clips[i], wall_thick-clip_depth+tol, clip_height]) {
        translate([0, clip_depth, 0])
          cube([clip_width, clip_depth, bottom_height]);
        translate([0, clip_depth, 0])
          rotate([45, 0, 0])
          cube([clip_width, clip_depth, clip_depth]);
      }
      translate([clips[i], wall_thick+pi4_width+2*tol, clip_height]) {
        translate([0, -clip_depth, 0])
          cube([clip_width, clip_depth, bottom_height]);
        rotate([45, 0, 0])
          cube([clip_width, clip_depth, clip_depth]);
      }
    }
  }
}

module picase_bottom() {
    color("green", 0.25)
      union() {
        difference() {
          cube([pi4_length+2*wall_thick, pi4_width+2*wall_thick, bottom_height]);
          innerhollow();
          port_fix();
          pi4_inplace();
          picase_lip();
          sd_slot();
          clip_female();
        }
        pi_feet();
      }
}

module picase_top() {
    color("blue", 0.25)
      union() {
        difference() {
          union() {
            translate([0, 0, bottom_height])
              cube([
                  pi4_length+2*wall_thick,
                  pi4_width+2*wall_thick,
                  case_height-bottom_height]);
            picase_lip();
          }
          innerhollow();
          port_fix();
          pi4_inplace();
          translate([wall_thick/2, wall_thick, case_height-wall_thick])
            pi_hex_tiles();
        }
        clip_male();
      }
}

module picase() {
  if (RENDER_MODE == 0) {
    picase_top();
    picase_bottom();
    %pi4_inplace();
  } else if (RENDER_MODE == 1) {
    picase_bottom();
  } else if (RENDER_MODE == 2) {
    picase_top();
  }
}

picase();
//pi4();
