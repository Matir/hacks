#!/bin/bash

function make_table {
  INFILE=${1}
  OUTFILE=${2}
  cat >${OUTFILE} <<EOF
package ptrace

var SyscallMetadata = map[int]SyscallMeta{
EOF
  grep '^\[' ${INFILE} | while read line ; do
    NR="$(echo ${line} | cut -d '[' -f2 | cut -d ']' -f1)"
    ARGC="$(echo ${line} | cut -d '{' -f2 | cut -d ',' -f1)"
    NAME="$(echo ${line} | cut -d '"' -f2)"
    echo "${NR}: SyscallMeta{SyscallName: \"${NAME}\", NumArgs: ${ARGC},}," >>${OUTFILE}
  done
  echo '}' >>${OUTFILE}
}

make_table syscallent_amd64.h syscalls_amd64.go
make_table syscallent_i386.h syscalls_386.go
