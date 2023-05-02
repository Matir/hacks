#!/bin/bash

function make_table {
  INFILE=${1}
  OUTFILE=${2}
  cat >${OUTFILE} <<EOF
package ptrace

var SyscallMetadata = map[int]SyscallMeta{
EOF
  grep '^\[' ${INFILE} | while read line ; do
    NR="$(echo "${line}" | cut -d '[' -f2 | cut -d ']' -f1)"
    ARGC="$(echo "${line}" | cut -d '{' -f2 | cut -d ',' -f1 | tr -d ' \n')"
    NAME="$(echo "${line}" | cut -d '"' -f2)"
    if [[ "${NR}" == *"..."* ]] ; then
      continue
    fi
    if ! [[ "${ARGC}" =~ ^[0-9]+$ ]] ; then
      continue
    fi
    TYPELINE="$(grep -m1 -F "(${NAME}," syscalls.txt)"
    echo "${NR}: SyscallMeta{SyscallName: \"${NAME}\", NumArgs: ${ARGC}, ArgInfo: []SyscallArgInfo{" >>${OUTFILE}
    for i in $(seq 1 ${ARGC}) ; do
      ATYPE="$(echo "${TYPELINE}" | sed 's/, /,/g' | cut -d, -f$(($i * 2)))"
      echo "{KernelType: \"${ATYPE}\",}," >>${OUTFILE}
    done
    echo "}}," >>${OUTFILE}
  done
  echo '}' >>${OUTFILE}
  gofmt -w "${OUTFILE}"
}

make_table syscallent_amd64.h syscalls_amd64.go
make_table syscallent_i386.h syscalls_386.go
