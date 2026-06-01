from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

from mobile_proxy.config import MobileProxySettings


PBKDF2_ROUNDS = 200_000


@dataclass(frozen=True)
class AuthConfig:
    username: str
    salt_b64: str
    password_hash_b64: str
    session_secret: str


def _pbkdf2(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)


def generate_auth_payload(
    username: str,
    password: str,
    *,
    session_secret: str | None = None,
) -> dict[str, str]:
    salt = secrets.token_bytes(16)
    password_hash = _pbkdf2(password, salt)
    return {
        "username": username,
        "salt_b64": base64.b64encode(salt).decode("ascii"),
        "password_hash_b64": base64.b64encode(password_hash).decode("ascii"),
        "session_secret": session_secret or secrets.token_urlsafe(32),
    }


def write_auth_file(path: Path, payload: dict[str, str], *, force: bool = False) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        raise FileExistsError(f"Auth file already exists: {path}")
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def read_auth_file(path: Path) -> AuthConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return AuthConfig(
        username=str(payload["username"]),
        salt_b64=str(payload["salt_b64"]),
        password_hash_b64=str(payload["password_hash_b64"]),
        session_secret=str(payload["session_secret"]),
    )


def _bootstrap_password() -> str | None:
    password_file = os.getenv("HERMES_MOBILE_PASSWORD_FILE", "").strip()
    if password_file:
        value = Path(password_file).expanduser().read_text(encoding="utf-8").strip()
        return value or None
    value = os.getenv("HERMES_MOBILE_PASSWORD", "").strip()
    return value or None


def ensure_auth_file(settings: MobileProxySettings, *, force: bool = False) -> Path:
    if settings.auth_path.exists() and not force:
        try:
            os.chmod(settings.auth_path, 0o600)
        except OSError:
            pass
        return settings.auth_path
    password = _bootstrap_password()
    if not password:
        raise RuntimeError(
            "No mobile auth file found and no bootstrap password was supplied. "
            "Set HERMES_MOBILE_PASSWORD or HERMES_MOBILE_PASSWORD_FILE, "
            "or run scripts/create_mobile_auth.sh first."
        )
    username = os.getenv("HERMES_MOBILE_USERNAME", "hermes").strip() or "hermes"
    payload = generate_auth_payload(
        username,
        password,
        session_secret=os.getenv("HERMES_MOBILE_SESSION_SECRET", "").strip() or None,
    )
    return write_auth_file(settings.auth_path, payload, force=True)


def load_or_create_auth_config(settings: MobileProxySettings) -> AuthConfig:
    path = ensure_auth_file(settings)
    return read_auth_file(path)


def verify_password(password: str, cfg: AuthConfig) -> bool:
    salt = base64.b64decode(cfg.salt_b64)
    expected = base64.b64decode(cfg.password_hash_b64)
    actual = _pbkdf2(password, salt)
    return hmac.compare_digest(actual, expected)


def sign(data: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), data.encode("utf-8"), hashlib.sha256).hexdigest()


def make_session(username: str, secret: str, session_ttl: int) -> str:
    expires = int(time.time()) + session_ttl
    nonce = secrets.token_urlsafe(12)
    payload = f"{username}|{expires}|{nonce}"
    return f"{payload}|{sign(payload, secret)}"


def read_session(raw: str | None, secret: str) -> str | None:
    if not raw:
        return None
    try:
        username, expires_s, nonce, sig = raw.split("|", 3)
        payload = f"{username}|{expires_s}|{nonce}"
    except ValueError:
        return None
    if not hmac.compare_digest(sig, sign(payload, secret)):
        return None
    try:
        expires = int(expires_s)
    except ValueError:
        return None
    if expires < int(time.time()):
        return None
    return username
