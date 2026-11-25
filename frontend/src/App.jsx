import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Chatbot from "./pages/Chatbot.jsx";
import RaiseQuery from "./pages/RaiseQuery.jsx";
import Queries from "./pages/Queries.jsx";
import KnowledgeBase from "./pages/KnowledgeBase.jsx";
import Admin from "./pages/Admin.jsx";
import Analytics from "./pages/Analytics.jsx";
import Reports from "./pages/Reports.jsx";

function Guard({ roles, children }) {
  const { user, loading } = useAuth();
  if (loading) return <p className="muted pad">Loading…</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  const { user } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route element={<Guard><Layout /></Guard>}>
        <Route index element={<Dashboard />} />
        <Route path="chat" element={<Guard roles={["student"]}><Chatbot /></Guard>} />
        <Route path="raise" element={<Guard roles={["student"]}><RaiseQuery /></Guard>} />
        <Route path="queries" element={<Queries />} />
        <Route path="queries/:id" element={<Queries />} />
        <Route path="kb" element={<Guard roles={["admin", "staff"]}><KnowledgeBase /></Guard>} />
        <Route path="admin" element={<Guard roles={["admin"]}><Admin /></Guard>} />
        <Route path="analytics" element={<Guard roles={["admin", "staff"]}><Analytics /></Guard>} />
        <Route path="reports" element={<Guard roles={["admin", "staff"]}><Reports /></Guard>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
