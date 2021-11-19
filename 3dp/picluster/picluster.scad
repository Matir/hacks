use <../library/rounded.scad>;
use <../library/hex.scad>;

// Curve setups
$fs = 0.1;
$fa = 5;

// Common variables
default_plate_thickness = 2.5;
pi_plate_width = 78;
cluster_frame_width = 104;
cluster_frame_height = 115;
cluster_frame_thickness = 10;
// Between front and back supports, on centers
cluster_piece_spacing = 83;
// Spacing between mounting screws top/bottom
mnt_screw_spacing = 42;
tab_screw_height = 5;
tab_width = 8;
side_plate_width = 100;
$m3_hex_width = 6;
$m3_hex_depth = 3;
$m3_screw_dia = 3.30;
$m3_head_dia = 6;
$m3_head_depth = 3;

// Useful functions
function cat(L1, L2) = [for(L=[L1, L2], a=L) a];

module switch_backplate(
  plate_width,
  mount_spacing,
  tab_offset,
  plate_thickness=default_plate_thickness) {
  // main plate
  // bottom is along the y-axis
  switch_width = 94.2;
  switch_depth = 89.0;
  plate_depth = 100;
  standoff_mm = 3;
  standoff_hole = $m3_screw_dia;
  pcb_thickness = 1.6;

  standoffs_5mm_base_dia = 8;
  standoffs_5mm_dia = 4.8;
  standoffs_5mm = [[7, 11.1], [7, switch_depth-17]];
  standoffs_3mm_base_dia = 6;
  standoffs_3mm = [[switch_width-34.0, 4.4], [switch_width-7, switch_depth-16.8]];

  difference() {
    union() {
      rounded_flat_cube([plate_width, plate_depth, plate_thickness], 2);
      // Standoffs
      translate([
        (plate_width - switch_width)/2,
        (plate_depth - switch_depth)/2,
        plate_thickness]) {
        // 5mm standoffs, positive
        for (pos=standoffs_5mm) {
          translate([pos[0], pos[1], 0]) {
            cylinder(h=standoff_mm, d=standoffs_5mm_base_dia);
            cylinder(h=standoff_mm+pcb_thickness, d=standoffs_5mm_dia);
          };
        };
        // 3mm standoffs
        for (pos=standoffs_3mm) {
          translate([pos[0], pos[1], 0]) {
            cylinder(h=standoff_mm, d=standoffs_3mm_base_dia);
          };
        };
      };
      // Depth blocks
      blocker_y = plate_depth - (plate_depth - mount_spacing)/2 + tab_offset;
      translate([0, blocker_y, plate_thickness/2]) {
        rotate([90, 0, 0]) {
          for (x = [0, 1]) {
            blocker_width = 5;
            translate([x*(plate_width-blocker_width), 0, -plate_thickness]) {
              cube([blocker_width, standoff_mm, plate_thickness]);
            };
          };
        };
      };
    };

    // Cutout
    cutout_width = 60;
    cutout_depth = 60;
    translate([(plate_width-cutout_width)/2, (plate_depth-cutout_depth)/2, -plate_thickness]) {
      rounded_flat_cube([cutout_width, cutout_depth, plate_thickness*3], 4);
    };

    // Screwholes
    translate([
      (plate_width - switch_width)/2,
      (plate_depth - switch_depth)/2,
      0]) {
      for (pos=cat(standoffs_5mm, standoffs_3mm)) {
        translate([pos[0], pos[1], -0.1]) {
          cylinder(
            h=standoff_mm+pcb_thickness+plate_thickness+1,
            d=standoff_hole);
        };
      };
    };

    // Mount locks
    translate([
      0,
      plate_depth/2,
      0]) {
        for (y = [-1, 1]) {
          for(x = [0, 1]) {
            ypos = y * mount_spacing/2;
            xpos = x * plate_width;
            translate([xpos, ypos, -plate_thickness]) {
              rotate([0, 0, x*180+90]) {
                union() {
                  translate([-$m3_screw_dia/2, -$m3_screw_dia, 0])
                    cube([$m3_screw_dia, $m3_screw_dia*2, plate_thickness*3]);
                  translate([0, -$m3_screw_dia, 0])
                    cylinder(d=$m3_screw_dia, h=plate_thickness*3);
                };
              };
            };
          };
        };
    }; // end mount locks
  };
};

