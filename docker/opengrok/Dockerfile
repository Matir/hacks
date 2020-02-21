FROM debian:stretch-slim

ENV DEBIAN_FRONTEND noninteractive
ENV OPENGROK_INSTANCE_BASE /opt/opengrok

# man directory is expected by openjdk-8-jre-headless
RUN mkdir -p /usr/share/man/man1/ && \
  apt-get update && \
  apt-get install -y \
    exuberant-ctags \
    git \
    libservlet3.1-java \
    mercurial \
    default-jre-headless \
    subversion \
    tomcat8 \
  && rm -rf /var/lib/apt/lists/*

RUN mkdir -p ${OPENGROK_INSTANCE_BASE}/{data,etc}
ADD https://github.com/oracle/opengrok/releases/download/1.1-rc21/opengrok-1.1-rc21.tar.gz /tmp
RUN tar zxf /tmp/opengrok*.tar.gz --strip-components=1 -C ${OPENGROK_INSTANCE_BASE}
RUN ${OPENGROK_INSTANCE_BASE}/bin/OpenGrok deploy
COPY opengrok.sh /opengrok.sh

EXPOSE 8080

CMD /opengrok.sh
