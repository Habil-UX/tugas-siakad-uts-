import base64
import hashlib
import hmac
import json
import os
import time
from typing import Callable, Iterable, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_model import AppUser

SECRET_KEY = os.getenv("SECRET_KEY", "siakad-default-hmac-secret-key-2026")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "siakad-webhook-secret-2026")
TOKEN_TTL_SECONDS = 86400


def hash_password(password: str, salt: Optional[str] = None) -> str:
    if salt is None:
        salt = hashlib.sha256(os.urandom(16)).hexdigest()[:16]
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    )
    return f"{salt}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    if "$" not in stored_hash:
        return False
    salt, _ = stored_hash.split("$", 1)
    expected = hash_password(password, salt=salt)
    return hmac.compare_digest(expected, stored_hash)


def create_access_token(
    payload: dict,
    expires_in: int = TOKEN_TTL_SECONDS,
    secret: str = SECRET_KEY,
) -> str:
    body = {
        **payload,
        "exp": int(time.time()) + expires_in,
    }
    raw_json = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
    b64_payload = base64.urlsafe_b64encode(raw_json).decode("ascii").rstrip("=")
    signature = hmac.new(
        secret.encode("utf-8"),
        b64_payload.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return f"{b64_payload}.{signature}"


def verify_access_token(token: str, secret: str = SECRET_KEY) -> dict:
    if not token or "." not in token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Format token autentikasi tidak valid",
        )
    b64_payload, signature = token.rsplit(".", 1)
    expected_sig = hmac.new(
        secret.encode("utf-8"),
        b64_payload.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature token autentikasi tidak valid",
        )
    padding = "=" * (-len(b64_payload) % 4)
    try:
        raw = base64.urlsafe_b64decode((b64_payload + padding).encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Payload token tidak dapat didekode",
        )
    if int(data.get("exp", 0)) < int(time.time()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token autentikasi telah kedaluwarsa",
        )
    return data


def compute_webhook_signature(payload_str: str, secret: str = WEBHOOK_SECRET) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        payload_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_webhook_signature(
    payload_str: str,
    signature: str,
    secret: str = WEBHOOK_SECRET,
) -> bool:
    if not signature:
        return False
    expected = compute_webhook_signature(payload_str, secret=secret)
    return hmac.compare_digest(expected, signature.strip())


def get_optional_current_user(
    authorization: Optional[str] = Header(default=None),
    x_user_role: Optional[str] = Header(default=None),
    x_user_nim: Optional[str] = Header(default=None),
    x_user_nidn: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Optional[dict]:
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Header Authorization harus berformat Bearer <token>",
            )
        claims = verify_access_token(token)
        user_id = claims.get("sub")
        if user_id is not None:
            user = db.query(AppUser).filter(AppUser.id == int(user_id)).first()
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Pengguna tidak ditemukan atau tidak aktif",
                )
        return claims

    if x_user_role:
        return {
            "role": x_user_role.lower().strip(),
            "nim": x_user_nim,
            "nidn": x_user_nidn,
        }

    return None


def require_roles(allowed_roles: Iterable[str]) -> Callable:
    allowed = {r.lower() for r in allowed_roles}

    def dependency(
        current_user: Optional[dict] = Depends(get_optional_current_user),
    ) -> Optional[dict]:
        if current_user is None:
            return None
        role = str(current_user.get("role", "")).lower()
        if role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Akses ditolak: peran '{role}' tidak memiliki "
                    f"hak akses (membutuhkan: {', '.join(sorted(allowed))})"
                ),
            )
        return current_user

    return dependency