module pi_plate(
  pi_plate_width,
  tab_screw_height,
  tab_width,
  plate_thickness=default_plate_thickness) {
  // Pi plate, oriented in long direction on x.
  plate_depth = pi_plate_width;
  plate_width = 90;
  pi_depth = 56;
  pi_width = 85;
  pi_shift_x = 0;
  pi_shift_y = 1.5;

  pi_standoff_pos = [
    [3.5, 3.5],
    [3.5, pi_depth-3.5],
    [58+3.5, pi_depth-3.5],
    [58+3.5, 3.5]
  ];

  pi_standoff_peg = [pi_standoff_pos[0], pi_standoff_pos[2]];
  pi_standoff_screw = [pi_standoff_pos[1], pi_standoff_pos[3]];
  pi_standoff_dia = 5;
  pi_standoff_peg_dia = 2.5;
  pi_standoff_peg_len = 3;
  pi_standoff_screw_dia = 3;
  pi_standoff_len = 2.5;

  tab_thick = plate_thickness;
  tab_screw_dia = 3;

  corner_roundoff = 3;
  front_tab_depth = 5;

  sd_notch_depth = 16;
  sd_notch_width = 10;

  thermal_width = 50;
  thermal_depth = 30;

  translate([front_tab_depth, 0, 0])
  difference() {
    union() {
      translate([corner_roundoff, 0, 0])
        cube([plate_width-corner_roundoff, plate_depth, plate_thickness], center=false);
      for(y = [0, 1]) {
        hull() {
          roundoff_round = corner_roundoff + y * (plate_depth - 2 * corner_roundoff);
          translate([corner_roundoff-front_tab_depth, roundoff_round, 0])
            cylinder(r=corner_roundoff, h=plate_thickness);
          translate([corner_roundoff, (plate_depth - 1)/2, 0])
            cube([1, 1, plate_thickness]);
          translate([corner_roundoff, y*(plate_depth - 1), 0])
            cube([1, 1, plate_thickness]);
        };
      }
      translate([0, corner_roundoff, 0])
        cube([
          corner_roundoff*2,
          plate_depth-2*corner_roundoff,
          plate_thickness]);
      // Standoffs
      translate([
        (plate_width - pi_width)/2 + pi_shift_x,
        (plate_depth - pi_depth)/2 + pi_shift_y,
        plate_thickness]) {
        for (pos=pi_standoff_pos) {
          translate([pos[0], pos[1], 0])
            cylinder(d=pi_standoff_dia, h=pi_standoff_len);
        };
        for (pos=pi_standoff_peg) {
          translate([pos[0], pos[1], pi_standoff_len]) {
            cylinder(d=pi_standoff_peg_dia, h=pi_standoff_peg_len);
          };
        };
      };
      // Front tabs
      for(y = [0, plate_depth-tab_width]) {
        translate([plate_width, y, plate_thickness]) {
          rotate([0, 0, 90])
          difference() {
            union() {
              cube([tab_width, tab_thick, tab_screw_height]);
              translate([tab_width/2, 0, tab_screw_height])
                rotate([-90, 0, 0])
                cylinder(d=tab_width, h=tab_thick);
            };
            // Hole in cylinder
              translate([tab_width/2, -tab_thick, tab_screw_height])
                rotate([-90, 0, 0])
                cylinder(d=tab_screw_dia, h=tab_thick*3);
          };
        };
      };
    };
    translate([
      (plate_width - pi_width)/2 + pi_shift_x,
      (plate_depth - pi_depth)/2 + pi_shift_y,
      0]) {
      // Screw holes
      for (pos=pi_standoff_screw) {
        translate([pos[0], pos[1], -0.1]) {
          cylinder(d=pi_standoff_screw_dia,
            h=pi_standoff_peg_len+pi_standoff_len+plate_thickness+1);
        };
      };
    };
    // Notch for SD card
    translate([
      -sd_notch_width,
      (plate_depth-sd_notch_depth)/2+pi_shift_y,
      -plate_thickness])
      rounded_flat_cube([
        sd_notch_width*2,
        sd_notch_depth,
        plate_thickness*3], 2);
    // Thermal opening
    translate([
      (plate_width - thermal_width)/2 + pi_shift_x,
      (plate_depth - thermal_depth)/2 + pi_shift_y,
      -plate_thickness]) {
        rounded_flat_cube([thermal_width, thermal_depth, plate_thickness*3], 3);
      }
  };
};

