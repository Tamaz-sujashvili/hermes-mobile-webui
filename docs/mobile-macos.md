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

## 5. HTTPS / remote access

launchd only keeps the services running locally. You still need your own secure edge:

- Tailscale
- Cloudflare Tunnel
- reverse proxy with TLS

Expose the mobile proxy port, not the raw WebUI port.
