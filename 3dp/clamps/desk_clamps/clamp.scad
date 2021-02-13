include <settings.scad>

use <threadlib/threadlib.scad>
use <hex.scad>

module desk_bracket(width, thickness) {
  thread_turns = clamp_body_thickness / thread_pitch * 2;
  union() {
    // top of table
    translate([0, 0, clamp_body_thickness+clamp_open_thickness])
    difference() {
      cube([
        clamp_depth+clamp_body_thickness,
        clamp_width,
        clamp_body_thickness], false);
      translate([clamp_depth/2+clamp_body_thickness, clamp_width/2, -0.1])
      union() {
        cylinder(d=6.3, h=13.5, $fn=24);
        linear_extrude(height=4.6)
          hexagon(r=6);
      };
    };
    // vertical rise
    cube([clamp_body_thickness,
      clamp_width,
      clamp_open_thickness+clamp_body_thickness], false);
    // under table
    difference() {
      cube([
        clamp_depth+clamp_body_thickness,
        clamp_width,
        clamp_body_thickness], false);
      translate([clamp_depth/2+clamp_body_thickness, clamp_width/2, 0])
        tap(screw_thread, turns=thread_turns);
    };
  };
};

desk_bracket();