module cluster_frame(
  frame_width,
  frame_height,
  frame_thickness,
  plate_width,
  tab_screw_height,
  tab_width,
  side_slot_length,
  mnt_screw_spacing,
  plate_thickness=default_plate_thickness) {

  pi_module_spacing = 24;
  pi_module_count = 4;
  slot_width = tab_width;
  slot_clearance = 3;
  slot_extra = 0.5;

  difference() {
    union() {
      cube([frame_width, frame_height, frame_thickness]);
    };

    // All the Space for pis
    pi_cutout_width = plate_width - 2*slot_width;
    pi_cutout_height = pi_module_spacing * pi_module_count + slot_clearance;
    cutout_x = (frame_width - pi_cutout_width)/2;
    cutout_y = (frame_height - pi_cutout_height)/2;
    translate([cutout_x, cutout_y, -frame_thickness]) {
      cube([pi_cutout_width, pi_cutout_height, frame_thickness*3]);
      for(i = [0:pi_module_count-1]) {
        // Each slot
        translate([-(slot_width+slot_extra), i*pi_module_spacing+slot_clearance-slot_extra, 0])
          cube([plate_width+2*slot_extra, plate_thickness+2*slot_extra, frame_thickness*3]);
        // Screw holes
        tab_screw_dia = 3;
        for(x = [-tab_width/2, plate_width-3*tab_width/2]) {
          translate([x,
            i*pi_module_spacing + plate_thickness + tab_screw_height + slot_clearance,
            0])
            union() {
              cylinder(d=$m3_screw_dia, h=frame_thickness*3);
              // Hex for nuts
              translate([0, 0, 2*frame_thickness-$m3_hex_depth])
                rotate([0, 0, 90])
                  hexagon3d($m3_hex_width/2, $m3_hex_depth*2);
            };
        };
      };
    };

    // Other slots (power/switch support)
    slot_inset = 2;
    slot_hold_width = 3;
    for (x = [0, 1]) {
      translate([
        slot_inset + (frame_width - 2 * slot_inset) * x,
        (frame_height - side_slot_length)/2 - slot_extra,
        -frame_thickness + (x*frame_thickness*3)])
        rotate([0, x*-180, 0])
          union() {
            // Holding slot (backplate edges)
            cube([
              plate_thickness+slot_extra,
              side_slot_length+2*slot_extra,
              frame_thickness*3]);
            // Cutout
            translate([-2*slot_inset, slot_hold_width+slot_extra, 0])
              cube([
                slot_inset*4.5,
                side_slot_length-2*slot_hold_width,
                frame_thickness*3]);
          };
    };

    // Slot inset screws
    hex_side_depth = 10;
    side_hole_dia = $m3_screw_dia+0.2;
    side_hole_len = 23;
    side_hole_inset = (frame_height - side_slot_length)/2;
    for (x = [-1, 1]) {
      for (y = [0, 1]) {
        translate([
          x*(frame_width/2-side_hole_len)+frame_width/2,
          side_hole_inset + y*(frame_height-side_hole_inset*2),
          frame_thickness/2])
        rotate([0, 90*x, 0])
          union() {
            cylinder(d=side_hole_dia, h=side_hole_len+2);
            rotate([0, 0, 90])
              hexagon3d($m3_hex_width/2, hex_side_depth);
          };
      };
    };

    // Mounting screws to top/bottom
    hex_depth = 3;
    mnt_hole_dia = $m3_screw_dia;
    //mnt_hole_spacing = plate_width-4*slot_width;
    mnt_hole_spacing = mnt_screw_spacing;
    mnt_hole_len = (frame_height-pi_cutout_height)/2;
    for (x = [-1, 1]) {
      for (y = [0, 1]) {
        translate([
          frame_width/2 + x * mnt_hole_spacing/2,
          (y*frame_height-mnt_hole_len)+mnt_hole_len,
          frame_thickness/2]) {
          rotate([90+180*y, 0, 0]) {
            translate([0, 0, -(mnt_hole_len+0.1)])
            union() {
              cylinder(d=mnt_hole_dia, h=mnt_hole_len*2);
              rotate([0, 0, 90])
                hexagon3d($m3_hex_width/2, hex_depth);
            };
          };
        };
      };
    };

    // 80mm fan mounting screws?
    fan_screw_shift = 5;
    translate([
      frame_width/2,
      frame_height/2 + fan_screw_shift,
      -frame_thickness]) {
      //cube([80, 80, 10], center=true);
      fan_screw_centers = 71.5; // from specs
      fan_screw_hole = 5.5; // from specs, though different specs differ
      for (x = [-1, 1]) {
        for (y = [-1, 1]) {
          translate([x * fan_screw_centers/2, y * fan_screw_centers/2, 0])
            cylinder(d=fan_screw_hole, h=frame_thickness*3);
        };
      };
    };
  };
};

