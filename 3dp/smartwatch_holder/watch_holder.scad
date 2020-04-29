charger_dia = 26;
cable_dia = 4;
charger_thick = 7;
watch_dia = 46;
bracket_width = 30.5;
watch_thick = 11.5;

module charger(charger_dia, charger_thick, cable_dia) {
    union() {
        cylinder(charger_thick, r=charger_dia/2, center=true, $fn=72);
        rotate([90, 0, 0])
            translate([0, 0, 50/2])
            cylinder(50, r=cable_dia/2, center=true, $fn=16);
        translate([0, -50/2, -cable_dia/2])
            cube([cable_dia, 50, charger_thick/2], center=true);
    }
}

module watch(watch_dia, watch_thick, bracket_width) {
    union() {
        cylinder(watch_thick, r=watch_dia/2, center=true, $fn=72);
        translate([watch_dia/2+2, 0, -1])
            cube([20, bracket_width, watch_thick+2], center=true);
        translate([-watch_dia/2-2, 0, -1])
            cube([20, bracket_width, watch_thick+2], center=true);
    }
}

module carveout() {
    translate([0, 0, charger_thick/2])
    union() {
        charger(charger_dia, charger_thick, cable_dia);
        translate([0, 0, (watch_thick+charger_thick)/2])
            watch(watch_dia, watch_thick, bracket_width);
    }
}

module bracket() {
    thickness = watch_thick+charger_thick;
    difference() {
        translate([0, 0, thickness/2])
            difference() {
                cylinder(thickness, r=watch_dia/2+8, center=true);
                translate([0, 20, 0])
                cube([80, 40, thickness], center=true);
            }
        carveout();
    }
}

bracket();
//watch(watch_dia,watch_thick,bracket_width);