#!/bin/sh

set -ue

export WEBDAV_ROOT="${WEBDAV_ROOT:-/webdav}"

get_handle_paths() {
  sed -n '/handle /{s/\s*handle\s\+\([A-Za-z0-9_/.-]\+\)\(\/\*\)\?.*/\1/p}' "${1}"
}

for path in $(get_handle_paths /etc/caddy/Caddyfile.auth); do
  if test ! -d "${WEBDAV_ROOT}/${path}" ; then
    echo "Creating ${WEBDAV_ROOT}/${path}"
    mkdir -p "${WEBDAV_ROOT}/${path}"
  fi
done

# Maybe create test data
if test -n "${TESTDATA:-}" ; then
  echo 'root file' > /webdav/root.txt
  echo 'a file' > /webdav/a/a.txt
fi

# Start caddy
exec /usr/bin/caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
