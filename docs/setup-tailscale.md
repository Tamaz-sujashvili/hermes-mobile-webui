# Tailscale setup (recommended)

Remote access uses **Tailscale only** by default — no Cloudflare quick tunnels.

## Steps

1. Install [Tailscale for Mac](https://tailscale.com/download/mac) and on iPhone (App Store).
2. Sign in with the **same account** on both devices.
3. On the Mac, with dashboard (9119) and proxy (9200) running:

```bash
./scripts/setup_tailscale.sh
sudo tailscale serve --bg --https=443 http://127.0.0.1:9200
tailscale serve status
```

4. On iPhone: enable Tailscale → open the HTTPS URL → log in at `/login`.

## Security

- Do not expose ports 9119 or 9200 directly to the public internet.
- Tailscale limits who can reach your Mac; the proxy adds a second password layer.
