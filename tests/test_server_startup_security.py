from __future__ import annotations

import builtins
from types import SimpleNamespace

import pytest

import api.auth as auth
import api.config as config
import api.gateway_watcher as gateway_watcher
import api.models as models
import api.session_lifecycle as session_lifecycle
import api.session_recovery as session_recovery
import server


def test_resolve_address_family_prefers_ipv6_for_literal():
    assert server._resolve_address_family("::1", 8787) == server.socket.AF_INET6


def test_resolve_address_family_uses_getaddrinfo_for_hostname(monkeypatch):
    monkeypatch.setattr(
        server.socket,
        "getaddrinfo",
        lambda host, port, family, socktype, proto, flags: [
            (server.socket.AF_INET6, socktype, proto, "", ("::1", port, 0, 0))
        ],
    )
    assert server._resolve_address_family("example.test", 8787) == server.socket.AF_INET6


def test_server_refuses_public_bind_without_password(monkeypatch):
    monkeypatch.setattr(server, "HOST", "192.168.1.10")
    monkeypatch.setattr(server, "PORT", 8787)
    monkeypatch.setattr(server, "fix_credential_permissions", lambda: None)
    monkeypatch.setattr(server, "_raise_fd_soft_limit", lambda target=4096: {"status": "unchanged", "soft": 1024, "hard": 1024})
    monkeypatch.setattr(config, "print_startup_config", lambda: None)
    monkeypatch.setattr(config, "verify_hermes_imports", lambda: (True, [], {}))
    monkeypatch.setattr(auth, "is_auth_enabled", lambda: False)
    monkeypatch.setattr(models, "_active_state_db_path", lambda: None)
    monkeypatch.setattr(session_recovery, "recover_all_sessions_on_startup", lambda *a, **k: {"restored": 0, "scanned": 0})
    monkeypatch.setattr(gateway_watcher, "start_watcher", lambda: None)
    monkeypatch.setattr(session_lifecycle, "drain_all_on_shutdown", lambda: None)
    monkeypatch.delenv("HERMES_WEBUI_ALLOW_INSECURE_BIND", raising=False)

    real_open = builtins.open

    def fake_open(path, *args, **kwargs):
        if path == "/.within_container":
            raise FileNotFoundError
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)

    with pytest.raises(RuntimeError, match="Refusing to start without authentication"):
        server.main()


def test_server_allows_public_bind_with_explicit_override(monkeypatch):
    monkeypatch.setattr(server, "HOST", "192.168.1.10")
    monkeypatch.setattr(server, "PORT", 8787)
    monkeypatch.setattr(server, "fix_credential_permissions", lambda: None)
    monkeypatch.setattr(server, "_raise_fd_soft_limit", lambda target=4096: {"status": "unchanged", "soft": 1024, "hard": 1024})
    monkeypatch.setattr(config, "print_startup_config", lambda: None)
    monkeypatch.setattr(config, "verify_hermes_imports", lambda: (True, [], {}))
    monkeypatch.setattr(auth, "is_auth_enabled", lambda: False)
    monkeypatch.setattr(models, "_active_state_db_path", lambda: None)
    monkeypatch.setattr(session_recovery, "recover_all_sessions_on_startup", lambda *a, **k: {"restored": 0, "scanned": 0})
    monkeypatch.setattr(gateway_watcher, "start_watcher", lambda: None)
    monkeypatch.setattr(session_lifecycle, "drain_all_on_shutdown", lambda: None)
    monkeypatch.setenv("HERMES_WEBUI_ALLOW_INSECURE_BIND", "1")
    monkeypatch.setattr(server, "STATE_DIR", SimpleNamespace(mkdir=lambda **kwargs: None))
    monkeypatch.setattr(server, "SESSION_DIR", SimpleNamespace(mkdir=lambda **kwargs: None))
    monkeypatch.setattr(server, "DEFAULT_WORKSPACE", SimpleNamespace(mkdir=lambda **kwargs: None))

    class _FakeHTTPServer:
        def __init__(self, *_args, **_kwargs):
            pass

        def serve_forever(self):
            raise RuntimeError("stop-test-server")

    monkeypatch.setattr(server, "QuietHTTPServer", _FakeHTTPServer)

    real_open = builtins.open

    def fake_open(path, *args, **kwargs):
        if path == "/.within_container":
            raise FileNotFoundError
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fake_open)

    with pytest.raises(RuntimeError, match="stop-test-server"):
        server.main()
