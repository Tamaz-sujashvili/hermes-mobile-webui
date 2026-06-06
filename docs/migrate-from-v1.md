# Migrate from v1 (hermes-webui + cloudflared)

## Stop legacy services

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.mobile-proxy.plist 2>/dev/null || true
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.mobile-tunnel.plist 2>/dev/null || true
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.hermes.mobile-webui.plist 2>/dev/null || true
```

Optional — stop separate WebUI on 8787:

```bash
~/Documents/hermes-webui/ctl.sh stop
```

## Install v2

```bash
HERMES_MOBILE_PASSWORD='new-password' ./scripts/install_macos.sh
./scripts/setup_tailscale.sh
sudo tailscale serve --bg --https=443 http://127.0.0.1:9200
```

Runtime moves to `~/.hermes/mobile-remote/` (was `mobile-webui` or `mobile_dashboard`).

## What changed

| v1 | v2 |
|----|-----|
| Proxy → :8787 hermes-webui | Proxy → :9119 official dashboard |
| Proxy on :9120 (conflicts with Hermes.app) | Proxy on :9200 |
| cloudflared trycloudflare | Tailscale |

Legacy WebUI code: [`archive/hermes-webui/`](../archive/hermes-webui/).
