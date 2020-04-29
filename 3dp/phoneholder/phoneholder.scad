model_width = 95;
model_height = 100;
model_depth = 20;
wall_thickness = 4;

module body(width, depth, height) {
    union(){
    translate([width/2-depth/2, 0, 0])
        cylinder(h=height, r=depth/2);
    translate([-(width/2-depth/2), 0, 0])
        cylinder(h=height, r=depth/2);
    translate([-(width-depth)/2, -depth/2, 0])
        cube([width-depth, depth, height]);
    }
}

module cradle(width, depth, height) {
    cutout_width = width/3.2;
    difference() {
        // outer body
        body(width, depth, height);
        
        // inner body
        translate([0, 0, wall_thickness])
            body(width-wall_thickness/2, depth-wall_thickness, height);
        
        // front cutout
        translate([-cutout_width/2, wall_thickness-depth, 0])
            cube([cutout_width, depth, height]);
    
        // notch   
        translate([0, -depth/2, height])
            rotate([0, 45, 0])
            cube([cutout_width*2, depth, cutout_width*2], center=true);
    }
}

cradle(model_width, model_depth, model_height);