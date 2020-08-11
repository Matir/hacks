#!/bin/bash

exec 3>vars.go

trap "rm vars.go" SIGINT SIGTERM ERR

echo -e "package words\n" >&3
echo "// Code generated -- DO NOT EDIT." >&3

for f in *.txt ; do
  var_name=$(basename $f .txt)
  echo -e "\n\nvar $var_name = []string{" >&3
  sed 's/\\/\\\\/g;s/"/\\"/g;s/$/",/;s/^/    "/' $f >&3
  echo -e "}" >&3
done
