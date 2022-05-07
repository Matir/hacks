#!/bin/bash

set -ue

SCRIPTPATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
PORT=${PORT:-3306}

docker volume create mysql-$1
docker run -d --name mysql-$1 \
    --mount source=mysql-$1,target=/var/lib/mysql \
    -v ${SCRIPTPATH}/auth.cnf:/etc/mysql/conf.d/auth.cnf \
    -e MYSQL_ROOT_PASSWORD=foobarbaz \
    -p ${PORT}:3306 \
    mysql:latest
