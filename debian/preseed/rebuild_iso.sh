#!/bin/bash
# This script uses the "initrd" method of preseeding a Debian ISO
# This method is described here:
# https://wiki.debian.org/DebianInstaller/Preseed/EditIso

set -ue

ISOURL="https://cdimage.debian.org/cdimage/unofficial/non-free/cd-including-firmware/weekly-builds/amd64/iso-cd/firmware-testing-amd64-netinst.iso"
ISONAME="$(basename $ISOURL)"
REBUILD_DIR="$(mktemp --tmpdir -d debiso.XXXXXXXX)"
ISOFILES="${REBUILD_DIR}/isofiles"

REQUIRED_TOOLS="cpio gunzip gzip xorriso md5sum"

# Flags and defaults
DISABLE_FDE=0
OUTNAME="$REBUILD_DIR/preseed-$ISONAME"
APT_PROXY=""
TASKS=""
PACKAGES=""
while getopts ":Co:P:t:p:" options; do
  case "${options}" in
    C)
      DISABLE_FDE=1
      echo "Disabling LUKS in ISO."
      ;;
    o)
      OUTNAME="${OPTARG}"
      echo "Writing output to ${OUTNAME}"
      ;;
    P)
      APT_PROXY="${OPTARG}"
      echo "Using APT proxy ${APT_PROXY}"
      ;;
    p)
      PACKAGES="${PACKAGES} ${OPTARG}"
      echo "Adding package ${OPTARG}"
      ;;
    t)
      TASKS="${TASKS},${OPTARG}"
      echo "Adding task ${OPTARG}"
      ;;
    \?)
      echo "Usage: ${0} [-C] [-o output.iso] [-P apt_proxy] [-p packages] [-t tasks] [template_preseed.cfg]"
      echo ""
      echo -e "\t-C: Do not use LUKS by default."
      echo -e "\t-o: Write output ISO to this file."
      echo -e "\t-P: Use this host as APT proxy."
      echo -e "\t-p: Additional packages"
      echo -e "\t-t: Additional tasks for tasksel."
      exit 2
      ;;
    *)
      echo "Invalid flag ${options}"
      exit 1
      ;;
  esac
done
shift $((OPTIND - 1))

PRESEED_SRC="${1:-preseed.cfg}"

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
PRESEED_REAL="${REBUILD_DIR}/preseed.cfg"
cp "${PRESEED_SRC}" "${PRESEED_REAL}"

# Make modifications
if [ "${DISABLE_FDE}" -eq "1" ] ; then
  sed -i 's/^d-i partman-auto\/method string crypto/d-i partman-auto\/method string lvm/' \
    "${PRESEED_REAL}"
fi
if [ "${APT_PROXY}" != "" ] ; then
  sed -i "/^d-i mirror\\/http\\/proxy / s/$/ ${APT_PROXY}/" \
    "${PRESEED_REAL}"
fi
if [ "${TASKS}" != "" ] ; then
  sed -i "/^tasksel tasksel\\/first multiselect/ s/\\s*$/${TASKS}/" \
    "${PRESEED_REAL}"
fi
if [ "${PACKAGES}" != "" ] ; then
  sed -i "/^d-i pkgsel\\/include string/ s/$/ ${PACKAGES}/" \
    "${PRESEED_REAL}"
fi

# Validate the generated file
if ! debconf-set-selections -c "${PRESEED_REAL}" ; then
  echo "Syntax check failed!!"
  exit 1
fi

# Extract the ISO
mkdir -p "${ISOFILES}"
xorriso -osirrox on -indev "${ISOPATH}" -extract / "${ISOFILES}"
chmod -R u+w "${ISOFILES}"

# Modify all the initrds
find "${ISOFILES}" -name 'initrd.gz' -print 2>/dev/null | while read -r INITRD ; do
  echo "Updating ${INITRD}"
  gunzip "${INITRD}"
  ( cd "${REBUILD_DIR}"
    printf 'preseed.cfg\npreseed_early.sh\n' | cpio -H newc -o -A -F "${INITRD%.*}" )
  gzip "${INITRD%.*}"
done

# Regenerate md5sums
( cd "${ISOFILES}"
  chmod +w md5sum.txt
  # shellcheck disable=SC2046
  md5sum $(find . -follow -type f) > md5sum.txt
  chmod -w md5sum.txt )

# Generate new ISO
( cd "${REBUILD_DIR}"
  xorriso -as mkisofs -r -o "${OUTNAME}" \
        -isohybrid-mbr /usr/lib/ISOLINUX/isohdpfx.bin \
        -c isolinux/boot.cat -b isolinux/isolinux.bin -no-emul-boot \
        -boot-load-size 4 -boot-info-table \
        -eltorito-alt-boot -e boot/grub/efi.img -no-emul-boot \
        -isohybrid-gpt-basdat \
        isofiles )

# Done!
echo "Produced ${OUTNAME}!"
exit 0
