import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";
import { formatDate } from "../utils";

export default function Compliance() {
  const { user } = useAuth();
  const isAdmin = user.account_type === "carrier_admin";
  const [record, setRecord] = useState(null);
  const [form, setForm] = useState({
    insurance_expiry: "", mc_dot_status: "active", approved_equipment: "", approved_commodities: "",
  });
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.getCompliance(user.org_id)
      .then((r) => {
        setRecord(r);
        setForm({
          insurance_expiry: r.insurance_expiry ? r.insurance_expiry.slice(0, 10) : "",
          mc_dot_status: r.mc_dot_status,
          approved_equipment: r.approved_equipment.join(", "),
          approved_commodities: r.approved_commodities.join(", "),
        });
      })
      .catch(() => { /* no record yet */ });
  }, [user.org_id]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    setSaved(false);
    try {
      const updated = await api.upsertCompliance(user.org_id, {
        insurance_expiry: form.insurance_expiry ? new Date(form.insurance_expiry).toISOString() : null,
        mc_dot_status: form.mc_dot_status,
        approved_equipment: form.approved_equipment.split(",").map((s) => s.trim()).filter(Boolean),
        approved_commodities: form.approved_commodities.split(",").map((s) => s.trim()).filter(Boolean),
      });
      setRecord(updated);
      setSaved(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Compliance Record</h1>
          <div className="sub">Insurance, authority, and approved equipment / commodities for your fleet</div>
        </div>
      </div>

      {error && <div className="form-error">{error}</div>}
      {saved && <div className="panel" style={{ background: "var(--good-bg)", borderColor: "#BEE3CE", color: "var(--good)", marginBottom: 16, fontSize: 13 }}>Compliance record saved. Loads assigned to your fleet will be re-checked against this on their next assignment.</div>}

      <div className="panel">
        {!isAdmin ? (
          <p style={{ color: "var(--muted)" }}>Only your Carrier Admin can edit this record. Current on file:</p>
        ) : null}
        <form onSubmit={submit}>
          <div className="field-row">
            <div className="field">
              <label>Insurance expiry</label>
              <input type="date" value={form.insurance_expiry} disabled={!isAdmin}
                onChange={(e) => setForm({ ...form, insurance_expiry: e.target.value })} />
            </div>
            <div className="field">
              <label>MC/DOT authority status</label>
              <select value={form.mc_dot_status} disabled={!isAdmin}
                onChange={(e) => setForm({ ...form, mc_dot_status: e.target.value })}>
                <option value="active">Active</option>
                <option value="expired">Expired</option>
                <option value="suspended">Suspended</option>
              </select>
            </div>
          </div>
          <div className="field">
            <label>Approved equipment (comma-separated)</label>
            <input value={form.approved_equipment} disabled={!isAdmin}
              placeholder="Dry Van, Reefer, Flatbed"
              onChange={(e) => setForm({ ...form, approved_equipment: e.target.value })} />
          </div>
          <div className="field">
            <label>Approved commodities (comma-separated)</label>
            <input value={form.approved_commodities} disabled={!isAdmin}
              placeholder="General Freight, Food Grade"
              onChange={(e) => setForm({ ...form, approved_commodities: e.target.value })} />
          </div>
          {isAdmin && (
            <button className="btn btn-amber" disabled={busy}>{busy ? "Saving…" : "Save Compliance Record"}</button>
          )}
        </form>
        {record && (
          <p style={{ marginTop: 14, fontSize: 12, color: "var(--muted)" }}>Last updated {formatDate(record.updated_at)}</p>
        )}
      </div>
    </div>
  );
}
