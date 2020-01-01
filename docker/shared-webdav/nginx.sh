#!/bin/sh

set -ue

env

if [ -n "${UID-}" -a -n "${GID-}" ] ; then
  getent passwd nginx && userdel nginx
  getent group nginx && groupdel nginx
  # Recreate nginx with specified UID and GID
  groupadd -g "${GID}" -o nginx
  useradd -u "${UID}" -g "${GID}" -M -o -r -s /bin/false nginx
  echo "Created nginx with UID ${UID}"
fi

# setup environment
: ${SERVER_NAME:=localhost}
: ${AUTH_REALM:=WebDAV Server}
export SERVER_NAME
export AUTH_REALM

envsubst '$SERVER_NAME $AUTH_REALM' \
  < /etc/nginx/nginx.conf.template \
  > /etc/nginx/nginx.conf

mkdir -p /tmp/nginx/bodies && chown -R nginx:nginx /tmp/nginx

exec "$@"
