#!/usr/bin/env bash
# Repair Hermes.app first-launch bootstrap when install.sh 404s on GitHub.
#
# Root cause: Hermes.app was built from a local-only git commit (dirty
# stamp baked into app.asar/install-stamp.json).  The bootstrap runner
# tries to fetch install.sh from GitHub at that commit and gets a 404.
#
# This script does NOT modify files inside the .app bundle — touching
# sealed resources invalidates the macOS code signature and Gatekeeper
# will silently refuse to launch the app.
#
# Instead we:
#   1. Seed ~/.hermes/bootstrap-cache/ with install.sh for every stamp
#      commit the app might reference (including the dirty one inside
#      app.asar).
#   2. Ensure .hermes-bootstrap-complete marker exists so the bootstrap
#      runner skips the download entirely on subsequent launches.
#   3. Ensure the venv uses Python 3.11+ and dependencies are installed.
#   4. Build dashboard web assets if missing (fixes HERMES_WEB_DIST
#      pointing at app.asar/dist which Python cannot read).
#   5. Set HERMES_DESKTOP_WEB_DIST via launchctl for GUI app sessions.
set -euo pipefail

HERMES_HOME="${HERMES_HOME:-${HOME}/.hermes}"
AGENT="${HERMES_HOME}/hermes-agent"

if [[ ! -d "${AGENT}" ]]; then
  echo "ERROR: ${AGENT} not found. Install Hermes Agent first." >&2
  exit 1
fi

echo "==> Hermes desktop bootstrap repair"
echo "    HERMES_HOME: ${HERMES_HOME}"

# ── 1. Seed bootstrap-cache for all known stamp commits ──────────────

cd "${AGENT}"
git fetch origin main 2>/dev/null || true
ORIGIN_MAIN="$(git rev-parse origin/main 2>/dev/null || git rev-parse HEAD)"
echo "    origin/main: ${ORIGIN_MAIN}"

mkdir -p "${HERMES_HOME}/bootstrap-cache"

# Cache install.sh for origin/main
cp "${AGENT}/scripts/install.sh" "${HERMES_HOME}/bootstrap-cache/install-${ORIGIN_MAIN}.sh"
chmod +x "${HERMES_HOME}/bootstrap-cache/install-${ORIGIN_MAIN}.sh"

# Extract the stamp commit baked inside app.asar (read-only, never modify)
ASAR="/Applications/Hermes.app/Contents/Resources/app.asar"
if [[ -f "${ASAR}" ]]; then
  # Node can read asar files; extract the stamp without modifying anything
  ASAR_COMMIT="$(node -e "
    try {
      const stamp = JSON.parse(require('original-fs').readFileSync(
        require('path').join('${ASAR}', 'install-stamp.json'), 'utf8'));
      process.stdout.write(stamp.commit || '');
    } catch {}
  " 2>/dev/null || true)"

  if [[ -n "${ASAR_COMMIT}" && "${ASAR_COMMIT}" != "${ORIGIN_MAIN}" ]]; then
    echo "    asar stamp commit: ${ASAR_COMMIT:0:12}"
    # Cache install.sh for the asar stamp commit (prevents the 404)
    cp "${AGENT}/scripts/install.sh" \
       "${HERMES_HOME}/bootstrap-cache/install-${ASAR_COMMIT}.sh"
    chmod +x "${HERMES_HOME}/bootstrap-cache/install-${ASAR_COMMIT}.sh"
    echo "    cached install.sh for asar commit"
  fi
fi

# Also cache for whatever external install-stamp.json exists (belt & suspenders)
EXT_STAMP="/Applications/Hermes.app/Contents/Resources/install-stamp.json"
if [[ -f "${EXT_STAMP}" ]]; then
  EXT_COMMIT="$(python3 -c "import json; print(json.load(open('${EXT_STAMP}'))['commit'])" 2>/dev/null || true)"
  if [[ -n "${EXT_COMMIT}" ]]; then
    cp "${AGENT}/scripts/install.sh" \
       "${HERMES_HOME}/bootstrap-cache/install-${EXT_COMMIT}.sh" 2>/dev/null || true
    chmod +x "${HERMES_HOME}/bootstrap-cache/install-${EXT_COMMIT}.sh" 2>/dev/null || true
  fi
