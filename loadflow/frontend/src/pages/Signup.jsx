import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

export default function Signup() {
  const [mode, setMode] = useState("broker"); // broker | carrier | shipper
  const [orgName, setOrgName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { refresh } = useAuth();
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      let token;
      if (mode === "shipper") {
        ({ access_token: token } = await api.registerShipper({ email, password }));
      } else {
        ({ access_token: token } = await api.registerOrg({
          org_name: orgName, org_type: mode, admin_email: email, admin_password: password,
        }));
      }
      api.setToken(token);
      await refresh();
      navigate("/");
    } catch (err) {
      setError(err.message || "Signup failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-brand">LOAD<span>FLOW</span></div>
        <div className="auth-sub">
          {mode === "shipper"
            ? "Ship freight and track it door to door."
            : "Bootstrap your organization's first Admin account."}
        </div>

        <div className="tabbar">
          <button className={mode === "broker" ? "active" : ""} onClick={() => setMode("broker")} type="button">Broker</button>
          <button className={mode === "carrier" ? "active" : ""} onClick={() => setMode("carrier")} type="button">Carrier</button>
          <button className={mode === "shipper" ? "active" : ""} onClick={() => setMode("shipper")} type="button">Shipper</button>
        </div>

        {error && <div className="form-error">{error}</div>}

        <form onSubmit={submit}>
          {mode !== "shipper" && (
            <div className="field">
              <label>{mode === "broker" ? "Brokerage" : "Carrier"} name</label>
              <input value={orgName} onChange={(e) => setOrgName(e.target.value)} required />
            </div>
          )}
          <div className="field">
            <label>{mode === "shipper" ? "Email" : "Admin email"}</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="field">
            <label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} />
          </div>
          {mode !== "shipper" && (
            <p style={{ fontSize: 12, color: "var(--muted)", marginTop: -6, marginBottom: 14 }}>
              This creates your org's first Admin. Admins invite staff and define
              custom roles afterward — there's no separate staff signup.
            </p>
          )}
          <button className="btn btn-amber" style={{ width: "100%" }} disabled={busy}>
            {busy ? "Creating…" : "Create account"}
          </button>
        </form>

        <p style={{ marginTop: 18, fontSize: 13, color: "var(--muted)" }}>
          Already have an account? <Link to="/login" className="link-btn">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
