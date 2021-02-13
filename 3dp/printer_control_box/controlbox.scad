module controlbox_bottom(boxdim=[96, 96, 44], wall=2) {
  bottom_thick = wall;
  inner_h = boxdim[2];
  pi_pos = [boxdim[0]-85+wall, boxdim[1]-6-56+wall, 2];

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
    eth_w = 17;
    eth_h = 15;
    usb_w = 16;
    usb_h = 17;
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
            cylinder(d=2, h=3, $fn=12);
        }
      }
    }
  }

  module dc_dc_holder() {
    l = 26.2;
    w = 26.2;
    difference() {
      cube([l+4, w+4, 4]);
      translate([2, 2, 0])
        cube([l, w, 6]);
    }
    // feet
    translate([2.1, 2.1, 0]) {
      for(pos=[[2.2, 2.2], [2.2+21.1, 2.2], [2.2+21.1, 2.2+21.1]]) {
        translate([pos[0], pos[1], 0]) {
          cylinder(d=3.6, h=2, $fn=12);
          translate([0, 0, 2])
            cylinder(d=2, h=2, $fn=12);
        }
      }
    }
  }

  module relay_holder() {
    l = 26;
    w = 31;
    difference() {
      cube([l+4, w+2, 14]);
      translate([2, 2, 10])
        cube([l, w, 6]);
    }
  }

  module dimmer_holder() {
    l = 31;
    w = 25;
    difference() {
      cube([l+2, w+4, 6]);
      translate([0, 2, 4])
        cube([l, w, 4]);
      translate([2, 2, 0])
        cube([l-4, w, 6]);
    }
  }

  module vents(l, h, vent_w=3, vent_s=6) {
    spacing = vent_w + vent_s;
    thick = wall*3;
    translate([vent_w/2, wall/2, 0]) {
      for (i = [0:l/spacing]) {
        translate([i*spacing, 0, 0]) {
          // bottom
          rotate([90, 0, 0])
            cylinder(d=vent_w, h=thick, center=true, $fn=12);
          // in between
          translate([-vent_w/2, -thick/2, 0])
            cube([vent_w, thick, h-vent_w]);
          // top
          translate([0, 0, h-vent_w])
            rotate([90, 0, 0])
              cylinder(d=vent_w, h=thick, center=true, $fn=12);
        }
      }
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
    translate([boxdim[0], wall+14, bottom_thick+28])
      rotate([0, 90, 0])
      cylinder(d=8.5, h=wall*3, $fn=16);

    // dimmer opening
    translate([-wall, wall+13, bottom_thick+6.5+5])
      rotate([0, 90, 0])
      cylinder(d=8.2, h=wall*3, $fn=16);

    // dc wires out
    translate([boxdim[0], 32, bottom_thick+28])
      rotate([0, 90, 0])
      cylinder(d=8, h=wall*3, $fn=16);

    // stop button
    translate([-wall, boxdim[1]-40, bottom_thick+32])
      rotate([0, 90, 0])
      cylinder(d=16.2, h=wall*3, $fn=25);

    // ventilation
    for(i=[0, boxdim[1]+wall])
      translate([7+wall, i, 16+bottom_thick])
        vents(l=boxdim[0]-15, h=boxdim[2]-25);

    // usb opening
    // Serial board
    translate([-wall, boxdim[1]-23+wall, bottom_thick+18])
      rotate([0, 90, 0])
      hull() {
        cylinder(d=6, h=wall*4);
        translate([0, 10, 0])
          cylinder(d=6, h=wall+4);
      }

    // camera cable cut
    translate([boxdim[0], boxdim[1]+wall-38-24, bottom_thick+boxdim[2]-4])
      cube([wall*3, 24, 6]);
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
  translate([boxdim[0]-32, wall-1, bottom_thick])
    dc_dc_holder();

  // dimmer
  translate([wall, 5, bottom_thick])
    dimmer_holder();

  // relay
  translate([boxdim[0]-(32+28), wall-2, bottom_thick])
    relay_holder();

  // reinforce rear
  translate([boxdim[0], wall+5, boxdim[2]-4])
    union() {
      cube([2, boxdim[1]-10, 2]);
      rotate([0, 45, 0])
        cube([2*sqrt(2), boxdim[1]-10, 2*sqrt(2)]);
    }
}

module controlbox_top(boxdim=[96, 96], wall=2) {
  module corner_support(d=6, h=3) {
    translate([d/2, d/2, -h]) {
      cylinder(d=d, h=h, $fn=12);
      translate([-d/2, -d/2, 0])
        cube([d, d/2, h]);
      translate([-d/2, -d/2, 0])
        cube([d/2, d, h]);
    }
  }

  module slats(edge=8, width=3, spacing=4) {
    slat_len = boxdim[0]+2*wall-edge*2;
    interval = (width+spacing)/sin(45);
    offs = slat_len - floor(slat_len/interval)*interval;
    echo(interval);
    echo(offs);
    for (i = [1:slat_len/interval]) {
      hull() {
        translate([edge, interval*i+edge, 0])
          cylinder(d=width, h=wall*3, $fn=12);
        translate([interval*i+edge, edge, 0])
          cylinder(d=width, h=wall*3, $fn=12);
      }
      hull() {
        translate([boxdim[0]-edge+2*wall, boxdim[1]-interval*i-edge+offs, 0])
          cylinder(d=width, h=wall*3, $fn=12);
        translate([boxdim[0]-interval*i-edge+offs, boxdim[1]-edge+2*wall, 0])
          cylinder(d=width, h=wall*3, $fn=12);
      }
    }
  }

  difference() {
    union() {
      // Flat
      cube([boxdim[0]+wall*2, boxdim[1]+wall*2, wall]);
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
      difference() {
        translate([wall, wall, -wall])
          cube([boxdim[0], boxdim[1], wall]);
        translate([wall*2, wall*2, -wall*2])
          cube([boxdim[0]-wall*2, boxdim[1]-wall*2, wall*2]);
      }
    }
    translate([wall+5/2, wall+5/2, -wall*2])
      cylinder(d=3, h=wall*5, $fn=12);
    translate([wall+boxdim[0]-5/2, wall+5/2, -wall*2])
      cylinder(d=3, h=wall*5, $fn=12);
    translate([wall+boxdim[0]-5/2, wall+boxdim[1]-5/2, -wall*2])
      cylinder(d=3, h=wall*5, $fn=12);
    translate([wall+5/2, wall+boxdim[1]-5/2, -wall*2])
      cylinder(d=3, h=wall*5, $fn=12);

    translate([0, 0, -wall])
      slats();
  }
}

//intersection() {
//  controlbox_bottom();
//  cube([100, 100, 10]);
//}

//intersection() {
//    controlbox_bottom();
//    cube([10, 100, 100]);
//}

//intersection() {
//    controlbox_bottom();
//    cube([100, 60, 100]);
//}

controlbox_bottom();
//translate([0, -10, 42])
//  rotate([180, 0, 0])
//  controlbox_top();
