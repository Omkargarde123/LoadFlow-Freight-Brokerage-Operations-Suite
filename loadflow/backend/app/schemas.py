from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, field_validator

from .models import PERMISSION_CATALOG


# ---------- Auth ----------
class OrgSignup(BaseModel):
    org_name: str
    org_type: str  # "broker" | "carrier"
    admin_email: EmailStr
    admin_password: str

    @field_validator("org_type")
    @classmethod
    def check_org_type(cls, v):
        if v not in ("broker", "carrier"):
            raise ValueError("org_type must be 'broker' or 'carrier'")
        return v


class ShipperSignup(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: int
    email: str
    account_type: str
    org_id: Optional[int]
    org_name: Optional[str]
    role_name: Optional[str]
    permissions: List[str]


# ---------- Roles ----------
class RoleCreate(BaseModel):
    name: str
    permissions: List[str]

    @field_validator("permissions")
    @classmethod
    def check_perms(cls, v):
        bad = [p for p in v if p not in PERMISSION_CATALOG]
        if bad:
            raise ValueError(f"Unknown permissions: {bad}")
        return v


class RoleOut(BaseModel):
    id: int
    name: str
    permissions: List[str]


# ---------- Staff ----------
class StaffInvite(BaseModel):
    email: EmailStr
    temp_password: str
    role_id: int


class StaffUpdate(BaseModel):
    role_id: Optional[int] = None
    is_active: Optional[bool] = None


class StaffOut(BaseModel):
    id: int
    email: str
    account_type: str
    role_id: Optional[int]
    role_name: Optional[str]
    is_active: bool


# ---------- Compliance ----------
class ComplianceUpsert(BaseModel):
    insurance_expiry: Optional[datetime] = None
    mc_dot_status: str = "active"
    approved_equipment: List[str] = []
    approved_commodities: List[str] = []


class ComplianceOut(BaseModel):
    carrier_org_id: int
    carrier_org_name: str
    insurance_expiry: Optional[datetime]
    mc_dot_status: str
    approved_equipment: List[str]
    approved_commodities: List[str]
    updated_at: datetime


# ---------- Loads ----------
class LoadCreate(BaseModel):
    shipper_id: int
    origin: str
    destination: str
    pickup_date: Optional[datetime] = None
    delivery_date: Optional[datetime] = None
    commodity: Optional[str] = None
    equipment_type: Optional[str] = None
    weight: Optional[float] = None


class AssignCarrierRequest(BaseModel):
    carrier_org_id: int


class StatusChangeRequest(BaseModel):
    to_status: str
    note: Optional[str] = None


class RateConfirmationCreate(BaseModel):
    base_rate: float
    accessorials: List[dict] = []  # [{"label": "...", "amount": ...}]


class RateConfirmationOut(BaseModel):
    id: int
    version: int
    base_rate: float
    accessorials: List[dict]
    is_current: bool
    confirmed_by: str
    confirmed_at: datetime


class HistoryOut(BaseModel):
    from_status: Optional[str]
    to_status: str
    changed_by: str
    changed_at: datetime
    note: Optional[str]


class LoadOut(BaseModel):
    id: int
    broker_org_id: int
    broker_org_name: str
    shipper_id: int
    shipper_email: str
    carrier_org_id: Optional[int]
    carrier_org_name: Optional[str]
    origin: str
    destination: str
    pickup_date: Optional[datetime]
    delivery_date: Optional[datetime]
    commodity: Optional[str]
    equipment_type: Optional[str]
    weight: Optional[float]
    status: str
    compliance_flag: bool
    compliance_flag_reason: Optional[str]
    compliance_overridden: bool
    created_at: datetime
    history: List[HistoryOut] = []
    rate_confirmations: List[RateConfirmationOut] = []


class CarrierOrgOut(BaseModel):
    id: int
    name: str


class PermissionDeniedOut(BaseModel):
    id: int
    email: Optional[str]
    endpoint: str
    required_permission: Optional[str]
    reason: str
    timestamp: datetime
