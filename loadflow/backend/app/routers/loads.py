from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    Load, LoadStatus, STATUS_ORDER, LoadStatusHistory, RateConfirmation,
    CarrierCompliance, MCDotStatus, User, AccountType, Org,
)
from ..schemas import (
    LoadCreate, AssignCarrierRequest, StatusChangeRequest, RateConfirmationCreate,
    LoadOut, HistoryOut, RateConfirmationOut,
)
from ..deps import get_current_user, require_permission

router = APIRouter(prefix="/loads", tags=["loads"])


def _load_to_out(load: Load) -> LoadOut:
    return LoadOut(
        id=load.id,
        broker_org_id=load.broker_org_id,
        broker_org_name=load.broker_org.name,
        shipper_id=load.shipper_id,
        shipper_email=load.shipper.email,
        carrier_org_id=load.carrier_org_id,
        carrier_org_name=load.carrier_org.name if load.carrier_org else None,
        origin=load.origin,
        destination=load.destination,
        pickup_date=load.pickup_date,
        delivery_date=load.delivery_date,
        commodity=load.commodity,
        equipment_type=load.equipment_type,
        weight=load.weight,
        status=load.status.value,
        compliance_flag=load.compliance_flag,
        compliance_flag_reason=load.compliance_flag_reason,
        compliance_overridden=load.compliance_overridden,
        created_at=load.created_at,
        history=[
            HistoryOut(
                from_status=h.from_status, to_status=h.to_status,
                changed_by=h.changed_by.email, changed_at=h.changed_at, note=h.note,
            ) for h in load.history
        ],
        rate_confirmations=[
            RateConfirmationOut(
                id=r.id, version=r.version, base_rate=r.base_rate,
                accessorials=r.accessorials, is_current=r.is_current,
                confirmed_by=r.confirmed_by.email, confirmed_at=r.confirmed_at,
            ) for r in load.rate_confirmations
        ],
    )


def _scope_query(db: Session, current_user: User):
    """Object-level scoping, independent of granular permissions:
    - Shipper: only their own loads
    - Carrier staff/admin: only loads assigned to their own carrier org
    - Broker staff/admin: only loads posted by their own broker org
    """
    q = db.query(Load)
    if current_user.account_type == AccountType.shipper:
        return q.filter(Load.shipper_id == current_user.id)
    if current_user.is_carrier_side:
        return q.filter(Load.carrier_org_id == current_user.org_id)
    if current_user.is_broker_side:
        return q.filter(Load.broker_org_id == current_user.org_id)
    return q.filter(False)


def _get_scoped_load_or_404(db: Session, current_user: User, load_id: int) -> Load:
    load = _scope_query(db, current_user).filter(Load.id == load_id).first()
    if not load:
        raise HTTPException(404, "Load not found")
    return load


def _run_compliance_check(db: Session, load: Load):
    """Auto-flags a load if the assigned carrier has expired insurance,
    non-active MC/DOT authority, or lacks the required equipment/commodity
    approval. Blocks progression past 'Carrier Assigned' until resolved."""
    record = db.query(CarrierCompliance).filter(CarrierCompliance.carrier_org_id == load.carrier_org_id).first()
    reasons = []
    if not record:
        reasons.append("No compliance record on file for carrier")
    else:
        if record.mc_dot_status != MCDotStatus.active:
            reasons.append(f"MC/DOT authority status is '{record.mc_dot_status.value}'")
        if record.insurance_expiry and record.insurance_expiry < datetime.utcnow():
            reasons.append("Carrier insurance has expired")
        if load.equipment_type and record.approved_equipment and load.equipment_type not in record.approved_equipment:
            reasons.append(f"Carrier not approved for equipment type '{load.equipment_type}'")
        if load.commodity and record.approved_commodities and load.commodity not in record.approved_commodities:
            reasons.append(f"Carrier not approved for commodity '{load.commodity}'")

    if reasons:
        load.compliance_flag = True
        load.compliance_flag_reason = "; ".join(reasons)
        load.compliance_overridden = False
    else:
        load.compliance_flag = False
        load.compliance_flag_reason = None


