# Hermes Mobile-WebUI Implementation Tickets

## Milestone M1: Shim + Boot + Chat (Validation Gate: "Phone Sends First Message")

---

### Ticket 1: Architecture ADR and Upstream Sync Strategy

**Type:** HITL  
**Blocked by:** None  
**User Stories:** US8  
**Outcome:** Freeze the port shape: vendor the official desktop renderer, add a browser shim for `window.hermesDesktop`, define what stays mobile-specific, and choose the upstream sync method.

**Acceptance Criteria:**
- [ ] Document the browser shim architecture: which Electron IPC calls map to web transport (WebSocket/HTTP)
- [ ] Define the `window.hermesDesktop` API surface: list all preload.cjs bridge calls that need browser equivalents
- [ ] Specify what stays mobile-specific (e.g., mobile_proxy auth, touch gestures, PWA manifest) vs. what mirrors desktop exactly
- [ ] Choose upstream sync method: git submodule + patch files, fork + periodic merge, or vendor + manual import
- [ ] Create a compatibility test checklist: list all bridge calls that will fail if the shim doesn't implement them
- [ ] Document the import/update workflow: step-by-step instructions for pulling upstream desktop changes
- [ ] ADR reviewed and approved by maintainer
- [ ] ADR stored in repo as `docs/adr/001-mobile-webui-architecture.md`

---

### Ticket 2: Secure Browser Shell for the Official Renderer

**Type:** AFK  
**Blocked by:** 1  
**User Stories:** US1, US2  
**Outcome:** Phone opens the secure mobile URL and loads the official desktop shell with a minimal browser bridge and working boot/connection state.

**Acceptance Criteria:**
- [ ] Mobile proxy route configured: `/mobile` or subdomain serves the desktop renderer
- [ ] Browser shim implemented: `window.hermesDesktop` object with stub methods for all preload.cjs calls
- [ ] Renderer boots without console errors related to missing Electron APIs
- [ ] Connection state loads: gateway config read from shared `~/.hermes` (local) or remote API (mobile_proxy)
- [ ] Auth/session handling works: mobile_proxy session cookie or token authenticates the browser renderer
- [ ] Basic shell renders: sidebar, chat area, composer visible and functional
- [ ] No Electron-specific code paths execute (e.g., `ipcRenderer`, `fs`, `path` modules)
- [ ] Tested on Safari iOS and Chrome Android

---

### Ticket 3: Shared Session Sidebar from Live Hermes State

**Type:** AFK  
**Blocked by:** 2  
**User Stories:** US2  
**Outcome:** The official sidebar lists, opens, pins, archives, and searches sessions from the same shared Hermes home as desktop.

**Acceptance Criteria:**
- [ ] Session list fetched from shared Hermes state (same `~/.hermes/sessions/` or API endpoint as desktop)
- [ ] Sidebar displays sessions with title, timestamp, pin indicator
- [ ] Clicking a session opens it in the chat area
- [ ] Pin/unpin toggle works and persists to shared state
- [ ] Archive action works and moves session to archived list
- [ ] Session search filters the list by title/content match
- [ ] New session button creates a session visible on desktop immediately
- [ ] Real-time sync: sessions created on desktop appear on mobile within 5s (polling or WebSocket)

---

### Ticket 4: Chat Submit and Live Stream Through the Browser Bridge

**Type:** AFK  
**Blocked by:** 3  
**User Stories:** US2, US3  
**Outcome:** Create a new session from phone, send messages, stream assistant output and tool activity, and see the same history on desktop.

**Acceptance Criteria:**
- [ ] Composer input accepts text and submits messages
- [ ] New session created on first message if none selected
- [ ] Assistant response streams token-by-token (not batched)
- [ ] Tool calls display in the chat UI with live progress (e.g., "Running terminal command...")
- [ ] Tool results render inline (terminal output, file previews, web search results)
- [ ] Message history persists: refresh the page and all messages remain
- [ ] Desktop shows the same chat history (shared state verified)
- [ ] Typing indicators show when assistant is generating
- [ ] Stop generation button interrupts streaming

---

## Milestone M2: Sessions + APIs + Both WebUIs Running

---

### Ticket 5: Gateway Mode Settings in the Browser Port

**Type:** AFK  
**Blocked by:** 2  
**User Stories:** US6  
**Outcome:** The official settings screen can read, save, apply, and test local/remote gateway configuration without Electron IPC.

