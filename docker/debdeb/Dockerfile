# This is a docker container intended for debugging docker/k8s issues
# It provides traditional tools for debugging, I hope :)

FROM debian:testing

RUN apt-get -yy update && \
  apt-get -yy install \
    bind9-dnsutils \
    bind9-host \
    netcat-traditional \
    procps \
    nmap \
    curl \
    wget

ENTRYPOINT ["/bin/bash"]
CMD ["-c", "sleep infinity"]
