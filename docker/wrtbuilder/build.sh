#!/bin/bash

set -ue

OPENWRT_DIR=${OPENWRT_DIR:-/opt/openwrt}
CONFIG_DIR=${CONFIG_DIR:-/opt/configs}
FILES_DIR=${FILES_DIR:-/opt/files}

cd "${OPENWRT_DIR}"

cat ${CONFIG_DIR}/*.config > .config

ln -sf ${FILES_DIR} ${OPENWRT_DIR}/files

make defconfig
make
