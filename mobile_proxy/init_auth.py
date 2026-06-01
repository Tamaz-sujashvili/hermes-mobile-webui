from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path

from mobile_proxy.auth import generate_auth_payload, write_auth_file
from mobile_proxy.config import load_settings


def _read_password(args: argparse.Namespace) -> str:
    if args.password:
        return args.password
    if args.password_file:
        return Path(args.password_file).expanduser().read_text(encoding="utf-8").strip()
    first = getpass.getpass("Mobile proxy password: ").strip()
    second = getpass.getpass("Confirm password: ").strip()
    if not first:
        raise SystemExit("Password cannot be blank.")
    if first != second:
        raise SystemExit("Passwords do not match.")
    return first


def parse_args() -> argparse.Namespace:
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Create a Hermes Mobile WebUI auth file.")
    parser.add_argument(
        "--auth-path",
        default=str(settings.auth_path),
        help="Path to the generated auth.json runtime file.",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("HERMES_MOBILE_USERNAME", "hermes"),
        help="Username stored in the auth runtime file.",
    )
    parser.add_argument("--password", help="Bootstrap password. Prefer env or prompt.")
    parser.add_argument("--password-file", help="Read the password from a file.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing auth file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    password = _read_password(args)
    payload = generate_auth_payload(args.username.strip() or "hermes", password)
    path = write_auth_file(Path(args.auth_path).expanduser(), payload, force=args.force)
    print(f"Wrote mobile auth runtime to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
