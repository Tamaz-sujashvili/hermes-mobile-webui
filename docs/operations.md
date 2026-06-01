# Operations guide

## State locations

By default:

- Hermes home: `~/.hermes`
- WebUI state: `~/.hermes/webui`
- Mobile proxy runtime: `~/.hermes/mobile-webui`

Docker equivalents:

- `hermes-home` volume
- `hermes-agent-src` volume
- `mobile-proxy-state` volume

## Backups

For a full backup, capture:

1. Hermes home / `hermes-home`
2. WebUI state
3. Mobile proxy runtime only if you want to preserve the current login state

If you want a cleaner restore path, back up Hermes/WebUI state and regenerate the mobile auth runtime after restore instead of carrying the old auth file forward.

## Upgrades

### Native

1. Pull the new repo version.
2. Reinstall Python dependencies if required.
3. Restart the WebUI and mobile proxy services.

### Docker

For single-container:

```bash
docker compose pull
docker compose up -d --force-recreate
```

For multi-container:

```bash
docker compose -f docker-compose.three-container.yml down
docker volume rm <project>_hermes-agent-src
docker compose -f docker-compose.three-container.yml pull
docker compose -f docker-compose.three-container.yml up -d
```

That refreshes the cached Hermes Agent source volume.

## Password rotation

Native:

```bash
./scripts/create_mobile_auth.sh --force
```

Docker:

1. change `HERMES_MOBILE_PASSWORD` in `.env`
2. remove the old `mobile-proxy-state` auth file or volume if you want a fresh runtime
3. recreate the `mobile-proxy` service

## Health checks

- WebUI: `http://127.0.0.1:8787/health`
- Mobile proxy: `http://127.0.0.1:9120/healthz`

The public mobile health check intentionally does not leak local filesystem paths.
