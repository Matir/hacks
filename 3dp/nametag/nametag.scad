current_color = "ALL";
// current_color = "SkyBlue";
// current_color = "white";
// current_color = "black";
$fn=64;

module multicolor(c) {
    if (current_color == "ALL" || current_color == c) {
        color(c)
            children();
    }
}

module nametag(name) {
    module tagtext(h=2) {
        text(name, size=24, font="Heyam:style=Regular", $fn=64);
    }
    union() {
        multicolor("SkyBlue")
        translate([0, 0, 2])
            linear_extrude(2)
            tagtext();
        multicolor("white")
        union() {
            translate([-4.0, 12, 0])
            difference() {
                union() {
                    cylinder(h=2, d=8.8);
                    translate([0, -4.4, 0])
                        cube([8.8, 8.8, 2]);
                }
                translate([0, 0, -0.25])
                    cylinder(h=2.5, d=5.5);
            }
            linear_extrude(2)
            minkowski() {
                circle(r=2.25, $fn=64);
                tagtext();
            }
        }
    }
}

nametag("Davey");