**Acceptance Criteria:**
- [ ] Settings screen accessible from sidebar or top nav
- [ ] Gateway config form displays: host, port, API key, mode (local/remote)
- [ ] Current config loads from shared Hermes state on screen open
- [ ] Form validation: invalid host/port shows error before save
- [ ] Save action writes config to shared `~/.hermes/config.yaml` or API backend
- [ ] Apply action restarts gateway connection and shows status (connected/disconnected)
- [ ] Test Connection button pings the gateway and displays latency + success/failure
- [ ] Config changes on mobile reflect on desktop within 10s

---

### Ticket 6: File Browser and Preview Pane Over Web Transport

**Type:** AFK  
**Blocked by:** 4  
**User Stories:** US4  
**Outcome:** The official right-side file browser works on mobile with directory listing, file preview, and preview-target normalization.

**Acceptance Criteria:**
- [ ] File browser panel opens from chat UI or sidebar
- [ ] Directory listing shows files/folders with icons, names, sizes, modified dates
- [ ] Navigation: click folder to enter, breadcrumb shows current path, up-one-level button works
- [ ] File preview opens for: text (`.txt`, `.md`, `.py`), images (`.png`, `.jpg`), PDFs
- [ ] Preview pane renders content inline (no download required)
- [ ] Large files (>1MB) show a "Download to view" fallback instead of timing out
- [ ] Preview-target normalization: same file opens identically on mobile and desktop
- [ ] File actions: download, copy path, delete (with confirmation)

---

### Ticket 7: Terminal Rail Over WebSocket/PTTY Backend

**Type:** AFK  
**Blocked by:** 4  
**User Stories:** US5  
**Outcome:** The official terminal panel works from phone with start, resize, write, stream, and exit over web transport.

**Acceptance Criteria:**
- [ ] Terminal panel opens from sidebar or chat command
- [ ] Start session: launches a shell (bash/zsh) via WebSocket/PTTY backend
- [ ] Terminal displays output with correct colors (ANSI escape codes rendered)
- [ ] Keyboard input works: typing sends commands to the shell
- [ ] Resize handling: terminal adjusts columns/rows when panel resizes
- [ ] Stream output: long-running commands show progressive output (not batched at end)
- [ ] Exit/cleanup: close button terminates the shell session cleanly
- [ ] Mobile keyboard: special keys (Tab, Ctrl, Arrow keys) send correct escape sequences

---

### Ticket 8: Browser-Safe Attachments, Uploads, and Save/Export Fallbacks

**Type:** AFK  
**Blocked by:** 4  
**User Stories:** US3, US4  
**Outcome:** File upload, image attachment, clipboard/save/download actions degrade cleanly on Safari/iPhone instead of relying on native Electron APIs.

**Acceptance Criteria:**
- [ ] Image attachment: camera roll picker works on iOS, files upload and attach to chat
- [ ] File upload: document picker works, files upload to shared storage, link appears in chat
- [ ] Clipboard copy: "Copy message" action copies text to mobile clipboard (fallback to manual select if OSC 52 unavailable)
- [ ] Save/export: "Save conversation" triggers a download blob instead of writing to disk
- [ ] Download fallback: Safari download manager shows the file, user can open/save
- [ ] Drag-and-drop disabled on mobile (no desktop-style drop zones)
- [ ] Upload progress indicator shows percentage + cancel button
- [ ] Error handling: failed uploads show retry button + error message

---

## Milestone M3: Responsive + Gateway + Fallback Removal

---

### Ticket 9: Responsive Mobile Layout Pass for the Official Information Architecture

**Type:** HITL (REQUIRED - URGENT sub-items)  
**Blocked by:** 6, 7, 8  
**User Stories:** US1, US3, US4, US5  
**Outcome:** Same desktop structure, but with mobile-safe layout behavior: drawer sidebar, compact top chrome, bottom-sheet/right-rail behavior, touch-sized controls, stable composer.

