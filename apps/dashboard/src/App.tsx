import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { MainLayout } from './layout/MainLayout';
import { Overview } from './pages/Overview';
import './App.css';

// Placeholder pages
const Activity = () => <div className="text-slate-400 p-8">Activity Explorer (Planned)</div>;
const Approvals = () => <div className="text-slate-400 p-8">Approval Queue Management (Planned)</div>;
const Policies = () => <div className="text-slate-400 p-8">Governance Constitution (Planned)</div>;
const Integrations = () => <div className="text-slate-400 p-8">Integration Marketplace (Planned)</div>;
const Settings = () => <div className="text-slate-400 p-8">Global Configuration (Planned)</div>;

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Overview />} />
          <Route path="activity" element={<Activity />} />
          <Route path="approvals" element={<Approvals />} />
          <Route path="policies" element={<Policies />} />
          <Route path="integrations" element={<Integrations />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
