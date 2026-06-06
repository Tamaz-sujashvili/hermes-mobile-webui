from __future__ import annotations

from mobile_proxy.config import HERMES_APP_PORT_CEILING, HERMES_APP_PORT_FLOOR

DEFAULT_DASHBOARD_PORT = 9119
DEFAULT_PROXY_PORT = 9200


def assert_not_hermes_app_port(port: int, *, label: str) -> None:
    if HERMES_APP_PORT_FLOOR <= port <= HERMES_APP_PORT_CEILING:
        raise ValueError(
            f"{label}={port} is inside the Hermes.app reserved range "
            f"{HERMES_APP_PORT_FLOOR}-{HERMES_APP_PORT_CEILING}."
        )


def assert_dashboard_port(port: int) -> None:
    assert_not_hermes_app_port(port, label="dashboard port")
    if port == DEFAULT_PROXY_PORT:
        raise ValueError(
            f"Dashboard cannot use proxy port {DEFAULT_PROXY_PORT}; "
            f"use {DEFAULT_DASHBOARD_PORT}."
        )
