#!/bin/bash

set -ue

BASE="http://localhost:9999"

curl_code() {
  URL="${BASE}${1:-/}"
  if test -z "${2:-}" ; then
    curl -s -o /dev/null -w "%{http_code}" "${URL}"
  else
    curl -s -o /dev/null -u "${2}" -w "%{http_code}" "${URL}"
  fi
}

expect_code() {
  resp=$(curl_code "${2}" "${3:-}")
  if [ "${resp}" -ne "${1}" ] ; then
    echo -n "Requested ${2}"
    if test -n "${3:-}" ; then
      echo -n " (with ${3})"
    fi
    echo ", expected ${1} got ${resp}"
  fi
}

expect_code 200 /_static/index.html
expect_code 200 / admin:testing123
expect_code 401 /
expect_code 401 / auser:testing123
expect_code 200 /a/ admin:testing123
expect_code 200 /a/ auser:testing123
expect_code 401 /a/
