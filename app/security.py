import hmac
import os
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, Header, HTTPException


@dataclass(frozen=True)
class Principal:
    subject: str
    role: str


@lru_cache(maxsize=4)
def _oidc_jwks_client(jwks_url: str):
    return jwt.PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=300)


def _authenticate_oidc(token: str) -> Principal:
    issuer = os.getenv("NEXUS_OIDC_ISSUER", "").strip()
    audience = os.getenv("NEXUS_OIDC_AUDIENCE", "").strip()
    jwks_url = os.getenv("NEXUS_OIDC_JWKS_URL", "").strip()
    admin_group = os.getenv("NEXUS_OIDC_ADMIN_GROUP", "").strip()
    operator_group = os.getenv("NEXUS_OIDC_OPERATOR_GROUP", "").strip()
    groups_claim = os.getenv("NEXUS_OIDC_GROUPS_CLAIM", "groups").strip()
    if not all((issuer, audience, jwks_url, admin_group, operator_group, groups_claim)):
        raise HTTPException(status_code=503, detail="OIDC authentication is not fully configured")
    try:
        signing_key = _oidc_jwks_client(jwks_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Bearer token expired") from None
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=403, detail="Invalid bearer token") from None
    except Exception:
        raise HTTPException(status_code=503, detail="OIDC signing keys are unavailable") from None

    groups = claims.get(groups_claim, [])
    if not isinstance(groups, list) or not all(isinstance(item, str) for item in groups):
        raise HTTPException(status_code=403, detail="OIDC role claim is invalid")
    if admin_group in groups:
        role = "admin"
    elif operator_group in groups:
        role = "operator"
    else:
        raise HTTPException(status_code=403, detail="OIDC principal has no NEXUS role")
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(status_code=403, detail="OIDC subject is invalid")
    return Principal(subject, role)


def authenticate(authorization: str | None = Header(default=None)) -> Principal:
    """Authenticate OIDC JWTs or bootstrap bearer tokens; fail closed by default."""
    scheme, separator, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not separator or not supplied:
        raise HTTPException(status_code=401, detail="Bearer authentication required")

    auth_mode = os.getenv("NEXUS_AUTH_MODE", "static").strip().lower()
    if auth_mode == "oidc":
        return _authenticate_oidc(supplied)
    if auth_mode != "static":
        raise HTTPException(status_code=503, detail="Unsupported authentication mode")

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

    for token, principal in configured:
        if hmac.compare_digest(supplied, token):
            return principal
    raise HTTPException(status_code=403, detail="Invalid credentials")


def require_admin(principal: Principal = Depends(authenticate)) -> str:
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator role required")
    return principal.subject
