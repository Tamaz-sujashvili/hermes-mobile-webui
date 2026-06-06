# macOS setup (Hermes.app + iPhone)

## Ports

| Port | Owner |
|------|--------|
| 9119 | `com.hermes.mobile-remote.dashboard` — phone/browser dashboard |
| 9200 | `com.hermes.mobile-remote.proxy` — Tailscale target |
| 9120–9199 | **Hermes.app** only |

## Install

```bash
cd /path/to/hermes-mobile-remote
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
HERMES_MOBILE_PASSWORD='your-password' ./scripts/install_macos.sh
```

## Verify

```bash
curl -s http://127.0.0.1:9200/healthz
curl -s http://127.0.0.1:9119/api/status | python3 -m json.tool
```

## Hermes.app bootstrap: `install.sh` HTTP 404

If Hermes.app shows **Hermes couldn't start** with `Failed to download
install.sh: HTTP 404`, the desktop build's `install-stamp.json` (baked
inside `app.asar`) is pinned to a git commit that does not exist on
GitHub — common after building Hermes.app from a dirty/unpushed checkout.

**Fix:** seed `~/.hermes/bootstrap-cache/` with `install.sh` for the
commit the app expects, so the bootstrap runner finds a cached copy
instead of trying GitHub:

```bash
./scripts/repair_hermes_desktop.sh
```

Then quit Hermes.app and reopen.

> **Do not** edit files inside `/Applications/Hermes.app/Contents/` —
> this invalidates the macOS code signature and Gatekeeper will silently
> refuse to launch the app.  If this already happened, right-click
> Hermes.app in Finder → **Open** → click **Open** in the dialog to
> create a permanent Gatekeeper exception.

Manual checks:

```bash
# Bootstrap cache should have install.sh for the asar stamp commit
ls ~/.hermes/bootstrap-cache/install-*.sh

# Agent venv must be Python 3.11+
~/.hermes/hermes-agent/venv/bin/python --version

# Bootstrap marker should exist
cat ~/.hermes/hermes-agent/.hermes-bootstrap-complete
```

## Hermes.app timeout: `Timed out connecting to Hermes backend`

The packaged `Hermes.app` sets `HERMES_WEB_DIST` to
`app.asar/dist` which Python cannot read as a regular directory.
The Python dashboard reports `"Frontend not built"` and fails to
respond, causing the Electron frontend to time out.

**Fix:** register on-disk web assets for the macOS GUI session:

```bash
./scripts/launch_hermes_app.sh
```

Or manually:

```bash
# Set for all future GUI app launches in this session
launchctl setenv HERMES_DESKTOP_WEB_DIST \
  "$HOME/.hermes/hermes-agent/hermes_cli/web_dist"
open /Applications/Hermes.app
```

If `hermes_cli/web_dist/index.html` is missing:

```bash
cd ~/.hermes/hermes-agent/web && npm install && npm run build
```

## Hermes.app gateway offline after an update

If the desktop shows **Could not connect to Hermes gateway** but `curl http://127.0.0.1:9120/api/status` works:

1. Remove `HERMES_DASHBOARD_SESSION_TOKEN` from `~/.hermes/.env` if present (that value is per-process only; Hermes.app mints a fresh token each launch).
2. Quit Hermes.app completely, then reopen **/Applications/Hermes.app** (not older **Hermes Agent.app** copies).
3. Track upstream fix: [hermes-agent#39349](https://github.com/NousResearch/hermes-agent/issues/39349).

## In-app update stuck or “already up to date”

The agent checkout must be on `main`, not a detached HEAD:

```bash
cd ~/.hermes/hermes-agent
git checkout main
git pull --ff-only origin main
~/.local/bin/hermes update
```

If update fails on `uv pip install`, recreate the venv with Python 3.11+:

```bash
cd ~/.hermes/hermes-agent
rm -rf venv
python3.11 -m venv venv
venv/bin/pip install -e .
```

Keep personal projects (pipelines, scripts) **outside** `~/.hermes/hermes-agent` so `hermes update` does not stash conflicts on tracked paths.

## Unload

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.hermes.mobile-remote.dashboard.plist
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.hermes.mobile-remote.proxy.plist
```
