import { statusClass, formatDate } from "../utils";

export default function LoadCard({ load, onOpen, children }) {
  const flagged = load.compliance_flag && !load.compliance_overridden;
  const resolvedFlag = load.compliance_flag && load.compliance_overridden;

  return (
    <div className="load-card">
      {flagged && (
        <div className="compliance-stamp">
          <span className="badge">HOLD</span>
          {load.compliance_flag_reason}
        </div>
      )}
      {resolvedFlag && (
        <div className="compliance-stamp resolved">
          <span className="badge">OVERRIDDEN</span>
          {load.compliance_flag_reason}
        </div>
      )}
      <div className="load-card-top">
        <div>
          <div className="load-route">
            #{load.id} &nbsp; {load.origin} <span className="arrow">&rarr;</span> {load.destination}
          </div>
          <div className="load-meta">
            <span>PU {formatDate(load.pickup_date)}</span>
            <span>DEL {formatDate(load.delivery_date)}</span>
            {load.weight && <span>{load.weight.toLocaleString()} lb</span>}
          </div>
        </div>
        <span className={`status-tag ${statusClass(load.status)}`}>{load.status}</span>
      </div>
      <div className="load-card-body">
        <div className="load-tags">
          {load.equipment_type && <span className="tag-chip">{load.equipment_type}</span>}
          {load.commodity && <span className="tag-chip">{load.commodity}</span>}
          {load.carrier_org_name && <span className="tag-chip">Carrier: {load.carrier_org_name}</span>}
          {load.broker_org_name && <span className="tag-chip">Broker: {load.broker_org_name}</span>}
        </div>
        <div className="load-actions">
          {onOpen && (
            <button className="btn btn-outline btn-sm" onClick={() => onOpen(load)}>
              Details
            </button>
          )}
          {children}
        </div>
      </div>
    </div>
  );
}
