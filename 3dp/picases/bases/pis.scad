// All dimensions in mm!

pi4_length = 85;
pi4_width = 56;

// Rough model for the pi4 for cases
module pi4(tol=0) {
  pcb_with_holes(tol=tol);
  headers(tol=tol);
  translate([80, 9, 0])
    usb_stack(tol=tol);
  translate([80, 27, 0])
    usb_stack(tol=tol);
  translate([78, 45.75, 0])
    ethernet_jack(tol=tol);
  translate([3.5+7.7, 2, 0])
    usb_c(tol=tol);
  // pi4 cpu
  color("grey")
    translate([25.75+3.5, 32.5, 2.8])
    cube([12, 12, 2.4], center=true);
  translate([3.5+7.7+14.8, 1.75, 0])
    micro_hdmi(tol=tol);
  translate([3.5+7.7+14.8+13.5, 1.75, 0])
    micro_hdmi(tol=tol);
  translate([3.5+7.7+14.8+13.5+7+7.5, 6.25, 0])
    trrs(tol=tol);
  translate([1.5, 22, 0])
    microsd(tol=tol);
}

module pcb_with_holes(tol=0) {
  color("green") {
    translate([-tol, -tol, 0])
    difference() {
      cube([pi4_length+2*tol, pi4_width+2*tol, 1.6]);
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

module headers(tol=0) {
  color("black")
    translate([3.5+29-52/2-tol, 50-tol, 1.6])
    cube([52+2*tol, 5+2*tol, 8.5+tol]);
}

module usb_stack(tol=0) {
  color("blue") {
    translate([0, 0, 9.6])
      cube([17.5+2*tol, 14.5+2*tol, 16+tol], center=true);
  }
}

module ethernet_jack(tol=0) {
  color("grey") {
    translate([0, 0, 13.6/2+1.6])
      cube([21.2+2*tol, 15.9+2*tol, 13.6+tol], center=true);
  }
}

module usb_c(tol=0) {
  color("red") {
    translate([0, 0, 3.3/2+1.6])
      cube([9.4+2*tol, 8+2*tol, 3.3+tol], center=true);
  }
}

module micro_hdmi(tol=0) {
  color("orange") {
    translate([0, 0, 3/2+1.6])
      cube([7.4+2*tol, 7.5+2*tol, 3+tol], center=true);
  }
}

module trrs(tol=0) {
  color("purple") {
    translate([0, 0, 3+1.6]) {
      cube([7+2*tol, 12.5+2*tol, 6+tol], center=true);
      translate([0, -7.5, 0])
        rotate([90, 0, 0])
        cylinder(d=6+2*tol, h=2.5, center=true, $fn=12);
    }
  }
}

module microsd(tol=0) {
  color("white") {
    // bottom of pcb
    translate([-tol, -tol, -(1.8+tol)]) {
      cube([11.4+2*tol, 12+2*tol, 1.8+tol]);
    }
  }
}
