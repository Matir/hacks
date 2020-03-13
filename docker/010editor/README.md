010Editor
=========


Build
-----

To create the image `matir/010editor`, execute the following command in the
`010editor` folder:

    docker build -t matir/010editor .


Run
---

Then, when starting your 010editor container, you will want to share the X11
socket file as a volume so that the 010Editor X windows can be displayed on your
Xorg server. You may also need to run command `xhost +` on the host.

    $ docker pull matir/010editor

    $ docker run -it \
        -h $(hostname) \
        -u ${USER}:$(id -g -n) \
        --name 010editor \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        -v ${PROJECT_PATH}:/workspace \
        -v ${HOME}/.Xauthority:/tmp/.Xauthority:ro \
        -e DISPLAY=unix$DISPLAY \
        -e XAUTHORITY=/tmp/.Xauthority \
        matir/010editor
