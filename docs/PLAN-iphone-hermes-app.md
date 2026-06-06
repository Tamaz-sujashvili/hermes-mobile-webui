# Plan: Rewrite Hermes Mobile for iPhone control of official Hermes.app

**Status:** Draft (2026-06-05)  
**Target user:** Mac with `/Applications/Hermes.app` v0.15.1+, `~/.hermes`, gateway already running  
**Goal:** Reliable iPhone control of the **same agent and sessions** as Hermes.app — **not** a fork of `hermes-webui` on port 8787.

---

## 1. Problem statement

### What exists today (broken for your goal)

| Layer | Current state | Why it fails |
|-------|---------------|--------------|
| This repo | Full copy of `nesquena/hermes-webui` + `mobile_proxy` | Product is **WebUI**, README targets 8787 |
| Your Mac | `hermes-webui` via `ctl.sh` on **8787** | Different UI than **Hermes.app** |
| Your Mac | `~/.hermes/mobile_dashboard` proxy on **9120** | **Port conflict** with Hermes.app (9120–9199) |
| Your Mac | `cloudflared` quick tunnel | Public, unstable, not Tailscale |
| Hermes.app | Electron UI + `hermes dashboard --tui` on dynamic port | No first-class iPhone path |

### What “success” looks like

1. iPhone opens **one HTTPS URL** (Tailscale) → password gate → **official Nous web dashboard** (`--tui`).
2. **Sessions** tab lists the same threads as Hermes.app (shared `~/.hermes`).
3. **Chat** tab resumes/continues sessions; approvals and tools work.
4. Hermes.app on Mac keeps working; **no port fights**; gateway stays on launchd.
5. Repo is **small**, documented, and maintainable — not 700 files of unrelated WebUI.

### Explicit non-goals

- Pixel-perfect clone of Hermes.app Electron UI on iPhone (requires a future iOS app from Nous).
- Replacing or forking `hermes-agent` / `hermes-webui` upstream.
- Exposing raw dashboard or gateway ports to the public internet.

---

## 2. Target architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│ iPhone (Safari / Add to Home Screen)                            │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS (Tailscale Serve / Funnel)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ Mac — tailnet only                                              │
│   hermes-mobile-proxy :9200  (password cookie, Safari fixes)   │
└────────────────────────────┬────────────────────────────────────┘
                             │ http://127.0.0.1:9119
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ Official Hermes dashboard (dedicated instance for mobile)       │
│   hermes dashboard --tui --no-open --host 127.0.0.1 --port 9119│
│   HERMES_WEB_DIST → hermes-agent/hermes_cli/web_dist            │
│   Mobile proxy uses its own auth.json (not dashboard session token) │
└────────────────────────────┬────────────────────────────────────┘
                             │ same HERMES_HOME
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ ~/.hermes  (state.db, config.yaml, gateway, sessions)          │
│   ai.hermes.gateway (launchd) — already on your Mac           │
│   Hermes.app — own dashboard child on 9120 (unchanged)        │
└─────────────────────────────────────────────────────────────────┘
```

### Port policy (no conflicts)

| Port | Owner | Purpose |
|------|--------|---------|
| **9119** | This project (`hermes-mobile-dashboard`) | Fixed dashboard for **iPhone / browser** |
| **9200** | This project (`hermes-mobile-proxy`) | Password gate for Tailscale |
| **9120–9199** | **Hermes.app only** | App-spawned dashboard; do not bind services here |
| **8787** | *Deprecated in this project* | Old `hermes-webui`; stop for iPhone path |

Hermes.app and the phone dashboard are **two dashboard processes**, same `HERMES_HOME`. That is supported: both read the same session store.

---

## 3. Repository rewrite (phased)

### Phase A — Strip and rename (structural)

**Deliverables**

- [ ] Rename product in `README.md` → **Hermes Mobile Remote** (or **Hermes iPhone Control**).
- [ ] Move vendored WebUI to `archive/hermes-webui/` **or** drop it and document dependency on installed `hermes-agent` only.
- [ ] Remove / stop publishing: `bootstrap.py`, `server.py`, `static/`, `api/`, `tests/test_*.py` (5000+ tests) unless kept as optional submodule.
- [ ] New top-level layout:

```text
hermes-mobile-remote/
  mobile_proxy/          # keep, rewrite (dashboard-first)
  services/
    dashboard.py         # wrapper: spawn/manage dashboard on 9119
    port_policy.py       # guard against 9120-9199 binds
  scripts/
    install_macos.sh     # Tailscale check, auth, launchd
    create_auth.sh
    audit_release.py     # keep hygiene checks
  deploy/macos/
    *.plist              # gateway untouched; proxy + dashboard only
  docs/
    PLAN-iphone-hermes-app.md  # this file
    setup-macos.md
    setup-tailscale.md
    troubleshooting-iphone.md
  docker/                # optional: proxy + dashboard only (no webui image)
  tests/
    test_proxy_dashboard.py
    test_port_policy.py
  requirements.txt       # fastapi, uvicorn, httpx, websockets only
