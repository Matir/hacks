include <settings.scad>

use <threadlib/threadlib.scad>
use <hex.scad>

module clamp_bolt() {
  turns = clamp_width/thread_pitch;
  union() {
    bolt(screw_thread, turns);
    translate([0, 0, -clamp_body_thickness])
      linear_extrude(height=clamp_body_thickness)
      hexagon(thread_dia*1.4/2);
  };
};

clamp_bolt();
