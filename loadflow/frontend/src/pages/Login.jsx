import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-brand">LOAD<span>FLOW</span></div>
        <div className="auth-sub">Freight brokerage operations, pickup to delivery.</div>

        {error && <div className="form-error">{error}</div>}

        <form onSubmit={submit}>
          <div className="field">
            <label>Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
          </div>
          <div className="field">
            <label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <button className="btn btn-amber" style={{ width: "100%", marginTop: 6 }} disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p style={{ marginTop: 18, fontSize: 13, color: "var(--muted)" }}>
          New here? <Link to="/signup" className="link-btn">Create an account</Link>
        </p>

        <div style={{ marginTop: 18, paddingTop: 14, borderTop: "1px solid var(--line)", fontSize: 11.5, color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
          Demo logins (password: password123)<br />
          admin@summitfreight.com · dispatcher@summitfreight.com<br />
          admin@ironcladtrucking.com · driver@ironcladtrucking.com<br />
          ops@acmemanufacturing.com
        </div>
      </div>
    </div>
  );
}
