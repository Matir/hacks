// Cube with rounded corners in x-y dimensions.
// Corner order: front left, back left, back right, front right
module rounded_cube(dims, corner_radii, $fn=undef) {
  fn = $fn ? $fn : 20;
  h = dims[2];
  _corner_radii = is_list(corner_radii) ? corner_radii : [
        corner_radii, corner_radii, corner_radii, corner_radii];
  corners = [
    _corner_radii[0] ? _corner_radii[0] : 0,
    _corner_radii[1] ? _corner_radii[1] : 0,
    _corner_radii[2] ? _corner_radii[2] : 0,
    _corner_radii[3] ? _corner_radii[3] : 0,
  ];
  hull() {
    // Front left
    translate([corners[0], corners[0], 0])
      cylinder(r=corners[0], h=h, $fn=fn);
    // Back left
    translate([corners[1], dims[1]-corners[1], 0])
      cylinder(r=corners[1], h=h, $fn=fn);
    // Back right
    translate([dims[0]-corners[2], dims[1]-corners[2], 0])
      cylinder(r=corners[2], h=h, $fn=fn);
    // Front right
    translate([dims[0]-corners[3], corners[3], 0])
      cylinder(r=corners[3], h=h, $fn=fn);
    // Fill to guarantee extension to corner if a fillet is 0
    #linear_extrude(h)
      polygon([
        [corners[0], corners[0]],
        [corners[1], dims[1]-corners[1]],
        [dims[0]-corners[2], dims[1]-corners[2]],
        [dims[0]-corners[3], corners[3]]
      ]);
  }
}

module _rounded_cube_examples() {
  rounded_cube([10, 20, 1], [3, 3, 0, 0]);

  translate([20, 0, 0])
  rounded_cube([10, 20, 1], [1, 2, 3, 4]);

  translate([-20, 0, 0])
  rounded_cube([10, 20, 1], [1]);

  translate([0, 25, 0])
  rounded_cube([6, 6, 2], 2);
}
