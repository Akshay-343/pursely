import { useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { tokens } from "./lib/api";
import { useMe } from "./lib/hooks";
import Budgets from "./pages/Budgets";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Settings from "./pages/Settings";
import Subscriptions from "./pages/Subscriptions";
import Transactions from "./pages/Transactions";

function Protected() {
  const qc = useQueryClient();
  const me = useMe();
  useEffect(() => {
    const out = () => { qc.clear(); location.assign("/login"); };
    window.addEventListener("mt-logout", out);
    return () => window.removeEventListener("mt-logout", out);
  }, [qc]);
  if (!tokens.get()) return <Navigate to="/login" replace />;
  if (me.isLoading) return <div className="p-8 text-muted-foreground">Loading…</div>;
  if (me.isError) return <Navigate to="/login" replace />;
  return <Layout user={me.data!} />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Protected />}>
        <Route index element={<Dashboard />} />
        <Route path="transactions" element={<Transactions />} />
        <Route path="subscriptions" element={<Subscriptions />} />
        <Route path="budgets" element={<Budgets />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
