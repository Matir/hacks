use <rounded.scad>

$fn = $preview ? 16 : 24;

module small_tray() {
  pocket=25;
  gap=2;
  w=pocket*3+gap*4;
  difference() {
    rounded_flat_cube([w, w, 7], 5, $fn=16);
    union() {
      for (x=[0:2]) {
        for (y=[0:2]) {
          translate([x*(pocket+gap)+gap, y*(pocket+gap)+gap, 3.5])
            rounded_cube([pocket, pocket, 10], 5, $fn=16);
          magnet_d = 12.5;
          translate([x*(pocket+gap)+gap+magnet_d, y*(pocket+gap)+gap+magnet_d, 0])
            cylinder(d=magnet_d, h=2.2, $fn=32);
        }
      }
    }
  }
}

small_tray();
