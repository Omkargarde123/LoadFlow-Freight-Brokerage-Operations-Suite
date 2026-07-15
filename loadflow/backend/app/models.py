import enum
import json
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum
)
from sqlalchemy.orm import relationship

from .database import Base


# ---------------------------------------------------------------------------
# Fixed permission catalog. Code checks against THESE STRINGS, never role
# names. Admins of an org implicitly hold every permission scoped to their
# org type; everyone else's permissions come entirely from their assigned
# Role row.
# ---------------------------------------------------------------------------
PERMISSION_CATALOG = [
    "load.create",
    "load.assign_carrier",
    "load.override_compliance_flag",
    "rate.confirm",
    "load.update_status",
    "staff.manage",
    "pod.upload",
]

BROKER_PERMISSIONS = [
    "load.create", "load.assign_carrier", "load.override_compliance_flag",
    "rate.confirm", "load.update_status", "staff.manage",
]
CARRIER_PERMISSIONS = [
    "load.update_status", "pod.upload", "staff.manage",
]


class OrgType(str, enum.Enum):
    broker = "broker"
    carrier = "carrier"


class AccountType(str, enum.Enum):
    broker_admin = "broker_admin"
    broker_staff = "broker_staff"
    carrier_admin = "carrier_admin"
    carrier_staff = "carrier_staff"
    shipper = "shipper"


class LoadStatus(str, enum.Enum):
    posted = "Posted"
    carrier_assigned = "Carrier Assigned"
    rate_confirmed = "Rate Confirmed"
    dispatched = "Dispatched"
    in_transit = "In Transit"
    delivered = "Delivered"
    pod_verified = "POD Verified"
    closed = "Invoiced/Closed"


# Linear forward progression of the state machine. Enforced in routers/loads.py
STATUS_ORDER = [
    LoadStatus.posted, LoadStatus.carrier_assigned, LoadStatus.rate_confirmed,
    LoadStatus.dispatched, LoadStatus.in_transit, LoadStatus.delivered,
    LoadStatus.pod_verified, LoadStatus.closed,
]


class MCDotStatus(str, enum.Enum):
    active = "active"
    expired = "expired"
    suspended = "suspended"


class Org(Base):
    __tablename__ = "orgs"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(Enum(OrgType), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="org")
    roles = relationship("Role", back_populates="org")


class Role(Base):
    """A bundle of permissions, defined by an org Admin through the UI.
    Permissions are stored as a JSON-encoded list validated against
    PERMISSION_CATALOG on write (see schemas.py / routers/roles.py)."""
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("orgs.id"), nullable=False)
    name = Column(String, nullable=False)
    permissions_json = Column(Text, nullable=False, default="[]")

    org = relationship("Org", back_populates="roles")
    users = relationship("User", back_populates="role")

    @property
    def permissions(self):
        return json.loads(self.permissions_json)

    @permissions.setter
    def permissions(self, value):
        self.permissions_json = json.dumps(value)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    account_type = Column(Enum(AccountType), nullable=False)
    org_id = Column(Integer, ForeignKey("orgs.id"), nullable=True)  # null for shippers
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)  # null for admins/shippers
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    org = relationship("Org", back_populates="users")
    role = relationship("Role", back_populates="users")

    @property
    def effective_permissions(self):
        if self.account_type == AccountType.broker_admin:
            return set(BROKER_PERMISSIONS)
        if self.account_type == AccountType.carrier_admin:
            return set(CARRIER_PERMISSIONS)
        if self.account_type == AccountType.shipper:
            return set()
        if self.role:
            return set(self.role.permissions)
        return set()

    @property
    def is_broker_side(self):
        return self.account_type in (AccountType.broker_admin, AccountType.broker_staff)

    @property
    def is_carrier_side(self):
        return self.account_type in (AccountType.carrier_admin, AccountType.carrier_staff)


