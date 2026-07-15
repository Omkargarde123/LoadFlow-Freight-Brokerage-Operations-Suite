from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Load, LoadStatus, User, AccountType
from ..deps import get_current_user
from .loads import _scope_query

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = _scope_query(db, current_user)
    loads = q.all()

    by_status = {}
    for l in loads:
        by_status[l.status.value] = by_status.get(l.status.value, 0) + 1

    flagged = [l for l in loads if l.compliance_flag and not l.compliance_overridden]

    return {
        "account_type": current_user.account_type.value,
        "total_loads": len(loads),
        "by_status": by_status,
        "compliance_flags_open": len(flagged),
        "flagged_load_ids": [l.id for l in flagged],
    }
