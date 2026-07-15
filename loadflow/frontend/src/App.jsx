import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import Loads from "./pages/Loads";
import Compliance from "./pages/Compliance";
import StaffRoles from "./pages/StaffRoles";
import AuditLog from "./pages/AuditLog";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div style={{ padding: 40 }}>Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function PublicOnly({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div style={{ padding: 40 }}>Loading…</div>;
  if (user) return <Navigate to="/" replace />;
  return children;
}

function RequireAdmin({ children }) {
  const { user } = useAuth();
  const isAdmin = user.account_type === "broker_admin" || user.account_type === "carrier_admin";
  if (!isAdmin) return <Navigate to="/" replace />;
  return children;
}

function RequireCarrierSide({ children }) {
  const { user } = useAuth();
  if (!user.account_type.startsWith("carrier")) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
          <Route path="/signup" element={<PublicOnly><Signup /></PublicOnly>} />
          <Route
            path="/"
            element={
              <Protected>
                <Layout />
              </Protected>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="loads" element={<Loads />} />
            <Route path="compliance" element={<RequireCarrierSide><Compliance /></RequireCarrierSide>} />
            <Route path="staff" element={<RequireAdmin><StaffRoles /></RequireAdmin>} />
            <Route path="audit" element={<RequireAdmin><AuditLog /></RequireAdmin>} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
