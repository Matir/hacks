$fs=0.2;

module probe_tray(
    n_probes=10,
    needle_radius=1.5,
    body_radius=4.25,
    needle_length=28,
    body_length=65,
    wall_size=3,
    body_gap=2) {
  total_width = wall_size*2 + body_radius*2*n_probes + body_gap*(n_probes-1);
  total_depth = body_length + needle_length + 2*wall_size;
  total_height = 2*body_radius + wall_size;

  module probe() {
    union() {
      translate([body_radius, 0, body_radius])
      rotate([-90, 0, 0])
        union() {
          cylinder(r=body_radius, h=body_length);
          translate([0, 0, body_length]) {
            cylinder(r=needle_radius, h=needle_length);
            translate([-needle_radius, -body_radius, 0])
              cube([needle_radius*2, body_radius, needle_length]);
          }
        }
    }
  }

  difference() {
    // Main body
    color("blue", 0.25)
      cube([total_width, total_depth, total_height]);
    // Probe cutouts
    for(i=[0:n_probes-1]) {
      x_offset = i*(body_radius*2+body_gap);
      translate([wall_size+x_offset, wall_size, wall_size])
        #probe();
    }
    // Finger access
    translate([wall_size, wall_size, wall_size+body_radius])
      cube([total_width-2*wall_size, body_length, body_radius]);
    // Deeper in the middle
    translate([wall_size, wall_size+body_length/4, wall_size])
      cube([total_width-2*wall_size, body_length/2, total_height]);
  }
}

probe_tray();
