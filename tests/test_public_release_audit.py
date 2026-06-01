from __future__ import annotations

import importlib.util
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "audit_public_release.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("audit_public_release", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_scan_repo_passes_clean_tree(tmp_path: Path):
    mod = _load_module()
    (tmp_path / "README.md").write_text("clean repo\n", encoding="utf-8")
    assert mod.scan_repo(tmp_path) == []


def test_scan_repo_flags_runtime_artifacts_and_live_urls(tmp_path: Path):
    mod = _load_module()
    (tmp_path / "auth.json").write_text('{"session_secret":"x"}\n', encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "https://closing-omissions-out-planets.trycloudflare.com\n/Users/tazo/private\n",
        encoding="utf-8",
    )
    findings = mod.scan_repo(tmp_path)
    assert any("banned runtime file committed" in item for item in findings)
    assert any("live-cloudflare-tunnel" in item for item in findings)
    assert any("local-user-path" in item for item in findings)
