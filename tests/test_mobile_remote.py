import pytest

from mobile_proxy.config import HERMES_APP_PORT_CEILING, HERMES_APP_PORT_FLOOR, load_settings
from services.port_policy import (
    DEFAULT_PROXY_PORT,
    assert_dashboard_port,
    assert_not_hermes_app_port,
)


def test_proxy_default_port_avoids_hermes_app_range(monkeypatch):
    monkeypatch.delenv("HERMES_MOBILE_PROXY_PORT", raising=False)
    monkeypatch.setenv("HERMES_MOBILE_RUNTIME_DIR", "/tmp/hermes-mobile-remote-test")
    load_settings.cache_clear()
    settings = load_settings()
    assert settings.proxy_port == DEFAULT_PROXY_PORT
    assert settings.proxy_port > HERMES_APP_PORT_CEILING
    assert settings.proxy_port != 9119
    assert settings.upstream_base.endswith(":9119")


def test_proxy_rejects_hermes_app_port(monkeypatch):
    monkeypatch.setenv("HERMES_MOBILE_PROXY_PORT", "9120")
    monkeypatch.setenv("HERMES_MOBILE_RUNTIME_DIR", "/tmp/hermes-mobile-remote-test")
    load_settings.cache_clear()
    with pytest.raises(ValueError, match="9120"):
        load_settings()


def test_dashboard_port_policy():
    assert_not_hermes_app_port(9200, label="proxy")
    with pytest.raises(ValueError):
        assert_dashboard_port(9121)
