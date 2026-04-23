import { Navigate, Route, Routes } from "react-router-dom";
import { DashboardLayout } from "../layout/DashboardLayout";
import { LoginPage } from "../pages/Login";
import { OverviewPage } from "../pages/Overview";
import { ApprovalsPage } from "../pages/Approvals";
import { ActivityPage } from "../pages/Activity";
import { AuditExplorerPage } from "../pages/AuditExplorer";
import { PoliciesPage } from "../pages/Policies";
import { AgentsPage } from "../pages/Agents";
import { IncidentsPage } from "../pages/Incidents";
import { EmergencyPage } from "../pages/Emergency";
import { SettingsPage } from "../pages/Settings";
import { useAuth } from "../hooks/useAuth";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" />;
  return <>{children}</>;
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
        <Route index element={<Navigate to="/overview" replace />} />
        <Route path="/overview" element={<OverviewPage />} />
        <Route path="/approvals" element={<ApprovalsPage />} />
        <Route path="/activity" element={<ActivityPage />} />
        <Route path="/audit" element={<AuditExplorerPage />} />
        <Route path="/policies" element={<PoliciesPage />} />
        <Route path="/agents" element={<AgentsPage />} />
        <Route path="/incidents" element={<IncidentsPage />} />
        <Route path="/emergency" element={<EmergencyPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
