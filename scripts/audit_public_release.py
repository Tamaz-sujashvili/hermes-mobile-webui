#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


BANNED_FILE_NAMES = {
    "auth.json",
    "public_url.txt",
    "client-errors.log",
}
BANNED_PATH_PARTS = {
    "mobile-proxy-state",
}
BANNED_CONTENT_PATTERNS = {
    "local-user-path": re.compile(r"/Users/tazo\b"),
    "live-cloudflare-tunnel": re.compile(r"\b[\w-]+\.trycloudflare\.com\b"),
    "local-runtime-url": re.compile(r"https?://(?:closing-omissions-out-planets|hong-linking-sandy-adipex|prayers-answer-detail-register)\.trycloudflare\.com\b"),
}
TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".py",
    ".js",
    ".css",
    ".html",
    ".json",
    ".yml",
    ".yaml",
    ".sh",
    ".plist",
    ".ini",
    ".toml",
    ".env",
    ".example",
}
IGNORED_DIRS = {
    ".git",
    ".venv",
    "archive",
    "__pycache__",
}
SELF_ALLOWED_FILES = {
    Path("scripts/audit_public_release.py"),
    Path("tests/test_public_release_audit.py"),
}


def iter_files(repo_root: Path):
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(repo_root)
        if any(part in IGNORED_DIRS for part in rel.parts):
            continue
        yield path, rel


def should_scan_text(path: Path) -> bool:
    if path.name == "LICENSE":
        return True
    return any(path.name.endswith(suffix) for suffix in TEXT_SUFFIXES)


def scan_repo(repo_root: Path) -> list[str]:
    findings: list[str] = []
    for path, rel in iter_files(repo_root):
        if rel in SELF_ALLOWED_FILES:
            continue
        if path.name in BANNED_FILE_NAMES:
            findings.append(f"banned runtime file committed: {rel}")
        if any(part in BANNED_PATH_PARTS for part in rel.parts):
            findings.append(f"banned runtime path committed: {rel}")
        if not should_scan_text(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in BANNED_CONTENT_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{label}: {rel}")
    return findings


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    findings = scan_repo(repo_root)
    if findings:
        print("Public release audit failed:")
        for finding in findings:
            print(f" - {finding}")
        return 1
    print("Public release audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
