mode=1;

tolerance=.2;

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
   tab_height = 4;
   union() {
       difference() {
         // Main body
         linear_extrude(height=height) {
             hexagon(diameter/2);
         }
         linear_extrude(height=height-lens_height*2) {
             hexagon(diameter/2-5);
         }
         linear_extrude(height=height-lens_height) {
             hexagon(diameter/2-10);
         }
         hexagon_each(diameter/2) {
             // Cable holes
             translate([0, -3, 3])
                cube([10, 6, 10], center=true);
             // Tab holes
             translate([diameter/6, -3, tab_height])
                dovetail(width1=8+tolerance, width2=6+tolerance, length=6, height=6);
         }
         translate([0, 0, height/2])
         tri_each(plate_size/2*.95) {
            cube([plate_size*.2+tolerance*2, 3+tolerance*2, height], center=true);
         }
       }
       // tabs that stick out
       hexagon_each(diameter/2) {
           translate([-diameter/6, 3, tab_height])
             difference() {
                 dovetail(width1=6-tolerance, width2=8-tolerance, length=6, height=6-tolerance*2.5);
                 // Cut in center
                 translate([0, 0, 3])
                     cube([2, 6, 6], center=true);
                 // Tapering at front
                 translate([4, 2.5, 3])
                 rotate([0, 0, 30])
                     cube([2.8, 6, 6], center=true);
                 translate([-4, 2.5, 3])
                 rotate([0, 0, -30])
                     cube([2.8, 6, 6], center=true);
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
        tri_each(diameter/2*.95) {
            translate([(diameter*.2-clip_size)/2, 0, 0])
                cube([clip_size, clip_size, clip_height*2/3], center=true);
            translate([-(diameter*.2-clip_size)/2, 0, 0])
                cube([clip_size, clip_size, clip_height*2/3], center=true);
            translate([0, 0, -clip_height/2])
                cube([diameter*.2, clip_size, clip_height/3], center=true);
        }
    }
}

if (mode == 0) {
    tile(15, 90, plate_size=80);
    // Just for display
    translate([0, 0, 30]) color("green")
        front_plate(80);
} else if (mode == 1) {
    tile(15, 90, plate_size=80);
} else if (mode == 2) {
    front_plate(80);
} else if (mode == 3) {
    intersection(){
        tile(15, 90, plate_size=80);
        translate([45,0,10])
        cube([20,60,20], center=true);
    }
}