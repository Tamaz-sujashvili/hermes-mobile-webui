from __future__ import annotations

import asyncio
import json
import time
from typing import Iterable
from urllib.parse import urlencode, urlsplit, urlunsplit

import httpx
import websockets
from fastapi import FastAPI, Form, Request, WebSocket
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from mobile_proxy.auth import (
    AuthConfig,
    load_or_create_auth_config,
    make_session,
    read_session,
    verify_password,
)
from mobile_proxy.config import MobileProxySettings, load_settings


APP = FastAPI(title="Hermes Mobile WebUI Proxy")
SETTINGS = load_settings()
AUTH_CONFIG: AuthConfig | None = None

HTTP_TIMEOUT = httpx.Timeout(120.0, connect=20.0)
DROP_REQ_HEADERS = {
    "host",
    "content-length",
    "connection",
    "accept-encoding",
    "upgrade",
    "sec-websocket-key",
    "sec-websocket-version",
    "sec-websocket-extensions",
    "sec-websocket-accept",
}
DROP_RESP_HEADERS = {
    "content-length",
    "content-encoding",
    "connection",
    "keep-alive",
    "transfer-encoding",
    "date",
    "server",
}
PUBLIC_PATHS = {
    "/login",
    "/logout",
    "/healthz",
    "/manifest.json",
    "/favicon.ico",
    "/sw.js",
    "/__client-log",
}
PUBLIC_PREFIXES = ("/static/",)


def _auth_config() -> AuthConfig:
    if AUTH_CONFIG is None:
        raise RuntimeError("Mobile proxy auth is not initialized.")
    return AUTH_CONFIG


@APP.on_event("startup")
async def _startup() -> None:
    global AUTH_CONFIG
    SETTINGS.runtime_dir.mkdir(parents=True, exist_ok=True)
    AUTH_CONFIG = load_or_create_auth_config(SETTINGS)


def _is_authenticated_request(request: Request, cfg: AuthConfig) -> bool:
    session = request.cookies.get(SETTINGS.session_cookie)
    return read_session(session, cfg.session_secret) == cfg.username


def _is_authenticated_ws(websocket: WebSocket, cfg: AuthConfig) -> bool:
    session = websocket.cookies.get(SETTINGS.session_cookie)
    return read_session(session, cfg.session_secret) == cfg.username


def _safe_next(raw: str | None) -> str:
    if not raw or not raw.startswith("/"):
        return "/"
    if raw.startswith("//") or raw.startswith("/login") or raw.startswith("/logout"):
        return "/"
    return raw


def _pick_upstream(path: str) -> tuple[str, str, str]:
    normalized = path if path.startswith("/") else f"/{path}"
    if SETTINGS.disable_dashboard and (
        normalized == SETTINGS.dashboard_prefix
        or normalized.startswith(f"{SETTINGS.dashboard_prefix}/")
    ):
        return SETTINGS.webui_upstream_base, "", ""
    if normalized == SETTINGS.dashboard_prefix or normalized.startswith(
        f"{SETTINGS.dashboard_prefix}/"
    ):
        remainder = normalized[len(SETTINGS.dashboard_prefix) :].lstrip("/")
        return SETTINGS.dashboard_upstream_base, remainder, SETTINGS.dashboard_prefix
    return SETTINGS.webui_upstream_base, normalized.lstrip("/"), ""


def _client_headers(
    source,
    *,
    forwarded_prefix: str = "",
    forwarded_proto: str | None = None,
) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in source.headers.items():
        if key.lower() in DROP_REQ_HEADERS:
            continue
        headers[key] = value
    if forwarded_prefix:
        headers["X-Forwarded-Prefix"] = forwarded_prefix
    headers["X-Forwarded-Host"] = source.headers.get("host", source.url.netloc)
    headers["X-Forwarded-Proto"] = forwarded_proto or source.headers.get(
        "x-forwarded-proto",
        source.url.scheme,
    )
    return headers


