drive_width = 83.4;
drive_thick = 13.3;
drive_length = 130;
vesa_size = 100;
back_thick = 3;
back_height = 115;

$fs=1;

module drive_box() {
  color("green")
  union() {
    cube([drive_width, drive_thick, drive_length]);
    // usb plug opening
    cable_width = 15;
    for(i = [14, drive_width-14-cable_width])
      translate([i, (drive_thick-9)/2, -10])
        cube([cable_width, 9, 10]);
  }
}

module backplate() {
  vesa_r = 4.5/2;
  back_offset = (back_height-vesa_size)/2;
  difference() {
    cube([40, back_thick, back_height]);

    for (i = [back_offset, back_height-back_offset])
      translate([back_offset, back_thick*2, i])
        rotate([90, 0, 0])
          cylinder(r=vesa_r, h=back_thick*3);
  }
}

module main_body() {
  body_thick = drive_thick+back_thick*2;
  translate([-body_thick, 0, 0])
  difference() {
    union() {
      translate([body_thick*5/4, 0, 0])
        cube([drive_width-body_thick/2, body_thick, back_height]);
      translate([body_thick/4+2, 0, 0])
        cube([body_thick*3/4, body_thick/2, back_height]);
      translate([drive_width+body_thick*3/4, body_thick/2, 0])
        cylinder(d=body_thick, h=back_height);
      translate([body_thick*5/4, body_thick/2, 0])
        cylinder(d=body_thick, h=back_height);
    }
    #translate([(body_thick-back_thick+1)*3/8, (body_thick-back_thick)/2+back_thick, 0])
      cylinder(d=body_thick-back_thick, h=back_height);
  }
}

module front_cutout() {
  corner_radius = drive_width/4;
  union() {
    translate([drive_width/3, 0, 10])
      cube([drive_width/3, back_thick*3, back_height]);
    translate([(drive_width-(drive_width/3+2*corner_radius))/2, 0, back_height-corner_radius])
      difference() {
          cube([drive_width/3+2*corner_radius, back_thick*3, back_height/3]);
          for (i=[0, drive_width/3+2*corner_radius])
          #translate([i, back_thick*2, 0])
            rotate([90, 0, 0])
            cylinder(r=corner_radius, h=back_thick*3);
      }
  }
}

module drive_mount() {
  difference() {
    union() {
      backplate();
      translate([30, 0, 0])
        main_body();
    }
    // drive box
    translate([30, back_thick, back_thick])
      drive_box();
    // front cutout
    translate([30, back_thick+drive_thick, 0])
      front_cutout();
  }
}

mirror([1, 0, 0])
  drive_mount();