fi

echo "    bootstrap-cache: $(ls "${HERMES_HOME}/bootstrap-cache/"install-*.sh 2>/dev/null | wc -l | tr -d ' ') scripts cached"

# ── 2. Sync agent checkout ────────────────────────────────────────────

echo "==> Syncing agent checkout to origin/main"
git checkout main 2>/dev/null || true
git reset --hard origin/main 2>/dev/null || true

# ── 3. Ensure venv uses Python 3.11+ ─────────────────────────────────

echo "==> Checking venv Python version"
VENV_PY="${AGENT}/venv/bin/python"
NEED_VENV=false
if [[ ! -x "${VENV_PY}" ]]; then
  NEED_VENV=true
elif ! "${VENV_PY}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
  NEED_VENV=true
fi

if ${NEED_VENV}; then
  PY=""
  for candidate in python3.12 python3.11 python3; do
    if command -v "${candidate}" >/dev/null 2>&1 && \
       "${candidate}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
      PY="${candidate}"
      break
    fi
  done
  if [[ -z "${PY}" ]]; then
    echo "ERROR: Python 3.11+ required. Install python3.11 and re-run." >&2
    exit 1
  fi
  echo "    Recreating venv with ${PY}"
  rm -rf venv
  "${PY}" -m venv venv
fi
echo "    venv Python: $("${VENV_PY}" --version 2>&1)"

# ── 4. Ensure bootstrap marker exists ────────────────────────────────

MARKER="${AGENT}/.hermes-bootstrap-complete"
if [[ ! -f "${MARKER}" ]]; then
  echo "==> Creating bootstrap-complete marker"
  python3 -c "
import json, datetime
print(json.dumps({
  'schemaVersion': 1,
  'pinnedCommit': '${ORIGIN_MAIN}',
  'pinnedBranch': 'main',
  'completedAt': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
  'desktopVersion': '0.15.1',
}, indent=2))
" > "${MARKER}"
fi

# ── 5. Install Python deps if hermes_cli isn't importable ─────────────

if ! "${VENV_PY}" -c "import hermes_cli" 2>/dev/null; then
  echo "==> Installing Python dependencies"
  "${VENV_PY}" -m pip install -e "${AGENT}" -q 2>/dev/null || \
  "${VENV_PY}" -m pip install -e "${AGENT}" 2>&1
fi

# ── 6. Build dashboard web assets if missing ──────────────────────────

WEB_DIST="${AGENT}/hermes_cli/web_dist"
if [[ ! -f "${WEB_DIST}/index.html" ]]; then
  echo "==> Building dashboard web assets"
  if [[ -d "${AGENT}/web" ]]; then
    (cd "${AGENT}/web" && npm install && npm run build)
  else
    echo "WARNING: ${WEB_DIST}/index.html missing and ${AGENT}/web/ not found." >&2
  fi
fi

# ── 7. Set HERMES_DESKTOP_WEB_DIST for GUI sessions ──────────────────

if [[ -d "${WEB_DIST}" ]]; then
  launchctl setenv HERMES_DESKTOP_WEB_DIST "${WEB_DIST}" 2>/dev/null || true
  echo "    HERMES_DESKTOP_WEB_DIST → ${WEB_DIST}"
fi

# ── 8. Restart gateway ────────────────────────────────────────────────

echo "==> Restarting gateway"
export PATH="${HOME}/.local/bin:${PATH}"
hermes gateway start >/dev/null 2>&1 || true

echo ""
echo "Done."
echo ""
echo "If Hermes.app refuses to launch (Gatekeeper rejection after app bundle"
echo "was modified), right-click Hermes.app in Finder → Open, then click"
echo "\"Open\" in the dialog. This creates a permanent exception."
echo ""
echo "Logs: ${HERMES_HOME}/logs/desktop.log"
