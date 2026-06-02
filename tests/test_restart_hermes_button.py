"""Regression coverage for the System-pane restart controls.

The lightweight WebUI already exposed a "Restart WebUI" button, but it only
queued a relaunch and did not provide a "restart the whole local Hermes stack"
control. These tests pin both the new frontend affordance and the backend
restart routes so future refactors do not silently remove them.
"""

from __future__ import annotations

import io
import json
import os
from urllib.parse import urlparse


_SRC = os.path.join(os.path.dirname(__file__), "..")


def _read(name: str) -> str:
    with open(os.path.join(_SRC, name), encoding="utf-8") as fh:
        return fh.read()


class _FakeHandler:
    """Minimal request-handler stand-in for routes.handle_post tests."""

    def __init__(self, body_bytes: bytes = b""):
        self.status = None
        self.sent_headers: list[tuple[str, str]] = []
        self.body = bytearray()
        self.wfile = self
        self.rfile = io.BytesIO(body_bytes)
        self.headers = {"Content-Length": str(len(body_bytes))}
        self.server = object()

    def send_response(self, status):
        self.status = status

    def send_header(self, name, value):
        self.sent_headers.append((name, value))

    def end_headers(self):
        pass

    def write(self, data):
        self.body.extend(data)

    def json_body(self):
        return json.loads(bytes(self.body).decode("utf-8"))


def _post(path: str):
    from api.routes import handle_post

    handler = _FakeHandler()
    parsed = urlparse(f"http://example.com{path}")
    handle_post(handler, parsed)
    return handler


def test_system_pane_has_restart_hermes_button():
    html = _read("static/index.html")
    assert 'id="btnRestartHermes"' in html
    assert 'id="btnRestartHermesLabel"' in html
    assert 'id="restartHermesStatus"' in html
    assert 'data-ui-click="restartHermesStack()"' in html
    assert 'Restart the full local Hermes stack' in html


def test_panels_js_has_restart_hermes_stack_handler():
    js = _read("static/panels.js")
    assert "function restartHermesStack()" in js
    assert "endpoint:'/api/server/restart-all'" in js or "/api/server/restart-all" in js
    assert "buttonId:'btnRestartHermes'" in js or "btnRestartHermes" in js
    assert "labelId:'btnRestartHermesLabel'" in js or "btnRestartHermesLabel" in js
    assert "statusId:'restartHermesStatus'" in js or "restartHermesStatus" in js


def test_restart_endpoint_uses_webui_only_restart(monkeypatch):
    import api.routes as routes

    restart_flags: list[bool] = []
    scheduled: list[object] = []

    monkeypatch.setattr(routes, "_check_csrf", lambda handler: True)
    monkeypatch.setattr(
        routes,
        "_spawn_server_restart",
        lambda restart_gateway=False: restart_flags.append(restart_gateway)
        or {"ok": True, "reload_after_ms": 3000, "restart_gateway": restart_gateway},
    )
    monkeypatch.setattr(routes, "_schedule_server_shutdown", lambda handler: scheduled.append(handler))

    handler = _post("/api/server/restart")

    assert handler.status == 200
    assert handler.json_body() == {
        "ok": True,
        "reload_after_ms": 3000,
        "restart_gateway": False,
    }
    assert restart_flags == [False]
    assert len(scheduled) == 0  # /restart does NOT schedule shutdown


def test_restart_all_endpoint_restarts_gateway_and_webui(monkeypatch):
    import api.routes as routes

    restart_flags: list[bool] = []
    scheduled: list[object] = []

    monkeypatch.setattr(routes, "_check_csrf", lambda handler: True)
    monkeypatch.setattr(
        routes,
        "_spawn_server_restart",
        lambda restart_gateway=False: restart_flags.append(restart_gateway)
        or {"ok": True, "reload_after_ms": 5000, "restart_gateway": restart_gateway},
    )
    monkeypatch.setattr(routes, "_schedule_server_shutdown", lambda handler: scheduled.append(handler))

    handler = _post("/api/server/restart-all")

    assert handler.status == 200
    assert handler.json_body() == {
        "ok": True,
        "reload_after_ms": 5000,
        "restart_gateway": True,
    }
    assert restart_flags == [True]
    assert len(scheduled) == 1  # /restart-all DOES schedule shutdown


def test_spawn_server_restart_helper_uses_detached_restarter(monkeypatch):
    import api.routes as routes

    popen_calls: list[tuple[list[str], dict]] = []

    class _Proc:
        pass

    def fake_popen(args, **kwargs):
        popen_calls.append((args, kwargs))
        return _Proc()

    monkeypatch.setattr(routes.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(routes.os, "getpid", lambda: 4242)
    monkeypatch.setenv("HERMES_WEBUI_HOST", "127.0.0.1")
    monkeypatch.setenv("HERMES_WEBUI_PORT", "8787")

    payload = routes._spawn_server_restart(restart_gateway=True)

    assert payload == {
        "ok": True,
        "reload_after_ms": 5000,
        "restart_gateway": True,
    }
    assert len(popen_calls) == 1
    args, kwargs = popen_calls[0]
    # The helper checks for ctl.sh first; if it exists, that's used instead of
    # the Python in-process fallback, so don't assert exact args.
    assert len(args) >= 2
    assert kwargs["start_new_session"] is True
    assert kwargs.get("cwd")
