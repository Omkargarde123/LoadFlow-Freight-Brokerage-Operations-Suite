import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../context/AuthContext";

export default function StaffRoles() {
  const { user } = useAuth();
  const isBrokerSide = user.account_type.startsWith("broker");
  const [roles, setRoles] = useState([]);
  const [staff, setStaff] = useState([]);
  const [catalog, setCatalog] = useState([]);
  const [error, setError] = useState("");
  const [showRoleModal, setShowRoleModal] = useState(null); // null | 'new' | role object
  const [showInvite, setShowInvite] = useState(false);

  const reload = () => {
    api.listRoles().then(setRoles).catch((e) => setError(e.message));
    api.listStaff().then(setStaff).catch((e) => setError(e.message));
    api.permissionCatalog().then(setCatalog).catch(() => {});
  };

  useEffect(reload, []);

  const allowedPerms = isBrokerSide
    ? ["load.create", "load.assign_carrier", "load.override_compliance_flag", "rate.confirm", "load.update_status", "staff.manage"]
    : ["load.update_status", "pod.upload", "staff.manage"];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Staff &amp; Roles</h1>
          <div className="sub">Define permission bundles, then assign staff to them. Code checks permissions, never role names.</div>
        </div>
      </div>

      {error && <div className="form-error">{error}</div>}

      <div className="panel" style={{ marginBottom: 20 }}>
        <div className="page-header" style={{ marginBottom: 14 }}>
          <h3 style={{ fontSize: 15 }}>Roles</h3>
          <button className="btn btn-sm btn-amber" onClick={() => setShowRoleModal("new")}>+ New Role</button>
        </div>
        <table className="data-table">
          <thead><tr><th>Role</th><th>Permissions</th><th>Staff assigned</th><th></th></tr></thead>
          <tbody>
            {roles.map((r) => (
              <tr key={r.id}>
                <td><strong>{r.name}</strong></td>
                <td className="mono" style={{ fontSize: 11.5 }}>{r.permissions.join(", ") || "—"}</td>
                <td>{staff.filter((s) => s.role_id === r.id).length}</td>
                <td><button className="btn btn-outline btn-sm" onClick={() => setShowRoleModal(r)}>Edit</button></td>
              </tr>
            ))}
            {roles.length === 0 && <tr><td colSpan={4} style={{ color: "var(--muted)" }}>No roles defined yet.</td></tr>}
          </tbody>
        </table>
      </div>

      <div className="panel">
        <div className="page-header" style={{ marginBottom: 14 }}>
          <h3 style={{ fontSize: 15 }}>Staff</h3>
          <button className="btn btn-sm btn-amber" onClick={() => setShowInvite(true)} disabled={roles.length === 0}>+ Invite Staff</button>
        </div>
        <table className="data-table">
          <thead><tr><th>Email</th><th>Role</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {staff.map((s) => (
              <tr key={s.id}>
                <td>{s.email}</td>
                <td>{s.role_name || "—"}</td>
                <td>{s.is_active ? "Active" : "Deactivated"}</td>
                <td>
                  <button className="btn btn-outline btn-sm" onClick={async () => {
                    await api.updateStaff(s.id, { is_active: !s.is_active });
                    reload();
                  }}>{s.is_active ? "Deactivate" : "Reactivate"}</button>
                </td>
              </tr>
            ))}
            {staff.length === 0 && <tr><td colSpan={4} style={{ color: "var(--muted)" }}>No staff invited yet.</td></tr>}
          </tbody>
        </table>
      </div>

      {showRoleModal && (
        <RoleModal
          role={showRoleModal === "new" ? null : showRoleModal}
          allowedPerms={allowedPerms}
          onClose={() => setShowRoleModal(null)}
          onSaved={() => { setShowRoleModal(null); reload(); }}
        />
      )}
      {showInvite && (
        <InviteModal roles={roles} onClose={() => setShowInvite(false)} onSaved={() => { setShowInvite(false); reload(); }} />
      )}
    </div>
  );
}

function RoleModal({ role, allowedPerms, onClose, onSaved }) {
  const [name, setName] = useState(role ? role.name : "");
  const [perms, setPerms] = useState(new Set(role ? role.permissions : []));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const toggle = (p) => {
    const next = new Set(perms);
    next.has(p) ? next.delete(p) : next.add(p);
    setPerms(next);
  };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload = { name, permissions: [...perms] };
      if (role) await api.updateRole(role.id, payload);
      else await api.createRole(payload);
      onSaved();
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
          <h3>{role ? "Edit Role" : "New Role"}</h3>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        {error && <div className="form-error">{error}</div>}
        <form onSubmit={submit}>
          <div className="field">
            <label>Role name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Dispatcher" required />
          </div>
          <label style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--muted)", fontFamily: "var(--font-display)" }}>
            Permissions
          </label>
          <div className="perm-grid" style={{ marginTop: 8 }}>
            {allowedPerms.map((p) => (
              <label className="perm-check" key={p}>
                <input type="checkbox" checked={perms.has(p)} onChange={() => toggle(p)} />
                {p}
              </label>
            ))}
          </div>
          <button className="btn btn-amber" style={{ width: "100%" }} disabled={busy}>{busy ? "Saving…" : "Save Role"}</button>
        </form>
      </div>
    </div>
  );
}

function InviteModal({ roles, onClose, onSaved }) {
  const [email, setEmail] = useState("");
  const [tempPassword, setTempPassword] = useState("");
  const [roleId, setRoleId] = useState(roles[0]?.id || "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.inviteStaff({ email, temp_password: tempPassword, role_id: Number(roleId) });
      onSaved();
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
          <h3>Invite Staff</h3>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>
        {error && <div className="form-error">{error}</div>}
        <form onSubmit={submit}>
          <div className="field">
            <label>Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="field">
            <label>Temporary password</label>
            <input value={tempPassword} onChange={(e) => setTempPassword(e.target.value)} required minLength={6} />
          </div>
          <div className="field">
            <label>Role</label>
            <select value={roleId} onChange={(e) => setRoleId(e.target.value)} required>
              {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </div>
          <p style={{ fontSize: 12, color: "var(--muted)", marginTop: -6, marginBottom: 14 }}>
            Share the email + temp password with this person out-of-band. There's
            no email delivery in this demo.
          </p>
          <button className="btn btn-amber" style={{ width: "100%" }} disabled={busy}>{busy ? "Inviting…" : "Invite Staff"}</button>
        </form>
      </div>
    </div>
  );
}
