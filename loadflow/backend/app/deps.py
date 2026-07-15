import logging

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, PermissionDeniedLog

logger = logging.getLogger("loadflow.rbac")
logging.basicConfig(level=logging.INFO)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _log_denied(db: Session, user, endpoint: str, permission: str, reason: str):
    entry = PermissionDeniedLog(
        user_id=user.id if user else None,
        email=user.email if user else None,
        endpoint=endpoint,
        required_permission=permission,
        reason=reason,
    )
    db.add(entry)
    db.commit()
    logger.warning(
        "PERMISSION DENIED user=%s endpoint=%s permission=%s reason=%s",
        user.email if user else "anonymous", endpoint, permission, reason,
    )


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    from .security import decode_access_token

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_permission(permission: str):
    """Dependency factory: blocks the request at the API layer (not just
    hiding a UI button) unless the caller's effective permission set
    contains `permission`. Every denial is logged."""

    def _checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if permission not in current_user.effective_permissions:
            _log_denied(db, current_user, str(request.url.path), permission, "missing_permission")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}",
            )
        return current_user

    return _checker


def require_account_types(*account_types: str):
    """For endpoints gated by account type rather than a granular permission
    (e.g. only shippers may view the shipper dashboard)."""

    def _checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if current_user.account_type.value not in account_types:
            _log_denied(db, current_user, str(request.url.path), None, "wrong_account_type")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized for this account type")
        return current_user

    return _checker