module top_panel(
  panel_width,
  panel_length,
  screw_spacing_length,
  screw_spacing_width,
  is_top=0,
  plate_thickness=default_plate_thickness) {

  // Width in x, length in y, supports at front/back

  screw_pos_x = [-screw_spacing_width/2, screw_spacing_width/2];
  feet_pos_x = [-panel_width/2 + $m3_head_dia*1.25, panel_width/2 - $m3_head_dia*1.25];
  screw_feet_x = (is_top == 1) ? screw_pos_x : cat(screw_pos_x, feet_pos_x);


  module rounded_slot (slot_width, slot_length) {
    union() {
      cylinder(d=slot_width, h=plate_thickness*3);
      translate([0, -slot_width/2, 0])
        cube([slot_length, slot_width, plate_thickness*3]);
      translate([slot_length, 0, 0])
        cylinder(d=slot_width, h=plate_thickness*3);
    };
  };

  difference() {
    union() {
      cube([panel_width, panel_length, plate_thickness]);
      // Screw supports, feet
      translate([panel_width/2, panel_length/2, 0]) {
        for(x = screw_feet_x) {
          for(y = [-screw_spacing_length/2, screw_spacing_length/2]) {
            translate([x, y, plate_thickness/2])
              linear_extrude(
                height=(is_top == 1) ? plate_thickness*2.2 : plate_thickness*3.2, scale=0.75)
                rotate([0, 0, 90])
                  hexagon($m3_head_dia*0.9);
          };
        };
      };
      // Reinforcement ribs -- longways
      rib_width=$m3_head_dia*0.8;
      for (x = [-1, 1]) {
        translate([
          x * screw_spacing_width/2 + panel_width/2,
          (panel_length-screw_spacing_length)/2,
          plate_thickness]) {
            linear_extrude(height=plate_thickness*1.2, scale=[0.5, 1])
              translate([-rib_width/2, 0, 0])
                square([rib_width, screw_spacing_length]);
          };
      };
    };

    // screw holes
    translate([panel_width/2, panel_length/2, 0]) {
      for(x = [-screw_spacing_width/2, screw_spacing_width/2]) {
        for(y = [-screw_spacing_length/2, screw_spacing_length/2]) {
          translate([x, y, -plate_thickness]) {
            cylinder(d=$m3_screw_dia+0.3, h=plate_thickness*6);
            translate([0, 0, plate_thickness*3]) {
              cylinder(d=$m3_head_dia, h=$m3_head_depth*2);
            };
          };
        };
      };
    };

    // Airflow slots
    airflow_slot_width = 3;
    airflow_area_y = floor(
      (screw_spacing_length - $m3_head_dia*2 - airflow_slot_width*2)/
        (airflow_slot_width*2)) * airflow_slot_width*2;
    // TODO: round to even number of slots
    airflow_margin_y = (panel_length - airflow_area_y)/2;
    airflow_area_x = screw_spacing_width - airflow_slot_width*3;
    airflow_slot_spacing = airflow_slot_width * 2;
    airflow_margin_x = (panel_width - airflow_area_x)/2;
    // additional slots
    airflow_side_length = airflow_margin_x/2;
    airflow_side_x = [airflow_margin_x/4, panel_width - 3*airflow_margin_x/4];

    for(o = [0:airflow_slot_spacing:airflow_area_y]) {
      translate([
        airflow_margin_x,
        airflow_margin_y + o,
        -plate_thickness]) {
        rounded_slot(airflow_slot_width, airflow_area_x);
      };
      for (x = airflow_side_x) {
        translate([x, airflow_margin_y + o, -plate_thickness]) {
          rounded_slot(airflow_slot_width, airflow_side_length);
        };
      };
    };
  };
};

