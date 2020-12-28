#!/bin/bash

set -ue

cd $(dirname "${0}")

if test -z "${1:-}" ; then
  echo "Must specify BUILD." >/dev/stderr
  exit 1
fi

BUILD="${1}"
BUILDSRC="$(pwd)/builds/${BUILD}"

if test \! -d "${BUILDSRC}" ; then
  echo "Build ${BUILD} does not exist." >/dev/stderr
  exit 1
fi

TEMPD=$(mktemp --tmpdir -d wrtbuilder.XXXXXX)

cp -Lr "${BUILDSRC}/configs" "${TEMPD}/configs"
mkdir -p "${BUILDSRC}/bin"

ARGS="-v ${TEMPD}/configs:/opt/configs -v ${BUILDSRC}/bin:/opt/openwrt/bin"

if test -d "${BUILDSRC}/files" ; then
  cp -Lr "${BUILDSRC}/files" "${TEMPD}/files"
  ARGS="${ARGS} -v ${TEMPD}/files:/opt/files"
fi

CMD="docker run --user=$(id -u) ${ARGS} matir/wrtbuilder"
echo ${CMD}
eval ${CMD}
