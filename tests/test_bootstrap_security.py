from __future__ import annotations
from pathlib import Path

import pytest

import bootstrap


class _FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_wait_for_health_parses_json_without_whitespace(monkeypatch):
    monkeypatch.setattr(
        bootstrap.urllib.request,
        "urlopen",
        lambda *args, **kwargs: _FakeResponse(b'{"status":"ok"}'),
    )
    assert bootstrap.wait_for_health("http://127.0.0.1:8787/health", timeout=0.1) is True


def test_install_hermes_agent_requires_explicit_opt_in():
    with pytest.raises(RuntimeError, match="Automatic installation is disabled by default"):
        bootstrap.install_hermes_agent()


def test_install_hermes_agent_downloads_temp_script_when_opted_in(monkeypatch):
    ran = {}
    removed = {}

    monkeypatch.setattr(
        bootstrap.urllib.request,
        "urlopen",
        lambda *args, **kwargs: _FakeResponse(b"#!/bin/bash\necho installer\n"),
    )

    def fake_run(cmd, check):
        ran["cmd"] = cmd
        script_path = Path(cmd[1])
        assert script_path.exists()
        assert script_path.read_text(encoding="utf-8") == "#!/bin/bash\necho installer\n"
        return None

    monkeypatch.setattr(bootstrap.subprocess, "run", fake_run)

    real_unlink = Path.unlink

    def tracking_unlink(self, *args, **kwargs):
        removed["path"] = self
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", tracking_unlink)

    bootstrap.install_hermes_agent(allow_remote_script=True)

    assert ran["cmd"][0] == "/bin/bash"
    assert removed["path"] == Path(ran["cmd"][1])
