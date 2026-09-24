import React, { useEffect, useState } from 'react';
import { ShieldAlert, CheckCircle, ExternalLink } from 'lucide-react';
import type { Bug } from '../types';
import { fetchBugs } from '../services/api';
import { HumanApprovalModal } from '../components/HumanApprovalModal';

export const BugsPage: React.FC = () => {
  const [bugs, setBugs] = useState<Bug[]>([]);
  const [selectedBug, setSelectedBug] = useState<Bug | null>(null);

  const loadBugs = async () => {
    try {
      const data = await fetchBugs();
      setBugs(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadBugs();
  }, []);

  return (
    <div className="space-y-6 pb-12">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100">Confirmed Defects & Bugs</h2>
          <p className="text-xs text-slate-400">Classified application defects with root cause analysis & evidence.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {bugs.length === 0 ? (
          <div className="glass-card p-12 text-center text-slate-500 rounded-xl">
            No confirmed defects reported yet.
          </div>
        ) : (
          bugs.map((bug) => (
            <div key={bug.id} className="glass-card p-6 rounded-xl border border-slate-800 space-y-4">
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-3">
                  <span className="font-mono text-sm font-bold text-cyan-400">{bug.bug_id}</span>
                  <h3 className="font-bold text-slate-100 text-base">{bug.title}</h3>
                </div>

                <div className="flex items-center space-x-2">
                  <span className={`px-2.5 py-1 rounded text-xs font-bold ${
                    bug.severity === 'Critical' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30' : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                  }`}>
                    {bug.severity}
                  </span>
                  <span className="bg-slate-800 text-slate-300 px-2 py-0.5 rounded text-xs font-semibold">
                    {bug.priority}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <span className="text-slate-500 font-semibold block mb-1">Actual Result Error:</span>
                  <p className="text-rose-300 font-mono">{bug.actual_result}</p>
                </div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <span className="text-slate-500 font-semibold block mb-1">Likely Root Cause:</span>
                  <p className="text-slate-300">{bug.root_cause}</p>
                </div>
              </div>

              {/* GitHub Issue Action Bar */}
              <div className="pt-2 flex items-center justify-between border-t border-slate-800/80">
                <span className="text-xs text-slate-500">Env: {bug.environment}</span>

                {bug.github_issue_status === 'CREATED' ? (
                  <a
                    href={bug.github_issue_url || '#'}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-emerald-400 hover:underline flex items-center space-x-1 font-semibold"
                  >
                    <CheckCircle className="w-4 h-4" />
                    <span>GitHub Issue Created</span>
                    <ExternalLink className="w-3 h-3 ml-1" />
                  </a>
                ) : (
                  <button
                    onClick={() => setSelectedBug(bug)}
                    className="px-3 py-1.5 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-lg text-xs font-semibold transition-colors flex items-center space-x-1.5"
                  >
                    <ShieldAlert className="w-4 h-4 text-amber-400" />
                    <span>Approve & Create GitHub Issue</span>
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      <HumanApprovalModal
        bug={selectedBug}
        onClose={() => setSelectedBug(null)}
        onApproved={loadBugs}
      />
    </div>
  );
};
