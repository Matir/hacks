sd_shaft_dia = 10;
sd_body_dia = 28;
sd_body_height = 25;

c_width = 18;
c_depth = 10;

body_w = 80;
body_d = 50;
body_h = 40;
body_r = 5;

$fn=0;
$fa=6;
$fs=0.3;

difference() {
    // main body
    translate([body_r, body_r, body_r]) {
        minkowski() {
            cube([body_w-2*body_r, body_d, body_h-2*body_r]);
            sphere(r=body_r, $fs=0.4);
        }
    };

    // make the back flat
    translate([-body_r, body_d, -body_r])
        cube([body_w+2*body_r, body_r*2, body_h+2*body_r]);

    // holder of calipers
    translate([body_r*1.5, body_d-body_r-c_depth, 0]) {
        union() {
            translate([0, 0, -body_r])
                cube([c_width, c_depth, body_h+2*body_r]);
            translate([c_width/2, c_depth/2, body_h-body_r])
                linear_extrude(body_r, scale=1.3)
                    square(size=[c_width, c_depth], center=true);
        };
    };

    // holder of screwdriver
    translate([body_w-22, body_d-32, 0]) {
        union() {
            translate([0, 0, body_h-body_r])
                cylinder(d1=sd_body_dia, d2=sd_body_dia+body_r, h=body_r);
            translate([0, 0, body_h-sd_body_height])
                cylinder(d=sd_body_dia, h=body_h, $fs=0.1);
            translate([0, 0, -body_r]) {
                cylinder(d=sd_shaft_dia, h=body_h+2*body_r);
            translate([0, 0, body_h-sd_body_height+0.01])
                cylinder(d1=sd_shaft_dia, d2=sd_shaft_dia*1.5, h=body_r);
            translate([-sd_shaft_dia/2, -body_d, 0])
                cube([sd_shaft_dia, body_d, body_h+2*body_r]);
            }
        };
    };
}