def _rewrite_location(value: str, forwarded_prefix: str) -> str:
    if not forwarded_prefix or not value:
        return value
    parsed = urlsplit(value)
    path = parsed.path or "/"
    if path.startswith(forwarded_prefix):
        return value
    dashboard_host = urlsplit(SETTINGS.dashboard_upstream_base)
    if parsed.scheme and parsed.netloc:
        same_dashboard = (
            parsed.scheme == dashboard_host.scheme
            and parsed.netloc == dashboard_host.netloc
        )
        if not same_dashboard:
            return value
    rewritten = (
        f"{forwarded_prefix}{path}" if path.startswith("/") else f"{forwarded_prefix}/{path}"
    )
    return urlunsplit(("", "", rewritten, parsed.query, parsed.fragment))


def _response_headers(
    headers: httpx.Headers,
    *,
    forwarded_prefix: str = "",
    disable_cache: bool = False,
) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in headers.items():
        lower = key.lower()
        if lower in DROP_RESP_HEADERS:
            continue
        if disable_cache and lower in {"cache-control", "pragma"}:
            continue
        if lower == "location":
            value = _rewrite_location(value, forwarded_prefix)
        out[key] = value
    if disable_cache:
        out["Cache-Control"] = "no-store, no-cache, must-revalidate"
        out["Pragma"] = "no-cache"
    return out


def _upstream_url(base: str, path: str, query_items: Iterable[tuple[str, str]]) -> str:
    url = f"{base}/{path}" if path else f"{base}/"
    query = urlencode(list(query_items), doseq=True)
    return f"{url}?{query}" if query else url


@APP.middleware("http")
async def auth_middleware(request: Request, call_next):
    cfg = _auth_config()
    path = request.url.path
    if path in PUBLIC_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES):
        return await call_next(request)
    if _is_authenticated_request(request, cfg):
        return await call_next(request)
    next_path = _safe_next(path + (f"?{request.url.query}" if request.url.query else ""))
    return RedirectResponse(url=f"/login?next={next_path}", status_code=302)


@APP.get("/healthz")
async def healthz():
    return {
        "ok": True,
        "dashboard_disabled": SETTINGS.disable_dashboard,
    }


@APP.post("/__client-log")
async def client_log(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {"raw": (await request.body()).decode("utf-8", "replace")}
    record = {
        "ts": int(time.time()),
        "ip": request.client.host if request.client else None,
        "ua": request.headers.get("user-agent"),
        "referer": request.headers.get("referer"),
        "payload": payload,
    }
    SETTINGS.client_error_log_path.parent.mkdir(parents=True, exist_ok=True)
    with SETTINGS.client_error_log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"ok": True}


