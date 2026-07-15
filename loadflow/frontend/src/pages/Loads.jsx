import { useEffect, useState, useCallback } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import LoadCard from "../components/LoadCard";
import LoadDetailModal from "../components/LoadDetailModal";
import { nextStatus } from "../utils";

export default function Loads() {
  const { user } = useAuth();
  const perms = new Set(user.permissions);
  const isBrokerSide = user.account_type.startsWith("broker");
  const isCarrierSide = user.account_type.startsWith("carrier");

  const [loads, setLoads] = useState([]);
  const [filters, setFilters] = useState({ status: "", origin: "", destination: "", equipment_type: "" });
  const [error, setError] = useState("");
  const [detail, setDetail] = useState(null);

  const [showCreate, setShowCreate] = useState(false);
  const [assignTarget, setAssignTarget] = useState(null);
  const [rateTarget, setRateTarget] = useState(null);

  const load = useCallback(() => {
    api.listLoads(filters).then(setLoads).catch((e) => setError(e.message));
  }, [filters]);

  useEffect(() => { load(); }, [load]);

  const openDetail = async (l) => {
    const full = await api.getLoad(l.id);
    setDetail(full);
  };

  const doOverride = async (l) => {
    try {
      await api.overrideCompliance(l.id);
      load();
    } catch (e) { setError(e.message); }
  };

  const doAdvance = async (l) => {
    const to = nextStatus(l.status);
    if (!to) return;
    try {
      await api.updateStatus(l.id, { to_status: to });
      load();
    } catch (e) { setError(e.message); }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>{isBrokerSide ? "Load Board" : isCarrierSide ? "Assigned Loads" : "My Shipments"}</h1>
          <div className="sub">{loads.length} load{loads.length === 1 ? "" : "s"} in view</div>
        </div>
        {isBrokerSide && perms.has("load.create") && (
          <button className="btn btn-amber" onClick={() => setShowCreate(true)}>+ Post Load</button>
        )}
      </div>

      {error && <div className="form-error">{error}</div>}

      {isBrokerSide && (
        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="field-row">
            <div className="field">
              <label>Status</label>
              <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
                <option value="">All</option>
                {["Posted", "Carrier Assigned", "Rate Confirmed", "Dispatched", "In Transit", "Delivered", "POD Verified", "Invoiced/Closed"].map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Origin</label>
              <input value={filters.origin} onChange={(e) => setFilters({ ...filters, origin: e.target.value })} placeholder="Chicago" />
            </div>
            <div className="field">
              <label>Destination</label>
              <input value={filters.destination} onChange={(e) => setFilters({ ...filters, destination: e.target.value })} placeholder="Dallas" />
            </div>
            <div className="field">
              <label>Equipment</label>
              <input value={filters.equipment_type} onChange={(e) => setFilters({ ...filters, equipment_type: e.target.value })} placeholder="Dry Van" />
            </div>
          </div>
        </div>
      )}

      {loads.length === 0 ? (
        <div className="empty-state panel">
          <h3>No loads here yet</h3>
          <p>{isBrokerSide ? "Post a load to get started." : "Nothing assigned to you right now."}</p>
        </div>
      ) : (
        <div className="load-list">
          {loads.map((l) => (
            <LoadCard key={l.id} load={l} onOpen={openDetail}>
              {isBrokerSide && l.status === "Posted" && perms.has("load.assign_carrier") && (
                <button className="btn btn-sm" onClick={() => setAssignTarget(l)}>Assign Carrier</button>
              )}
              {isBrokerSide && l.compliance_flag && !l.compliance_overridden && perms.has("load.override_compliance_flag") && (
                <button className="btn btn-danger btn-sm" onClick={() => doOverride(l)}>Override Flag</button>
              )}
              {isBrokerSide && ["Carrier Assigned", "Rate Confirmed"].includes(l.status) && perms.has("rate.confirm") && (
                <button className="btn btn-sm" onClick={() => setRateTarget(l)}>
                  {l.status === "Rate Confirmed" ? "Reconfirm Rate" : "Confirm Rate"}
                </button>
              )}
              {perms.has("load.update_status") && nextStatus(l.status) && l.status !== "Posted" && l.status !== "Carrier Assigned" && (
                <button
                  className="btn btn-outline btn-sm"
                  disabled={l.compliance_flag && !l.compliance_overridden}
                  onClick={() => doAdvance(l)}
                  title={l.compliance_flag && !l.compliance_overridden ? "Blocked by compliance hold" : ""}
                >
                  Advance → {nextStatus(l.status)}
                </button>
              )}
            </LoadCard>
          ))}
        </div>
      )}

      <LoadDetailModal load={detail} onClose={() => setDetail(null)} />

      {showCreate && (
        <CreateLoadModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); load(); }} />
      )}
      {assignTarget && (
        <AssignCarrierModal load={assignTarget} onClose={() => setAssignTarget(null)} onDone={() => { setAssignTarget(null); load(); }} />
      )}
      {rateTarget && (
        <RateConfirmModal load={rateTarget} onClose={() => setRateTarget(null)} onDone={() => { setRateTarget(null); load(); }} />
      )}
    </div>
  );
}

