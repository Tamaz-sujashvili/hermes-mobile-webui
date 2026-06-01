# Hermes Mobile WebUI

Hermes Mobile WebUI is a self-hosted browser interface for [Hermes Agent](https://hermes-agent.nousresearch.com/) with a built-in secure mobile-access layer. It packages the existing `hermes-webui` experience together with a reusable password-gated reverse proxy so you can use the same Hermes sessions from your Mac and iPhone without exposing raw local services.

The package is built around one rule: desktop and mobile stay in sync when they point at the same Hermes backend state. A session created on your Mac should be visible on your phone, and continuing it from your phone should update the same history your desktop WebUI is already showing.

## What this repo ships

- A full source copy of the Hermes WebUI codebase
- A reusable `mobile_proxy` service for secure remote browser access
- Docker setups for local-only, split-service, and mobile-ready deployments
- Native macOS launchd templates for always-on WebUI + mobile proxy
- CI checks that reject local paths, runtime auth state, live tunnel URLs, and similar release mistakes

## What this repo does not ship

- Live tunnel endpoints
- Real passwords, session secrets, cookies, or auth runtime files
- Local launch agents from a specific machine
- The official Hermes dashboard as part of the supported product surface

The legacy dashboard integration is disabled by default in this package. The supported public surface is the synced WebUI plus the secure mobile proxy.

## Architecture

```text
iPhone / remote browser
        |
        | HTTPS via your tunnel / private network
        v
mobile_proxy (password gate, Safari fixes, WS/HTTP proxy)
        |
        v
Hermes WebUI
        |
        v
Hermes Agent state (~/.hermes or shared Docker volume)
```

The WebUI and the mobile proxy are intentionally separate. The WebUI remains local-only by default; the mobile proxy is the only service you should place behind a tunnel or private network.

## Quick start

### Local macOS / Linux

```bash
git clone https://github.com/Tamaz-sujashvili/hermes-mobile-webui.git
cd hermes-mobile-webui
python3 bootstrap.py
```

Open [http://127.0.0.1:8787](http://127.0.0.1:8787).

To add the mobile proxy locally:

```bash
cp .env.example .env
./scripts/create_mobile_auth.sh
./scripts/run_mobile_proxy.sh
```

That starts the password-gated proxy on `127.0.0.1:9120`. Put your own HTTPS/private-access layer in front of it.

### Docker

The repo supports three main Docker shapes:

| Setup | When to use it | Command |
|---|---|---|
| Single container | Fastest local-only setup | `docker compose up -d` |
| Two container | Agent and WebUI split | `docker compose -f docker-compose.two-container.yml up -d` |
| Three container | Agent + WebUI + secure mobile proxy | `docker compose -f docker-compose.three-container.yml up -d` |

You can also add the mobile proxy as an overlay:

```bash
docker compose -f docker-compose.yml -f docker-compose.mobile.yml up -d
docker compose -f docker-compose.two-container.yml -f docker-compose.mobile.yml up -d
```

Before using the mobile proxy with Docker:

```bash
cp .env.docker.example .env
# Set UID/GID on macOS, then set a strong HERMES_MOBILE_PASSWORD
docker compose -f docker-compose.three-container.yml up -d
```

## Secure mobile access

This repo deliberately does not auto-publish your WebUI. You bring your own secure edge:

- Tailscale / Headscale
- Cloudflare Tunnel
- Caddy / Nginx / Traefik behind your own TLS
- SSH port forwarding

Recommended pattern:

1. Keep Hermes WebUI bound to localhost or internal Docker networking only.
2. Expose only the `mobile_proxy` service.
3. Put HTTPS and access control in front of the proxy.
4. Use the same Hermes home / state on desktop and mobile so session history stays shared.

More detail:

- [Docker guide](docs/docker.md)
- [macOS launchd guide](docs/mobile-macos.md)
- [Security model](docs/security.md)
- [Operations guide](docs/operations.md)
- [iPhone / Safari troubleshooting](docs/mobile-troubleshooting.md)

## Session sync model

Desktop and mobile remain in sync when all clients point at the same backend state:

- same `HERMES_HOME`
- same WebUI state directory
- same Hermes session database / shared Docker volume

The WebUI in this package enables Hermes CLI/session bridging by default so old Hermes sessions can appear in the WebUI sidebar instead of being split across separate surfaces.

## Native macOS service mode

For an always-on setup on a Mac mini or laptop:

1. Generate the mobile auth runtime once:

```bash
./scripts/create_mobile_auth.sh
```

2. Use the launchd templates in [`deploy/macos`](deploy/macos) and the guide in [docs/mobile-macos.md](docs/mobile-macos.md).

The native service path uses `bootstrap.py --foreground` for the WebUI and `uvicorn mobile_proxy.app:APP` for the proxy, which keeps launchd restart behavior predictable.

## Release hygiene

The repo includes a public-release audit that checks for:

- local home paths such as `/Users/...`
- `trycloudflare.com` URLs
- committed runtime auth files
- tunnel state files, logs, screenshots, and similar local artifacts

Run it locally:

```bash
python3 scripts/audit_public_release.py
```

## Development

Core entry points:

- WebUI server: [`server.py`](server.py)
- API routes: [`api/routes.py`](api/routes.py)
- Mobile proxy: [`mobile_proxy/app.py`](mobile_proxy/app.py)
- Docker mobile image: [`Dockerfile.mobile-proxy`](Dockerfile.mobile-proxy)

Useful commands:

```bash
pytest tests/ -v
python3 scripts/audit_public_release.py
docker compose -f docker-compose.three-container.yml config
```

## License

MIT. See [LICENSE](LICENSE).