@APP.get("/login")
async def login_page(next: str = "/", error: str = ""):
    next_value = _safe_next(next)
    error_html = "<p style='color:#b42318'>Wrong password.</p>" if error else ""
    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Hermes Mobile WebUI Login</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      background: linear-gradient(180deg, #101828 0%, #0b1220 100%);
      color: #f8fafc;
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
    }}
    form {{
      width: min(92vw, 360px);
      background: rgba(15, 23, 42, 0.92);
      border: 1px solid rgba(148, 163, 184, 0.2);
      border-radius: 18px;
      padding: 24px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.35);
    }}
    h1 {{ margin: 0 0 8px; font-size: 24px; }}
    p {{ margin: 0 0 16px; color: #cbd5e1; }}
    input {{
      width: 100%;
      box-sizing: border-box;
      padding: 14px 12px;
      border-radius: 12px;
      border: 1px solid #334155;
      background: #0f172a;
      color: white;
      margin: 12px 0 16px;
      font-size: 16px;
    }}
    button {{
      width: 100%;
      padding: 14px 12px;
      border: 0;
      border-radius: 12px;
      background: #f59e0b;
      color: #111827;
      font-weight: 700;
      font-size: 16px;
    }}
  </style>
</head>
<body>
  <form method="post" action="/login">
    <h1>Hermes Mobile WebUI</h1>
    <p>Enter the mobile access password.</p>
    {error_html}
    <input type="hidden" name="next" value="{next_value}">
    <input type="password" name="password" placeholder="Password" autocomplete="current-password" autofocus>
    <button type="submit">Open Hermes</button>
  </form>
</body>
</html>"""
    return HTMLResponse(html)


@APP.post("/login")
async def login_submit(password: str = Form(...), next: str = Form("/")):
    cfg = _auth_config()
    safe_next = _safe_next(next)
    if not verify_password(password, cfg):
        return RedirectResponse(url=f"/login?next={safe_next}&error=1", status_code=303)
    session = make_session(cfg.username, cfg.session_secret, SETTINGS.session_ttl)
    response = RedirectResponse(url=safe_next, status_code=303)
    response.set_cookie(
        SETTINGS.session_cookie,
        session,
        max_age=SETTINGS.session_ttl,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )
    return response


@APP.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SETTINGS.session_cookie, path="/")
    return response


@APP.get("/dashboard")
async def dashboard_root_redirect():
    if SETTINGS.disable_dashboard:
        return RedirectResponse(url="/", status_code=307)
    return RedirectResponse(url="/dashboard/", status_code=307)


@APP.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy_http(path: str, request: Request):
    if SETTINGS.disable_dashboard and (
        request.url.path == SETTINGS.dashboard_prefix
        or request.url.path.startswith(f"{SETTINGS.dashboard_prefix}/")
    ):
        return RedirectResponse(url="/", status_code=307)
    upstream_base, upstream_path, forwarded_prefix = _pick_upstream(request.url.path)
    url = _upstream_url(upstream_base, upstream_path, request.query_params.multi_items())
    body = await request.body()
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=False) as client:
        upstream = await client.request(
            method=request.method,
            url=url,
            content=body,
            headers=_client_headers(request, forwarded_prefix=forwarded_prefix),
        )
    content_type = upstream.headers.get("content-type", "")
    disable_cache = any(
        marker in content_type
        for marker in ("text/html", "javascript", "text/css", "application/json")
    )
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=_response_headers(
            upstream.headers,
            forwarded_prefix=forwarded_prefix,
            disable_cache=disable_cache,
        ),
    )


@APP.websocket("/{path:path}")
async def proxy_ws(websocket: WebSocket, path: str):
    cfg = _auth_config()
    if not _is_authenticated_ws(websocket, cfg):
        await websocket.close(code=1008)
        return
    if SETTINGS.disable_dashboard and (
        websocket.url.path == SETTINGS.dashboard_prefix
        or websocket.url.path.startswith(f"{SETTINGS.dashboard_prefix}/")
    ):
        await websocket.close(code=1008)
        return

    upstream_base, upstream_path, forwarded_prefix = _pick_upstream(websocket.url.path)
    qs = urlencode(list(websocket.query_params.multi_items()), doseq=True)
    upstream = upstream_base.replace("http://", "ws://").replace("https://", "wss://")
    upstream_url = f"{upstream}/{upstream_path}" if upstream_path else f"{upstream}/"
    if qs:
        upstream_url = f"{upstream_url}?{qs}"

    await websocket.accept()

    async with websockets.connect(
        upstream_url,
        max_size=None,
        additional_headers=_client_headers(
            websocket,
            forwarded_prefix=forwarded_prefix,
            forwarded_proto=websocket.headers.get("x-forwarded-proto", "https"),
        ),
    ) as upstream_ws:
        async def client_to_upstream():
            while True:
                message = await websocket.receive()
                if "text" in message and message["text"] is not None:
                    await upstream_ws.send(message["text"])
                elif "bytes" in message and message["bytes"] is not None:
                    await upstream_ws.send(message["bytes"])
                elif message.get("type") == "websocket.disconnect":
                    await upstream_ws.close()
                    return

        async def upstream_to_client():
            while True:
                message = await upstream_ws.recv()
                if isinstance(message, bytes):
                    await websocket.send_bytes(message)
                else:
                    await websocket.send_text(message)

        done, pending = await asyncio.wait(
            {
                asyncio.create_task(client_to_upstream()),
                asyncio.create_task(upstream_to_client()),
            },
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        for task in done:
            exc = task.exception()
            if exc:
                raise exc
