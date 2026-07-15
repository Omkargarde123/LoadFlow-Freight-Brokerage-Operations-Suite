"""
Populates a fresh loadflow.db with demo accounts so the app is immediately
walkthrough-able. Run with: python seed_demo.py
(Safe to re-run against an empty DB; will error on a non-empty one to avoid
duplicate-email crashes -- delete loadflow.db first if you want a reset.)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timedelta

from app.database import SessionLocal, Base, engine
from app.models import (
    Org, OrgType, User, AccountType, Role, CarrierCompliance, MCDotStatus, Load, LoadStatus,
    LoadStatusHistory, BROKER_PERMISSIONS, CARRIER_PERMISSIONS,
)
from app.security import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()

if db.query(User).count() > 0:
    print("DB already has users -- skipping seed. Delete loadflow.db for a clean reset.")
    sys.exit(0)

# --- Broker org + admin ---
broker_org = Org(name="Summit Freight Brokerage", type=OrgType.broker)
db.add(broker_org)
db.flush()

broker_admin = User(
    email="admin@summitfreight.com", password_hash=hash_password("password123"),
    account_type=AccountType.broker_admin, org_id=broker_org.id,
)
db.add(broker_admin)

dispatcher_role = Role(org_id=broker_org.id, name="Dispatcher")
dispatcher_role.permissions = ["load.assign_carrier", "rate.confirm", "load.update_status"]
ops_lead_role = Role(org_id=broker_org.id, name="Ops Lead")
ops_lead_role.permissions = BROKER_PERMISSIONS
db.add_all([dispatcher_role, ops_lead_role])
db.flush()

broker_staff = User(
    email="dispatcher@summitfreight.com", password_hash=hash_password("password123"),
    account_type=AccountType.broker_staff, org_id=broker_org.id, role_id=dispatcher_role.id,
)
db.add(broker_staff)

# --- Carrier org (compliant) + admin ---
carrier_org = Org(name="Ironclad Trucking LLC", type=OrgType.carrier)
db.add(carrier_org)
db.flush()

carrier_admin = User(
    email="admin@ironcladtrucking.com", password_hash=hash_password("password123"),
    account_type=AccountType.carrier_admin, org_id=carrier_org.id,
)
db.add(carrier_admin)

driver_role = Role(org_id=carrier_org.id, name="Driver")
driver_role.permissions = ["load.update_status", "pod.upload"]
carrier_dispatch_role = Role(org_id=carrier_org.id, name="Carrier Dispatch")
carrier_dispatch_role.permissions = ["load.update_status"]
db.add_all([driver_role, carrier_dispatch_role])
db.flush()

driver = User(
    email="driver@ironcladtrucking.com", password_hash=hash_password("password123"),
    account_type=AccountType.carrier_staff, org_id=carrier_org.id, role_id=driver_role.id,
)
db.add(driver)

compliance_good = CarrierCompliance(
    carrier_org_id=carrier_org.id,
    insurance_expiry=datetime.utcnow() + timedelta(days=180),
    mc_dot_status=MCDotStatus.active,
)
compliance_good.approved_equipment = ["Dry Van", "Reefer"]
compliance_good.approved_commodities = ["General Freight", "Food Grade"]
db.add(compliance_good)

# --- Carrier org (non-compliant, to demo auto-flagging) ---
carrier_org2 = Org(name="Rustbelt Haulers Inc", type=OrgType.carrier)
db.add(carrier_org2)
db.flush()

carrier_admin2 = User(
    email="admin@rustbelthaulers.com", password_hash=hash_password("password123"),
    account_type=AccountType.carrier_admin, org_id=carrier_org2.id,
)
db.add(carrier_admin2)

compliance_bad = CarrierCompliance(
    carrier_org_id=carrier_org2.id,
    insurance_expiry=datetime.utcnow() - timedelta(days=10),  # expired!
    mc_dot_status=MCDotStatus.active,
)
compliance_bad.approved_equipment = ["Flatbed"]
compliance_bad.approved_commodities = ["General Freight"]
db.add(compliance_bad)

# --- Shipper ---
shipper = User(
    email="ops@acmemanufacturing.com", password_hash=hash_password("password123"),
    account_type=AccountType.shipper,
)
db.add(shipper)
db.flush()

# --- A couple of sample loads ---
load1 = Load(
    broker_org_id=broker_org.id, shipper_id=shipper.id,
    origin="Chicago, IL", destination="Dallas, TX",
    pickup_date=datetime.utcnow() + timedelta(days=2),
    delivery_date=datetime.utcnow() + timedelta(days=4),
    commodity="General Freight", equipment_type="Dry Van", weight=38000,
    status=LoadStatus.posted, created_by=broker_admin.id,
)
db.add(load1)
db.flush()
db.add(LoadStatusHistory(load_id=load1.id, from_status=None, to_status=LoadStatus.posted.value, changed_by_user_id=broker_admin.id, note="Load posted"))

load2 = Load(
    broker_org_id=broker_org.id, shipper_id=shipper.id,
    origin="Atlanta, GA", destination="Miami, FL",
    pickup_date=datetime.utcnow() + timedelta(days=1),
    delivery_date=datetime.utcnow() + timedelta(days=2),
    commodity="Food Grade", equipment_type="Reefer", weight=42000,
    status=LoadStatus.posted, created_by=broker_admin.id,
)
db.add(load2)
db.flush()
db.add(LoadStatusHistory(load_id=load2.id, from_status=None, to_status=LoadStatus.posted.value, changed_by_user_id=broker_admin.id, note="Load posted"))

db.commit()

print("Seed complete. Demo logins (all password: password123):")
print("  Broker Admin:      admin@summitfreight.com")
print("  Broker Dispatcher: dispatcher@summitfreight.com")
print("  Carrier Admin (compliant, Ironclad):     admin@ironcladtrucking.com")
print("  Carrier Driver (Ironclad):                driver@ironcladtrucking.com")
print("  Carrier Admin (non-compliant, Rustbelt):  admin@rustbelthaulers.com")
print("  Shipper:            ops@acmemanufacturing.com")
