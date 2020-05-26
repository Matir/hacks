#!/bin/bash

if ! test -f ip2asn-v4.tsv ; then
  wget -O ip2asn-v4.tsv.gz https://iptoasn.com/data/ip2asn-v4.tsv.gz
  gunzip ip2asn-v4.tsv.gz
fi

cat <<"EOF" | sqlite3 ip2asn.db
.mode tabs
.load ./sqlite3-inet/libsqliteipv4
drop table if exists ip2asn;
drop table if exists tornodes;
create table ip2asn (iplow TEXT, iphigh TEXT, asn TEXT, country TEXT, asnname TEXT);
create table tornodes (ip TEXT);
.import ip2asn-v4.tsv ip2asn
.import torbulkexitlist tornodes
create index tornode_idx on tornodes(ip);
alter table ip2asn add column iplow_n INT;
alter table ip2asn add column iphigh_n INT;
create index iphigh_index on ip2asn(iphigh_n);
create index iplow_index on ip2asn(iplow_n);
update ip2asn set iplow_n=IP2INT(iplow), iphigh_n=IP2INT(iphigh);
EOF
