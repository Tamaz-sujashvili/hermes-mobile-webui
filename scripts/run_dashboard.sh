#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON="${HERMES_MOBILE_PYTHON:-}"

if [[ -z "${PYTHON}" ]]; then
  HERMES_HOME="${HERMES_HOME:-${HOME}/.hermes}"
  if [[ -x "${HERMES_HOME}/hermes-agent/venv/bin/python" ]]; then
    PYTHON="${HERMES_HOME}/hermes-agent/venv/bin/python"
  elif [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
    PYTHON="${REPO_ROOT}/.venv/bin/python"
  else
    PYTHON="$(command -v python3)"
  fi
fi

if [[ -n "${HERMES_WEBUI_EXTRA_PATH:-}" ]]; then
  export PATH="${HERMES_WEBUI_EXTRA_PATH}:${PATH}"
fi

export PYTHONPATH="${REPO_ROOT}:${PYTHONPATH:-}"
cd "${REPO_ROOT}"
exec "${PYTHON}" services/dashboard.py "$@"
