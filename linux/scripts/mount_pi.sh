#!/bin/bash

# Mount the / and /boot partitions of a raspberry pi image

set -ue

if [ $(id -u) != "0" ] ; then
  echo "You are not root, this is unlikely to work properly." >/dev/stderr
fi

function mount_img {
  IMG="${1}"
  WHERE="${2}"
  if ! test -f "${IMG}" ; then
    echo "${IMG} does not exist!" >/dev/stderr
    exit 1
  fi
  mkdir -p ${WHERE}
  KPARTX="$(kpartx -av "${IMG}")"
  BASELO="$(echo "${KPARTX}" | awk '/p1/{sub(/p1/,"",$3);print $3}')"
  echo "Created mapping on ${BASELO}"
  mount /dev/mapper/${BASELO}p2 ${WHERE}
  mount /dev/mapper/${BASELO}p1 ${WHERE}/boot
  echo "Mounted on ${WHERE}"
}

function unmount_img {
  IMG="${1}"
  if ! test -f "${IMG}" ; then
    echo "${IMG} does not exist!" >/dev/stderr
    exit 1
  fi
  KPARTX="$(kpartx -av "${IMG}")"
  BASELO="$(echo "${KPARTX}" | awk '/p1/{sub(/p1/,"",$3);print $3}')"
  umount /dev/mapper/${BASELO}p1
  umount /dev/mapper/${BASELO}p2
  kpartx -d "${IMG}"
}

case "$1" in
  -u)
    unmount_img "${2}"
    ;;
  *)
    mount_img "${1}" "${2}"
    ;;
esac
