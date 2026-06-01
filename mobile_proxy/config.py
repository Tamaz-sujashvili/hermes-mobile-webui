from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


_TRUE_VALUES = {"1", "true", "yes", "on"}


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_VALUES


def _default_hermes_home() -> Path:
    raw = os.getenv("HERMES_HOME", "")
    if raw.strip():
        return Path(raw).expanduser()
    return Path.home() / ".hermes"


def _default_runtime_dir() -> Path:
    return _default_hermes_home() / "mobile-webui"


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class MobileProxySettings:
    runtime_dir: Path
    auth_path: Path
    client_error_log_path: Path
    webui_upstream_base: str
    dashboard_upstream_base: str
    disable_dashboard: bool
    proxy_host: str
    proxy_port: int
    session_cookie: str
    session_ttl: int
    dashboard_prefix: str


@lru_cache(maxsize=1)
def load_settings() -> MobileProxySettings:
    runtime_dir = Path(
        os.getenv("HERMES_MOBILE_RUNTIME_DIR", str(_default_runtime_dir()))
    ).expanduser()
    auth_path = Path(
        os.getenv("HERMES_MOBILE_AUTH_PATH", str(runtime_dir / "auth.json"))
    ).expanduser()
    client_error_log_path = Path(
        os.getenv(
            "HERMES_MOBILE_CLIENT_ERROR_LOG_PATH",
            str(runtime_dir / "client-errors.log"),
        )
    ).expanduser()
    return MobileProxySettings(
        runtime_dir=runtime_dir,
        auth_path=auth_path,
        client_error_log_path=client_error_log_path,
        webui_upstream_base=os.getenv(
            "HERMES_MOBILE_WEBUI_UPSTREAM",
            os.getenv("HERMES_MOBILE_UPSTREAM", "http://127.0.0.1:8787"),
        ).rstrip("/"),
        dashboard_upstream_base=os.getenv(
            "HERMES_MOBILE_DASHBOARD_UPSTREAM",
            "http://127.0.0.1:9119",
        ).rstrip("/"),
        disable_dashboard=_env_flag("HERMES_MOBILE_DISABLE_DASHBOARD", True),
        proxy_host=os.getenv("HERMES_MOBILE_PROXY_HOST", "127.0.0.1").strip()
        or "127.0.0.1",
        proxy_port=_int_env("HERMES_MOBILE_PROXY_PORT", 9120),
        session_cookie=os.getenv("HERMES_MOBILE_SESSION_COOKIE", "hermes_mobile_session").strip()
        or "hermes_mobile_session",
        session_ttl=_int_env("HERMES_MOBILE_SESSION_TTL", 60 * 60 * 24 * 14),
        dashboard_prefix=os.getenv("HERMES_MOBILE_DASHBOARD_PREFIX", "/dashboard").strip()
        or "/dashboard",
    )
