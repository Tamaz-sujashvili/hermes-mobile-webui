from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest

from mobile_proxy import app as mobile_app
from mobile_proxy.auth import (
    generate_auth_payload,
    make_session,
    read_auth_file,
    read_session,
    write_auth_file,
)


@pytest.mark.asyncio
async def test_healthz_payload_does_not_expose_runtime_path():
    payload = await mobile_app.healthz()
    assert payload["ok"] is True
    assert "runtime_dir" not in payload


def test_response_headers_strip_content_encoding_and_disable_cache():
    headers = httpx.Headers(
        {
            "Content-Encoding": "gzip",
            "Content-Type": "application/json",
            "Cache-Control": "public, max-age=3600",
            "Location": "http://127.0.0.1:9119/chat",
        }
    )
    out = mobile_app._response_headers(
        headers,
        forwarded_prefix="/dashboard",
        disable_cache=True,
    )
    lowered = {k.lower(): v for k, v in out.items()}
    assert "content-encoding" not in lowered
    assert lowered["cache-control"] == "no-store, no-cache, must-revalidate"
    assert lowered["pragma"] == "no-cache"
    assert lowered["location"] == "/dashboard/chat"


def test_auth_runtime_file_is_private(tmp_path: Path):
    payload = generate_auth_payload("hermes", "password-123")
    path = write_auth_file(tmp_path / "auth.json", payload)
    mode = path.stat().st_mode & 0o777
    assert mode == 0o600
    cfg = read_auth_file(path)
    assert cfg.username == "hermes"


def test_session_roundtrip():
    raw = make_session("hermes", "secret", 60)
    assert read_session(raw, "secret") == "hermes"
    assert read_session(raw, "wrong-secret") is None
