# Take Hermes Agent in Your Pocket — Mobile WebUI Guide

A step-by-step guide to set up Hermes Mobile WebUI and control your Hermes Agent from iPhone via Tailscale.

---

## What is Hermes Mobile WebUI?

Hermes Mobile WebUI packages the existing Hermes WebUI with a password-gated reverse proxy so you can use the same Hermes sessions from your Mac and iPhone — without exposing raw local services to the internet.

**Architecture:**
```
iPhone → Tailscale → mobile_proxy (password gate) → Hermes WebUI → ~/.hermes state
```

Desktop and mobile stay in sync when they point at the same Hermes backend state. A session created on your Mac appears on your phone instantly.

---

## Prerequisites

- macOS with [Hermes Agent](https://hermes-agent.nousresearch.com/) installed
- [Tailscale](https://tailscale.com/) on your Mac and iPhone (same account)
- Git

---

## Step 1: Clone and Start the WebUI

```bash
git clone https://github.com/Tamaz-sujashvili/hermes-mobile-webui.git
cd hermes-mobile-webui
python3 bootstrap.py 8787 --no-browser --host 127.0.0.1
```

The WebUI starts on `http://127.0.0.1:8787` — local-only by design.

## Step 2: Start the Mobile Proxy (Password Gate)

Generate auth with a password you'll remember:

```bash
cd hermes-mobile-webui
python3 -c "
from mobile_proxy.auth import generate_auth_payload, write_auth_file
from pathlib import Path
import os
pwd = 'your-password-here'
payload = generate_auth_payload('hermes', pwd)
write_auth_file(Path(os.path.expanduser('~/.hermes/mobile-remote/auth.json')), payload, force=True)
print(f'Auth created. Password: {pwd}')
"
```

Start the proxy:

```bash
cd hermes-mobile-webui
HERMES_MOBILE_UPSTREAM=http://127.0.0.1:8787 \
.venv/bin/python -m uvicorn mobile_proxy.app:APP --host 0.0.0.0 --port 9200
```

The proxy listens on `0.0.0.0:9200` — accessible from your Tailscale network.

> **Note:** The `secure=False` cookie flag is set intentionally — Tailscale is a trusted private network and HTTPS would require additional tunnel setup.

## Step 3: Connect from iPhone

Ensure your iPhone has Tailscale installed and logged into the same account.

Open Safari and go to:

```
http://<mac-tailscale-ip>:9200
```

Find your Mac's Tailscale IP:

```bash
tailscale status | head -1 | awk '{print $1}'
```

Login with your username and password.

## Step 4: Make It Permanent (launchd)

Install the launchd services so WebUI + proxy restart automatically:

```bash
cd hermes-mobile-webui
bash scripts/install_macos.sh
```

This installs two launch agents:
- `com.hermes.mobile-remote.proxy` — mobile proxy on port 9200
- `com.hermes.mobile-remote.dashboard` — optional Hermes dashboard on port 9119

Control them:

```bash
# Start/stop proxy
launchctl kickstart -k gui/$(id -u)/com.hermes.mobile-remote.proxy
launchctl bootout gui/$(id -u)/com.hermes.mobile-remote.proxy

# Check logs
tail -f ~/.hermes/mobile-remote/proxy.out.log
tail -f ~/.hermes/mobile-remote/proxy.err.log
```

## Step 5: Optional — Cloudflare Tunnel (Internet Access)

For access without Tailscale:

```bash
cloudflared tunnel --url http://localhost:9200
```

This gives a temporary `https://<random>.trycloudflare.com` URL.

For a permanent tunnel, create a named tunnel via Cloudflare Zero Trust dashboard.

---

## Security Model

| Layer | Protection |
|-------|-----------|
| WebUI | Bound to `127.0.0.1` — localhost only |
| Mobile Proxy | Password-gated, bound to `0.0.0.0` for Tailscale |
| Tailscale | WireGuard-encrypted, device-auth only |
| Auth File | `auth.json` — PBKDF2-SHA256 hashed, `chmod 600` |

Never expose the raw WebUI (port 8787) to the internet. Only the mobile proxy (port 9200) should be behind a tunnel.

---

## Troubleshooting

**"Server response could not be read" on iPhone:**
→ The WebUI server may have stopped. Restart it: `python3 bootstrap.py 8787 --no-browser`

**Login keeps failing:**
→ Regenerate auth: delete `~/.hermes/mobile-remote/auth.json` and re-run the auth generation script, then restart the proxy.

**Cookie not sticking (login loop):**
→ The `secure=True` flag is incompatible with plain HTTP. The fix is included in this repo (mobile_proxy/app.py sets `secure=False`).

**Tailscale can't reach the proxy:**
→ Ensure the proxy binds to `0.0.0.0` (not `127.0.0.1`). Check with `lsof -i :9200`.

---

## Links

- **Repo:** https://github.com/Tamaz-sujashvili/hermes-mobile-webui
- **Hermes Agent:** https://hermes-agent.nousresearch.com
- **Tailscale:** https://tailscale.com
- **Cloudflare Tunnel:** https://developers.cloudflare.com/cloudflare-one/connections/connect-networks

---

*Built on top of the open-source hermes-webui by @nesquena. Mobile proxy, launchd templates, macOS install scripts, and Tailscale-first auth by @Tamaz_Sujashvili.*