```

**Acceptance:** `pytest tests/ -q` runs in &lt;30s; repo size and CI time drop by orders of magnitude.

---

### Phase B — Rewrite `mobile_proxy` (dashboard-native)

**Current issues**

- Defaults to `8787` and `HERMES_MOBILE_DISABLE_DASHBOARD=1`.
- Assumes `/dashboard` path prefix; official dashboard is served at **root** on 9119.
- No forwarding of `X-Hermes-Session-Token` from mobile login to upstream.

**New behavior**

| Feature | Spec |
|---------|------|
| Default upstream | `http://127.0.0.1:9119` |
| Routing | All paths → dashboard upstream (no webui fallback) |
| WebSocket | Proxy `/api/ws`, `/api/pty`, SSE, long timeouts |
| Safari | Keep header normalization (`Content-Encoding`, etc.) |
| Auth | Layer 1: mobile proxy cookie (PBKDF2); Layer 2: inject or forward dashboard token for API after login |
| Health | `/healthz` local; upstream `/api/status` version check |
| Config | `HERMES_MOBILE_UPSTREAM`, `HERMES_MOBILE_PROXY_PORT=9200` |

**Acceptance:** iPhone can load `/`, `/chat`, `/sessions`, resume session via ▶, send a message, receive streaming reply.

---

### Phase C — Dashboard service manager

**Script / launchd:** `ai.hermes.mobile-dashboard`

```bash
# Environment (launchd or .env)
HERMES_HOME=/Users/tazo/.hermes
HERMES_WEB_DIST=$HERMES_HOME/hermes-agent/hermes_cli/web_dist
# Do not set HERMES_DASHBOARD_SESSION_TOKEN in .env — it is per-process only.

exec $HERMES_HOME/hermes-agent/venv/bin/python -m hermes_cli.main \
  dashboard --no-open --host 127.0.0.1 --port 9119
```

**`services/dashboard.py` responsibilities**

- Verify `web_dist/index.html` exists; print build hint (`cd hermes-agent/web && npm run build`) if missing.
- Refuse to bind ports in 9120–9199.
- Optional: wait for `/api/status` before declaring healthy.

**Acceptance:** `curl http://127.0.0.1:9119/api/status` returns JSON with `version` matching installed agent.

---

### Phase D — Tailscale integration (required path)

**No cloudflared in default install.**

| Step | Action |
|------|--------|
| Install | Mac App Store or pkg; same account on iPhone |
| Mac | `tailscale serve --bg --https=443 http://127.0.0.1:9200` |
| iPhone | Open MagicDNS name; bookmark; Add to Home Screen |
| Optional | Tailscale ACL restricting who can reach the Mac |

**Script:** `scripts/setup_tailscale.sh` — idempotent checks, prints exact `serve` command.

**Acceptance:** Phone off-LAN can open dashboard after Tailscale connect + proxy login.

---

### Phase E — Mac one-shot installer

**`scripts/install_macos.sh`**

1. Preconditions: Hermes.app or `hermes-agent` venv at `~/.hermes/hermes-agent`.
2. Unload legacy agents: `ai.hermes.mobile-proxy`, `ai.hermes.mobile-tunnel`, `ai.hermes.mobile-webui`.
3. Stop `hermes-webui` ctl on 8787 (optional prompt).
4. Create `~/.hermes/mobile-remote/auth.json` via `create_auth.sh`.
5. Install plists: `mobile-dashboard`, `mobile-proxy`.
6. Print Tailscale + iPhone checklist.

**Acceptance:** Fresh Mac with Hermes.app → one script → iPhone usable in &lt;15 minutes.

---

### Phase F — Docs, CI, migration