@router.get("/lookup/shippers")
def list_shippers(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Broker-side helper to pick a shipper when posting a new load."""
    if not current_user.is_broker_side:
        raise HTTPException(403, "Broker side only")
    shippers = db.query(User).filter(User.account_type == AccountType.shipper).all()
    return [{"id": s.id, "email": s.email} for s in shippers]


@router.post("", response_model=LoadOut)
def create_load(
    payload: LoadCreate,
    current_user: User = Depends(require_permission("load.create")),
    db: Session = Depends(get_db),
):
    shipper = db.query(User).filter(User.id == payload.shipper_id, User.account_type == AccountType.shipper).first()
    if not shipper:
        raise HTTPException(400, "Shipper not found")

    load = Load(
        broker_org_id=current_user.org_id,
        shipper_id=shipper.id,
        origin=payload.origin,
        destination=payload.destination,
        pickup_date=payload.pickup_date,
        delivery_date=payload.delivery_date,
        commodity=payload.commodity,
        equipment_type=payload.equipment_type,
        weight=payload.weight,
        status=LoadStatus.posted,
        created_by=current_user.id,
    )
    db.add(load)
    db.flush()
    db.add(LoadStatusHistory(load_id=load.id, from_status=None, to_status=LoadStatus.posted.value, changed_by_user_id=current_user.id, note="Load posted"))
    db.commit()
    db.refresh(load)
    return _load_to_out(load)


@router.get("", response_model=list[LoadOut])
def list_loads(
    status_filter: Optional[str] = Query(None, alias="status"),
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    equipment_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = _scope_query(db, current_user)
    if status_filter:
        q = q.filter(Load.status == status_filter)
    if origin:
        q = q.filter(Load.origin.ilike(f"%{origin}%"))
    if destination:
        q = q.filter(Load.destination.ilike(f"%{destination}%"))
    if equipment_type:
        q = q.filter(Load.equipment_type.ilike(f"%{equipment_type}%"))
    loads = q.order_by(Load.created_at.desc()).all()
    return [_load_to_out(l) for l in loads]


@router.get("/{load_id}", response_model=LoadOut)
def get_load(load_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    load = _get_scoped_load_or_404(db, current_user, load_id)
    return _load_to_out(load)


@router.post("/{load_id}/assign-carrier", response_model=LoadOut)
def assign_carrier(
    load_id: int,
    payload: AssignCarrierRequest,
    current_user: User = Depends(require_permission("load.assign_carrier")),
    db: Session = Depends(get_db),
):
    load = db.query(Load).filter(Load.id == load_id, Load.broker_org_id == current_user.org_id).first()
    if not load:
        raise HTTPException(404, "Load not found")
    if load.status != LoadStatus.posted:
        raise HTTPException(400, f"Cannot assign a carrier while load is in status '{load.status.value}'")
    carrier_org = db.query(Org).filter(Org.id == payload.carrier_org_id).first()
    if not carrier_org:
        raise HTTPException(400, "Carrier org not found")

    load.carrier_org_id = carrier_org.id
    _run_compliance_check(db, load)
    old_status = load.status
    load.status = LoadStatus.carrier_assigned
    db.add(LoadStatusHistory(
        load_id=load.id, from_status=old_status.value, to_status=load.status.value,
        changed_by_user_id=current_user.id,
        note=f"Assigned to {carrier_org.name}" + (f" (COMPLIANCE FLAG: {load.compliance_flag_reason})" if load.compliance_flag else ""),
    ))
    db.commit()
    db.refresh(load)
    return _load_to_out(load)


@router.post("/{load_id}/override-compliance", response_model=LoadOut)
def override_compliance(
    load_id: int,
    current_user: User = Depends(require_permission("load.override_compliance_flag")),
    db: Session = Depends(get_db),
):
    load = db.query(Load).filter(Load.id == load_id, Load.broker_org_id == current_user.org_id).first()
    if not load:
        raise HTTPException(404, "Load not found")
    if not load.compliance_flag:
        raise HTTPException(400, "Load is not currently flagged")
    load.compliance_overridden = True
    db.add(LoadStatusHistory(
        load_id=load.id, from_status=load.status.value, to_status=load.status.value,
        changed_by_user_id=current_user.id,
        note=f"Compliance flag overridden by {current_user.email}: {load.compliance_flag_reason}",
    ))
    db.commit()
    db.refresh(load)
    return _load_to_out(load)


@router.post("/{load_id}/rate-confirmation", response_model=LoadOut)
def confirm_rate(
    load_id: int,
    payload: RateConfirmationCreate,
    current_user: User = Depends(require_permission("rate.confirm")),
    db: Session = Depends(get_db),
):
    load = db.query(Load).filter(Load.id == load_id, Load.broker_org_id == current_user.org_id).first()
    if not load:
        raise HTTPException(404, "Load not found")
    if load.status not in (LoadStatus.carrier_assigned, LoadStatus.rate_confirmed):
        raise HTTPException(400, f"Cannot confirm a rate while load is in status '{load.status.value}'")
    if load.compliance_flag and not load.compliance_overridden:
        raise HTTPException(400, f"Blocked by unresolved compliance flag: {load.compliance_flag_reason}")

    # Versioning: mark any existing confirmation not-current, add the next version.
    existing = [r for r in load.rate_confirmations]
    for r in existing:
        r.is_current = False
    next_version = (max((r.version for r in existing), default=0)) + 1

    rc = RateConfirmation(
        load_id=load.id, version=next_version, base_rate=payload.base_rate,
        confirmed_by_user_id=current_user.id, is_current=True,
    )
    rc.accessorials = payload.accessorials
    db.add(rc)

    old_status = load.status
    load.status = LoadStatus.rate_confirmed
    db.add(LoadStatusHistory(
        load_id=load.id, from_status=old_status.value, to_status=load.status.value,
        changed_by_user_id=current_user.id, note=f"Rate confirmed v{next_version}: ${payload.base_rate}",
    ))
    db.commit()
    db.refresh(load)
    return _load_to_out(load)


@router.post("/{load_id}/status", response_model=LoadOut)
def update_status(
    load_id: int,
    payload: StatusChangeRequest,
    current_user: User = Depends(require_permission("load.update_status")),
    db: Session = Depends(get_db),
):
    load = _get_scoped_load_or_404(db, current_user, load_id)

    try:
        target = LoadStatus(payload.to_status)
    except ValueError:
        raise HTTPException(400, f"Unknown status '{payload.to_status}'")

    current_idx = STATUS_ORDER.index(load.status)
    target_idx = STATUS_ORDER.index(target)
    if target_idx != current_idx + 1:
        raise HTTPException(
            400,
            f"Invalid transition: '{load.status.value}' -> '{target.value}'. "
            f"Loads may only advance one step at a time, in order.",
        )
    if target_idx >= STATUS_ORDER.index(LoadStatus.rate_confirmed) and load.compliance_flag and not load.compliance_overridden:
        raise HTTPException(400, f"Blocked by unresolved compliance flag: {load.compliance_flag_reason}")

    old_status = load.status
    load.status = target
    db.add(LoadStatusHistory(
        load_id=load.id, from_status=old_status.value, to_status=target.value,
        changed_by_user_id=current_user.id, note=payload.note,
    ))
    db.commit()
    db.refresh(load)
    return _load_to_out(load)
