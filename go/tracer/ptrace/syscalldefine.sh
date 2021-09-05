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
    sed 's/^[ \t]*\(COMPAT_\)*//' | sort -u > syscalls.txt
fi

while read line ; do
  #echo ${line}
  NUMARGS="$(echo $line | sed 's/SYSCALL_DEFINE\([0-9]*\).*/\1/')"
  NAME="SYS_$(echo $line | sed 's/.*(\([a-z0-9_]\+\),.*/\1/' | tr '[:lower:]' '[:upper:]')"
  echo "$NAME: $NUMARGS"
done < syscalls.txt
