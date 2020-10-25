#!/bin/bash

# Todo:
# arguments for disk size, cpu, memory, network

set -ue

NAME=${1:-vi-test}
VMDIR=${VMDIR:-/vms}
NET=${NET:-bridge=br-lab}
PRESEED=${PRESEED:-$(pwd)/preseed.vm.cfg}

virt-install \
  --connect qemu:///system \
  -n ${NAME} \
  --os-variant debian10 \
  --memory 1024 \
  --vcpus 1 \
  --cpu host \
  --location https://debian.osuosl.org/debian/dists/stable/main/installer-amd64/ \
  --disk ${VMDIR}/${NAME}.qcow2,bus=virtio,size=20,format=qcow2 \
  --network=${NET} \
  --initrd-inject=${PRESEED} \
  --video qxl \
  --channel spicevmc \
  --noautoconsole \
  --extra-args="preseed/file=/$(basename ${PRESEED}) netcfg/hostname=${NAME} auto-install/enable=true debconf/priority=critical"
