#!/usr/bin/env bash
set -euo pipefail

PROXY_PORT="${HERMES_MOBILE_PROXY_PORT:-9200}"
UPSTREAM_PORT="${HERMES_MOBILE_DASHBOARD_PORT:-9119}"

if ! command -v tailscale >/dev/null 2>&1; then
  cat <<EOF
Tailscale is not installed.

Install on macOS:
  App Store: https://apps.apple.com/app/tailscale/id1475387142
  Or: https://tailscale.com/download/mac

Install on iPhone:
  App Store: search for Tailscale

Sign in with the same account on both devices, then re-run this script.
EOF
  exit 1
fi

if ! tailscale status >/dev/null 2>&1; then
  echo "Tailscale is installed but not connected. Open the Tailscale app and sign in." >&2
  exit 1
fi

echo "Tailscale is connected."
echo ""
echo "Expose the mobile proxy (recommended — password gate in front of dashboard):"
echo "  sudo tailscale serve --bg --https=443 http://127.0.0.1:${PROXY_PORT}"
echo ""
echo "Check status:"
echo "  tailscale serve status"
echo ""
echo "Prerequisites on this Mac:"
echo "  - Dashboard on http://127.0.0.1:${UPSTREAM_PORT} (scripts/run_dashboard.sh or launchd)"
echo "  - Proxy on http://127.0.0.1:${PROXY_PORT} (scripts/run_mobile_proxy.sh or launchd)"
echo ""
echo "On iPhone: connect Tailscale, open the HTTPS URL from 'tailscale serve status', log in at /login"
