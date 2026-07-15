from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, Org, OrgType, AccountType
from ..schemas import OrgSignup, ShipperSignup, LoginRequest, Token, MeResponse
from ..security import hash_password, verify_password, create_access_token
from ..deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register-org", response_model=Token)
def register_org(payload: OrgSignup, db: Session = Depends(get_db)):
    """Bootstraps a brand-new Broker or Carrier org. This is the ONLY way an
    Admin account is created: self-service signup that creates the org and
    its first Admin together, atomically. Every other user on that org
    (staff) must be invited by that Admin via /staff -- there is no public
    staff signup endpoint."""
    if db.query(User).filter(User.email == payload.admin_email).first():
        raise HTTPException(400, "Email already registered")

    org = Org(name=payload.org_name, type=OrgType(payload.org_type))
    db.add(org)
    db.flush()

    account_type = AccountType.broker_admin if payload.org_type == "broker" else AccountType.carrier_admin
    admin = User(
        email=payload.admin_email,
        password_hash=hash_password(payload.admin_password),
        account_type=account_type,
        org_id=org.id,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    token = create_access_token({"sub": str(admin.id)})
    return Token(access_token=token)


@router.post("/register-shipper", response_model=Token)
def register_shipper(payload: ShipperSignup, db: Session = Depends(get_db)):
    """Shippers are individuals/businesses with no org and no sub-roles, so
    they can self-serve signup directly (no admin bootstrap needed)."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        account_type=AccountType.shipper,
        org_id=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Account is deactivated")
    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)):
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        account_type=current_user.account_type.value,
        org_id=current_user.org_id,
        org_name=current_user.org.name if current_user.org else None,
        role_name=current_user.role.name if current_user.role else None,
        permissions=sorted(current_user.effective_permissions),
    )
