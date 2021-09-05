#!/bin/bash

LINSRC=${LINSRC:-/usr/src/linux-source-5.10}

if test -f syscalls.txt ; then
  echo "Not regenerating syscalls.txt"
else
  find "${LINSRC}" -name '*.c' | \
    xargs grep -lF 'SYSCALL_DEFINE' | \
    grep -vP 'arch/(?!x86/)' | \
    xargs -L1 indent -st -l5000 | \
    grep -E '^[[:space:]]*(COMPAT_)?SYSCALL_DEFINE' | \
    sed 's/^[ \t]*\(COMPAT_\)*//' | \
    sed -e 's/compat_ulong_t/unsigned long/g' \
      -e 's/ compat_/ /g' -e 's/ __kernel_/ /g' \
      -e 's/ u32,/ unsigned int,/g' -e 's/ const / /g' | \
    sort -u > syscalls.txt
fi

# For the moment, we arbitrarily select the first from duplicates.
SEEN_SC=""

while read line ; do
  #echo ${line}
  NUMARGS="$(echo $line | sed 's/SYSCALL_DEFINE\([0-9]*\).*/\1/')"
  NAME="SYS_$(echo $line | sed 's/.*(\([a-z0-9_]\+\)[,)].*/\1/' | tr '[:lower:]' '[:upper:]')"
  if echo "${SEEN_SC}" | grep -q " ${NAME}" ; then
    continue
  fi
  LCNAME="$(echo $line | sed 's/.*(\([a-z0-9_]\+\)[,)].*/\1/')"
  SEEN_SC="${SEEN_SC} ${NAME}"
  ARGS="$(echo $line | sed 's/[^,]*, \(.*\))/\1/')"
  echo "$NAME: $NUMARGS $ARGS"
done < syscalls.txt
