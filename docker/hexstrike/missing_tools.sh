#!/bin/bash

if [ "${1:-json}" == "plain" ] ; then
  PLAINFILTER=" | join(\"\n\")"
fi

curl http://127.0.0.1:8888/health | jq -r ".tools_status | with_entries(select(.value == false)) | keys ${PLAINFILTER}"
