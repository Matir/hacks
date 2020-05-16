module clip(opening=6.2, width=10, cliplen=6.6, thickness=1.5) {
    union() {
        // back piece
        translate([-cliplen, 0, 0])
        cube([cliplen*3, thickness, width]);
        // curve at back
        translate([cliplen*2, -opening/2, width/2]) {
            difference() {
                cylinder(h=width, d=opening+2*thickness, center=true, $fn=32);
                cylinder(h=width, d=opening, center=true, $fn=32);
                translate([-cliplen/2, 0, 0])
                cube([cliplen, opening+2*thickness, width], center=true);
            }
        }
        // front
        rot_angle = 12;
        offset_x = cos(rot_angle)*(cliplen/2);
        offset_y = -sin(rot_angle)*(cliplen/2-thickness/4);
        echo("offset_x=", offset_x, ", offset_y=", offset_y);
        translate([
            (cliplen*2)-offset_x+thickness/2,
            -(opening+offset_y+thickness/2),
            width/2]) {
            rotate([0, 0, -rot_angle]) {
                cube([cliplen, thickness, width], center=true);
            }
        }
        // rounding on end
        translate([
            cliplen+offset_x/2-thickness/4,
            -opening*1.5+offset_y+thickness/4,
            width/2]) {
            difference() {
                cylinder(h=width, d=opening+2*thickness, center=true, $fn=32);
                cylinder(h=width, d=opening, center=true, $fn=32);
                translate([cliplen/2, 0, 0])
                cube([cliplen, opening+2*thickness, width], center=true);
                translate([-cliplen/2, -opening/6, 0])
                cube([cliplen, cliplen+thickness, width], center=true);
            }
        }
    }
}

module drive_holder(length=111, width=31, depth=15, thickness=1.5) {
    // back piece
    translate([0, 0, depth/2+thickness])
        cube([length, thickness, width-depth]);
    // curved edge
    module edge() {
        difference() {
            cylinder(h=length, d=(depth+thickness*2), center=true, $fn=32);
            cylinder(h=length, d=depth, center=true, $fn=32);
            translate([depth/2+thickness, 0, 0])
                cube([depth+thickness*2, depth+thickness*2, length], center=true);
        }
    }
    // bottom curve
    translate([length/2, depth/2+thickness, depth/2+thickness])
        rotate([0, 90, 0])
        rotate([0, 0, 180])
        edge();
    // top curve
    translate([length/2, depth/2+thickness, width-depth/2+thickness])
        rotate([0, 90, 0])
        edge();
}

translate([102, 0, 9])
    clip(opening=6.5, width=16);
drive_holder();