class CarrierCompliance(Base):
    """One record per carrier org. Loads auto-flag against this."""
    __tablename__ = "carrier_compliance"

    id = Column(Integer, primary_key=True)
    carrier_org_id = Column(Integer, ForeignKey("orgs.id"), unique=True, nullable=False)
    insurance_expiry = Column(DateTime, nullable=True)
    mc_dot_status = Column(Enum(MCDotStatus), default=MCDotStatus.active)
    approved_equipment_json = Column(Text, default="[]")   # e.g. ["Dry Van","Reefer"]
    approved_commodities_json = Column(Text, default="[]")  # e.g. ["General Freight"]
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    carrier_org = relationship("Org")

    @property
    def approved_equipment(self):
        return json.loads(self.approved_equipment_json)

    @approved_equipment.setter
    def approved_equipment(self, value):
        self.approved_equipment_json = json.dumps(value)

    @property
    def approved_commodities(self):
        return json.loads(self.approved_commodities_json)

    @approved_commodities.setter
    def approved_commodities(self, value):
        self.approved_commodities_json = json.dumps(value)


class Load(Base):
    __tablename__ = "loads"

    id = Column(Integer, primary_key=True)
    broker_org_id = Column(Integer, ForeignKey("orgs.id"), nullable=False)
    shipper_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    carrier_org_id = Column(Integer, ForeignKey("orgs.id"), nullable=True)

    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    pickup_date = Column(DateTime, nullable=True)
    delivery_date = Column(DateTime, nullable=True)
    commodity = Column(String, nullable=True)
    equipment_type = Column(String, nullable=True)
    weight = Column(Float, nullable=True)

    status = Column(Enum(LoadStatus), default=LoadStatus.posted, nullable=False)

    compliance_flag = Column(Boolean, default=False)
    compliance_flag_reason = Column(String, nullable=True)
    compliance_overridden = Column(Boolean, default=False)
    compliance_overridden_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    broker_org = relationship("Org", foreign_keys=[broker_org_id])
    carrier_org = relationship("Org", foreign_keys=[carrier_org_id])
    shipper = relationship("User", foreign_keys=[shipper_id])

    history = relationship("LoadStatusHistory", back_populates="load", order_by="LoadStatusHistory.changed_at")
    rate_confirmations = relationship("RateConfirmation", back_populates="load", order_by="RateConfirmation.version")


class LoadStatusHistory(Base):
    __tablename__ = "load_status_history"

    id = Column(Integer, primary_key=True)
    load_id = Column(Integer, ForeignKey("loads.id"), nullable=False)
    from_status = Column(String, nullable=True)
    to_status = Column(String, nullable=False)
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)
    note = Column(String, nullable=True)

    load = relationship("Load", back_populates="history")
    changed_by = relationship("User")


class RateConfirmation(Base):
    """Versioned broker-carrier agreement. Reconfirming a rate creates a new
    version rather than mutating the old one; historical loads keep whatever
    version was actually current at the time they progressed."""
    __tablename__ = "rate_confirmations"

    id = Column(Integer, primary_key=True)
    load_id = Column(Integer, ForeignKey("loads.id"), nullable=False)
    version = Column(Integer, nullable=False)
    base_rate = Column(Float, nullable=False)
    accessorials_json = Column(Text, default="[]")  # [{"label":"Detention","amount":75}]
    is_current = Column(Boolean, default=True)
    confirmed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    confirmed_at = Column(DateTime, default=datetime.utcnow)

    load = relationship("Load", back_populates="rate_confirmations")
    confirmed_by = relationship("User")

    @property
    def accessorials(self):
        return json.loads(self.accessorials_json)

    @accessorials.setter
    def accessorials(self, value):
        self.accessorials_json = json.dumps(value)


class PermissionDeniedLog(Base):
    """Server-side audit of blocked access attempts, per assessment's RBAC
    requirement to log permission-denied attempts."""
    __tablename__ = "permission_denied_log"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    email = Column(String, nullable=True)
    endpoint = Column(String, nullable=False)
    required_permission = Column(String, nullable=True)
    reason = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
