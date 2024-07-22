
// =======
// OPTIONS
// =======

draw_cube = 1; //if draw_cube ==1 characters are rounded to fill all faces (repeating)
draw_letters = 0;
N_cubes=5;

//characters=rep(39,6*3); //options = ["all","random", ["A","B","C","E","F"], "none"]
//characters = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"];
characters = [
    ["D", "A", "B", "C", "E", "F"],
    ["A", "B", "Y", "A", "B", "Y"],
    ["V", "R", "S", "T", "W", "X"],
    ["E", "F", "G", "H", "I", "J"],
    ["Y", "Z", "A", "B", "C", "D"],
];


// HIDDEN

eps=0.01;
size=20;
expand=1.35; 
letter_depth=1;
tol = 0.1;
gap=3; //gap between cubes in X or Y direction

// =========
// VARIABLES
// =========
letterset = ["A","B","C","D","E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S","T","U","V","W","X","Y","Z","1","2","3","4","5","6","7","8","9"];
fontset = rep("Arial Rounded MT Bold:style=Regular",len(letterset));

characterlist = concat(t(concat([letterset,rep(10,len(letterset)),fontset])),
    [["\U00266B",15,"Apple Symbols:style=Regular"]], //MUSIC NOTES
    [["\U002666",15,"Apple Symbols:style=Regular"]], //DIAMOND
    [["\U0025CF",10,"Apple Symbols:style=Regular"]], //CIRCLE
    [["\U0025FC",15,"Apple Symbols:style=Regular"]], //SQUARE
    [["\U002665",13,"Apple Symbols:style=Regular"]], //HEART (39)
    [["\U002658",14,"Apple Symbols:style=Regular"]], //KNIGHT
    [["\U002639",15,"Apple Symbols:style=Regular"]], //FROWN
    [["\U00263A",15,"Apple Symbols:style=Regular"]], //SMILE
    [["\U002605",15,"Apple Symbols:style=Regular"]], //STAR
    [["\U002600",15,"Apple Symbols:style=Regular"]], //SUN
    [["\U002602",15,"Apple Symbols:style=Regular"]], //UMBRELLA
    [["\U002601",15,"Apple Symbols:style=Regular"]]); //CLOUD


char2 = (is_list(characters) && len(characters) > 0 && is_list(characters[0])) ? [for (i=[0:len(characters)]) each characters[i]] : characters;

letters=
    characters=="all" ? [for(i=[0:(6*N_cubes-1)]) restart(i,len(characterlist)-1)] :
    characters=="random" ? [for (i=rands(0,len(characterlist),6*N_cubes)) round(i)] :
    characters=="none" ? [] :
    [for (i=[0:ceil(6*N_cubes/len(char2))]) each char2];    

// =========
// FUNCTIONS
// =========
    
// checks if x >= X and if so reduces it by X (recursive)
function restart(x,X) =
    x > X ? restart(x-X,X) :
    x;

// repeats M N times: rep(1,3) -> [1,1,1]
function rep(M,N) = [for (i=[0:(N-1)]) M];

// transposes matrix M: t(M[4x2]) -> M[2x4]
function t(M) = [for(j=[0:(dim(M)[1]-1)]) [for(i=[0:(dim(M)[0]-1)]) M[i][j]]];

// dim(M) gives the dimensions of 2D array (M)
function dim(M) = [len(M), len(M[0])];

// flattens a list by removing the outer list: flatten([[1,2],[3,4]]) -> [1,2,3,4]
function flatten(l) = [ for (a = l) for (b = a) b ] ;

// ADD a code for random letters
//echo([for (i=rands(0,25,6)) alphabet[round(i)]]);

module nice_cube(x,f) {
    translate([x/2,x/2,x/2]) intersection() {
        translate([-x/2,-x/2,-x/2]) cube([x,x,x]);
        rotate([45,0,0]) translate(f*[-x/2,-x/2,-x/2]) cube(f*[x,x,x]);
        rotate([0,45,0]) translate(f*[-x/2,-x/2,-x/2]) cube(f*[x,x,x]);
        rotate([0,0,45]) translate(f*[-x/2,-x/2,-x/2]) cube(f*[x,x,x]);
    }
}

module minktext(t,x=10,ft,r=tol) {
    if(is_num(t)) {
        minkowski() {
            text(characterlist[t][0],
                size=characterlist[t][1],
                valign="center",
                halign="center",font=characterlist[t][2]);
            circle(r);
        }
    } else {
        minkowski() {
            text(t,size=x,valign="center",halign="center",font=ft);
            circle(r);
        }
    }
}

if(draw_letters == 1) {
    for(j=[0:(N_cubes-1)]) {
        for(i=[0:5]) {
            translate([i*size + size/2,-j * size - size/2,0])
                linear_extrude(letter_depth-tol) minktext(letters[6*j + i],r=2*tol);
        }
    }
}

if(draw_cube == 1) {
    for(j=[0:(N_cubes-1)]) {
        translate([0,j*(size+gap),0]) difference() {
            nice_cube(size,expand);
            translate([size/2,letter_depth-eps,size/2])
                rotate([90,0,0]) linear_extrude(letter_depth+eps) minktext(letters[j*6]);
            translate([size-letter_depth+eps,size/2,size/2])
                rotate([90,0,90]) linear_extrude(letter_depth+eps) minktext(letters[1+j*6]);
            translate([size/2,size-letter_depth+eps,size/2])
                rotate([90,0,180]) linear_extrude(letter_depth+eps) minktext(letters[2+j*6]);
            translate([letter_depth-eps,size/2,size/2])
                rotate([90,0,270]) linear_extrude(letter_depth+eps) minktext(letters[3+j*6]);
            translate([size/2,size/2,size-letter_depth+eps])
                rotate([0,0,0]) linear_extrude(letter_depth+eps) minktext(letters[4+j*6]);
            translate([size/2,size/2,letter_depth-eps])
                rotate([180,0,0]) linear_extrude(letter_depth+eps) minktext(letters[5+j*6]);
        }
    }
}

