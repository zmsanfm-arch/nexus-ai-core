import hmac
import os
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException


@dataclass(frozen=True)
class Principal:
    subject: str
    role: str


def authenticate(authorization: str | None = Header(default=None)) -> Principal:
    """Authenticate server-issued bearer credentials; fail closed when unconfigured."""
    admin_token = os.getenv("NEXUS_ADMIN_TOKEN", "").strip()
    admin_id = os.getenv("NEXUS_ADMIN_ID", "").strip()
    api_token = os.getenv("NEXUS_API_TOKEN", "").strip()
    api_id = os.getenv("NEXUS_API_ID", "api-client").strip()

    configured = []
    if admin_token:
        if not admin_id:
            raise HTTPException(status_code=503, detail="Administrator identity is not configured")
        configured.append((admin_token, Principal(admin_id, "admin")))
    if api_token:
        if not api_id:
            raise HTTPException(status_code=503, detail="API client identity is not configured")
        configured.append((api_token, Principal(api_id, "operator")))

    if not configured:
        raise HTTPException(status_code=503, detail="Authentication is not configured")
    if len({token for token, _ in configured}) != len(configured):
        raise HTTPException(status_code=503, detail="Authentication credentials are misconfigured")

    scheme, separator, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not separator or not supplied:
        raise HTTPException(status_code=401, detail="Bearer authentication required")

    for token, principal in configured:
        if hmac.compare_digest(supplied, token):
            return principal
    raise HTTPException(status_code=403, detail="Invalid credentials")


def require_admin(principal: Principal = Depends(authenticate)) -> str:
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator role required")
    return principal.subject
