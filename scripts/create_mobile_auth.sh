#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${HERMES_MOBILE_PROXY_PYTHON:-${HERMES_WEBUI_PYTHON:-}}"

if [[ -z "${PYTHON}" ]]; then
  if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    PYTHON="${REPO_ROOT}/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    PYTHON="$(command -v python)"
  else
    echo "Python 3 is required to create the mobile auth runtime." >&2
    exit 1
  fi
fi

cd "${REPO_ROOT}"
exec "${PYTHON}" -m mobile_proxy.init_auth "$@"
