#!/bin/bash

# gemini-mcp.sh - Merges MCP server configurations into gemini-cli settings.

set -e -o pipefail

# --- Usage ---
usage() {
  echo "Usage: $0 [-o <output.json>] [-h] <path_to_settings.json> <mcp_file1.json> [mcp_file2.json]..."
  echo
  echo "Merges server configurations from one or more MCP JSON files into the"
  echo "gemini-cli settings.json file."
  echo
  echo "Options:"
  echo "  -o <output.json>    Path to write the output file. If not provided,"
  echo "                      the input settings file will be overwritten."
  echo "  -h                  Show this help message."
  exit 1
}

# --- Argument Parsing with getopt ---
OUTPUT_FILE=""

# Note: This uses BSD-compatible getopt, which is standard on macOS.
# For long options (--output), GNU getopt would be required.
PARSED_ARGS=$(getopt o:h "$@")
if [ $? -ne 0 ]; then
  usage
fi

eval set -- "$PARSED_ARGS"

while true; do
  case "$1" in
    -o)
      OUTPUT_FILE="$2"
      shift 2
      ;;
    -h)
      usage
      ;;
    --)
      shift
      break
      ;;
    *)
      # This case should not be reached with valid getopt parsing
      echo "Internal error!" >&2
      exit 1
      ;;
  esac
done


# --- Argument Validation ---
if [ "$#" -lt 2 ]; then
  echo "Error: Insufficient arguments."
  usage
fi

if ! command -v jq &> /dev/null; then
  echo "Error: 'jq' is not installed or not in your PATH. Please install jq to use this script."
  exit 1
fi

SETTINGS_FILE="$1"
shift

if [ ! -f "$SETTINGS_FILE" ]; then
  echo "Error: Settings file not found at '$SETTINGS_FILE'"
  exit 1
fi

for mcp_file in "$@"; do
  if [ ! -f "$mcp_file" ]; then
    echo "Error: MCP file not found at '$mcp_file'"
    exit 1
  fi
done


# --- Main Logic ---
TEMP_SETTINGS_FILE=$(mktemp)
cp "$SETTINGS_FILE" "$TEMP_SETTINGS_FILE"

# Ensure .mcp.servers key exists in the settings file
if ! jq -e '.mcp.servers' "$TEMP_SETTINGS_FILE" > /dev/null; then
  # This modification ensures we add the nested structure correctly if .mcp doesn't exist
  jq '.mcp += {"servers": {}}' "$TEMP_SETTINGS_FILE" > "$TEMP_SETTINGS_FILE.tmp" && mv "$TEMP_SETTINGS_FILE.tmp" "$TEMP_SETTINGS_FILE"
fi


for mcp_file in "$@"; do
  echo "Merging servers from '$mcp_file'..."
  # Merge the .servers object from the mcp file into the .mcp.servers object of the settings
  jq -s '.[0] * {mcp: {servers: .[0].mcp.servers * .[1].servers}}' "$TEMP_SETTINGS_FILE" "$mcp_file" > "$TEMP_SETTINGS_FILE.tmp"
  mv "$TEMP_SETTINGS_FILE.tmp" "$TEMP_SETTINGS_FILE"
done

# Determine the final destination
DEST_FILE="$SETTINGS_FILE"
if [ -n "$OUTPUT_FILE" ]; then
  DEST_FILE="$OUTPUT_FILE"
fi

# Overwrite the original or write to the new file
mv "$TEMP_SETTINGS_FILE" "$DEST_FILE"

echo "Successfully wrote merged MCP configuration to '$DEST_FILE'."
