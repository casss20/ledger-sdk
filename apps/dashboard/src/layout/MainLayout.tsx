import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Activity, 
  ShieldCheck, 
  Settings, 
  Lock, 
  Zap,
  CreditCard,
  GitBranch,
  ChevronRight,
  User
} from 'lucide-react';
import { cn } from '../lib/utils';

const navItems = [
  { icon: LayoutDashboard, label: 'Overview', path: '/' },
  { icon: Activity, label: 'Activity', path: '/activity' },
  { icon: GitBranch, label: 'Traceability', path: '/traceability' },
  { icon: ShieldCheck, label: 'Approvals', path: '/approvals' },
  { icon: Lock, label: 'Policies', path: '/policies' },
  { icon: Zap, label: 'Integrations', path: '/integrations' },
  { icon: CreditCard, label: 'Billing', path: '/billing' },
  { icon: Settings, label: 'Settings', path: '/settings' },
];

export const MainLayout: React.FC = () => {
  return (
    <div className="flex h-screen w-full bg-[#020617] text-slate-200 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800/50 bg-[#020617] flex flex-col">
        <div className="p-6 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-orange-600 flex items-center justify-center shadow-lg shadow-orange-900/20">
            <ShieldCheck size={20} className="text-white" />
          </div>
          <span className="text-xl font-black tracking-tighter text-white">CITADEL</span>
        </div>

        <nav className="flex-1 px-4 py-2 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => cn(
                "flex items-center justify-between px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group",
                isActive 
                  ? "bg-orange-600/10 text-orange-500" 
                  : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/50"
              )}
            >
              <div className="flex items-center gap-3">
                <item.icon size={18} className={cn(
                  "transition-colors",
                  "group-hover:text-slate-100"
                )} />
                {item.label}
              </div>
              <ChevronRight size={14} className={cn(
                "opacity-0 transition-all",
                "group-hover:opacity-100 group-hover:translate-x-1"
              )} />
            </NavLink>
          ))}
        </nav>

        <div className="p-4 mt-auto">
          <div className="p-4 rounded-2xl bg-slate-900/50 border border-slate-800/50">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center border border-slate-700">
                <User size={16} className="text-slate-400" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-bold text-slate-200 truncate">Admin User</p>
                <p className="text-[10px] text-slate-500 truncate">Enterprise Tier</p>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto bg-[radial-gradient(circle_at_top_right,_rgba(15,23,42,0.4),_transparent)]">
        <header className="h-16 border-b border-slate-800/50 flex items-center justify-between px-8 backdrop-blur-md sticky top-0 z-50">
          <h2 className="text-sm font-bold text-slate-400 uppercase tracking-widest">
            Control Plane
          </h2>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] font-bold text-emerald-500 uppercase tracking-tight">System Healthy</span>
            </div>
          </div>
        </header>

        <div className="p-8 max-w-7xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
};
