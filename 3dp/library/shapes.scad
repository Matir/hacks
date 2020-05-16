module truncated_pyramid(bottom=[2,2], top=[1,1], height=1) {
  delta_x = (bottom[0]-top[0])/2;
  delta_y = (bottom[1]-top[1])/2;
  polyhedron(points=[
      [0, 0, 0],
      [bottom[0], 0, 0],
      [bottom[0], bottom[1], 0],
      [0, bottom[1], 0],
      [delta_x, delta_y, height],
      [top[0]+delta_x, delta_y, height],
      [top[0]+delta_x, top[1]+delta_y, height],
      [delta_x, top[1]+delta_y, height],
    ],
    faces=[
      [0, 1, 2, 3],  // bottom
      [4, 5, 1, 0],  // front
      [7, 6, 5, 4],  // top
      [5, 6, 2, 1],  // right
      [6, 7, 3, 2],  // back
      [7, 4, 0, 3]   // left
    ]
  );
}
