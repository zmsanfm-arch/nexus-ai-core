import hmac
import os
from dataclasses import dataclass

from fastapi import Header, HTTPException


@dataclass(frozen=True)
class Principal:
    subject: str
    role: str


def authenticate(authorization: str | None = Header(default=None)) -> Principal:
    """Authenticate server-issued bearer credentials; fail closed when unconfigured."""
    credentials = {
        os.getenv("NEXUS_ADMIN_TOKEN", "").strip(): Principal(
            os.getenv("NEXUS_ADMIN_ID", "").strip(), "admin"
        ),
        os.getenv("NEXUS_API_TOKEN", "").strip(): Principal(
            os.getenv("NEXUS_API_ID", "api-client").strip(), "operator"
        ),
    }
    credentials.pop("", None)
    if not credentials:
        raise HTTPException(status_code=503, detail="Authentication is not configured")

    scheme, separator, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not separator or not supplied:
        raise HTTPException(status_code=401, detail="Bearer authentication required")

    for token, principal in credentials.items():
        if hmac.compare_digest(supplied, token):
            if not principal.subject:
                raise HTTPException(status_code=503, detail="Authenticated identity is not configured")
            return principal
    raise HTTPException(status_code=403, detail="Invalid credentials")


def require_admin(principal: Principal = __import__("fastapi").Depends(authenticate)) -> str:
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator role required")
    return principal.subject
