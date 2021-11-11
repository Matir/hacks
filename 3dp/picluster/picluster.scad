use <../library/rounded.scad>;
use <../library/hex.scad>;

// Curve setups
$fs = 0.1;
$fa = 5;

// Common variables
default_plate_thickness = 2.5;
pi_plate_width = 70;
cluster_frame_width = 90;
cluster_frame_height = 110;
cluster_frame_thickness = 8;
tab_screw_height = 4;
tab_width = 7;
side_plate_width = 100;

// Useful functions
function cat(L1, L2) = [for(L=[L1, L2], a=L) a];

module switch_backplate(plate_width, plate_thickness=default_plate_thickness) {
  // main plate
  switch_width = 94.2;
  switch_depth = 89.0;
  plate_depth = 100;
  standoff_mm = 3;
  standoff_hole = 3;
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

  sd_notch_depth = 16;
  sd_notch_width = 10;

  thermal_width = 50;
  thermal_depth = 30;

  difference() {
    union() {
      translate([corner_roundoff, 0, 0])
        cube([plate_width-corner_roundoff, plate_depth, plate_thickness], center=false);
      for(y = [corner_roundoff, plate_depth-corner_roundoff]) {
        translate([corner_roundoff, y, 0])
          cylinder(r=corner_roundoff, h=plate_thickness);
      }
      translate([0, corner_roundoff, 0])
        cube([
          corner_roundoff*2,
          plate_depth-2*corner_roundoff,
          plate_thickness]);
      // Standoffs
      translate([
        (plate_width - pi_width)/2 + pi_shift_x,
        (plate_depth - pi_depth)/2,
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
      (plate_depth - pi_depth)/2,
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
    translate([-sd_notch_width, (plate_depth-sd_notch_depth)/2, -plate_thickness])
      rounded_flat_cube([sd_notch_width*2, sd_notch_depth, plate_thickness*3], 2);
    // Thermal opening
    translate([
      (plate_width - thermal_width)/2 + pi_shift_x,
      (plate_depth - thermal_depth)/2,
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
  plate_thickness=default_plate_thickness) {

  pi_module_spacing = 24;
  pi_module_count = 4;
  slot_width = tab_width;
  slot_clearance = 3;

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
        translate([-slot_width, i*pi_module_spacing+slot_clearance, 0])
          cube([plate_width, plate_thickness+0.2, frame_thickness*3]);
        // Screw holes
        tab_screw_dia = 3;
        for(x = [-tab_width/2, plate_width-3*tab_width/2]) {
          translate([x,
            i*pi_module_spacing + plate_thickness + tab_screw_height + slot_clearance,
            0])
            cylinder(d=3, h=frame_thickness*3);
        };
      };
    };

    // Other slots (power/switch support)
    slot_inset = 2;
    slot_hold_width = 2.5;
    for (x = [0, 1]) {
      translate([
        slot_inset + (frame_width - 2 * slot_inset) * x,
        (frame_height - side_slot_length)/2,
        -frame_thickness + (x*frame_thickness*3)])
        rotate([0, x*-180, 0])
          union() {
            cube([plate_thickness+0.2, side_slot_length, frame_thickness*3]);
            translate([-2*slot_inset, slot_hold_width, 0])
              cube([
                slot_inset*3,
                side_slot_length-2*slot_hold_width,
                frame_thickness*3]);
          };
    };

    // Slot inset screws
    hex_side_depth = 10;
    hex_across = 5;
    side_hole_dia = 3;
    side_hole_len = 22;
    side_hole_inset = (frame_height - side_slot_length)/2;
    for (x = [0, 1]) {
      for (y = [0, 1]) {
        translate([
          x*(frame_width-side_hole_len*1.9)+side_hole_len*0.95,
          side_hole_inset + y*(frame_height-side_hole_inset*2),
          frame_thickness/2])
        rotate([0, -90+90*x*2, 0])
          #union() {
            cylinder(d=side_hole_dia, h=side_hole_len);
            rotate([0, 0, 90])
              hexagon3d(hex_across/2, hex_side_depth);
          };
      };
    };

    // Mounting screws to top/bottom
    hex_depth = 3;
    mnt_hole_dia = 3;
    mnt_hole_spacing = plate_width-4*slot_width;
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
                hexagon3d(hex_across/2, hex_depth);
            };
          };
        };
      };
    };
  };
};

//switch_backplate(side_plate_width);

//pi_plate(pi_plate_width, tab_screw_height, tab_width);

cluster_frame(
  cluster_frame_width,
  cluster_frame_height,
  cluster_frame_thickness,
  pi_plate_width,
  tab_screw_height,
  tab_width,
  side_plate_width);
