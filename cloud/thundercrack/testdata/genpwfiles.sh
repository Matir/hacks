#!/bin/bash
# Hashes every password in pwlist with a bunch of algos into passwd.$x

set -ue

PWFILE="pwlist"

rm -f passwd.*

for h in sha512crypt md5crypt descrypt nt ; do
  while read l ; do
    mkpasswd -m ${h} ${l}
  done <${PWFILE} >passwd.${h}
done

for h in sha512sum md5sum sha1sum ; do
  while read l ; do
    echo -n ${l} | ${h}
  done <${PWFILE} >passwd.${h}
done
