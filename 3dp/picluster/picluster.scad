use <../library/rounded.scad>;

// Curve setups
$fs = 0.1;
$fa = 5;

// Common variables
default_plate_thickness = 2.5;

// Useful functions
function cat(L1, L2) = [for(L=[L1, L2], a=L) a];

module switch_backplate(plate_thickness=default_plate_thickness) {
  // main plate
  switch_width = 94.2;
  switch_depth = 89.1;
  plate_width = 100;
  plate_depth = 100;
  standoff_mm = 4;
  standoff_hole = 3;
  pcb_thickness = 1.6;

  standoffs_5mm_base_dia = 8;
  standoffs_5mm_dia = 4.8;
  standoffs_5mm = [[7, 10.2], [7, switch_depth-17]];
  standoffs_3mm_base_dia = 6;
  standoffs_3mm = [[switch_width-33.5, 4.4], [switch_width-7, switch_depth-16.8]];

  difference() {
    union() {
      cube([plate_width, plate_depth, plate_thickness], center=false);
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

module pi_plate(plate_thickness=default_plate_thickness) {
  // Pi plate, oriented in long direction on x.
  plate_depth = 70;
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
  pi_standoff_len = 4;

  tab_width = 7;
  tab_thick = plate_thickness;
  tab_screw_dia = 3;
  tab_screw_height = 4;

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

//switch_backplate();
pi_plate();
