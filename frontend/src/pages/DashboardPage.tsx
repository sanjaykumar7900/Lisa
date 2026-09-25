import React, { useEffect, useState } from 'react';
import { 
  FolderGit2, 
  PlayCircle, 
  CheckCircle2, 
  Bug as BugIcon, 
  Plus, 
  ArrowRight,
  Activity,
  BrainCircuit,
  CircleDot,
  Sparkles,
  Link,
  ListChecks,
  Play,
  SearchCheck
} from 'lucide-react';
import { MetricsCard } from '../components/MetricsCard';
import { LiveLogViewer } from '../components/LiveLogViewer';
import type { Project, TestRun, Bug } from '../types';
import { fetchProjects, fetchTestRuns, fetchBugs, createProject } from '../services/api';

interface DashboardPageProps {
  onSelectProject: (id: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onSelectProject }) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [testRuns, setTestRuns] = useState<TestRun[]>([]);
  const [bugs, setBugs] = useState<Bug[]>([]);
  const [newRepoUrl, setNewRepoUrl] = useState('');
  const [loading, setLoading] = useState(false);

  const loadData = async () => {
    try {
      const [p, tr, b] = await Promise.all([fetchProjects(), fetchTestRuns(), fetchBugs()]);
      setProjects(p);
      setTestRuns(tr);
      setBugs(b);
    } catch (err) {
      console.error('Failed loading dashboard data', err);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleAddProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRepoUrl.trim()) return;
    setLoading(true);
    try {
      const proj = await createProject(newRepoUrl);
      setNewRepoUrl('');
      await loadData();
      onSelectProject(proj.id);
    } catch (err: any) {
      alert(err.message || 'Error adding project');
    } finally {
      setLoading(false);
    }
  };

  // Metrics computation
  const totalProjects = projects.length;
  const totalExecutions = testRuns.reduce((acc, r) => acc + r.total_tests, 0);
  const totalPassed = testRuns.reduce((acc, r) => acc + r.passed_tests, 0);
  const passRate = totalExecutions > 0 ? ((totalPassed / totalExecutions) * 100).toFixed(1) : 'N/A';
  const totalBugs = bugs.length;
  const criticalBugs = bugs.filter((b) => b.severity === 'Critical').length;
  const latestRunId = testRuns.length > 0 ? testRuns[0].id : undefined;

  return (
    <div className="space-y-6 pb-12">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="eyebrow text-cyan-300">Overview</p>
          <h1 className="text-2xl md:text-3xl font-semibold tracking-tight mt-2">Your QA overview</h1>
          <p className="text-sm text-slate-500 mt-2">Connect a project to start testing your application.</p>
        </div>
        <div className="hidden md:flex items-center gap-2 text-[10px] mono text-slate-500">
          <Activity className="w-3.5 h-3.5 text-cyan-300" />
          <span>Everything is working</span>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1.6fr)_minmax(280px,.8fr)] gap-6">
        <div className="glass-card p-6 md:p-8 relative overflow-hidden">
          <div className="absolute -right-12 -top-16 w-64 h-64 rounded-full border border-cyan-300/10" />
          <div className="absolute -right-2 -top-6 w-44 h-44 rounded-full border border-cyan-300/[0.07]" />
          <div className="relative max-w-2xl">
            <div className="flex items-center gap-2 mb-5">
              <span className="status-dot" />
              <span className="eyebrow text-cyan-300">Add a project</span>
            </div>
            <h2 className="text-xl md:text-2xl font-semibold text-slate-100 mb-2">Start testing a GitHub project</h2>
            <p className="text-sm text-slate-400 mb-7 max-w-xl leading-6">
              Add your repository URL and LISA will review the code, find important areas to test, and create a test plan.
            </p>

          <form onSubmit={handleAddProject} className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <div className="relative flex-1">
              <FolderGit2 className="w-4 h-4 text-slate-600 absolute left-4 top-3.5" />
              <input
                type="text"
                aria-label="GitHub repository URL"
                placeholder="github.com/org/repository"
                value={newRepoUrl}
                onChange={(e) => setNewRepoUrl(e.target.value)}
                className="w-full bg-[#070A0F] border border-white/[0.1] rounded-md py-3 pl-11 pr-4 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-400/60 transition-colors mono"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-3 bg-cyan-300 hover:bg-cyan-200 text-[#041014] font-semibold rounded-md text-sm transition-all flex items-center justify-center space-x-2 shadow-[0_0_24px_rgba(0,229,255,.12)] shrink-0 disabled:opacity-50"
            >
              <Plus className="w-4 h-4" />
              <span>{loading ? 'Adding project...' : 'Add project'}</span>
            </button>
          </form>
          </div>
        </div>

        <div className="glass-card p-6 border-violet-400/15 bg-violet-400/[0.025]">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2"><BrainCircuit className="w-4 h-4 text-violet-300" /><span className="eyebrow text-violet-200">What LISA does</span></div>
            <span className="mono text-[10px] text-violet-300/70">READY</span>
          </div>
          <div className="flex items-center gap-4 mb-6">
            <div className="pulse-ring w-14 h-14 rounded-full border border-violet-300/40 bg-violet-400/10 flex items-center justify-center"><Sparkles className="w-5 h-5 text-violet-200" /></div>
            <div><p className="text-sm text-slate-200">Your testing assistant</p><p className="text-xs text-slate-500 mt-1">Ready to review your project</p></div>
          </div>
          <div className="space-y-3 text-xs">
            {['Review your project', 'Create a test plan', 'Run tests and report issues'].map((item, index) => <div key={item} className="flex items-center gap-3 text-slate-500"><CircleDot className={`w-3.5 h-3.5 ${index === 0 ? 'text-violet-300' : 'text-slate-700'}`} /><span>{item}</span></div>)}
          </div>
        </div>
      </div>

      <section className="glass-card p-5 md:p-6" aria-labelledby="getting-started-title">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 mb-5">
          <div>
            <p className="eyebrow text-cyan-300">Getting started</p>
            <h2 id="getting-started-title" className="text-lg font-semibold text-slate-100 mt-1">How to use LISA</h2>
          </div>
          <p className="text-xs text-slate-500">Follow these four steps to test your project.</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
          {[
            { number: '01', title: 'Add your project', text: 'Paste an authorized GitHub repository URL above.', icon: Link },
            { number: '02', title: 'Review the plan', text: 'Check the areas LISA recommends testing first.', icon: ListChecks },
            { number: '03', title: 'Run the tests', text: 'Start a test run from your project workspace.', icon: Play },
            { number: '04', title: 'Fix issues', text: 'Open the results to understand and resolve problems.', icon: SearchCheck },
          ].map((step) => {
            const Icon = step.icon;
            return (
              <div key={step.number} className="flex gap-3 p-3 rounded-md bg-white/[0.025] border border-white/[0.06]">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-cyan-400/20 bg-cyan-400/[0.06] text-cyan-300">
                  <Icon className="w-4 h-4" aria-hidden="true" />
                </div>
                <div>
                  <p className="mono text-[10px] text-cyan-300/70">STEP {step.number}</p>
                  <h3 className="text-sm font-medium text-slate-200 mt-1">{step.title}</h3>
                  <p className="text-xs leading-5 text-slate-500 mt-1">{step.text}</p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Metrics Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        <MetricsCard
          title="Projects"
          value={totalProjects}
          subtitle="Connected repositories"
          icon={FolderGit2}
          color="cyan"
        />
        <MetricsCard
          title="Tests run"
          value={totalExecutions}
          subtitle="Across all projects"
          icon={PlayCircle}
          color="purple"
        />
        <MetricsCard
          title="Tests passed"
          value={`${passRate}%`}
          subtitle="Average success rate"
          icon={CheckCircle2}
          color="emerald"
        />
        <MetricsCard
          title="Issues found"
          value={totalBugs}
          subtitle={`${criticalBugs} high priority`}
          icon={BugIcon}
          color="rose"
        />
      </div>

      {/* Live Log Streamer & Recent Runs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <LiveLogViewer runId={latestRunId} />
        </div>

        {/* Recent Projects Sidebar */}
        <div className="glass-card p-5 flex flex-col">
          <h3 className="eyebrow mb-4 flex items-center justify-between">
            <span>Recent projects</span>
            <span className="mono text-[10px] text-slate-600 font-normal">{String(projects.length).padStart(2, '0')} total</span>
          </h3>

          <div className="space-y-3 flex-1 overflow-y-auto max-h-72">
            {projects.length === 0 ? (
              <div className="text-xs text-slate-500 py-6 text-center">No projects added yet.</div>
            ) : (
              projects.map((proj) => (
                <button
                  key={proj.id}
                  onClick={() => onSelectProject(proj.id)}
                  className="w-full text-left p-3 rounded-lg bg-slate-900/60 hover:bg-slate-800/80 border border-slate-800/80 transition-colors flex items-center justify-between group"
                >
                  <div>
                    <h4 className="text-sm font-semibold text-slate-200 group-hover:text-cyan-400 transition-colors">
                      {proj.name}
                    </h4>
                    <p className="text-xs text-slate-500 truncate max-w-[200px]">{proj.repo_url}</p>
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-cyan-400 transition-colors" />
                </button>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
