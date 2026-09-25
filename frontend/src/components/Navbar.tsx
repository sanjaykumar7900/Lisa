import React from 'react';
import { Bell, Command, Shield } from 'lucide-react';

interface NavbarProps {
  title: string;
}

export const Navbar: React.FC<NavbarProps> = ({ title }) => {
  return (
    <header className="min-h-16 bg-[#080C12]/80 backdrop-blur-xl border-b border-white/[0.07] px-5 md:px-8 py-3 flex items-center justify-between gap-4 sticky top-0 z-10">
      <div className="flex items-center space-x-3">
        <div>
          <p className="eyebrow">LISA / Quality dashboard</p>
          <h2 className="text-base font-semibold text-slate-100 mt-1">{title}</h2>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        <div className="hidden xl:flex items-center gap-2 px-3 py-2 border border-emerald-400/20 bg-emerald-400/[0.05] rounded-md text-[10px] mono tracking-wide">
          <span className="status-dot !w-1.5 !h-1.5 !bg-emerald-400 !shadow-[0_0_8px_rgba(34,197,94,.8)]"></span>
          <span className="text-emerald-300">Ready to help</span>
        </div>
        <div className="hidden md:flex items-center gap-2 text-[10px] mono text-slate-500">
          <Shield className="w-3.5 h-3.5 text-cyan-300" />
          <span>AI provider: <b className="text-slate-300 font-medium">NVIDIA</b></span>
          <span className="text-slate-700">/</span>
          <span>Latest run: <b className="text-slate-300 font-medium">—</b></span>
        </div>
        <button aria-label="Open command palette" className="hidden sm:flex items-center gap-2 px-3 py-2 text-[10px] mono text-slate-500 hover:text-cyan-300 border border-white/[0.08] rounded-md transition-colors">
          <Command className="w-3.5 h-3.5" /> <span>Commands</span>
        </button>
        <button aria-label="View notifications" className="p-2 text-slate-400 hover:text-slate-200 border border-white/[0.08] rounded-md transition-colors">
          <Bell className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
