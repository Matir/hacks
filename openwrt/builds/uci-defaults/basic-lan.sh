#!/bin/sh

uci -q batch <<EOF
  set network.lan.ipaddr='10.41.0.1'
  set network.wwan=interface
  set network.wwan.proto='dhcp'
EOF
