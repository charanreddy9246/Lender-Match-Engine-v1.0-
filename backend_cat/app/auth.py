"""Checks that an admin request is really from someone who's logged in via
Firebase — the actual "lock on the door" for anything that changes lender
data. The login itself (username/password) is handled entirely by Firebase on
the frontend; this file only verifies the proof-of-login (a signed token)
Firebase hands the frontend after a successful login, using the private
service account key so that proof can't be faked.

Any endpoint that changes data (add a bank, edit a rate, edit bias facts)
should depend on `require_admin` — anything that only reads data (the
borrower-facing match endpoint) stays open, same as today.
"""

from pathlib import Path
from typing import Annotated

import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

from app.config import settings

_bearer_scheme = HTTPBearer(auto_error=False)

_service_account_path = Path(settings.firebase_service_account_path)
if not _service_account_path.is_absolute():
    # Resolve relative to the backend project root (where this file's parent's
    # parent is), not whatever directory the process happened to be launched
    # from — the .env value is meant to be a simple filename like
    # "firebase-service-account.json" sitting next to .env.
    _service_account_path = Path(__file__).resolve().parent.parent / _service_account_path

_firebase_app: firebase_admin.App | None = None
if _service_account_path.exists():
    _firebase_app = firebase_admin.initialize_app(credentials.Certificate(str(_service_account_path)))


async def require_admin(
    credentials_header: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> str:
    """FastAPI dependency — add to any admin-only route. Returns the logged-in
    admin's email on success; raises 401 otherwise. A missing service account
    file fails closed (every admin request rejected) rather than silently
    skipping the check, so a misconfigured deploy can't accidentally leave
    admin routes wide open.
    """
    if _firebase_app is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin login isn't configured on this server yet (missing Firebase service account file).",
        )
    if credentials_header is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing login token.")
    try:
        decoded = firebase_auth.verify_id_token(credentials_header.credentials, app=_firebase_app)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired login.") from exc
    return decoded.get("email", decoded["uid"])
