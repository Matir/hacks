module controlbox_bottom(boxdim=[96, 96, 40], wall=2) {
  bottom_thick = wall;
  inner_h = boxdim[2];
  pi_pos = [boxdim[0]-85+wall/2, boxdim[1]-7-56+wall, 2];

  module corner_support(outer_d=5, inner_d=2) {
    support_h = inner_h-3;
    translate([0, 0, bottom_thick])
    difference() {
      union() {
        translate([outer_d/2, outer_d/2, 0])
          cylinder(d=outer_d, h=support_h, $fn=20);
        cube([outer_d/2, outer_d/2, support_h]);
        translate([outer_d/2, 0, 0])
          cube([outer_d/2, outer_d/2, support_h]);
        translate([0, outer_d/2, 0])
          cube([outer_d/2, outer_d/2, support_h]);
      }
      translate([outer_d/2, outer_d/2, support_h/2])
        cylinder(d=inner_d, h=support_h/2, $fn=12);
    }
  }

  module pi_openings() {
    eth_w = 16;
    eth_h = 14;
    usb_w = 15;
    usb_h = 16;
    pcb_h = 2;
    translate([80, 0, bottom_thick]) {
      translate([0, 10.25-eth_w/2, pcb_h])
        cube([22, eth_w, eth_h]);
      // usb
      translate([0, 29-usb_w/2, pcb_h])
        cube([22, usb_w, usb_h]);
      // usb
      translate([0, 47-usb_w/2, pcb_h])
        cube([22, usb_w, usb_h]);
    }
  }

  module pi_stands() {
    x_pos = [3.5, 3.5+58];
    y_pos = [3.5, 3.5+49];
    h = 4;
    for (x = x_pos) {
      for (y = y_pos) {
        translate([x, y, bottom_thick-h]) {
          cylinder(d=5, h=h, $fn=12);
          translate([0, 0, h])
            cylinder(d=2, h=2, $fn=12);
        }
      }
    }
  }

  module dc_dc_holder() {
    l = 52;
    w = 26;
    difference() {
      cube([l+4, w+4, 4]);
      translate([2, 2, 0])
        cube([l, w, 6]);
    }
  }

  module dimmer_holder() {
    l = 30;
    w = 24;
    difference() {
      cube([l+2, w+4, 6]);
      translate([0, 2, 4])
        cube([l, w, 4]);
      translate([2, 2, 0])
        cube([l-4, w, 6]);
    }
  }

  // Outer enclosure
  difference() {
    cube([boxdim[0]+2*wall, boxdim[1]+2*wall, boxdim[2]+bottom_thick]);
    translate([wall, wall, bottom_thick+0.01])
      cube(boxdim);
    translate(pi_pos)
      pi_openings();
    // dc jack
    translate([boxdim[0], 15, bottom_thick+24])
      rotate([0, 90, 0])
      cylinder(d=8, h=wall*3, $fn=16);

    // dimmer opening
    translate([-wall, wall+6+8.5, bottom_thick+6.5+4])
      rotate([0, 90, 0])
      cylinder(d=8, h=wall*3, $fn=16);
  }

  // Corner supports
  translate([wall, wall, 0])
    corner_support();
  translate([wall+boxdim[0], wall, 0])
    rotate([0, 0, 90])
    corner_support();
  translate([wall+boxdim[0], wall+boxdim[1], 0])
    rotate([0, 0, 180])
    corner_support();
  translate([wall, wall+boxdim[1], 0])
    rotate([0, 0, 270])
    corner_support();

  // Pi supports
  translate(pi_pos)
    pi_stands();

  // DCDC
  translate([boxdim[0]-58, wall+2, bottom_thick])
    dc_dc_holder();

  // dimmer
  translate([wall, 6, bottom_thick])
    dimmer_holder();
}

intersection() {
  controlbox_bottom();
  cube([100, 100, 10]);
}
