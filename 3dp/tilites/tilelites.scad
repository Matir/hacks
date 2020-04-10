tolerance=.25;

module hexagon(r){
    polygon(points=[
                [r,(r*(tan(30)))],
                [0,(r*(2/sqrt(3)))],
                [-r,(r*(tan(30)))],
                [-r,-(r*(tan(30)))],
                [0,-(r*(2/sqrt(3)))], 
                [r,-(r*(tan(30)))]
    ]);     
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
module tri_each(r, offset=30) {
    for (a = [0:120:359]) {
        rotate([0, 0, a+offset]) {
            translate([0, r, 0]) {
                children();
            }
        }
    }
}

// Dovetail joint element
module dovetail(width1=8, width2=10, length=8, height=10) {
    linear_extrude(height=height) {
        polygon(points=[
            [-width1/2, -length/2],
            [width1/2, -length/2],
            [width2/2, length/2],
            [-width2/2, length/2],
        ]);
    }
}

module tile(height, diameter, lens_height=1, plate_size=80) {
   union() {
       difference() {
         // Main body
         linear_extrude(height=height) {
             hexagon(diameter/2);
         }
         linear_extrude(height=height-lens_height) {
             hexagon(diameter/2-5);
         }
         hexagon_each(diameter/2) {
             translate([0, -3, 3])
                cube([8,6,6], center=true);
             translate([diameter/6, -3, 0])
                dovetail(width1=8+tolerance, width2=6+tolerance, length=6, height=6);
         }
         translate([0, 0, height/2])
         tri_each(plate_size/2*.9) {
            cube([plate_size*.2+tolerance*2, 3+tolerance*2, height], center=true);
         }
       }
       // tabs that stick out
       hexagon_each(diameter/2) {
           translate([-diameter/6, 3, 0])
             difference() {
                 dovetail(width1=6-tolerance, width2=8-tolerance, length=6, height=6);
                 translate([0, 0, 3])
                     cube([1.5, 6, 6], center=true);
                 translate([4, 2.5, 3])
                 rotate([0, 0, 20])
                     cube([2, 6, 6], center=true);
                 translate([-4, 2.5, 3])
                 rotate([0, 0, -20])
                     cube([2, 6, 6], center=true);
             }
       }
   }
}

module front_plate(diameter, clip_height=8, thickness=2) {
    union() {
        linear_extrude(height=thickness) {
            union() {
                difference() {
                    hexagon(diameter/2);
                    hexagon(diameter/2*.8);
                }
                difference() {
                    hexagon(diameter/2*.45);
                    hexagon(diameter/2*.25);
                }
                tri_each(diameter*.35) {
                    square([diameter*.08, diameter/4], center=true);
                }
            }
        }
        clip_size=3;
        translate([0, 0, -thickness])
        tri_each(diameter/2*.9) {
            translate([(diameter*.2-clip_size)/2, 0, 0])
                cube([clip_size, clip_size, clip_height*2/3], center=true);
            translate([-(diameter*.2-clip_size)/2, 0, 0])
                cube([clip_size, clip_size, clip_height*2/3], center=true);
            translate([0, 0, -clip_height/2])
                cube([diameter*.2, clip_size, clip_height/3], center=true);
        }
    }
}

tile(10, 90, plate_size=80);

// Just for display
translate([0, 0, 20]) color("green")
    front_plate(80);