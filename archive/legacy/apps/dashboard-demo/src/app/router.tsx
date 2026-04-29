import { Route, Routes } from "react-router-dom";
import { MainLayout } from "../layout/MainLayout";
import { Overview } from "../pages/Overview";
import { Approvals } from "../pages/Approvals";
import { Activity } from "../pages/Activity";
import { Policies } from "../pages/Policies";
import { Integrations } from "../pages/Integrations";
import { Settings } from "../pages/Settings";
import { LoginPage } from "../pages/Login";
import { Agents } from "../pages/Agents";
import Billing from "../pages/Billing";

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Overview />} />
        <Route path="/overview" element={<Overview />} />
        <Route path="/approvals" element={<Approvals />} />
        <Route path="/activity" element={<Activity />} />
        <Route path="/policies" element={<Policies />} />
        <Route path="/integrations" element={<Integrations />} />
        <Route path="/billing" element={<Billing />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
