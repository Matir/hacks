#!/bin/bash

# Ensure gh is installed
if ! command -v gh &> /dev/null; then
    echo "Error: 'gh' CLI is not installed." >&2
    exit 1
fi

# Default values
REVERSE=false
BEFORE_DATE=""
SHOW_PARENT=false
OUTPUT_JSON=false
ONLY_FORKS=false
SKIP_FORKS=false

# Parse flags
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -r|--reverse) REVERSE=true ;;
        -p|--show-parent) SHOW_PARENT=true ;;
        -j|--json) OUTPUT_JSON=true ;;
        -f|--forks) ONLY_FORKS=true; SKIP_FORKS=false ;;
        --no-forks) SKIP_FORKS=true; ONLY_FORKS=false ;;
        -b|--before) 
            if [[ -z "$2" || "$2" == -* ]]; then
                echo "Error: --before requires a date argument (e.g., YYYY-MM-DD)" >&2
                exit 1
            fi
            BEFORE_DATE="$2"
            shift 
            ;;
        -h|--help)
            echo "Usage: $0 [-r|--reverse] [-p|--show-parent] [-j|--json] [-f|--forks] [--no-forks] [-b|--before YYYY-MM-DD]"
            exit 0
            ;;
        *) echo "Unknown parameter: $1" >&2; exit 1 ;;
    esac
    shift
done

# Logic: --forks implies --show-parent
[[ "$ONLY_FORKS" == true ]] && SHOW_PARENT=true

# Get the current GitHub username safely
USERNAME=$(gh api /user --jq .login 2>/dev/null)
if [[ -z "$USERNAME" ]]; then
    echo "Error: Could not determine GitHub username. Are you logged in? (Try 'gh auth login')" >&2
    exit 1
fi

# Build gh command arguments using an array (safer than eval)
GH_ARGS=(repo list "$USERNAME" --limit 1000 --json nameWithOwner,pushedAt,parent)
[[ "$ONLY_FORKS" == true ]] && GH_ARGS+=(--fork)
[[ "$SKIP_FORKS" == true ]] && GH_ARGS+=(--source)

# Build JQ filter
# 1. Filter for ownership
JQ_FILTER="map(select(.nameWithOwner | startswith(\"$USERNAME/\")))"
# 2. Filter by date
if [[ -n "$BEFORE_DATE" ]]; then
    JQ_FILTER="$JQ_FILTER | map(select(.pushedAt < \"$BEFORE_DATE\"))"
fi
# 3. Sort
JQ_FILTER="$JQ_FILTER | sort_by(.pushedAt)"
[[ "$REVERSE" == false ]] && JQ_FILTER="$JQ_FILTER | reverse"

# --- JSON Output Path ---
if [[ "$OUTPUT_JSON" == true ]]; then
    OBJ="{pushedAt: .pushedAt, nameWithOwner: .nameWithOwner"
    [[ "$SHOW_PARENT" == true ]] && OBJ="$OBJ, parent: (if .parent then (.parent.owner.login + \"/\" + .parent.name) else null end)"
    OBJ="$OBJ}"
    
    gh "${GH_ARGS[@]}" --jq "$JQ_FILTER | map($OBJ)"
    exit 0
fi

# --- Table Output Path ---
SORT_DESC="newest first"
[[ "$REVERSE" == true ]] && SORT_DESC="oldest first"

MSG="Listing repositories for user: $USERNAME, sorted by last push date ($SORT_DESC)"
[[ "$ONLY_FORKS" == true ]] && MSG="Listing FORKS owned by user: $USERNAME, sorted by last push date ($SORT_DESC)"
[[ "$SKIP_FORKS" == true ]] && MSG="Listing non-forks owned by user: $USERNAME, sorted by last push date ($SORT_DESC)"
if [[ -n "$BEFORE_DATE" ]]; then
    MSG="$MSG, pushed before $BEFORE_DATE"
fi

echo "$MSG..."
HEADER="%-25s %-45s"
[[ "$SHOW_PARENT" == true ]] && HEADER="$HEADER %-30s"
echo "--------------------------------------------------------------------------------------------------"
if [[ "$SHOW_PARENT" == true ]]; then
    printf "$HEADER\n" "DATE" "REPOSITORY" "PARENT (if fork)"
else
    printf "$HEADER\n" "DATE" "REPOSITORY"
fi

# Prepare JQ for TSV conversion (no redundant date check here)
JQ_TABLE_FILTER="$JQ_FILTER | .[] | [.pushedAt, .nameWithOwner"
if [[ "$SHOW_PARENT" == true ]]; then
    JQ_TABLE_FILTER="$JQ_TABLE_FILTER, (if .parent then (.parent.owner.login + \"/\" + .parent.name) else \"\" end)"
fi
JQ_TABLE_FILTER="$JQ_TABLE_FILTER] | @tsv"

gh "${GH_ARGS[@]}" --jq "$JQ_TABLE_FILTER" | \
  while IFS=$'\t' read -r pushedAt full_name parent; do
    formatted_date=$(echo "$pushedAt" | sed 's/T/ /; s/Z//')
    if [[ "$SHOW_PARENT" == true ]]; then
        printf "%-25s %-45s %-30s\n" "$formatted_date" "$full_name" "$parent"
    else
        printf "%-25s %s\n" "$formatted_date" "$full_name"
    fi
done
