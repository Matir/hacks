FROM debian:bullseye

RUN apt-get update && \
  apt-get install -yy \
    g++ cmake ninja-build libx11-dev \
    libxcursor-dev libxi-dev \
    libgl1-mesa-dev libfontconfig1-dev \
    git python2 python3 \
    libharfbuzz-dev

RUN mkdir -p /build /build/deps

WORKDIR /build/deps

RUN git clone --depth=1 https://chromium.googlesource.com/chromium/tools/depot_tools.git
RUN git clone --depth=1 -b aseprite-m81 https://github.com/aseprite/skia.git

ENV PATH="/build/deps/depot_tools:${PATH}"

RUN ln -s /usr/bin/python2 /build/deps/depot_tools/python

WORKDIR /build/deps/skia

RUN python tools/git-sync-deps

RUN gn gen out/Release-x64 --args="is_debug=false is_official_build=true skia_use_system_expat=false skia_use_system_icu=false skia_use_system_libjpeg_turbo=false skia_use_system_libpng=false skia_use_system_libwebp=false skia_use_system_zlib=false"

RUN ninja -C out/Release-x64 skia modules

WORKDIR /build

RUN git clone --recursive https://github.com/aseprite/aseprite.git
RUN mkdir -p /build/aseprite/build

WORKDIR /build/aseprite/build

RUN cmake \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DLAF_BACKEND=skia \
  -DSKIA_DIR=/build/deps/skia \
  -DSKIA_LIBRARY_DIR=/build/deps/skia/out/Release-x64 \
  -DSKIA_LIBRARY=/build/deps/skia/out/Release-x64/libskia.a \
  -G Ninja \
  ..

RUN ninja aseprite
