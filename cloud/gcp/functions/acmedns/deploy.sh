#!/bin/bash

gcloud functions deploy AcmeDNS \
  --env-vars-file env.yml \
  --runtime=go116 \
  --trigger-http \
  --no-allow-unauthenticated
