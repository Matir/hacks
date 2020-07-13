#!/bin/bash


set -ue

DEVICE=/dev/mmcblk0p3
NAME="datacrypt"

case "${1:-unlock}" in
  create)
    FIFOD=$(mktemp -d)
    trap "rm -rf ${FIFOD}" SIGINT SIGTERM ERR EXIT
    mkfifo ${FIFOD}/f1
    mkfifo ${FIFOD}/f2
    (
        cryptsetup luksFormat -b 256 -c aes-xts-plain64 "${DEVICE}" ${FIFOD}/f1
        cryptsetup luksOpen --key-file ${FIFOD}/f2 "${DEVICE}" "${NAME}"
        mkfs.ext4 "/dev/mapper/${NAME}"
        mount "/dev/mapper/${NAME}"
    ) &
    tee ${FIFOD}/f1 | tee ${FIFOD}/f2 >/dev/null
    wait
    echo "Successfully created."
    ;;
  unlock)
    cryptsetup luksOpen --key-file - "${DEVICE}" "${NAME}"
    mount /dev/mapper/datacrypt
    echo "Successfully unlocked/mounted."
    ;;
  *)
    echo "Unknown operation!" >/dev/stderr
    exit 1
    ;;
esac
