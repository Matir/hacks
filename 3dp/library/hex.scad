// Module hexagon
// R is radius across flat sides, not points
// points are (2/sqrt(3))*r
module hexagon(r){
    polygon(points=[
                [r,(r*(tan(30)))],
                [0,(r*(2/sqrt(3)))],
                [-r,(r*(tan(30)))],
                [-r,-(r*(tan(30)))],
                [0,-(r*(2/sqrt(3)))],
                [r,-(r*(tan(30)))]
    ]);
};

module hexagon3d(r, h) {
  linear_extrude(height=h)
    hexagon(r);
}

// Repeat something on each side
module hexagon_each(r, offset=30) {
    for (a = [0:60:359]) {
        rotate([0, 0, a+offset]) {
            translate([0, r, 0]) {
                children();
            }
        }
    }
}

// Repeat something in 3 positions
module hexagon_tri_each(r, offset=30) {
    for (a = [0:120:359]) {
        rotate([0, 0, a+offset]) {
            translate([0, r, 0]) {
                children();
            }
        }
    }
}
