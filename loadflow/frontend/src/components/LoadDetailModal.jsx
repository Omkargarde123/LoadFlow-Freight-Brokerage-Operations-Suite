import { statusClass, formatDateTime } from "../utils";

export default function LoadDetailModal({ load, onClose }) {
  if (!load) return null;
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <h3>Load #{load.id}</h3>
            <div className="page-header sub" style={{ marginTop: 4 }}>
              {load.origin} &rarr; {load.destination}
            </div>
          </div>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <span className={`status-tag ${statusClass(load.status)}`}>{load.status}</span>

        {load.compliance_flag && (
          <div style={{ marginTop: 14 }}>
            <div className={`compliance-stamp ${load.compliance_overridden ? "resolved" : ""}`} style={{ borderRadius: 4 }}>
              <span className="badge">{load.compliance_overridden ? "OVERRIDDEN" : "HOLD"}</span>
              {load.compliance_flag_reason}
            </div>
          </div>
        )}

        <h4 style={{ fontSize: 13, marginTop: 20, marginBottom: 8 }}>Rate Confirmations</h4>
        {load.rate_confirmations.length === 0 && (
          <p style={{ color: "var(--muted)", fontSize: 13 }}>No rate confirmed yet.</p>
        )}
        {load.rate_confirmations.map((r) => (
          <div key={r.id} className="history-item">
            <time>v{r.version}{r.is_current ? " (current)" : ""}</time>
            <span>
              ${r.base_rate.toLocaleString()} base
              {r.accessorials.length > 0 && (
                <> + {r.accessorials.map((a) => `${a.label} $${a.amount}`).join(", ")}</>
              )}
              {" — confirmed by "}{r.confirmed_by} on {formatDateTime(r.confirmed_at)}
            </span>
          </div>
        ))}

        <h4 style={{ fontSize: 13, marginTop: 20, marginBottom: 8 }}>Audit Trail</h4>
        <div>
          {load.history.map((h, i) => (
            <div key={i} className="history-item">
              <time>{formatDateTime(h.changed_at)}</time>
              <span>
                {h.from_status ? `${h.from_status} → ${h.to_status}` : h.to_status}
                {" "}by {h.changed_by}
                {h.note && <> — {h.note}</>}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
