"""Regression test: browser-executed inline event attributes must stay gone."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    ROOT / "static" / "index.html",
    ROOT / "static" / "onboarding.js",
    ROOT / "static" / "ui.js",
    ROOT / "static" / "sessions.js",
    ROOT / "static" / "panels.js",
]


def test_no_browser_executed_inline_event_attributes_remain():
    pattern = re.compile(r"(?<!\.)\bon[a-z]+=(?:\"|')")
    offenders = []
    for path in TARGETS:
        text = path.read_text(encoding="utf-8")
        match = pattern.search(text)
        if match:
            offenders.append(f"{path.name}:{match.group(0)}")
    assert not offenders, f"Inline event attributes must stay removed: {offenders}"


def test_inline_action_router_is_loaded_from_index():
    text = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    assert 'static/inline-actions.js?v=__WEBUI_VERSION__' in text
