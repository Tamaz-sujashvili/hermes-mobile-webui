#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
HERMES_HOME="${HERMES_HOME:-${HOME}/.hermes}"
RUNTIME_DIR="${HERMES_MOBILE_RUNTIME_DIR:-${HERMES_HOME}/mobile-remote}"
BIN_DIR="${RUNTIME_DIR}/bin"
LAUNCH_AGENTS="${HOME}/Library/LaunchAgents"
USER="${USER:-$(id -un)}"

echo "==> Hermes Mobile Remote — macOS install"
echo "    Repo: ${REPO_ROOT}"
echo "    HERMES_HOME: ${HERMES_HOME}"

if [[ ! -d "${HERMES_HOME}/hermes-agent" ]]; then
  echo "ERROR: ${HERMES_HOME}/hermes-agent not found. Install Hermes Agent first." >&2
  exit 1
fi

echo "==> Stopping legacy mobile/webui launch agents (safe if absent)"
for label in \
  ai.hermes.mobile-proxy \
  ai.hermes.mobile-tunnel \
  ai.hermes.mobile-webui \
  ai.hermes.mobile-dashboard \
  ai.hermes.iphone-official-proxy \
  com.hermes.mobile-remote.dashboard \
  com.hermes.mobile-remote.proxy; do
  launchctl bootout "gui/${UID}" "${LAUNCH_AGENTS}/${label}.plist" 2>/dev/null || true
done

echo "==> Python venv for mobile proxy"
if [[ ! -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  python3 -m venv "${REPO_ROOT}/.venv"
  "${REPO_ROOT}/.venv/bin/pip" install -q -r "${REPO_ROOT}/requirements.txt"
fi

mkdir -p "${RUNTIME_DIR}" "${BIN_DIR}"

if [[ ! -f "${RUNTIME_DIR}/auth.json" ]]; then
  echo "==> Create mobile proxy password"
  if [[ -z "${HERMES_MOBILE_PASSWORD:-}" ]]; then
    echo "Set HERMES_MOBILE_PASSWORD and re-run, or run:" >&2
    echo "  HERMES_MOBILE_PASSWORD='your-password' ${REPO_ROOT}/scripts/create_mobile_auth.sh" >&2
    exit 1
  fi
  HERMES_MOBILE_RUNTIME_DIR="${RUNTIME_DIR}" \
    HERMES_MOBILE_AUTH_PATH="${RUNTIME_DIR}/auth.json" \
    "${REPO_ROOT}/scripts/create_mobile_auth.sh" --force
fi

if ! grep -q '^HERMES_DASHBOARD_SESSION_TOKEN=' "${HERMES_HOME}/.env" 2>/dev/null; then
  echo "==> Pin dashboard session token in ${HERMES_HOME}/.env"
  token="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
  mkdir -p "${HERMES_HOME}"
  touch "${HERMES_HOME}/.env"
  chmod 600 "${HERMES_HOME}/.env"
  echo "HERMES_DASHBOARD_SESSION_TOKEN=${token}" >> "${HERMES_HOME}/.env"
  echo "    Added HERMES_DASHBOARD_SESSION_TOKEN (restart dashboard after install)."
fi

WEB_DIST="${HERMES_HOME}/hermes-agent/hermes_cli/web_dist/index.html"
if [[ ! -f "${WEB_DIST}" ]]; then
  echo "==> WARNING: dashboard web UI not built at ${WEB_DIST}"
  echo "    Run: cd ${HERMES_HOME}/hermes-agent/web && npm install && npm run build"
fi

echo "==> Installing launch wrappers in ${BIN_DIR}"
cat > "${BIN_DIR}/run_dashboard.sh" <<EOF
#!/bin/bash
set -euo pipefail
export HERMES_HOME="${HERMES_HOME}"
export HERMES_WEB_DIST="${HERMES_HOME}/hermes-agent/hermes_cli/web_dist"
export PYTHONPATH="${REPO_ROOT}"
export PATH="${HERMES_HOME}/hermes-agent/venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
cd "${REPO_ROOT}"
exec "${REPO_ROOT}/.venv/bin/python" services/dashboard.py
EOF

cat > "${BIN_DIR}/run_proxy.sh" <<EOF
#!/bin/bash
set -euo pipefail
export HERMES_HOME="${HERMES_HOME}"
export HERMES_MOBILE_RUNTIME_DIR="${RUNTIME_DIR}"
export HERMES_MOBILE_AUTH_PATH="${RUNTIME_DIR}/auth.json"
export HERMES_MOBILE_UPSTREAM="http://127.0.0.1:8787"
export HERMES_MOBILE_PROXY_PORT="9200"
export PATH="${HERMES_HOME}/hermes-agent/venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
cd "${REPO_ROOT}"
exec "${REPO_ROOT}/.venv/bin/python" -m uvicorn mobile_proxy.app:APP --host 0.0.0.0 --port 9200
EOF

chmod +x "${BIN_DIR}/run_dashboard.sh" "${BIN_DIR}/run_proxy.sh"

install_plist() {
  local src="$1"
  local name="$2"
  local dest="${LAUNCH_AGENTS}/${name}"
  sed \
    -e "s|{{REPO_ROOT}}|${REPO_ROOT}|g" \
    -e "s|{{HERMES_HOME}}|${HERMES_HOME}|g" \
    -e "s|{{USER}}|${USER}|g" \
    -e "s|{{RUNTIME_DIR}}|${RUNTIME_DIR}|g" \
    -e "s|{{BIN_DIR}}|${BIN_DIR}|g" \
    "${src}" > "${dest}"
  launchctl bootstrap "gui/${UID}" "${dest}"
  echo "    loaded ${name}"
}

echo "==> Installing launchd agents"
install_plist "${REPO_ROOT}/deploy/macos/com.hermes.mobile-remote.dashboard.plist" \
  "com.hermes.mobile-remote.dashboard.plist"
install_plist "${REPO_ROOT}/deploy/macos/com.hermes.mobile-remote.proxy.plist" \
  "com.hermes.mobile-remote.proxy.plist"

echo ""
echo "==> Done"
echo "    WebUI:  http://127.0.0.1:8787"
echo "    Proxy:  http://127.0.0.1:9200 (Tailscale: http://<tailscale-ip>:9200)"
echo "    Logs:   ${RUNTIME_DIR}/"
echo ""
echo "Mobile login: use the password you set."
echo "Next: install Tailscale on Mac + iPhone, then:"
echo "  ${REPO_ROOT}/scripts/setup_tailscale.sh"
