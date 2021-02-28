module diffuser(ring_dia=34, wall_thick=0.5, height=32, taper=3) {
  difference() {
    cylinder(d1=ring_dia+wall_thick*2, d2=ring_dia+wall_thick*2-taper, h=height, $fa=3, $fs=0.5);
    cylinder(d1=ring_dia, d2=ring_dia-taper, h=height-wall_thick, $fa=3, $fs=0.5);
  }
}

diffuser();
