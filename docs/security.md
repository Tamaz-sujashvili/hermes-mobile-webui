# Security model

Hermes Mobile WebUI is designed around a narrow public surface:

- Hermes WebUI stays local-only or internal-only.
- The bundled mobile proxy is the only service meant to sit behind a tunnel or reverse proxy.

## Threat model

The package assumes:

- you control the Mac, VPS, or Docker host
- you control the tunnel / reverse proxy / private network in front of the mobile proxy
- Hermes Agent itself remains a trusted local backend

The package does not try to be a zero-trust multitenant hosting platform.

## Safe exposure pattern

Recommended:

1. Bind WebUI to localhost or container-internal networking only.
2. Put `mobile_proxy` behind HTTPS and access control.
3. Keep auth runtime files outside git and outside public artifacts.
4. Rotate passwords by regenerating the auth runtime.

## Runtime auth model

The mobile proxy stores generated auth state in a runtime file such as:

- native: `~/.hermes/mobile-webui/auth.json`
- Docker: `${HERMES_MOBILE_RUNTIME_DIR}/auth.json`

That file contains:

- username
- password hash
- salt
- session signing secret

It is generated at runtime and intentionally ignored by git.

## What is blocked from public release

The public-release audit rejects:

- local home paths like `/Users/...`
- `trycloudflare.com` URLs
- committed runtime auth files
- committed mobile runtime logs
- tunnel state files

Run it before publishing:

```bash
python3 scripts/audit_public_release.py
```

## Operational guidance

- Do not expose raw port `8787` to the open internet.
- Do not commit `.env`, `auth.json`, `public_url.txt`, runtime logs, or screenshots.
- Prefer a tunnel or private network over direct port exposure.
- If you need to revoke access, regenerate the mobile auth runtime and restart the proxy.
