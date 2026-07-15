from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import PermissionDeniedLog, User, AccountType
from ..schemas import PermissionDeniedOut
from ..deps import require_account_types

router = APIRouter(prefix="/audit", tags=["audit"])

ADMIN_TYPES = (AccountType.broker_admin.value, AccountType.carrier_admin.value)


@router.get("/permission-denied", response_model=list[PermissionDeniedOut])
def list_permission_denied(
    current_user: User = Depends(require_account_types(*ADMIN_TYPES)),
    db: Session = Depends(get_db),
):
    """Admins can review permission-denied attempts. In a real multi-tenant
    system this would be scoped to attempts by users in their own org; kept
    simple here since it's a stretch goal."""
    entries = db.query(PermissionDeniedLog).order_by(PermissionDeniedLog.timestamp.desc()).limit(200).all()
    return [
        PermissionDeniedOut(
            id=e.id, email=e.email, endpoint=e.endpoint,
            required_permission=e.required_permission, reason=e.reason, timestamp=e.timestamp,
        ) for e in entries
    ]
