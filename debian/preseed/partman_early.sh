#!/bin/sh

set_partman_disk () {
  logger -t "partman_early" "Starting set_partman_disk"
  RET=$(debconf-get "partman-auto/disk")
  if [ $? -ne 0 ] || [ -z "$RET" ] ; then
    logger -t "partman_early" "Locating largest disk"
    DISK=""
    DISK_SZ=0
    /bin/list-devices disk > /tmp/list_devices_disk
    logger -t "partman_early" "Seen devices $(tr '\n' ' ' < /tmp/list_devices_disk)"
    while read -r try_disk ; do
      if [ $(blockdev --getsize ${try_disk}) -gt ${DISK_SZ} ] ; then
        logger -t "partman_early" "Device ${try_disk} is $(blockdev --getsize ${try_disk}) > ${DISK_SZ}"
        DISK=${try_disk}
        DISK_SZ=$(blockdev --getsize ${try_disk})
      fi
    done < /tmp/list_devices_disk
    if [ -n "$DISK" ] ; then
      logger -t "partman_early" "Setting partman-auto/disk to ${DISK}"
      debconf-set partman-auto/disk "${DISK}"
    fi
  else
    logger -t "partman_early" "Disk is already ${RET}"
  fi
  logger -t "partman_early" "Exiting set_partman_disk"
  return 0
}

logger -t "partman_early" "preseed_early.sh executing"
set_partman_disk
