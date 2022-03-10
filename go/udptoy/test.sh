#!/bin/bash

TMPDIR=$(mktemp -d)
INFILE=${TMPDIR}/input
OUTFILE=${TMPDIR}/output

DESTPORT=9185
PROXYPORT=19185

dd if=/dev/urandom of="${INFILE}" bs=1024 count=1024

socat -u UDP4-RECV:${DESTPORT} CREATE:"${OUTFILE}" &
SOCAT_PID=$!

setsid -w go run . \
  -dest localhost:${DESTPORT} \
  -listen localhost:${PROXYPORT} \
  &
#  -drop 5 \
#  -swappy 10 &
UDPTOY_PID=$!

# time for socket to be open, etc.
sleep 5
socat -u -b512 OPEN:"${INFILE}" UDP4-SENDTO:localhost:${PROXYPORT},sndbuf=2048
sleep 5
echo "Killing -$UDPTOY_PID"
kill -- -$UDPTOY_PID
kill $SOCAT_PID

md5sum "${TMPDIR}"/*
