import React from 'react';
import { 
  LayoutDashboard, 
  FolderGit2, 
  PlayCircle, 
  FileCheck2, 
  Bug, 
  Cpu, 
  FileSpreadsheet, 
  Settings, 
  Bot 
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab }) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'projects', label: 'Projects', icon: FolderGit2 },
    { id: 'test-runs', label: 'Test runs', icon: PlayCircle },
    { id: 'test-cases', label: 'Test cases', icon: FileCheck2 },
    { id: 'bugs', label: 'Issues found', icon: Bug },
    { id: 'automation', label: 'AI assistant', icon: Cpu },
    { id: 'reports', label: 'Reports', icon: FileSpreadsheet },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-[#080C12]/95 border-r border-white/[0.07] flex flex-col h-screen sticky top-0">
      {/* Brand Header */}
      <div className="p-5 border-b border-white/[0.07] flex items-center space-x-3">
        <div className="pulse-ring w-10 h-10 rounded-full bg-cyan-400/10 border border-cyan-300/50 text-cyan-300 flex items-center justify-center">
          <Bot className="w-5 h-5" />
        </div>
        <div>
          <h1 className="font-semibold text-lg tracking-[0.2em] text-white">LISA</h1>
          <p className="eyebrow mt-0.5">AI test assistant</p>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto" aria-label="Primary navigation">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-md text-sm font-medium transition-all border ${
                isActive
                  ? 'bg-cyan-400/[0.08] text-cyan-300 border-cyan-400/25 shadow-[inset_2px_0_0_#00E5FF]'
                  : 'text-slate-500 border-transparent hover:bg-white/[0.03] hover:text-slate-200'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-300' : 'text-slate-600'}`} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Status Footer */}
      <div className="p-4 border-t border-white/[0.07] bg-black/10">
        <div className="flex items-center justify-between text-[10px] mono tracking-wider text-slate-500">
          <span>Assistant status</span>
          <span className="flex items-center space-x-2 text-emerald-400 font-semibold">
            <span className="status-dot !w-1.5 !h-1.5 !bg-emerald-400 !shadow-[0_0_8px_rgba(34,197,94,.8)]"></span>
            <span>READY</span>
          </span>
        </div>
      </div>
    </aside>
  );
};
