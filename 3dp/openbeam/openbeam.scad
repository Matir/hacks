
// Just a rough approximation to use for negative space!
module openbeam(size=15, length=15, slot=3) {
    difference() {
        cube([size, size, length], center=true);
        for(i=[0:3]) {
            rotate([0, 0, i*90])
            translate([(size-slot)/2, 0, 0])
            cube([slot, slot, length], center=true);
        }
    }
}

// XY Rounded Edge Cube
module roundedcube(dims, radius=1, $fn=20) {
    minkowski() {
        cube([dims[0]-2*radius, dims[1]-2*radius, dims[2]/2], center=true);
        cylinder(r=radius, h=dims[2]/2, center=true, $fn=$fn);
    }
}

module endcap() {
    difference() {
        roundedcube([18.3, 18.3, 10], radius=3);
        translate([0, 0, 3])
            openbeam(size=15.2, slot=2.8);
    }
}

endcap();