width=65;
step_length=10;
step_height=.5;
num_steps=6;

module steps() {
    for(i = [0:num_steps-1]) {
        translate([0, step_length*i, 0])
        cube([width, step_length, (i+1)*step_height], center=false);
    }
}

steps();