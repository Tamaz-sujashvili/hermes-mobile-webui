1/ Take your @HermesAgent in your pocket 📱

Hermes Mobile WebUI lets you control your Hermes Agent from iPhone via Tailscale — same sessions, same state, password-gated.

Here's the setup in 3 minutes ↓

2/ What you need:
• macOS with Hermes Agent
• Tailscale on Mac + iPhone
• Git

3/ Step 1 — Clone & start the WebUI
git clone https://github.com/Tamaz-sujashvili/hermes-mobile-webui.git
cd hermes-mobile-webui
python3 bootstrap.py 8787 --no-browser --host 127.0.0.1

WebUI runs on localhost:8787

4/ Step 2 — Generate proxy password & start
python3 -c "
from mobile_proxy.auth import generate_auth_payload, write_auth_file
from pathlib import Path
pwd = 'your-password'
payload = generate_auth_payload('hermes', pwd)
write_auth_file(Path('~/.hermes/mobile-remote/auth.json').expanduser(), payload, force=True)
"

HERMES_MOBILE_UPSTREAM=http://127.0.0.1:8787 \
.venv/bin/python -m uvicorn mobile_proxy.app:APP --host 0.0.0.0 --port 9200

5/ Step 3 — Connect from iPhone
Open Safari → http://<mac-tailscale-ip>:9200
Login with hermes / your-password

Find your Tailscale IP:
tailscale status | head -1 | awk '{print $1}'

Done. Sessions sync instantly between Mac and phone.

6/ Step 4 — Make it permanent (launchd)
bash scripts/install_macos.sh
This auto-starts WebUI + proxy on boot.

7/ Architecture:
iPhone → Tailscale → mobile_proxy (password gate) → WebUI → ~/.hermes

Desktop and mobile share the same Hermes state. A session created on Mac appears on your phone instantly.

8/ Security model:
• WebUI: localhost only
• Mobile proxy: password-gated (PBKDF2)
• Tailscale: WireGuard-encrypted
• Never expose raw WebUI to internet

9/ Full guide & source:
github.com/Tamaz-sujashvili/hermes-mobile-webui

Built on hermes-webui by @nesquena.
Proxy, launchd templates, macOS scripts by @Tamaz_Sujashvili.

#HermesAgent #Tailscale #SelfHosted #AI
