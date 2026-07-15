import { useEffect, useState } from "react";
import { api } from "../api";
import { formatDateTime } from "../utils";

export default function AuditLog() {
  const [entries, setEntries] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.auditLog().then(setEntries).catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Audit Log</h1>
          <div className="sub">Server-side permission-denied attempts across LoadFlow</div>
        </div>
      </div>

      {error && <div className="form-error">{error}</div>}

      <div className="panel">
        <table className="data-table">
          <thead><tr><th>When</th><th>User</th><th>Endpoint</th><th>Required permission</th><th>Reason</th></tr></thead>
          <tbody>
            {entries.map((e) => (
              <tr key={e.id}>
                <td className="mono">{formatDateTime(e.timestamp)}</td>
                <td>{e.email || "—"}</td>
                <td className="mono">{e.endpoint}</td>
                <td className="mono">{e.required_permission || "—"}</td>
                <td>{e.reason}</td>
              </tr>
            ))}
            {entries.length === 0 && <tr><td colSpan={5} style={{ color: "var(--muted)" }}>No permission-denied attempts logged yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
