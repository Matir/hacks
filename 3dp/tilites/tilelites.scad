mode=2;

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

module tile(height, diameter, lens_height=1, plate_size=80, clip_width=10, clip_depth=8, clip_spacing=3, clip_thickness=3) {
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
             // Clips
             clip_inset=4;
             for(i = [-1:2:1]) {
                 translate([16*i, -(clip_spacing+(clip_inset/2)), clip_depth/2]) {
                     translate([0, clip_inset, -(clip_depth-clip_thickness)/2])
                     cube([clip_width, clip_inset, clip_thickness], center=true);
                     cube([clip_width, clip_inset, clip_depth], center=true);
                     translate([0, clip_thickness/2+1, clip_depth/2-.5])
                     cube([clip_width, 1, 1], center=true);
                 }
             }
         }
         // top slots for front plate
         translate([0, 0, height/2])
         tri_each(plate_size/2*.95) {
            cube([plate_size*.2+tolerance*2, 3+tolerance*2, height], center=true);
         }
       }
   }
}

module front_plate(diameter, clip_height=13, thickness=2) {
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
                    square([diameter*.05, diameter/4], center=true);
                }
            }
        }
        clip_size=3;
        translate([0, 0, -thickness])
        tri_each(diameter/2*.95) {
            difference() {
                union() {
                    for (i = [-1:2:1]) {
                    translate([i*(diameter*.2-clip_size)/2, 0, -clip_height/4])
                        cube([clip_size-tolerance, clip_size-tolerance, clip_height], center=true);
                    }
                    translate([0, 0, -(clip_height-clip_size)])
                        cube([diameter*.2-tolerance, clip_size-tolerance, clip_size], center=true);
                    translate([0, 0, clip_size/2])
                        cube([diameter*.2-tolerance, clip_size-tolerance, clip_size/2], center=true);
                } // clip union
                cutout_sz = clip_size*1.75;
                translate([0, 0, -(clip_height-clip_size/2)])
                rotate([0, 45, 0])
                    cube([cutout_sz, clip_size*2, cutout_sz], center=true);
            } // clip difference
        }
    }
}

module clip(width=10, depth=8, thickness=2, spacing=3.1) {
    rib = 0.5;
    tol = tolerance;
    linear_extrude(height=width-tol) {
        polygon(points=[
          [0, 0],
          [thickness+rib-tol, rib],
          [thickness+rib-tol, rib*2-tol],
          [thickness-tol, rib*2],
          [thickness-tol, depth-thickness+tol],
          [2*spacing+thickness+tol*2, depth-thickness+tol],
          [2*spacing+thickness+tol*2, rib*2],
          [2*spacing+thickness-rib+tol*2, rib*2-tol],
          [2*spacing+thickness-rib+tol*2, rib],
          [2*spacing+2*thickness, 0],
          [2*spacing+2*thickness, depth],
          [0, depth]
        ]);
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
    // Edge test
    intersection(){
        tile(15, 90, plate_size=80);
        translate([45,0,10])
        cube([20,60,20], center=true);
    }
} else if (mode == 4) {
    clip();
} else if (mode == 5) {
    // Half test
    intersection(){
        tile(15, 90, plate_size=80);
        translate([0,50,10])
        cube([100,100,20], center=true);
    }
}