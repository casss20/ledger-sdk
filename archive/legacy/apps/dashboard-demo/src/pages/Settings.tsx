import React from 'react';
import { Settings as SettingsIcon, Globe, Database, Shield, Server } from 'lucide-react';

export const Settings: React.FC = () => {
  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-white">Settings</h1>
          <p className="text-sm text-slate-500 mt-1">System configuration and status</p>
        </div>
        <SettingsIcon size={20} className="text-slate-500" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* API Configuration */}
        <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/50">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-blue-500/10 flex items-center justify-center">
              <Globe size={20} className="text-blue-500" />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-200">API Endpoint</p>
              <p className="text-xs text-slate-500">Connected backend</p>
            </div>
          </div>
          <div className="p-3 rounded-xl bg-slate-950/50 border border-slate-800/50">
            <code className="text-xs text-emerald-400">https://api.citadelsdk.com</code>
          </div>
        </div>

        {/* Database */}
        <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/50">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center">
              <Database size={20} className="text-purple-500" />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-200">Database</p>
              <p className="text-xs text-slate-500">PostgreSQL on Neon</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-xs font-bold text-emerald-500">Connected</span>
          </div>
        </div>

        {/* Security */}
        <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/50">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-orange-500/10 flex items-center justify-center">
              <Shield size={20} className="text-orange-500" />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-200">Security</p>
              <p className="text-xs text-slate-500">Active protections</p>
            </div>
          </div>
          <div className="space-y-2">
            {['Rate Limiting', 'Tenant Isolation', 'Audit Logging', 'SSL/TLS'].map((item, i) => (
              <div key={i} className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                <span className="text-xs text-slate-400">{item}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Deployment */}
        <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/50">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center">
              <Server size={20} className="text-indigo-500" />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-200">Deployment</p>
              <p className="text-xs text-slate-500">Infrastructure</p>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">Platform</span>
              <span className="text-xs font-bold text-slate-300">Fly.io</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">Region</span>
              <span className="text-xs font-bold text-slate-300">IAD (Virginia)</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">SSL</span>
              <span className="text-xs font-bold text-emerald-500">Let's Encrypt</span>
            </div>
          </div>
        </div>
      </div>

      {/* Version Info */}
      <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800/50">
        <h3 className="text-sm font-bold text-slate-200 mb-4">System Information</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p className="text-[10px] font-bold text-slate-500 uppercase mb-1">Version</p>
            <p className="text-xs text-slate-300">1.0.0</p>
          </div>
          <div>
            <p className="text-[10px] font-bold text-slate-500 uppercase mb-1">Dashboard</p>
            <p className="text-xs text-slate-300">React + Vite + Tailwind</p>
          </div>
          <div>
            <p className="text-[10px] font-bold text-slate-500 uppercase mb-1">API</p>
            <p className="text-xs text-slate-300">FastAPI + PostgreSQL</p>
          </div>
        </div>
      </div>
    </div>
  );
};
