#!/bin/sh

. /usr/share/debconf/confmodule

function set_partman_disk {
  db_get partman-auto/disk
  if [ -z "$RET" ] ; then
    DISK=""
    DISK_SZ=0
    /bin/list-devices disk | while read try_disk ; do
      if [ $(blockdev --getsize ${try_disk}) -gt ${DISK_SZ} ] ; then
        DISK=${try_disk}
        DISK_SZ=$(blockdev --getsize ${try_disk})
      fi
      if [ -n "$DISK" ] ; then
        logger "Setting partman-auto/disk to ${DISK}"
        db_set partman-auto/disk "${DISK}"
      fi
    done
  fi
}
