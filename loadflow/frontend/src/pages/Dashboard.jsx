import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

const LABELS = {
  broker_admin: "Broker Admin",
  broker_staff: "Broker Staff",
  carrier_admin: "Carrier Admin",
  carrier_staff: "Carrier Staff",
  shipper: "Shipper",
};

export default function Dashboard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.dashboard().then(setData).catch((e) => setError(e.message));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <div className="sub">{LABELS[user.account_type]} · {user.org_name || user.email}</div>
        </div>
      </div>

      {error && <div className="form-error">{error}</div>}

      {data && (
        <div className="stat-row">
          <div className="stat-card">
            <div className="num">{data.total_loads}</div>
            <div className="label">Total loads in view</div>
          </div>
          {Object.entries(data.by_status).map(([status, count]) => (
            <div className="stat-card" key={status}>
              <div className="num">{count}</div>
              <div className="label">{status}</div>
            </div>
          ))}
          <div className={`stat-card ${data.compliance_flags_open > 0 ? "alert" : ""}`}>
            <div className="num">{data.compliance_flags_open}</div>
            <div className="label">Open compliance flags</div>
          </div>
        </div>
      )}

      <div className="panel">
        <h3 style={{ fontSize: 15, marginBottom: 10 }}>Where to next</h3>
        <p style={{ color: "var(--ink-soft)", fontSize: 13.5, marginBottom: 10 }}>
          {user.account_type === "shipper"
            ? "Track your shipments from posting through delivery."
            : user.account_type.startsWith("broker")
            ? "Post loads, assign carriers, confirm rates, and move loads through the pipeline."
            : "View loads assigned to your fleet and update status as they move."}
        </p>
        <Link to="/loads" className="btn btn-outline btn-sm">
          {user.account_type.startsWith("broker") ? "Open load board" : user.account_type === "shipper" ? "View my shipments" : "View assigned loads"}
        </Link>
      </div>
    </div>
  );
}
