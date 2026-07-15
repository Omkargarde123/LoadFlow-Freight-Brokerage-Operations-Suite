from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CarrierCompliance, Org, OrgType, User, AccountType
from ..schemas import ComplianceUpsert, ComplianceOut
from ..deps import get_current_user, require_account_types

router = APIRouter(prefix="/compliance", tags=["compliance"])


def _to_out(c: CarrierCompliance) -> ComplianceOut:
    return ComplianceOut(
        carrier_org_id=c.carrier_org_id,
        carrier_org_name=c.carrier_org.name,
        insurance_expiry=c.insurance_expiry,
        mc_dot_status=c.mc_dot_status.value,
        approved_equipment=c.approved_equipment,
        approved_commodities=c.approved_commodities,
        updated_at=c.updated_at,
    )


@router.get("/{carrier_org_id}", response_model=ComplianceOut)
def get_compliance(carrier_org_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Carrier staff/admin may only view their own org's record; broker side
    # may view any carrier's record (needed to make an informed assignment).
    if current_user.is_carrier_side and current_user.org_id != carrier_org_id:
        raise HTTPException(403, "Cannot view another carrier's compliance record")
    record = db.query(CarrierCompliance).filter(CarrierCompliance.carrier_org_id == carrier_org_id).first()
    if not record:
        raise HTTPException(404, "No compliance record on file for this carrier")
    return _to_out(record)


@router.put("/{carrier_org_id}", response_model=ComplianceOut)
def upsert_compliance(
    carrier_org_id: int,
    payload: ComplianceUpsert,
    current_user: User = Depends(require_account_types(AccountType.carrier_admin.value)),
    db: Session = Depends(get_db),
):
    if current_user.org_id != carrier_org_id:
        raise HTTPException(403, "Carrier admins may only edit their own org's compliance record")

    record = db.query(CarrierCompliance).filter(CarrierCompliance.carrier_org_id == carrier_org_id).first()
    if not record:
        record = CarrierCompliance(carrier_org_id=carrier_org_id)
        db.add(record)

    record.insurance_expiry = payload.insurance_expiry
    record.mc_dot_status = payload.mc_dot_status
    record.approved_equipment = payload.approved_equipment
    record.approved_commodities = payload.approved_commodities
    db.commit()
    db.refresh(record)
    return _to_out(record)


@router.get("/carriers/list")
def list_carriers(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Broker-side helper to pick a carrier org when assigning a load."""
    if not current_user.is_broker_side:
        raise HTTPException(403, "Broker side only")
    carriers = db.query(Org).filter(Org.type == OrgType.carrier).all()
    return [{"id": c.id, "name": c.name} for c in carriers]
