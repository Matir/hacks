#!/bin/bash

# Wrap hexstrike in Docker

CONTAINER_NAME="hexstrike"
IMAGE_NAME="hexstrike"

function hexstrike_running {
  docker ps -f "name=${CONTAINER_NAME}" -q 2>/dev/null | grep -q .
}

function start_hexstrike {
  docker run -p 8888:8888 --rm -d --name "${CONTAINER_NAME}" "${IMAGE_NAME}" >/dev/null
  # give it a moment to run
  sleep 5
}

function hexstrike_mcp {
  docker exec -i "${CONTAINER_NAME}" python3 /opt/hexstrike-ai/hexstrike_mcp.py
}

function stop_hexstrike {
  docker kill "${CONTAINER_NAME}"
}

case "${1:-}" in
  start)
    hexstrike_running || start_hexstrike
    ;;
  stop)
    stop_hexstrike
    ;;
  *)
    hexstrike_running || start_hexstrike
    hexstrike_mcp
    ;;
esac
