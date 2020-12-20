#!/bin/bash

set -ue

umask 000

OPENWRT_DIR=${OPENWRT_DIR:-/opt/openwrt}
CONFIG_DIR=${CONFIG_DIR:-/opt/configs}
FILES_DIR=${FILES_DIR:-/opt/files}

cd "${OPENWRT_DIR}"

cat ${CONFIG_DIR}/*.config > .config

ln -sf ${FILES_DIR} ${OPENWRT_DIR}/files

/opt/fixperms "${OPENWRT_DIR}"

make defconfig
make "$@"
