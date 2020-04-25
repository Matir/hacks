// All dimensions in mm!

// Rough model for the pi4 for cases
module pi4() {
  pcb_with_holes();
  headers();
  translate([80, 9, 0])
    usb_stack();
  translate([80, 27, 0])
    usb_stack();
  translate([78, 45.75, 0])
    ethernet_jack();
  translate([3.5+7.7, 2, 0])
    usb_c();
  // pi4 cpu
  color("grey")
    translate([25.75+3.5, 32.5, 2.8])
    cube([12, 12, 2.4], center=true);
  translate([3.5+7.7+14.8, 1.75, 0])
    micro_hdmi();
  translate([3.5+7.7+14.8+13.5, 1.75, 0])
    micro_hdmi();
  translate([3.5+7.7+14.8+13.5+7+7.5, 6.25, 0])
    trrs();
}

module pcb_with_holes() {
  color("green") {
    difference() {
      cube([85, 56, 1.6]);
      translate([0, 0, -0.2]) {
        translate([3.5, 3.5, 0])
          cylinder(r=1.25, h=2, $fn=16);
        translate([3.5, 49+3.5, 0])
          cylinder(r=1.25, h=2, $fn=16);
        translate([58+3.5, 3.5, 0])
          cylinder(r=1.25, h=2, $fn=16);
        translate([58+3.5, 49+3.5, 0])
          cylinder(r=1.25, h=2, $fn=16);
      }
    }
  }
}

module headers() {
  color("black")
    translate([3.5+29-52/2, 50, 1.6])
    cube([52, 5, 8.5]);
}

module usb_stack() {
  color("blue") {
    translate([0, 0, 9.6])
      cube([17.5, 14.5, 16], center=true);
  }
}

module ethernet_jack() {
  color("grey") {
    translate([0, 0, 13.6/2+1.6])
      cube([21.2, 15.9, 13.6], center=true);
  }
}

module usb_c() {
  color("red") {
    translate([0, 0, 3.3/2+1.6])
      cube([9, 8, 3.3], center=true);
  }
}

module micro_hdmi() {
  color("orange") {
    translate([0, 0, 3/2+1.6])
      cube([6.5, 7.5, 3], center=true);
  }
}

module trrs() {
  color("purple") {
    translate([0, 0, 3+1.6]) {
      cube([7, 12.5, 6], center=true);
      translate([0, -7.5, 0])
        rotate([90, 0, 0])
        cylinder(d=6, h=2.5, center=true, $fn=12);
    }
  }
}

pi4();
