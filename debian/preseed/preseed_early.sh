#!/bin/sh

. /usr/share/debconf/confmodule

set_partman_disk () {
  logger -t "preseed_early" "Starting set_partman_disk"
  db_get partman-auto/disk
  if [ $? -ne 0 ] || [ -z "$RET" ] ; then
    logger -t "preseed_early" "Locating largest disk"
    DISK=""
    DISK_SZ=0
    logger -t "preseed_early" "Seen devices $(/bin/list-devices disk | tr '\n' ' ')"
    /bin/list-devices disk | while read try_disk ; do
      if [ $(blockdev --getsize ${try_disk}) -gt ${DISK_SZ} ] ; then
        DISK=${try_disk}
        DISK_SZ=$(blockdev --getsize ${try_disk})
      fi
    done
    if [ -n "$DISK" ] ; then
      logger -t "preseed_early" "Setting partman-auto/disk to ${DISK}"
      db_set partman-auto/disk "${DISK}"
    fi
  else
    logger -t "preseed_early" "Disk is already ${RET}"
  fi
  logger -t "preseed_early" "Exiting set_partman_disk"
  return 0
}

logger -t "preseed_early" "preseed_early.sh executing"
set_partman_disk
