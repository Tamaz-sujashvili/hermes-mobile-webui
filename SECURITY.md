# Security policy

## Supported surface

This project supports:

- Hermes WebUI on trusted local or internal networks
- the bundled `mobile_proxy` behind your own HTTPS/private-access layer

This project does not support publishing raw WebUI directly to the public internet.

## Reporting a vulnerability

Please do not open a public issue for active security problems that could expose a running Hermes installation.

Instead:

1. open a private security advisory in GitHub, or
2. contact the maintainer through a private channel listed on the repository profile

Include:

- affected version or commit
- deployment mode: native, single-container, two-container, or three-container
- whether the issue affects WebUI, mobile proxy, or both
- minimal reproduction steps

## Secret-handling policy

Never include:

- `.env`
- generated `auth.json`
- tunnel URLs that are still live
- session cookies or signing secrets
- full Hermes home archives

Use `python3 scripts/audit_public_release.py` before publishing changes.

## Current hardening notes

- The current UI still relies on legacy inline scripts and inline event handlers,
  so the shipped CSP intentionally retains `'unsafe-inline'` for now. That is a
  known hardening gap, not a hidden guarantee.
- The supported deployment model remains: bind locally, require authentication,
  and place remote access behind your own HTTPS or private-network layer.
- `bootstrap.py` no longer auto-runs the upstream installer unless you opt in
  explicitly with `--allow-official-installer` or
  `HERMES_WEBUI_ALLOW_OFFICIAL_INSTALLER=1`.
