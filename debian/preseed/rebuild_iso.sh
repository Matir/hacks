#!/bin/bash
# This script uses the "initrd" method of preseeding a Debian ISO
# This method is described here:
# https://wiki.debian.org/DebianInstaller/Preseed/EditIso

set -ue

ISOURL="https://cdimage.debian.org/cdimage/unofficial/non-free/cd-including-firmware/weekly-builds/amd64/iso-cd/firmware-testing-amd64-netinst.iso"
ISONAME="$(basename $ISOURL)"
REBUILD_DIR="$(mktemp --tmpdir -d debiso.XXXXXXXX)"
ISOFILES="${REBUILD_DIR}/isofiles"
PRESEED_SRC="${1:-preseed.cfg}"

REQUIRED_TOOLS="7z cpio gunzip gzip xorriso md5sum"

# Check tools
for tool in ${REQUIRED_TOOLS} ; do  # intentionally split words
  if ! command -v "${tool}" >/dev/null ; then
    echo "Tool ${tool} is required!"
    exit 1
  fi
done

if ! test -f /usr/lib/ISOLINUX/isohdpfx.bin ; then
  echo "Need isolinux!"
  exit 1
fi

if ! test -f "${PRESEED_SRC}" ; then
  echo "Missing preseed file!"
  exit 1
fi

# Check if we need to download
if test -f "${ISONAME}" ; then
  ISOPATH="${ISONAME}"
else
  echo "Downloading ${ISONAME}"
  ISOPATH="${REBUILD_DIR}/${ISONAME}"
  wget -q -O "${ISOPATH}" "${ISOURL}"
  # TODO: verify debian sig!
fi

# copy the preseed
cp "${PRESEED_SRC}" "${REBUILD_DIR}/preseed.cfg"

# Extract the ISO
mkdir -p "${ISOFILES}"
7z x -o"${ISOFILES}" "${ISOPATH}"

# Modify all the initrds
find "${ISOFILES}" -name 'initrd.gz' -print 2>/dev/null | while read -r INITRD ; do
  echo "Updating ${INITRD}"
  gunzip "${INITRD}"
  ( cd "${REBUILD_DIR}"
    echo preseed.cfg | cpio -H newc -o -A -F "${INITRD%.*}" )
  gzip "${INITRD%.*}"
done

# Regenerate md5sums
( cd "${ISOFILES}"
  chmod +w md5sum.txt
  md5sum $(find -follow -type f) > md5sum.txt
  chmod -w md5sum.txt )

# Generate new ISO
( cd "${REBUILD_DIR}"
  xorriso -as mkisofs -o "preseed-${ISONAME}" \
        -isohybrid-mbr /usr/lib/ISOLINUX/isohdpfx.bin \
        -c isolinux/boot.cat -b isolinux/isolinux.bin -no-emul-boot \
        -boot-load-size 4 -boot-info-table isofiles )

# Done!
echo "Produced ${REBUILD_DIR}/preseed-${ISONAME}!"
exit 0
