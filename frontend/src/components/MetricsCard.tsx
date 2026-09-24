import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface MetricsCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  color?: 'cyan' | 'emerald' | 'amber' | 'rose' | 'purple';
}

export const MetricsCard: React.FC<MetricsCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  color = 'cyan'
}) => {
  const colorMap = {
    cyan: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    rose: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
  };

  return (
    <div className="glass-card glass-card-hover p-5 relative overflow-hidden">
      <div className="flex items-center justify-between">
        <div>
          <p className="eyebrow">{title}</p>
          <p className="text-3xl font-semibold text-slate-100 mt-3 tracking-tight mono">{value}</p>
          {subtitle && <p className="text-[11px] text-slate-500 mt-2">{subtitle}</p>}
        </div>

        <div className={`p-2.5 rounded-md border ${colorMap[color]}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
    </div>
  );
};
