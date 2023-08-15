#!/bin/bash

set -ue

mkdir -p "${NOTEBOOK_DIR}"

if test -n "${JUPYTER_PASSWORD}" ; then
  FN="$(mktemp)"
  cat >"${FN}" <<EOF
from jupyter_server.auth.security import set_password
import sys
set_password(sys.stdin.read().strip())
print('Password set!')
EOF
  ${VENV_DIR}/bin/python3 "${FN}" <<EOF
${JUPYTER_PASSWORD}
EOF
  rm "${FN}"
  unset JUPYTER_PASSWORD
fi

exec ${VENV_DIR}/bin/jupyter lab \
  --port "${PORT:-9999}" \
  --ip 0.0.0.0 \
  --no-browser \
  --log-level INFO \
  --notebook-dir "${NOTEBOOK_DIR}"