module _rounded_line(dims) {
  union() {
    translate([dims[1]/2, dims[1]/2, 0])
      cylinder(d=dims[1], h=dims[2]);
    translate([dims[0]-dims[1]/2, dims[1]/2, 0])
      cylinder(d=dims[1], h=dims[2]);
    translate([dims[1]/2, 0, 0])
      cube([dims[0]-dims[1], dims[1], dims[2]]);
  };
};

module _slot_filled_angle(dims, slot_width, slot_spacing) {
  if (dims[0] < dims[1]) {
    ang = atan(dims[1]/dims[0]);
    for (x = [slot_spacing:slot_spacing:dims[0]]) {
      slot_len = x/cos(ang);
      translate([dims[0]-x, 0, 0]) {
        rotate([0, 0, ang]) {
          _rounded_line([slot_len, slot_width, dims[2]]);
        };
      };
    };
  } else {
    ang = atan(dims[0]/dims[1]);
    for (x = [slot_spacing:slot_spacing:dims[0]]) {
      slot_len = x/cos(ang);
      translate([dims[0]-x, 0, 0]) {
        rotate([0, 0, ang]) {
          _rounded_line([slot_len, slot_width, dims[2]]);
        };
      };
    };
  };
};

module switch_plate_cover(
  frame_height,
  frame_depth,
  screw_distance_vertical_from_edge,
  screw_distance_horizontal,
  opening_width,
  plate_thickness=default_plate_thickness,
) {
  // Supports parallel to y axis, along x axis
  // y dimension is vertical
  cover_thickness=20;
  difference() {
    union() {
      cube([frame_depth, frame_height, cover_thickness]);
    };

    // Front to back cutout
    cutout_extra = 4;
    translate([
      -cutout_extra/2,
      (frame_height-opening_width)/2,
      -plate_thickness]) {
      cube([
        frame_depth+cutout_extra,
        opening_width,
        cover_thickness]);
    };

    // Widening cutout
    screw_edge_dist_hz = (frame_depth - screw_distance_horizontal)/2;
    opening_more_wide = 104;
    translate([
      screw_edge_dist_hz*2,
      (frame_height-opening_more_wide)/2,
      -plate_thickness]) {
      cube([
        frame_depth-screw_edge_dist_hz*4,
        opening_more_wide,
        cover_thickness]);
    };

    // Mount holes
    #for (x=[-1, 1]) {
      for (y=[-1, 1]) {
        translate([
          x*(screw_distance_horizontal/2)+frame_depth/2,
          y*(frame_height/2-screw_distance_vertical_from_edge)+frame_height/2,
          -0.1]) {
            cylinder(d=$m3_screw_dia, h=cover_thickness*2);
            translate([0, 0, 6])
              cylinder(d=$m3_head_dia+1, h=cover_thickness);
        };
      };
    };

    // Cooling slots
    for (q = [0, 1, 2, 3]) {
      translate([
        frame_depth/2,
        frame_height/2,
        cover_thickness-plate_thickness*2]) {
        rotate([0, 0, 90*q]) {
          // Fill parallel lines at an angle
          // TODO
        };
      };
    };
  };
};

build_target = "piplate";

if (build_target == "switchplate") {
  switch_backplate(
    side_plate_width,
    cluster_piece_spacing,
    cluster_frame_thickness/2);
} else if (build_target == "piplate") {
  pi_plate(pi_plate_width, tab_screw_height, tab_width);
} else if (build_target == "frame") {
  cluster_frame(
    cluster_frame_width,
    cluster_frame_height,
    cluster_frame_thickness,
    pi_plate_width,
    tab_screw_height,
    tab_width,
    side_plate_width,
    mnt_screw_spacing);
} else if (build_target == "top") {
  top_panel(
    cluster_frame_width,
    cluster_piece_spacing+12,
    cluster_piece_spacing,
    mnt_screw_spacing,
    is_top=1);
} else if (build_target == "bottom") {
  top_panel(
    cluster_frame_width,
    cluster_piece_spacing+12,
    cluster_piece_spacing,
    mnt_screw_spacing);
} else if (build_target == "switchcover") {
  switch_plate_cover(
    cluster_frame_height,
    cluster_piece_spacing+cluster_frame_thickness,
    (cluster_frame_height-side_plate_width)/2,
    cluster_piece_spacing,
    side_plate_width-4
  );
}

//_slot_filled_angle([50, 20, 4], 3, 8);
