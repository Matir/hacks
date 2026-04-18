#!/bin/bash

# Check if at least one file is provided
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 file1.json file2.json [file3.json ...]"
    exit 1
fi

# Use jq to deep merge all provided files
# '*' is the recursive merge operator in jq
jq -n 'reduce inputs as $item ({}; . * $item)' "$@"
