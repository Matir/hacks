FROM debian:buster

RUN mkdir /workspace

COPY 010answers /tmp/010answers

ADD https://www.sweetscape.com/download/010EditorLinux64Installer.tar.gz \
  /tmp/010Editor.tar.gz

RUN tar zxf /tmp/010Editor.tar.gz -C /tmp

RUN /tmp/010EditorLinux64Installer --mode silent --response-file /tmp/010answers

VOLUME /workspace
VOLUME /tmp/.X11-unix
VOLUME /tmp/.Xauthority

CMD ["/opt/010editor/010editor"]
