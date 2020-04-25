module slot(dim=[25, 75, 20], wall=1.5) {
  difference() {
    outerdim = [
      dim[0] + wall*2,
      dim[1] + wall*2,
      dim[2] + wall
    ];
    cube(outerdim);
    translate([wall, wall, wall])
      cube(dim);
  }
}

module tray(dim=[25, 75, 20], wall=1.5, nslots=3) {
  for (i=[0:nslots-1]) {
    translate([(dim[0]+wall)*i, 0, 0])
      slot(dim=dim, wall=wall);
  }
}

tray();
