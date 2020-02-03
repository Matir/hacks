#!/bin/bash

set -ue

docker volume create mysql-$1
docker run -d --name mysql-$1 \
    --mount source=mysql-$1,target=/var/lib/mysql \
    -e MYSQL_ROOT_PASSWORD=foobarbaz \
    -p 3306:3306 \
    mysql:latest
