include <bases/pis.scad>

RENDER_MODE = 2;

wall_thick = 2;
base_thick = wall_thick;
bottom_clearance = 2;
case_open_height = 28;
case_height = case_open_height+wall_thick+base_thick;
bottom_height = base_thick + 1.6 + 3.2 + bottom_clearance;
lip_height = 1;
lip_depth = wall_thick/3;
// tolerance on edges
tol = 0.15;
// clip positions
clips = [3.5+7.7+14.8/2, 72];
clip_width = 5;
clip_height = base_thick + 3.8;
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

module hexagon_tiles(hex_r, hex_sep, length, width, height, only=undef) {
  module a_hex() {
    linear_extrude(height=height) {
      hexagon(hex_r);
    }
  }
	tile_spacing = 2*hex_r + 2*hex_sep*2/sqrt(3);
	tile_row_spacing = 2*hex_r + hex_sep;
	num_cols = floor(length/tile_spacing);
	echo("Cols:", num_cols);
	num_rows = floor(width/tile_row_spacing);
	echo("Rows:", num_rows);
	extra_col = 1 - (round(length/tile_spacing) - num_cols);
	translate([0, -(hex_r*sqrt(3)/2), 0])
	for (i = [1:num_rows]) {
    row_offset = (tile_spacing / 2) * (i % 2);
	  translate([row_offset, i*tile_row_spacing, 0]) {
	    num_row_cols = num_cols - ((i%2) * extra_col);
	    echo("Row cols: ", num_row_cols);
      for (k = [1-(i%2):num_row_cols]) {
        dist = k*tile_spacing;
        if (only == undef) {
          translate([dist, 0, 0]) {
            a_hex();
          }
        } else {
          for (pt = only) {
            if (pt[0] == i && pt[1] == k) {
              translate([dist, 0, 0]) {
                a_hex();
              }
            }
          }
        }
      } // end column loop
	  }
	} // end row loop
}

module pi_hex_tiles(length, width, exclude=undef) {
  tile_size = 3.6;
  tile_spacing = 0.7;
  difference() {
    hexagon_tiles(tile_size, tile_spacing, length, width, wall_thick*2);
    if (exclude != undef) {
      hexagon_tiles(tile_size, tile_spacing, length, width, wall_thick*2, only=exclude);
    }
  }
}

module pi4_inplace() {
  translate([wall_thick+2*tol, wall_thick+tol, base_thick+bottom_clearance])
    pi4(tol=tol);
}

module innerhollow() {
  translate([wall_thick+tol, wall_thick+tol, base_thick])
    cube([pi4_length+2*tol, pi4_width+2*tol, case_open_height+2*tol]);
}

module picase_lip() {
  translate([wall_thick-lip_depth+tol, wall_thick-lip_depth+tol, bottom_height-lip_height])
  difference() {
    cube([pi4_length+2*lip_depth+2*tol, pi4_width+2*lip_depth+2*tol, lip_height]);
    translate([lip_depth+tol, lip_depth+tol, 0])
      cube([pi4_length, pi4_width, lip_height]);
  }
}

module port_fix() {
  // Expand the hdmi ports vertically just a touch
  translate([wall_thick+3.5+7.7+14.8+2*tol, 1.75+wall_thick+tol, base_thick+0.2+bottom_clearance]) {
    micro_hdmi(tol=tol);
    translate([13.5, 0, 0])
      micro_hdmi(tol=tol);
  }
  // Carve out space between ports
  translate([wall_thick+tol+pi4_length, 18, base_thick+bottom_clearance+1.6+tol])
    cube([2*wall_thick, 6, 16]);
  translate([wall_thick+tol+pi4_length, 36, base_thick+bottom_clearance+1.6+tol])
    cube([2*wall_thick, 6, 13.6]);
}

mounting_points = [[3.5, 3.5],
                   [3.5, 3.5+49],
                   [3.5+58, 3.5],
                   [3.5+58, 3.5+49]];

// Feet under pi
module pi_feet() {
  module single_foot() {
    difference() {
      cylinder(d=4, h=bottom_clearance, $fn=20);
      cylinder(d=2, h=bottom_clearance, $fn=12);
    }
  }
  translate([wall_thick+tol, wall_thick+tol, base_thick]) {
    for (pt = mounting_points) {
      translate([pt[0], pt[1], 0])
        single_foot();
    }
  }
}

// Holes in top
module top_screw_holes() {
  translate([wall_thick+tol, wall_thick+tol, case_height-wall_thick])
    for (pt = mounting_points) {
      translate([pt[0], pt[1], 0])
        cylinder(d=2, h=2*wall_thick, $fn=12);
    }
}

module sd_slot() {
  translate([-4, 22+wall_thick, base_thick])
    union() {
      cube([12+2*tol, 12+2*tol, bottom_clearance+tol]);
      // Extra depth to grab end of sd
      translate([0, 0, -base_thick-tol])
        cube([7+wall_thick*2, 12+2*tol, base_thick+tol]);
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
      translate([clips[i], wall_thick+pi4_width+3*tol, clip_height]) {
        translate([0, -clip_depth, 0])
          cube([clip_width, clip_depth, bottom_height]);
        rotate([45, 0, 0])
          cube([clip_width, clip_depth, clip_depth]);
      }
    }
  }
}

// Mounts for fan
module fan_mounts() {
  screw_dia = 3.2;
  translate([pi4_length/4+1, (pi4_width-32)/2+2.5, case_height-2*wall_thick]) {
    for (i=[0, 32]) {
      for (k=[0, 32]) {
        translate([i, k, 0])
          cylinder(d=screw_dia, h=5, $fn=12);
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
          //clip_female();
        }
        pi_feet();
      }
}

module picase_top() {
    color("blue", 0.5)
      union() {
        difference() {
          // Additive block
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
          translate([wall_thick/2+2, wall_thick, case_height-wall_thick])
            pi_hex_tiles(
              pi4_length-2*wall_thick,
              pi4_width,
              exclude=[
              // 40mm fan
              [2,2],[6,2],[2,6],[6,6],
              // Mounting screws
              [1,0],[7,0],[1,6],[7,6],
              ]);
          fan_mounts();
          top_screw_holes();
          // Hex on end wall
          #translate([-wall_thick+tol, wall_thick, case_height-wall_thick/2])
            rotate([0, 90, 0])
            pi_hex_tiles(case_height-bottom_height-wall_thick*2, pi4_width);
        }
        // Add some things back
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
