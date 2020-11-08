FROM debian:buster

RUN apt-get update && \
  apt-get install -yy build-essential gcc-multilib execstack

ADD https://download.samba.org/pub/samba/old-versions/samba-2.2.7.tar.gz \
  /tmp/samba.tar.gz

WORKDIR /tmp
RUN tar zxf /tmp/samba.tar.gz

WORKDIR /tmp/samba-2.2.7/source
RUN CFLAGS="-m32" LDFLAGS="-m32" ./configure && \
  sed -i 's/^SHLD=.*/SHLD=gcc -m32/' Makefile && \
  make && make install && \
  execstack -s /usr/local/samba/bin/smbd

COPY smb.conf /usr/local/samba/lib/smb.conf

WORKDIR /root
COPY smbd_wrapper.c /root/smbd_wrapper.c
RUN gcc -o smbd_wrapper smbd_wrapper.c

EXPOSE 139/tcp
CMD ["/root/smbd_wrapper"]
