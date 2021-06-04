#!/bin/bash

cd /app

# Sass compiling
if test -d /app/src/sass ; then
  npx sass --watch /app/src/sass:/app/srv/css &
fi

if test -d /app/src/css ; then
  ln -s /app/src/css* /app/srv/css
fi

ln -s /app/src/*.html /app/srv/

if test -d /app/src/js ; then
  npx babel /app/src/js --presets @babel/preset-react --watch --copy-files --out-dir /app/srv/js &
fi

npx http-server /app/srv -p ${PORT:-8080}
