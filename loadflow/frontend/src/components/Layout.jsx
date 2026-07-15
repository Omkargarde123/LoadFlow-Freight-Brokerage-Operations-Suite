import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Layout() {
  const { user, logout } = useAuth();
  if (!user) return null;

  const isAdmin = user.account_type === "broker_admin" || user.account_type === "carrier_admin";
  const isBrokerSide = user.account_type.startsWith("broker");
  const isCarrierSide = user.account_type.startsWith("carrier");
  const isShipper = user.account_type === "shipper";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="mark">LOADFLOW</span>
          <span className="org">{user.org_name || "Independent Shipper"}</span>
        </div>
        <nav>
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Dashboard
          </NavLink>
          {(isBrokerSide || isCarrierSide) && (
            <NavLink to="/loads" className={({ isActive }) => (isActive ? "active" : "")}>
              {isBrokerSide ? "Load Board" : "Assigned Loads"}
            </NavLink>
          )}
          {isShipper && (
            <NavLink to="/loads" className={({ isActive }) => (isActive ? "active" : "")}>
              My Shipments
            </NavLink>
          )}
          {isCarrierSide && (
            <NavLink to="/compliance" className={({ isActive }) => (isActive ? "active" : "")}>
              Compliance Record
            </NavLink>
          )}
          {isAdmin && (
            <NavLink to="/staff" className={({ isActive }) => (isActive ? "active" : "")}>
              Staff &amp; Roles
            </NavLink>
          )}
          {isAdmin && (
            <NavLink to="/audit" className={({ isActive }) => (isActive ? "active" : "")}>
              Audit Log
            </NavLink>
          )}
        </nav>
        <div className="sidebar-footer">
          <div className="who">
            {user.email}
            <br />
            {user.role_name || user.account_type.replace("_", " ")}
          </div>
          <button className="btn-ghost-light" onClick={logout}>Sign out</button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
