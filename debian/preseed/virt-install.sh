#!/bin/bash

NAME=${1:-vi-test}

virt-install \
  --connect qemu:///system \
  -n ${NAME} \
  --os-variant debian10 \
  --memory 1024 \
  --vcpus 1 \
  --cpu host \
  --location https://debian.osuosl.org/debian/dists/stable/main/installer-amd64/ \
  --disk /tmp/${NAME}.qcow2,bus=virtio,size=20,format=qcow2 \
  --network=default \
  --initrd-inject=$(pwd)/preseed.vm.cfg \
  --video qxl \
  --channel spicevmc \
  --noautoconsole \
  --extra-args="preseed/file=/preseed.vm.cfg netcfg/hostname=${NAME} auto-install/enable=true debconf/priority=critical"
