FROM debian:buster

RUN apt-get update && \
  apt-get install -yy \
    asciidoc bash binutils bzip2 flex git-core g++ gcc util-linux gawk \
    help2man intltool libelf-dev zlib1g-dev make libncurses5-dev libssl-dev \
    patch perl-modules python2-dev unzip wget gettext xsltproc

ARG OPENWRT_VERSION=v19.07.4
ENV OPENWRT_DIR=/opt/openwrt

RUN git clone --depth 1 --branch ${OPENWRT_VERSION} \
  https://git.openwrt.org/openwrt/openwrt.git \
  ${OPENWRT_DIR}

WORKDIR ${OPENWRT_DIR}

RUN chmod 777 .

RUN ./scripts/feeds update -a && \
    ./scripts/feeds install -a && \
    chmod -R ugo+rwX .

RUN mkdir -p /opt/configs /opt/files

ENV CONFIG_DIR=/opt/configs
ENV OUTPUT_DIR=/opt/openwrt/bin
ENV FILE_DIR=/opt/files

VOLUME ${CONFIG_DIR}
VOLUME ${FILE_DIR}
VOLUME ${OUTPUT_DIR}

COPY build.sh /opt/build.sh
COPY fixperms.c /opt/fixperms.c

RUN gcc -Wall -o /opt/fixperms /opt/fixperms.c && \
  chmod 4755 /opt/fixperms

CMD ["/opt/build.sh"]
