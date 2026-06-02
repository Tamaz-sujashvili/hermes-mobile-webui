# Native macOS launchd setup

This is the recommended always-on setup for a Mac mini or any Mac that should keep Hermes reachable from your phone.

## 1. Generate the mobile auth runtime

```bash
cd /path/to/hermes-mobile-webui
./scripts/create_mobile_auth.sh
```

That writes a hashed auth runtime outside the repo, typically under `~/.hermes/mobile-webui/auth.json`.

## 2. Install the launchd templates

Templates live in [`deploy/macos`](../deploy/macos).

Copy them into `~/Library/LaunchAgents/` and replace these placeholders:

- `{{REPO_ROOT}}`
- `{{HERMES_HOME}}`
- `{{LOG_DIR}}`

The two templates are:

- `com.example.hermes-mobile-webui.webui.plist`
- `com.example.hermes-mobile-webui.proxy.plist`

## 3. Load the agents

```bash
launchctl unload ~/Library/LaunchAgents/com.example.hermes-mobile-webui.webui.plist 2>/dev/null || true
launchctl unload ~/Library/LaunchAgents/com.example.hermes-mobile-webui.proxy.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.example.hermes-mobile-webui.webui.plist
launchctl load ~/Library/LaunchAgents/com.example.hermes-mobile-webui.proxy.plist
```

## 4. Why this uses foreground mode

The WebUI service runs `bootstrap.py --foreground --no-browser`. That matters because launchd should supervise the real long-lived process, not a parent wrapper that forks and exits.

The proxy service runs `scripts/run_mobile_proxy.sh` directly.

## 4a. If Hermes or MCP helpers depend on Node from nvm / asdf

launchd does not inherit your interactive shell startup files, so user-managed
toolchains such as `nvm`, `asdf`, and Volta are often missing from `PATH` even
when they work in Terminal.

The bundled launchd templates set a safe default PATH for Homebrew / system
bins. If your Hermes setup also needs user-managed Node binaries, add
`HERMES_WEBUI_EXTRA_PATH` to the WebUI plist and reload it:

```xml
<key>HERMES_WEBUI_EXTRA_PATH</key>
<string>/Users/youruser/.nvm/versions/node/v20.20.2/bin</string>
```

That value is prepended by both `scripts/run_webui_foreground.sh` and
`scripts/run_mobile_proxy.sh`, so the WebUI and mobile proxy inherit the same
toolchain view under launchd.

## 5. HTTPS / remote access

launchd only keeps the services running locally. You still need your own secure edge:

- Tailscale
- Cloudflare Tunnel
- reverse proxy with TLS

Expose the mobile proxy port, not the raw WebUI port.