**Acceptance Criteria:**
- [ ] Sidebar: drawer-style slide-in on narrow viewports (<768px), swipe-to-open gesture
- [ ] Top chrome: compact header with hamburger menu, session title, status indicator
- [ ] Bottom nav: optional bottom tab bar for primary actions (Chat, Files, Terminal, Settings)
- [ ] Right rail: file/terminal panels become bottom sheets or slide-overs on mobile
- [ ] Touch targets: all buttons/inputs ≥44px × 44px (iOS HIG minimum)
- [ ] Composer: sticky bottom bar with input + send button, expands for multi-line
- [ ] Safe-area insets: content respects iOS notch/home indicator (viewport-fit=cover)
- [ ] Tested breakpoints: 375px (iPhone SE), 390px (iPhone 12/13), 414px (Plus), 768px (iPad), 1024px (iPad Pro)
- [ ] HITL QA: manual multi-viewport testing documented with screenshots

---

### Ticket 10: PWA Install Path and Auth/Session Hardening

**Type:** AFK  
**Blocked by:** 4  
**User Stories:** US1, US7  
**Outcome:** Installable home-screen app, stable session handling behind mobile_proxy, and tightened auth/rate-limit/CSRF behavior for real remote use.

**Acceptance Criteria:**
- [ ] PWA manifest: `manifest.json` with name, icons, theme_color, display=standalone
- [ ] Service worker: caches shell + static assets, offline fallback page
- [ ] Install prompt: "Add to Home Screen" banner or instructions shown on first visit
- [ ] Home screen icon: launches in standalone mode (no browser chrome)
- [ ] Session persistence: login session survives app close + reopen
- [ ] Auth hardening: CSRF token on all state-changing requests
- [ ] Rate limiting: mobile_proxy enforces per-IP rate limits (configurable)
- [ ] Session timeout: inactive sessions auto-logout after configurable duration
- [ ] Biometric auth: optional FaceID/TouchID unlock (via WebAuthn if supported)

---

### Ticket 11: Upstream Import Tooling and Compatibility Checks

**Type:** AFK  
**Blocked by:** 2  
**User Stories:** US8  
**Outcome:** One documented import/update workflow for upstream desktop code, plus compatibility tests that fail when upstream adds bridge calls the browser shim does not implement.

**Acceptance Criteria:**
- [ ] Import script: `scripts/import-upstream.sh` pulls latest desktop renderer code
- [ ] Patch application: custom mobile changes apply as git patches or merge commits
- [ ] Conflict resolution: documented workflow for resolving upstream conflicts
- [ ] Compatibility test suite: automated tests for all `window.hermesDesktop` bridge calls
- [ ] CI integration: compatibility tests run on PRs touching the renderer or shim
- [ ] Failure mode: tests fail with clear error naming the missing bridge call
- [ ] Documentation: `docs/upstream-sync.md` with step-by-step import instructions
- [ ] Rollback plan: documented steps to revert a broken upstream import

---

### Ticket 12: Default Startup Cutover and Legacy Surface Retirement

**Type:** AFK  
**Blocked by:** 5, 9, 10, 11  
**User Stories:** US1, US2, US6, US8  
**Outcome:** Deploy scripts, launchd, Docker, and docs start the new browser-hosted desktop port by default; the old copied WebUI is no longer the primary product surface.

**Acceptance Criteria:**
- [ ] Deploy script updated: default target is the new browser-hosted desktop port
- [ ] Launchd plist (macOS): starts the new port service on boot
- [ ] Docker Compose: default service is the new port, old WebUI commented or removed
- [ ] Documentation updated: all user-facing docs reference the new port URL
- [ ] Redirect: old WebUI URL redirects to new port (or shows deprecation notice)
- [ ] Monitoring: new port has health checks + alerting configured
- [ ] Rollback plan: documented steps to revert to old WebUI if critical issues arise
- [ ] Legacy retirement: old WebUI files archived or moved to `legacy/` directory
- [ ] Announcement: users notified of the cutover via changelog + in-app notice

---

## Appendix: User Stories Reference

| ID | Story |
|----|-------|
| US1 | From my phone, I can open a secure URL and use the official Hermes Desktop UI |
| US2 | My phone and desktop share the same sessions/goals/history because they use the same Hermes state |
| US3 | I can create and continue chats from my phone with live streaming |
| US4 | I can browse files and previews from my phone |
| US5 | I can use a terminal from my phone |
| US6 | I can configure local or remote Hermes backend access from the UI |
| US7 | I can install the app to my phone home screen and use it reliably |
| US8 | The fork stays maintainable as upstream Hermes Desktop changes |
