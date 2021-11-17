#!/bin/bash

if test -n "${JUPYTER_PASSWORD}" ; then
  FN="$(mktemp)"
  cat <<EOF
from jupyter_server.auth.security import set_password
import sys
set_password(sys.stdin.read().strip())
EOF
  python3 "${FN}" <<EOF
${JUPYTER_PASSWORD}
EOF
  rm "${FN}"
fi

exec /usr/local/bin/jupyter lab \
  --port "${PORT:-9999}" \
  --ip 0.0.0.0 \
  --no-browser \
  --notebook-dir "${NOTEBOOK_DIR}"
