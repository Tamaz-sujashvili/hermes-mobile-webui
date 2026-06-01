# Hermes Mobile WebUI — Docker guide

This guide covers the supported Docker topologies for the public package.

## Pick a setup

| Setup | File(s) | Use it when |
|---|---|---|
| Single container | `docker-compose.yml` | You want the simplest local-only install. |
| Two container | `docker-compose.two-container.yml` | You want Hermes Agent and WebUI separated. |
| Three container | `docker-compose.three-container.yml` | You want a mobile-ready stack with the bundled password-gated proxy. |
| Overlay | base compose + `docker-compose.mobile.yml` | You already chose single or two-container and only want to add secure mobile access. |

## 5-minute local-only setup

```bash
cp .env.docker.example .env
docker compose up -d
open http://localhost:8787
```

This runs Hermes WebUI in one container and keeps everything local.

## Mobile-ready setup

```bash
cp .env.docker.example .env
# On macOS, replace UID/GID with `id -u` and `id -g`
# Then set a strong HERMES_MOBILE_PASSWORD
docker compose -f docker-compose.three-container.yml up -d
```

Services:

- `hermes-agent` — Hermes gateway / cron / session backend
- `hermes-webui` — local browser UI
- `mobile-proxy` — password-gated HTTP/WebSocket proxy for mobile access

The mobile proxy binds to `127.0.0.1:${HERMES_MOBILE_PROXY_PORT:-9120}` by default. Put your tunnel or reverse proxy in front of that port, not in front of raw WebUI.

## Overlay mode

If you want to keep the base compose file unchanged:

```bash
docker compose -f docker-compose.yml -f docker-compose.mobile.yml up -d
docker compose -f docker-compose.two-container.yml -f docker-compose.mobile.yml up -d
```

The overlay attaches `mobile-proxy` and `hermes-webui` to a shared `mobile-edge` Docker network so the proxy can reach the WebUI in both base layouts.

## UID / GID and bind mounts

The most common Docker failure is a host/container permission mismatch.

On macOS you should almost always set:

```bash
UID=$(id -u)
GID=$(id -g)
```

in `.env`.

This matters for:

- `docker-compose.yml` bind mounts of `~/.hermes`
- workspace bind mounts
- any custom host path you wire into the compose files

## Failure modes

### Permission denied on startup (#1399)

Cause: host files are owned by a different UID/GID.

Fix:

```bash
echo "UID=$(id -u)" >> .env
echo "GID=$(id -g)" >> .env
docker compose down
docker compose up -d
```

### Workspace appears empty (#1399)

Cause: same UID/GID mismatch as above.

Fix: align `UID` and `GID`.

### Mobile proxy fails at startup with missing auth runtime

Cause: no bootstrap password was supplied and no `auth.json` runtime exists yet.

Fix:

- Docker: set `HERMES_MOBILE_PASSWORD` in `.env`
- Native: run `./scripts/create_mobile_auth.sh` once before starting the service

### Mobile browser loads the shell but session list fails

Cause: almost always stale browser cache, a proxy/header issue in front of the mobile proxy, or clients pointing at different Hermes state.

Fix:

- confirm desktop and mobile point at the same Hermes state
- confirm the mobile client is going through `mobile-proxy`, not raw WebUI
- see [mobile troubleshooting](mobile-troubleshooting.md)

## Security model

The Docker package is designed around this exposure boundary:

- `hermes-webui`: local-only / internal-only
- `mobile-proxy`: the service you expose behind your own HTTPS/private-access layer

Do not publish raw `8787` to the open internet.

## What the multi-container setup isolates

The two- and three-container setups give you process and lifecycle separation between the agent, the WebUI, and the mobile proxy, but they are not a hard filesystem trust boundary. The agent and WebUI still share Hermes state, and the WebUI still installs Hermes Agent dependencies from the shared `hermes-agent-src` volume.

If you need a stricter boundary than that, put Hermes Agent on a different host and treat this package as a UI tier only.

## Upgrading the agent container

This is the same named-volume cache issue tracked in #1416.

The multi-container setups cache the Hermes Agent source tree in the `hermes-agent-src` named volume. Pulling a new agent image does not refresh that volume automatically.

To upgrade cleanly:

```bash
docker compose -f docker-compose.three-container.yml down
docker volume rm <project>_hermes-agent-src
docker compose -f docker-compose.three-container.yml pull
docker compose -f docker-compose.three-container.yml up -d
```

Use the same sequence for `docker-compose.two-container.yml`.

This keeps `hermes-home` intact while refreshing the agent source volume.

## Data locations

- Hermes home and session state: `hermes-home` volume or `${HERMES_HOME}`
- Agent source cache: `hermes-agent-src` volume
- Mobile proxy runtime: `mobile-proxy-state` volume or `${HERMES_MOBILE_RUNTIME_DIR}`

The mobile proxy runtime contains generated auth state and logs. It is intentionally not committed to the repo.

## Related references

- [sunnysktsang/hermes-suite](https://github.com/sunnysktsang/hermes-suite) for a community all-in-one image
- #1389 for bind-mounted credential permission fixes
- #1399 for Docker UID/GID alignment regressions
- #858 for missing agent-source wiring in multi-container setups
- #681 for the “tools run in the WebUI container” limitation

## Compose validation

Useful checks:

```bash
docker compose -f docker-compose.yml config
docker compose -f docker-compose.two-container.yml config
docker compose -f docker-compose.three-container.yml config
docker compose -f docker-compose.yml -f docker-compose.mobile.yml config
docker compose -f docker-compose.two-container.yml -f docker-compose.mobile.yml config
```
