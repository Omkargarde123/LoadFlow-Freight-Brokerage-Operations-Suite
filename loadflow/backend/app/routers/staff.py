from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Role, AccountType
from ..schemas import StaffInvite, StaffUpdate, StaffOut
from ..security import hash_password
from ..deps import get_current_user, require_account_types

router = APIRouter(prefix="/staff", tags=["staff"])

ADMIN_TYPES = (AccountType.broker_admin.value, AccountType.carrier_admin.value)


def _to_out(u: User) -> StaffOut:
    return StaffOut(
        id=u.id, email=u.email, account_type=u.account_type.value,
        role_id=u.role_id, role_name=u.role.name if u.role else None,
        is_active=u.is_active,
    )


@router.get("", response_model=list[StaffOut])
def list_staff(current_user: User = Depends(require_account_types(*ADMIN_TYPES)), db: Session = Depends(get_db)):
    staff = db.query(User).filter(
        User.org_id == current_user.org_id,
        User.account_type.in_([AccountType.broker_staff, AccountType.carrier_staff]),
    ).all()
    return [_to_out(u) for u in staff]


@router.post("", response_model=StaffOut)
def invite_staff(
    payload: StaffInvite,
    current_user: User = Depends(require_account_types(*ADMIN_TYPES)),
    db: Session = Depends(get_db),
):
    """No public staff-signup endpoint exists. An Admin creates the account
    directly with a temp password and communicates it out-of-band (in a real
    product this would email an invite link; out of scope for this demo)."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")

    role = db.query(Role).filter(Role.id == payload.role_id, Role.org_id == current_user.org_id).first()
    if not role:
        raise HTTPException(400, "Role not found in your org")

    staff_type = AccountType.broker_staff if current_user.is_broker_side else AccountType.carrier_staff
    staff = User(
        email=payload.email,
        password_hash=hash_password(payload.temp_password),
        account_type=staff_type,
        org_id=current_user.org_id,
        role_id=role.id,
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return _to_out(staff)


@router.put("/{staff_id}", response_model=StaffOut)
def update_staff(
    staff_id: int,
    payload: StaffUpdate,
    current_user: User = Depends(require_account_types(*ADMIN_TYPES)),
    db: Session = Depends(get_db),
):
    staff = db.query(User).filter(User.id == staff_id, User.org_id == current_user.org_id).first()
    if not staff:
        raise HTTPException(404, "Staff member not found")
    if payload.role_id is not None:
        role = db.query(Role).filter(Role.id == payload.role_id, Role.org_id == current_user.org_id).first()
        if not role:
            raise HTTPException(400, "Role not found in your org")
        staff.role_id = role.id
    if payload.is_active is not None:
        staff.is_active = payload.is_active
    db.commit()
    db.refresh(staff)
    return _to_out(staff)
