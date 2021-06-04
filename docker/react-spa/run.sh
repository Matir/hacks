#!/bin/bash

set -ue

docker run -p 8123:8080 --mount type=bind,src=${1},dst=/app/src,readonly --rm -d matir/react-spa
