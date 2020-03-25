FROM openjdk:14-jdk-alpine3.10

ENV DEBIAN_FRONTEND=noninteractive

ENV GHIDRA_REPOS_PATH /srv/repositories
ENV GHIDRA_INSTALL_PATH /opt
ENV GHIDRA_RELEASE_URL https://ghidra-sre.org/ghidra_9.1.1_PUBLIC_20191218.zip
ENV GHIDRA_VERSION 9.1.1_PUBLIC
ENV GHIDRA_SHA_256 b0d40a4497c66011084e4a639d61ac76da4b4c5cabd62ab63adadb7293b0e506

# Create ghidra user.
RUN addgroup -S ghidra && \
    adduser -D -S ghidra -G ghidra

RUN apk add --update --no-cache \
    wget \
    unzip \
    bash

# Get Ghidra.
WORKDIR ${GHIDRA_INSTALL_PATH}
RUN wget --progress=bar:force -O ghidra_${GHIDRA_VERSION}.zip ${GHIDRA_RELEASE_URL} && \
    echo "${GHIDRA_SHA_256}  ghidra_${GHIDRA_VERSION}.zip" | sha256sum -c && \
    unzip ghidra_${GHIDRA_VERSION}.zip && \
    mv ghidra_${GHIDRA_VERSION} ghidra && \
    rm ghidra_${GHIDRA_VERSION}.zip && \
    chown -R ghidra: ${GHIDRA_INSTALL_PATH}/ghidra

# Install Ghidra server.
RUN cd ${GHIDRA_INSTALL_PATH}/ghidra/server && \
    cp server.conf server.conf.bak && \
    mkdir -p ${GHIDRA_REPOS_PATH} && \
    sed 's|ghidra.repositories.dir=.*|ghidra.repositories.dir='"${GHIDRA_REPOS_PATH}"'|' server.conf.bak > server.conf && \
    ${GHIDRA_INSTALL_PATH}/ghidra/server/svrInstall && \
    chown -R ghidra: ${GHIDRA_REPOS_PATH} && \
    cd /home/ghidra && \
    ln -s ${GHIDRA_INSTALL_PATH}/ghidra/server/svrAdmin svrAdmin && \
    ln -s ${GHIDRA_INSTALL_PATH}/ghidra/server/server.conf server.conf && \
    ln -s ${GHIDRA_INSTALL_PATH}/ghidra/server/svrInstall svrInstall && \
    ln -s ${GHIDRA_INSTALL_PATH}/ghidra/server/svrUninstall svrUninstall && \
    ln -s ${GHIDRA_INSTALL_PATH}/ghidra/server/ghidraSvr ghidraSvr

VOLUME ${GHIDRA_REPOS_PATH}

# Setup user environment.
USER ghidra
WORKDIR /home/ghidra
ENV HOME /home/ghidra

# Ghidra's default ports.
EXPOSE 13100
EXPOSE 13101
EXPOSE 13102

ENTRYPOINT ${GHIDRA_INSTALL_PATH}/ghidra/server/ghidraSvr console
