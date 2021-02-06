include <settings.scad>

use <threadlib/threadlib.scad>

module desk_bracket(width, thickness) {
  thread_turns = clamp_body_thickness / thread_pitch * 2;
  union() {
    // top of table
    translate([0, 0, clamp_body_thickness+clamp_open_thickness])
    cube([
      clamp_depth+clamp_body_thickness,
      clamp_width,
      clamp_body_thickness], false);
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
