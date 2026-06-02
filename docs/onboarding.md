# Hermes Mobile WebUI — onboarding

This guide covers the first working install, not every Hermes feature.

## Choose a path

| Path | Use it when |
|---|---|
| Local bootstrap | You run directly on macOS, Linux, or WSL2. |
| Docker single-container | You want the simplest container install. |
| Docker two-container | You want the agent and WebUI separated. |
| Docker three-container | You want the secure mobile-ready package out of the box. |

If you are unsure, start with local bootstrap or Docker single-container first.

## Local bootstrap

```bash
python3 bootstrap.py
```

Then open `http://127.0.0.1:8787`.

If Hermes Agent is missing, bootstrap now fails closed by default. Install the
agent manually, or opt in explicitly with `python3 bootstrap.py --allow-official-installer`.

If you also want mobile access:

```bash
cp .env.example .env
./scripts/create_mobile_auth.sh
./scripts/run_mobile_proxy.sh
```

## Docker bootstrap

```bash
cp .env.docker.example .env
docker compose up -d
```

For the mobile-ready Docker path, also set `HERMES_MOBILE_PASSWORD` and use:

```bash
docker compose -f docker-compose.three-container.yml up -d
```

## What the first run should prove

You should be able to confirm:

1. WebUI opens locally.
2. Hermes can load your configured provider/model.
3. Session history appears in the sidebar.
4. If mobile proxy is enabled, the proxy login page opens and the same sessions are visible after login.

## Shared-state rule

If Mac and iPhone are not showing the same session history, check the backend state first:

- same `HERMES_HOME`
- same WebUI state directory
- same Docker volumes if you are using containers

The mobile proxy is only a transport layer. It does not create a second Hermes database.
