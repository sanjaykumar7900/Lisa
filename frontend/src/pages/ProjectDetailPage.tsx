import React, { useEffect, useState } from 'react';
import { 
  Cpu, 
  FileSpreadsheet, 
  PlayCircle, 
  Layers, 
  Code2, 
  Loader2,
  Trash2,
  Download
} from 'lucide-react';
import type { Project, TestRun, QAReport, TestPlan } from '../types';
import { fetchProjects, analyzeProject, generateTestPlan, startTestRun, fetchReport, downloadTestResults, deleteProject } from '../services/api';
import { LiveLogViewer } from '../components/LiveLogViewer';

interface ProjectDetailPageProps {
  projectId: string;
  onDeleted: () => void;
}

export const ProjectDetailPage: React.FC<ProjectDetailPageProps> = ({ projectId, onDeleted }) => {
  const [project, setProject] = useState<Project | null>(null);
  const [activeRun, setActiveRun] = useState<TestRun | null>(null);
  const [report, setReport] = useState<QAReport | null>(null);
  const [testPlan, setTestPlan] = useState<TestPlan | null>(null);
  const [testOptions, setTestOptions] = useState({
    test_types: ['ui', 'api', 'db', 'security'],
    scopes: ['All Modules'],
    include_negative: true,
    include_boundary: false
  });
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState<string>('');
  const isAnalyzed = project?.status === 'ANALYZED' && Boolean(project.tech_stack);

  const loadProjectData = async () => {
    try {
      const projects = await fetchProjects();
      const proj = projects.find((p) => p.id === projectId);
      if (proj) setProject(proj);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadProjectData();
  }, [projectId]);

  const handleAnalyze = async () => {
    if (!project) return;
    setLoading(true);
    setCurrentStep('Analyzing repository structure and tech stack...');
    try {
      const updated = await analyzeProject(project.id);
      setProject(updated);
    } catch (err: any) {
      alert(err.message || 'Analysis failed');
    } finally {
      setLoading(false);
      setCurrentStep('');
    }
  };

  const handleGeneratePlan = async () => {
    if (!project) return;
    setLoading(true);
    setCurrentStep('Generating AI QA Test Plan & Structured Test Cases...');
    try {
      const generatedPlan = await generateTestPlan(project.id);
      setTestPlan(generatedPlan);
    } catch (err: any) {
      alert(err.message || 'Test Plan generation failed');
    } finally {
      setLoading(false);
      setCurrentStep('');
    }
  };

  const handleStartQA = async () => {
    if (!project) return;
    setLoading(true);
    setCurrentStep('Starting local app container & launching Playwright test run with selected options...');
    try {
      const run = await startTestRun(project.id, 3, testOptions);
      setActiveRun(run);
    } catch (err: any) {
      alert(err.message || 'Test execution failed');
    } finally {
      setLoading(false);
      setCurrentStep('');
    }
  };

  const handleGenerateReport = async () => {
    if (!activeRun) {
      alert('Please start a QA Test Run first.');
      return;
    }
    setLoading(true);
    try {
      const r = await fetchReport(activeRun.id);
      setReport(r);
    } catch (err: any) {
      alert(err.message || 'Report generation failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadResults = async () => {
    if (!activeRun) return;
    try {
      await downloadTestResults(activeRun.id);
    } catch (err: any) {
      alert(err.message || 'Failed to download test results');
    }
  };

  const handleDelete = async () => {
    if (!project || !window.confirm(`Delete ${project.name}? This removes all related test data.`)) return;
    setLoading(true);
    try {
      await deleteProject(project.id);
      onDeleted();
    } catch (err: any) {
      alert(err.message || 'Failed to delete project');
      setLoading(false);
    }
  };

  if (!project) return <div className="p-8 text-slate-400">Loading project details...</div>;
  const architecture = project.tech_stack?.architecture || [];

  return (
    <div className="space-y-8 pb-12">
      {/* Header Banner */}
      <div className="glass-card p-6 rounded-xl border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-3 mb-1">
            <h2 className="text-2xl font-bold text-slate-100">{project.name}</h2>
            <span className="text-xs px-2.5 py-1 rounded-md font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
              {project.status}
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono">{project.repo_url}</p>
        </div>

        {/* 4 Required Action Buttons */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleDelete}
            disabled={loading}
            aria-label="Delete project"
            title="Delete project"
            className="p-2.5 text-rose-300 hover:bg-rose-400/10 border border-rose-400/20 rounded-lg transition-colors disabled:opacity-50"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button
            onClick={handleAnalyze}
            disabled={loading}
            className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold rounded-lg text-xs transition-colors flex items-center space-x-2 border border-slate-700 disabled:opacity-50"
          >
            <Code2 className="w-4 h-4 text-cyan-400" />
            <span>Analyze Project</span>
          </button>

          <button
            onClick={handleGeneratePlan}
            disabled={loading || !isAnalyzed}
            title={!isAnalyzed ? 'Analyze the project first' : 'Generate a test plan'}
            className="px-4 py-2.5 bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 font-semibold rounded-lg text-xs transition-colors flex items-center space-x-2 border border-purple-500/30 disabled:opacity-50"
          >
            <Cpu className="w-4 h-4 text-purple-400" />
            <span>Generate Test Plan</span>
          </button>

          {/* Dropdown Test Options */}
          <div className="w-full md:w-auto bg-slate-900/60 border border-slate-700 rounded-xl p-4 space-y-3">
            <p className="text-[10px] text-slate-500 uppercase font-bold tracking-wide">Test Options</p>
            <div className="flex flex-wrap gap-2">
              <label className="text-xs text-slate-300 flex items-center gap-2">
                <input type="checkbox" checked={testOptions.include_negative}
                  onChange={e => setTestOptions({...testOptions, include_negative: e.target.checked})}
                  className="accent-cyan-500 w-3.5 h-3.5" />
                Negative Tests
              </label>
              <label className="text-xs text-slate-300 flex items-center gap-2">
                <input type="checkbox" checked={testOptions.include_boundary}
                  onChange={e => setTestOptions({...testOptions, include_boundary: e.target.checked})}
                  className="accent-violet-500 w-3.5 h-3.5" />
                Boundary Tests
              </label>
            </div>
            <div className="flex gap-2">
              <select
                value={testOptions.scopes[0] || 'All Modules'}
                onChange={e => setTestOptions({...testOptions, scopes: [e.target.value]})}
                className="text-xs bg-slate-800 border border-slate-600 rounded px-2 py-1 text-slate-200 w-full"
              >
                <option>All Modules</option>
                <option>Frontend Only</option>
                <option>Backend Only</option>
                <option>API Only</option>
              </select>
            </div>
            <p className="text-[10px] text-slate-500">Selected: {testOptions.test_types.join(', ')} · Scope: {testOptions.scopes.join(', ')}</p>
          </div>

          <button
            onClick={handleStartQA}
            disabled={loading || !isAnalyzed}
            title={!isAnalyzed ? 'Analyze the project first' : 'Start the QA test'}
            className="px-5 py-2.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold rounded-lg text-xs transition-colors flex items-center space-x-2 shadow-lg shadow-cyan-500/20 disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlayCircle className="w-4 h-4" />}
            <span>Start QA Test</span>
          </button>

          <button
            onClick={handleGenerateReport}
            disabled={loading}
            className="px-4 py-2.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 font-semibold rounded-lg text-xs transition-colors flex items-center space-x-2 border border-emerald-500/30 disabled:opacity-50"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
            <span>Generate Report</span>
          </button>
        </div>
      </div>

      {loading && currentStep && (
        <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-xl p-4 flex items-center space-x-3 text-cyan-300 text-xs animate-pulse">
          <Loader2 className="w-4 h-4 animate-spin shrink-0" />
          <span>{currentStep}</span>
        </div>
      )}

      {/* Circular Progress Bar */}
      {activeRun && (
        <div className="glass-card p-5 rounded-xl border border-cyan-400/20 flex items-center gap-5">
          <div className="relative w-20 h-20 shrink-0">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="42" stroke="rgba(255,255,255,0.06)" strokeWidth="8" fill="none" />
              <circle
                cx="50" cy="50" r="42"
                stroke="#22d3ee"
                strokeWidth="8"
                fill="none"
                strokeLinecap="round"
                strokeDasharray={`${(activeRun.total_tests > 0 ? ((activeRun.passed_tests + activeRun.failed_tests) / activeRun.total_tests * 264) : 0)} 264`}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-lg font-extrabold text-cyan-300 leading-none">{activeRun.total_tests > 0 ? Math.round(((activeRun.passed_tests + activeRun.failed_tests) / activeRun.total_tests) * 100) : 0}%</span>
              <span className="text-[9px] text-slate-500 mt-0.5">Done</span>
            </div>
          </div>
          <div className="flex-1 min-w-0 space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-bold text-slate-100">Run Progress</h4>
              <span className="text-[10px] text-cyan-400 font-mono">{activeRun.run_number}</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-700">
              <div
                className="bg-gradient-to-r from-cyan-500 to-cyan-300 h-2 rounded-full transition-all duration-700 ease-out"
                style={{ width: `${activeRun.total_tests > 0 ? ((activeRun.passed_tests + activeRun.failed_tests) / activeRun.total_tests) * 100 : 0}%` }}
              />
            </div>
            <div className="flex items-center gap-4 text-[11px] text-slate-400">
              <span>✓ Passed: <b className="text-emerald-400">{activeRun.passed_tests}</b></span>
              <span>✗ Failed: <b className="text-rose-400">{activeRun.failed_tests}</b></span>
              <span>⏱ {new Date(activeRun.started_at || '').toLocaleTimeString()} — {activeRun.completed_at ? new Date(activeRun.completed_at).toLocaleTimeString() : 'Running...'}</span>
            </div>
          </div>
        </div>
      )}

      {/* Tech Stack Details */}
      {project.tech_stack && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="glass-card p-4 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase font-semibold block mb-1">Frontend</span>
            <span className="text-sm font-bold text-slate-200">{project.tech_stack.frontend}</span>
          </div>
          <div className="glass-card p-4 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase font-semibold block mb-1">Backend</span>
            <span className="text-sm font-bold text-slate-200">{project.tech_stack.backend}</span>
          </div>
          <div className="glass-card p-4 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase font-semibold block mb-1">Database</span>
            <span className="text-sm font-bold text-slate-200">{project.tech_stack.database}</span>
          </div>
          <div className="glass-card p-4 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase font-semibold block mb-1">Build System</span>
            <span className="text-sm font-bold text-slate-200">{project.tech_stack.package_manager}</span>
          </div>
          <div className="glass-card p-4 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-500 uppercase font-semibold block mb-1">ORM</span>
            <span className="text-sm font-bold text-slate-200">{project.tech_stack.orm}</span>
          </div>
        </div>
      )}

      {project.tech_stack && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <div className="glass-card p-6 border-cyan-400/15">
            <div className="flex items-center justify-between mb-5">
              <div><p className="eyebrow text-cyan-300">Architecture</p><h3 className="text-lg font-semibold text-slate-100 mt-1">How this project is connected</h3></div>
              <span className="mono text-[10px] text-slate-500">{project.tech_stack.route_count || 0} routes / {project.tech_stack.api_count || 0} API calls</span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {architecture.map((node, index) => (
                <React.Fragment key={`${node.label}-${index}`}>
                  <button type="button" title={`Evidence: ${(node.evidence || []).join(', ') || 'No files recorded'}`} className="text-left px-3 py-2 rounded-md border border-cyan-400/20 bg-cyan-400/[0.05] hover:border-cyan-300/50 transition-colors">
                    <p className="text-xs font-medium text-slate-200">{node.label}</p><p className="text-[10px] text-slate-500 mt-1">{(node.evidence || []).slice(0, 2).join(', ') || 'Detected from repository'}</p>
                  </button>
                  {index < architecture.length - 1 && <span className="text-cyan-300">→</span>}
                </React.Fragment>
              ))}
            </div>
            <div className="mt-5 space-y-2">
              {(project.tech_stack.ports || []).map((service) => <div key={service.name} className="flex justify-between text-xs border-t border-white/[0.06] pt-2"><span className="text-slate-400">{service.name} / {service.technology}</span><span className="mono text-cyan-300">:{service.port}</span></div>)}
            </div>
          </div>
          <div className="glass-card p-6 border-violet-400/15 bg-violet-400/[0.025]">
            <p className="eyebrow text-violet-200">LISA reasoning</p>
            <h3 className="text-lg font-semibold text-slate-100 mt-1">Why these areas matter</h3>
            <p className="text-sm text-slate-400 mt-4 leading-6">I detected {project.tech_stack.frontend || 'an application'} connected to {project.tech_stack.backend || 'a service'}{project.tech_stack.orm && project.tech_stack.orm !== 'Not detected' ? ` through ${project.tech_stack.orm}` : ''}{project.tech_stack.database && project.tech_stack.database !== 'Not detected' ? ` and ${project.tech_stack.database}` : ''}.</p>
            <div className="mt-4 grid grid-cols-2 gap-2 text-xs text-slate-400"><span>✓ API testing</span><span>✓ UI testing</span><span>✓ Negative testing</span><span>✓ Boundary testing</span><span>✓ Integration testing</span><span>✓ Regression testing</span></div>
            <p className="text-[10px] text-slate-600 mt-4">Reasoning is based on detected files: {(project.tech_stack.evidence?.backend || []).slice(0, 3).join(', ')}</p>
          </div>
        </div>
      )}

      {/* Discovered Modules & Real-time Live Log Viewer */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <LiveLogViewer runId={activeRun?.id} />
        </div>

        <div className="glass-card p-6 rounded-xl border border-slate-800 flex flex-col space-y-4">
          <h3 className="font-bold text-slate-200 text-sm flex items-center space-x-2">
            <Layers className="w-4 h-4 text-cyan-400" />
            <span>Discovered Modules ({project.modules?.length || 0})</span>
          </h3>

          <div className="space-y-2 overflow-y-auto max-h-80 text-xs">
            {project.modules?.map((mod, idx) => (
              <div key={idx} className="bg-slate-900/60 p-3 rounded-lg border border-slate-800/80">
                <div className="flex justify-between font-semibold text-slate-300">
                  <span>{mod.name}</span>
                  <span className="text-slate-500">{mod.files_count} files</span>
                </div>
                <div className="text-xs text-cyan-300 mt-1">{mod.role || 'Repository module'}</div>
                <div className="text-[10px] text-slate-500 mt-1">{mod.routes_count || 0} routes · {mod.components_count || mod.controllers_count || 0} components/controllers · {mod.api_count || 0} API calls/endpoints</div>
                <div className="text-[10px] text-slate-600 mt-1 truncate">Path: {mod.path}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {testPlan && (
        <div className="glass-card p-6 border-violet-400/15">
          <div className="flex items-center justify-between mb-4"><div><p className="eyebrow text-violet-200">Generated test plan</p><h3 className="text-lg font-semibold text-slate-100 mt-1">{testPlan.test_cases.length} repository-specific test cases</h3></div><span className="text-xs text-slate-500">Priority: {testPlan.priority}</span></div>
          <div className="overflow-x-auto"><table className="w-full text-left text-xs"><thead className="text-slate-500 border-b border-white/[0.08]"><tr><th className="py-3 pr-4">ID</th><th className="py-3 pr-4">Test</th><th className="py-3 pr-4">Type</th><th className="py-3 pr-4">Priority</th><th className="py-3">Expected result</th></tr></thead><tbody>{testPlan.test_cases.map((test) => <tr key={test.id} className="border-b border-white/[0.05]"><td className="py-3 pr-4 mono text-cyan-300">{test.test_id}</td><td className="py-3 pr-4 text-slate-200"><div>{test.title}</div><div className="text-[10px] text-slate-500 mt-1">{test.description}</div></td><td className="py-3 pr-4 text-slate-400">{test.test_type}</td><td className="py-3 pr-4 text-amber-300">{test.priority}</td><td className="py-3 text-slate-400">{test.expected_result}</td></tr>)}</tbody></table></div>
        </div>
      )}

      {/* Generated Report View */}
      {report && (
        <div className="glass-card p-8 rounded-2xl border border-slate-800 space-y-6">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <h3 className="text-xl font-bold text-slate-100">QA Executive Report</h3>
              <p className="text-xs text-slate-400">Generated at {new Date(report.generated_at).toLocaleString()}</p>
            </div>
            <div className="flex items-center gap-2">
              {activeRun && (
                <button
                  onClick={handleDownloadResults}
                  title="Download test case results as CSV"
                  aria-label="Download test case results as CSV"
                  className="p-2 text-cyan-300 hover:bg-cyan-400/10 border border-cyan-400/20 rounded-lg"
                >
                  <Download className="w-4 h-4" />
                </button>
              )}
              <span className={`px-4 py-1.5 rounded-lg text-sm font-bold border ${
                report.recommendation === 'PASS' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
              }`}>
                {report.recommendation}
              </span>
            </div>
          </div>

          <p className="text-sm text-slate-300 bg-slate-950 p-4 rounded-xl border border-slate-800">
            {report.executive_summary}
          </p>

          {report.html_report && (
            <div>
              <h4 className="text-sm font-bold text-slate-300 mb-2">HTML Report Preview</h4>
              <iframe
                srcDoc={report.html_report}
                className="w-full h-96 rounded-xl border border-slate-800 bg-slate-950"
                title="LISA HTML QA Report"
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};
