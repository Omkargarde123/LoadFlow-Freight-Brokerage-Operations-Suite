from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Role, User, AccountType, PERMISSION_CATALOG
from ..schemas import RoleCreate, RoleOut
from ..deps import get_current_user, require_account_types

router = APIRouter(tags=["roles"])

ADMIN_TYPES = (AccountType.broker_admin.value, AccountType.carrier_admin.value)


@router.get("/permissions/catalog", response_model=list[str])
def permission_catalog(current_user: User = Depends(get_current_user)):
    return PERMISSION_CATALOG


@router.get("/roles", response_model=list[RoleOut])
def list_roles(current_user: User = Depends(require_account_types(*ADMIN_TYPES)), db: Session = Depends(get_db)):
    roles = db.query(Role).filter(Role.org_id == current_user.org_id).all()
    return [RoleOut(id=r.id, name=r.name, permissions=r.permissions) for r in roles]


@router.post("/roles", response_model=RoleOut)
def create_role(
    payload: RoleCreate,
    current_user: User = Depends(require_account_types(*ADMIN_TYPES)),
    db: Session = Depends(get_db),
):
    # Restrict which permissions make sense per org type so a Broker admin
    # can't hand a Dispatcher role the ability to upload PODs, etc.
    from ..models import BROKER_PERMISSIONS, CARRIER_PERMISSIONS
    allowed = BROKER_PERMISSIONS if current_user.is_broker_side else CARRIER_PERMISSIONS
    bad = [p for p in payload.permissions if p not in allowed]
    if bad:
        raise HTTPException(400, f"Permissions not valid for this org type: {bad}")

    role = Role(org_id=current_user.org_id, name=payload.name)
    role.permissions = payload.permissions
    db.add(role)
    db.commit()
    db.refresh(role)
    return RoleOut(id=role.id, name=role.name, permissions=role.permissions)


@router.put("/roles/{role_id}", response_model=RoleOut)
def update_role(
    role_id: int,
    payload: RoleCreate,
    current_user: User = Depends(require_account_types(*ADMIN_TYPES)),
    db: Session = Depends(get_db),
):
    role = db.query(Role).filter(Role.id == role_id, Role.org_id == current_user.org_id).first()
    if not role:
        raise HTTPException(404, "Role not found")
    role.name = payload.name
    role.permissions = payload.permissions
    db.commit()
    db.refresh(role)
    return RoleOut(id=role.id, name=role.name, permissions=role.permissions)


@router.delete("/roles/{role_id}")
def delete_role(
    role_id: int,
    current_user: User = Depends(require_account_types(*ADMIN_TYPES)),
    db: Session = Depends(get_db),
):
    role = db.query(Role).filter(Role.id == role_id, Role.org_id == current_user.org_id).first()
    if not role:
        raise HTTPException(404, "Role not found")
    if role.users:
        raise HTTPException(400, "Cannot delete a role with staff still assigned to it")
    db.delete(role)
    db.commit()
    return {"ok": True}
