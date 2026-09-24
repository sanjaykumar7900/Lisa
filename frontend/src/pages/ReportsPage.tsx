import React, { useEffect, useState } from 'react';
import { Download } from 'lucide-react';
import type { TestRun } from '../types';
import { fetchTestRuns, fetchReport, downloadTestResults } from '../services/api';

export const ReportsPage: React.FC = () => {
  const [runs, setRuns] = useState<TestRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>('');
  const [report, setReport] = useState<any>(null);

  useEffect(() => {
    fetchTestRuns().then((data) => {
      setRuns(data);
      if (data.length > 0) {
        setSelectedRunId(data[0].id);
        fetchReport(data[0].id).then(setReport).catch(console.error);
      }
    });
  }, []);

  const handleSelectRun = (id: string) => {
    setSelectedRunId(id);
    fetchReport(id).then(setReport).catch(console.error);
  };

  const handleDownloadResults = async () => {
    if (!selectedRunId) return;
    try {
      await downloadTestResults(selectedRunId);
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Failed to download test results');
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100">QA Executive Reports</h2>
          <p className="text-xs text-slate-400">Downloadable HTML/JSON reports and release recommendations.</p>
        </div>

        {runs.length > 0 && (
          <div className="flex items-center gap-2">
            <select
              value={selectedRunId}
              onChange={(e) => handleSelectRun(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            >
              {runs.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.run_number} ({r.status})
                </option>
              ))}
            </select>
            <button
              onClick={handleDownloadResults}
              disabled={!selectedRunId}
              title="Download test case results as CSV"
              aria-label="Download test case results as CSV"
              className="p-2 text-cyan-300 hover:bg-cyan-400/10 border border-cyan-400/20 rounded-lg disabled:opacity-50"
            >
              <Download className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {report ? (
        <div className="glass-card p-8 rounded-2xl border border-slate-800 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs text-slate-500 uppercase font-semibold block">Release Recommendation</span>
              <span className={`text-xl font-extrabold ${
                report.recommendation === 'PASS' ? 'text-emerald-400' : (report.recommendation === 'FAIL' ? 'text-rose-400' : 'text-amber-400')
              }`}>
                {report.recommendation}
              </span>
            </div>

            <div className="text-right">
              <span className="text-xs text-slate-500 uppercase font-semibold block">Pass Rate</span>
              <span className="text-2xl font-bold text-cyan-400">
                {report.pass_rate !== null && report.pass_rate !== undefined ? `${report.pass_rate}%` : 'N/A'}
              </span>
            </div>
          </div>

          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs text-slate-300">
            <p className="font-semibold text-slate-200 mb-1">Reasoning:</p>
            <p>{report.recommendation_reasoning}</p>
          </div>

          {report.execution_summary && (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {[
                ['Total', report.execution_summary.total],
                ['Passed', report.execution_summary.passed],
                ['Failed', report.execution_summary.failed],
                ['Blocked', report.execution_summary.blocked],
                ['Pass rate', report.execution_summary.pass_rate !== null && report.execution_summary.pass_rate !== undefined ? `${report.execution_summary.pass_rate}%` : 'N/A'],
              ].map(([label, value]) => <div key={label} className="glass-card p-4"><span className="eyebrow">{label}</span><p className="mono text-xl text-slate-100 mt-2">{value}</p></div>)}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
              <p className="eyebrow text-cyan-300">Detected stack</p>
              <p className="text-slate-300 mt-3">{report.detected_technology_stack?.frontend || 'Frontend not detected'} · {report.detected_technology_stack?.backend || 'Backend not detected'} · {report.detected_technology_stack?.database || 'Database not detected'}</p>
              <p className="text-slate-500 mt-2">Code Coverage: {report.code_coverage || 'NOT MEASURED'}</p>
            </div>
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800">
              <p className="eyebrow text-violet-200">Test strategy</p>
              <p className="text-slate-400 mt-3">{report.test_strategy}</p>
              {report.recommendations?.map((item: string) => <p key={item} className="text-slate-500 mt-2">• {item}</p>)}
            </div>
          </div>

          {report.html_report && (
            <div>
              <h3 className="text-sm font-bold text-slate-200 mb-3">Standalone HTML Report View</h3>
              <iframe
                srcDoc={report.html_report}
                className="w-full h-[500px] rounded-xl border border-slate-800 bg-slate-950"
                title="QA Report iframe"
              />
            </div>
          )}
        </div>
      ) : (
        <div className="glass-card p-12 text-center text-slate-500 rounded-xl">
          No reports generated yet. Run a QA Test pipeline first.
        </div>
      )}
    </div>
  );
};
