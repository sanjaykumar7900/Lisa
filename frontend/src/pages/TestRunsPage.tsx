import React, { useEffect, useState } from 'react';
import type { TestRun } from '../types';
import { fetchTestRuns } from '../services/api';

export const TestRunsPage: React.FC = () => {
  const [runs, setRuns] = useState<TestRun[]>([]);

  useEffect(() => {
    fetchTestRuns().then(setRuns).catch(console.error);
  }, []);

  return (
    <div className="space-y-6 pb-12">
      <div>
        <h2 className="text-xl font-bold text-slate-100">Test Runs History</h2>
        <p className="text-xs text-slate-400">Execution logs and pass/fail metrics across all projects.</p>
      </div>

      <div className="glass-card rounded-xl border border-slate-800 overflow-hidden">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-900 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
            <tr>
              <th className="px-6 py-4">Run ID</th>
              <th className="px-6 py-4">Autonomy Level</th>
              <th className="px-6 py-4">Total Tests</th>
              <th className="px-6 py-4">Passed</th>
              <th className="px-6 py-4">Failed</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Started At</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {runs.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-8 text-center text-slate-500">
                  No test runs recorded yet.
                </td>
              </tr>
            ) : (
              runs.map((r) => (
                <tr key={r.id} className="hover:bg-slate-900/40 transition-colors">
                  <td className="px-6 py-4 font-mono font-bold text-cyan-400">{r.run_number}</td>
                  <td className="px-6 py-4">Level {r.autonomy_level}</td>
                  <td className="px-6 py-4 font-semibold text-slate-100">{r.total_tests}</td>
                  <td className="px-6 py-4 text-emerald-400 font-semibold">{r.passed_tests}</td>
                  <td className="px-6 py-4 text-rose-400 font-semibold">{r.failed_tests}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2.5 py-1 rounded text-[10px] font-bold uppercase ${
                      r.status === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
                    }`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-slate-500">{r.started_at ? new Date(r.started_at).toLocaleString() : 'N/A'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
