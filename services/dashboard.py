#!/usr/bin/env python3
"""Launch the official Hermes dashboard for iPhone/browser access (port 9119)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from services.port_policy import DEFAULT_DASHBOARD_PORT, assert_dashboard_port


def _hermes_home() -> Path:
    raw = os.getenv("HERMES_HOME", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".hermes"


def _python(hermes_home: Path) -> Path:
    override = os.getenv("HERMES_MOBILE_PYTHON", "").strip()
    if override:
        return Path(override).expanduser()
    venv_python = hermes_home / "hermes-agent" / "venv" / "bin" / "python"
    if venv_python.is_file():
        return venv_python
    raise SystemExit(
        f"Hermes agent venv not found at {venv_python}. "
        "Install Hermes Agent or set HERMES_MOBILE_PYTHON."
    )


def _web_dist(hermes_home: Path) -> Path:
    override = os.getenv("HERMES_WEB_DIST", "").strip()
    if override:
        return Path(override).expanduser()
    return hermes_home / "hermes-agent" / "hermes_cli" / "web_dist"


def build_env(hermes_home: Path, web_dist: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["HERMES_HOME"] = str(hermes_home)
    env["HERMES_WEB_DIST"] = str(web_dist)
    extra = os.getenv("HERMES_WEBUI_EXTRA_PATH", "").strip()
    if extra:
        env["PATH"] = f"{extra}:{env.get('PATH', '')}"
    return env


def build_command(
    *,
    host: str,
    port: int,
    hermes_home: Path,
) -> list[str]:
    assert_dashboard_port(port)
    python = _python(hermes_home)
    return [
        str(python),
        "-m",
        "hermes_cli.main",
        "dashboard",
        "--no-open",
        "--host",
        host,
        "--port",
        str(port),
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_DASHBOARD_PORT)
    args = parser.parse_args(argv)

    hermes_home = _hermes_home()
    web_dist = _web_dist(hermes_home)
    index = web_dist / "index.html"
    if not index.is_file():
        print(
            f"Dashboard frontend missing at {index}.\n"
            "Build it once:\n"
            f"  cd {hermes_home / 'hermes-agent' / 'web'} && npm install && npm run build",
            file=sys.stderr,
        )
        return 1

    cmd = build_command(host=args.host, port=args.port, hermes_home=hermes_home)
    env = build_env(hermes_home, web_dist)
    print("Starting:", " ".join(cmd), file=sys.stderr)
    return subprocess.call(cmd, env=env, cwd=str(hermes_home))


if __name__ == "__main__":
    raise SystemExit(main())