function CreateLoadModal({ onClose, onCreated }) {
  const [shippers, setShippers] = useState([]);
  const [form, setForm] = useState({
    shipper_id: "", origin: "", destination: "", pickup_date: "", delivery_date: "",
    commodity: "", equipment_type: "", weight: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.listShippers().then(setShippers).catch(() => {}); }, []);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.createLoad({
        ...form,
        shipper_id: Number(form.shipper_id),
        weight: form.weight ? Number(form.weight) : null,
        pickup_date: form.pickup_date || null,
        delivery_date: form.delivery_date || null,
      });
      onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>Post a Load</h3>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        {error && <div className="form-error">{error}</div>}
        <form onSubmit={submit}>
          <div className="field">
            <label>Shipper</label>
            <select value={form.shipper_id} onChange={(e) => setForm({ ...form, shipper_id: e.target.value })} required>
              <option value="">Select a shipper…</option>
              {shippers.map((s) => <option key={s.id} value={s.id}>{s.email}</option>)}
            </select>
          </div>
          <div className="field-row">
            <div className="field">
              <label>Origin</label>
              <input value={form.origin} onChange={(e) => setForm({ ...form, origin: e.target.value })} placeholder="Chicago, IL" required />
            </div>
            <div className="field">
              <label>Destination</label>
              <input value={form.destination} onChange={(e) => setForm({ ...form, destination: e.target.value })} placeholder="Dallas, TX" required />
            </div>
          </div>
          <div className="field-row">
            <div className="field">
              <label>Pickup date</label>
              <input type="date" value={form.pickup_date} onChange={(e) => setForm({ ...form, pickup_date: e.target.value })} />
            </div>
            <div className="field">
              <label>Delivery date</label>
              <input type="date" value={form.delivery_date} onChange={(e) => setForm({ ...form, delivery_date: e.target.value })} />
            </div>
          </div>
          <div className="field-row">
            <div className="field">
              <label>Equipment type</label>
              <input value={form.equipment_type} onChange={(e) => setForm({ ...form, equipment_type: e.target.value })} placeholder="Dry Van" />
            </div>
            <div className="field">
              <label>Commodity</label>
              <input value={form.commodity} onChange={(e) => setForm({ ...form, commodity: e.target.value })} placeholder="General Freight" />
            </div>
          </div>
          <div className="field">
            <label>Weight (lb)</label>
            <input type="number" value={form.weight} onChange={(e) => setForm({ ...form, weight: e.target.value })} />
          </div>
          <button className="btn btn-amber" style={{ width: "100%" }} disabled={busy}>{busy ? "Posting…" : "Post Load"}</button>
        </form>
      </div>
    </div>
  );
}

function AssignCarrierModal({ load, onClose, onDone }) {
  const [carriers, setCarriers] = useState([]);
  const [carrierId, setCarrierId] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.listCarriers().then(setCarriers).catch(() => {}); }, []);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.assignCarrier(load.id, { carrier_org_id: Number(carrierId) });
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>Assign Carrier — Load #{load.id}</h3>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        {error && <div className="form-error">{error}</div>}
        <form onSubmit={submit}>
          <div className="field">
            <label>Carrier</label>
            <select value={carrierId} onChange={(e) => setCarrierId(e.target.value)} required>
              <option value="">Select a carrier…</option>
              {carriers.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 14 }}>
            Compliance (insurance, MC/DOT authority, equipment &amp; commodity approval)
            is checked automatically on assignment.
          </p>
          <button className="btn btn-amber" style={{ width: "100%" }} disabled={busy}>{busy ? "Assigning…" : "Assign Carrier"}</button>
        </form>
      </div>
    </div>
  );
}

function RateConfirmModal({ load, onClose, onDone }) {
  const [baseRate, setBaseRate] = useState("");
  const [accessorials, setAccessorials] = useState([{ label: "", amount: "" }]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const updateAcc = (i, field, value) => {
    const next = [...accessorials];
    next[i] = { ...next[i], [field]: value };
    setAccessorials(next);
  };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const cleaned = accessorials
        .filter((a) => a.label && a.amount)
        .map((a) => ({ label: a.label, amount: Number(a.amount) }));
      await api.confirmRate(load.id, { base_rate: Number(baseRate), accessorials: cleaned });
      onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h3>Confirm Rate — Load #{load.id}</h3>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        {error && <div className="form-error">{error}</div>}
        <form onSubmit={submit}>
          <div className="field">
            <label>Base rate (USD)</label>
            <input type="number" value={baseRate} onChange={(e) => setBaseRate(e.target.value)} required />
          </div>
          <label style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--muted)", fontFamily: "var(--font-display)" }}>
            Accessorials
          </label>
          {accessorials.map((a, i) => (
            <div className="field-row" key={i} style={{ marginTop: 6 }}>
              <div className="field">
                <input placeholder="Detention" value={a.label} onChange={(e) => updateAcc(i, "label", e.target.value)} />
              </div>
              <div className="field" style={{ maxWidth: 120 }}>
                <input type="number" placeholder="Amount" value={a.amount} onChange={(e) => updateAcc(i, "amount", e.target.value)} />
              </div>
            </div>
          ))}
          <button type="button" className="btn btn-outline btn-sm" style={{ marginBottom: 16 }} onClick={() => setAccessorials([...accessorials, { label: "", amount: "" }])}>
            + Add accessorial
          </button>
          <button className="btn btn-amber" style={{ width: "100%" }} disabled={busy}>{busy ? "Confirming…" : "Confirm Rate"}</button>
        </form>
      </div>
    </div>
  );
}
