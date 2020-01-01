#!/bin/sh

set -ue

if [ -n "${UID-}" -a -n "${GID-}" ] ; then
  userdel nginx
  # Recreate nginx with specified UID and GID
  useradd -u "${UID}" -U -g "${GID}" -M -o -r -s /bin/false nginx
fi

# setup environment
: ${SERVER_NAME:=localhost}
: ${AUTH_REALM:=WebDAV Server}

envsubst < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

mkdir -p /tmp/nginx/bodies && chown -R nginx:nginx /tmp/nginx

exec "$@"
