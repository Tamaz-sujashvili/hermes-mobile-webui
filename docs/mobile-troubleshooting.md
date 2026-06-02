# iPhone / Safari troubleshooting

## Safari says `Load failed`

Check these in order:

1. Make sure the phone is hitting the mobile proxy, not raw WebUI.
2. Retry in a fresh Safari tab.
3. Confirm your reverse proxy is not rewriting `Content-Encoding` or caching stale HTML/JS.
4. Confirm the mobile proxy can reach `hermes-webui` on its configured upstream.

This package normalizes proxy response headers specifically to avoid Safari's strict handling of mismatched `Content-Encoding`.

## Sessions are missing on mobile

Usually one of these is true:

- desktop and mobile are not pointed at the same Hermes state
- the browser is cached against an older origin or older frontend
- CLI/session bridging is disabled in the backend settings

Check:

- same `HERMES_HOME`
- same WebUI state directory
- same Docker volumes
- `show_cli_sessions` is enabled in WebUI settings

## Mobile shows a different session than desktop

The WebUI and the mobile proxy share session state; they do not merge separate databases.

If the histories diverge, you are almost certainly talking to different backends. Verify:

- the tunnel target
- the proxy upstream
- the WebUI instance on the Mac
- the active Docker project / volume set

## Login keeps failing

- Confirm the auth runtime was generated from the password you expect.
- If you rotated the password, regenerate the auth runtime and restart the proxy.
- On Docker, changing only `.env` does not invalidate an already-generated auth file inside `mobile-proxy-state`.

## launchd starts the WebUI, but MCP helpers fail with `npx: No such file or directory`

This is a macOS service PATH problem, not a WebUI auth problem.

launchd does not read your shell startup files, so Node installed through
`nvm`, `asdf`, or similar tools may be missing even though it works in
Terminal.

Check:

- your launchd plist sets a sane `PATH`
- if you use a user-managed Node install, set `HERMES_WEBUI_EXTRA_PATH` to its
  `bin` directory
- reload the WebUI service after editing the plist

Example:

```xml
<key>HERMES_WEBUI_EXTRA_PATH</key>
<string>/Users/youruser/.nvm/versions/node/v20.20.2/bin</string>
```
