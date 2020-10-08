FROM debian:8

WORKDIR /root

RUN apt-get update && \
  apt-get -yy install build-essential git linux-headers-amd64 gawk \
    libpcre3-dev libdb-dev

# Build glibc
RUN git clone -b glibc-2.17 --depth 1 git://sourceware.org/git/glibc.git
RUN sed -i 's/3\.79//' glibc/configure
RUN mkdir glibc-build && cd glibc-build && \
  ../glibc/configure --prefix=/root/vuln && \
  make && make install

# Build exim 4.80
RUN git clone -b exim-4_80 --depth 1 https://github.com/Exim/exim.git
RUN useradd -r -M exim
RUN mkdir -p exim/src/Local
COPY Makefile exim/src/Local/Makefile
RUN cd exim/src && make && make install
COPY configure /root/vuln/exim/configure

# Configure
EXPOSE 25
CMD ["/root/vuln/exim/bin/exim", "-C", "/root/vuln/exim/configure", "-bdf", "-v"]