| Artifact | Content |
|----------|---------|
| `README.md` | Hermes.app-first; no 8787 quick start |
| `CHANGELOG.md` | Breaking: v2.0 removes bundled WebUI |
| `docs/setup-macos.md` | Port table, launchd, Hermes.app coexistence |
| `docs/setup-tailscale.md` | Serve vs Funnel; security notes |
| `docs/troubleshooting-iphone.md` | Safari, WS 4401/4403, token pin |
| CI | pytest proxy tests only; `audit_public_release.py` |
| Migration | `docs/migrate-from-mobile-webui.md` for your current `~/.hermes/mobile_dashboard` |

---

## 4. Your Mac migration checklist (execute during Phase E)

```bash
# 1. Stop legacy mobile stack
launchctl unload ~/Library/LaunchAgents/ai.hermes.mobile-proxy.plist 2>/dev/null || true
launchctl unload ~/Library/LaunchAgents/ai.hermes.mobile-tunnel.plist 2>/dev/null || true
launchctl unload ~/Library/LaunchAgents/ai.hermes.mobile-webui.plist 2>/dev/null || true

# 2. Stop separate hermes-webui (optional but recommended)
/Users/tazo/Documents/hermes-webui/ctl.sh stop 2>/dev/null || true

# 3. Ensure ~/.hermes/.env does NOT contain HERMES_DASHBOARD_SESSION_TOKEN
#    (stale values break Hermes.app gateway WS — see hermes-agent#39349)

# 4. After rewrite ships: run scripts/install_macos.sh from this repo

# 5. Install Tailscale on Mac + iPhone, then:
sudo tailscale serve --bg --https=443 http://127.0.0.1:9200
```

Keep **Hermes.app** and **`ai.hermes.gateway`** as they are.

---

## 5. iPhone usage model (post-rewrite)

| Task | Where on phone |
|------|----------------|
| See all sessions | Dashboard → **Sessions** |
| Read transcript | Expand session row |
| Continue Mac thread | ▶ resume → **Chat** (TUI) |
| New instruction | **Chat** tab |
| Approve shell/tool | Prompts inside **Chat** TUI |
| Change model / config | **Config** / **API Keys** tabs |
| Check Telegram/gateway | **Status** |

**Tips:** landscape for Chat; keep tab open during long runs; use Sessions for browsing, Chat for doing.

---

## 6. Risk register

| Risk | Mitigation |
|------|------------|
| Two dashboards confuse sessions | Same `HERMES_HOME`; document “Mac app vs phone browser” |
| TUI unusable on small screen | Sessions-first workflow; future: thin mobile web UI on dashboard APIs only |
| Token rotation breaks phone | Do not persist `HERMES_DASHBOARD_SESSION_TOKEN` in `.env`; use mobile-proxy password + Tailscale |
| Hermes.app breaks after upgrade | Pin `install-stamp.json`; installer checks agent version |
| Repo rewrite breaks your fork | Tag `v1.x-webui-legacy` before deleting WebUI tree |

---

## 7. Implementation order (suggested sprints)

| Sprint | Work | Days (est.) |
|--------|------|-------------|
| **S1** | Phase A: archive WebUI, new README, slim requirements | 1–2 |
| **S2** | Phase B: rewrite `mobile_proxy` + tests | 2–3 |
| **S3** | Phase C + E: dashboard service + `install_macos.sh` + plists | 1–2 |
| **S4** | Phase D: Tailscale docs/scripts | 0.5–1 |
| **S5** | Phase F: CI, migration doc, run on your Mac | 1 |
| **S6** | Optional: Docker slim image; PWA manifest for dashboard bookmark | 2+ |

**Total:** ~1–2 weeks for a minimal shippable v2.0 on your machine.

---

## 8. Decision needed before coding

Choose one for the WebUI tree:

| Option | Pros | Cons |
|--------|------|------|
| **A. Delete** WebUI from repo | Cleanest; matches “rewrite whole project” | No local 8787 from this repo |
| **B. Git submodule** `hermes-webui` optional | Preserves choice for power users | More doc complexity |
| **C. Keep in `archive/`** unchanged | Easy rollback | Bloat remains in git history |

**Recommendation:** **A** for v2.0 + git tag `v1.0-legacy-webui` on current `main`.

---

## 9. Approval gate

Proceed to implementation when you confirm:

1. **Target UI:** Official dashboard + TUI (not Hermes.app Electron clone) — **yes/no**
2. **Drop bundled `hermes-webui`:** Option A / B / C
3. **Ports:** 9119 dashboard + 9200 proxy — **yes/no**
4. **Tailscale-only** remote access (no cloudflared default) — **yes/no**

After confirmation, implementation starts at **Phase A** in this repository.
