#!/usr/bin/env bash
# Launch Hermes.app with the Python dashboard pointed at real on-disk web assets.
set -euo pipefail

HERMES_HOME="${HERMES_HOME:-${HOME}/.hermes}"
WEB_DIST="${HERMES_HOME}/hermes-agent/hermes_cli/web_dist"

if [[ ! -f "${WEB_DIST}/index.html" ]]; then
  echo "Building dashboard web assets..." >&2
  cd "${HERMES_HOME}/hermes-agent/web"
  npm install
  npm run build
fi

export HERMES_DESKTOP_WEB_DIST="${WEB_DIST}"
# macOS GUI apps launched via `open` do not inherit the parent shell env;
# register it for the user session so Hermes.app picks it up.
launchctl setenv HERMES_DESKTOP_WEB_DIST "${WEB_DIST}"
open -a "/Applications/Hermes.app"
