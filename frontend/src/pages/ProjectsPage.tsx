import React, { useEffect, useState } from 'react';
import { FolderGit2, Plus, ArrowRight, Trash2 } from 'lucide-react';
import type { Project } from '../types';
import { fetchProjects, createProject, deleteProject } from '../services/api';

interface ProjectsPageProps {
  onSelectProject: (id: string) => void;
}

export const ProjectsPage: React.FC<ProjectsPageProps> = ({ onSelectProject }) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [repoUrl, setRepoUrl] = useState('');

  const loadProjects = async () => {
    try {
      const data = await fetchProjects();
      setProjects(data);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl.trim()) return;
    try {
      const p = await createProject(repoUrl);
      setRepoUrl('');
      await loadProjects();
      onSelectProject(p.id);
    } catch (err: any) {
      alert(err.message || 'Error creating project');
    }
  };

  const handleDelete = async (project: Project) => {
    if (!window.confirm(`Delete ${project.name}? This removes its test plans, runs, issues, and analysis data.`)) return;
    try {
      await deleteProject(project.id);
      await loadProjects();
    } catch (err: any) {
      alert(err.message || 'Error deleting project');
    }
  };

  return (
    <div className="space-y-6 pb-12">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100">Authorized GitHub Repositories</h2>
          <p className="text-xs text-slate-400">Manage open-source applications target testing pipelines.</p>
        </div>

        <form onSubmit={handleAdd} className="flex items-center space-x-2">
          <input
            type="text"
            placeholder="https://github.com/org/repo"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-xs text-slate-200 placeholder-slate-500 w-72 focus:outline-none focus:border-cyan-500"
          />
          <button
            type="submit"
            className="px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold rounded-lg text-xs transition-colors flex items-center space-x-1"
          >
            <Plus className="w-4 h-4" />
            <span>Add Repo</span>
          </button>
        </form>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map((proj) => (
          <div key={proj.id} className="glass-card glass-card-hover p-6 rounded-xl border border-slate-800 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <div className="p-2 bg-cyan-500/10 rounded-lg border border-cyan-500/30 text-cyan-400">
                  <FolderGit2 className="w-5 h-5" />
                </div>
                <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded border ${
                  proj.status === 'ANALYZED' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-slate-800 text-slate-400 border-slate-700'
                }`}>
                  {proj.status}
                </span>
              </div>

              <div className="flex items-start justify-between gap-3">
                <h3 className="font-bold text-lg text-slate-100 mb-1">{proj.name}</h3>
                <button
                  type="button"
                  aria-label={`Delete ${proj.name}`}
                  title="Delete project"
                  onClick={() => handleDelete(proj)}
                  className="p-2 text-slate-500 hover:text-rose-300 hover:bg-rose-400/10 rounded-md transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
              <p className="text-xs text-slate-400 mb-4 truncate">{proj.repo_url}</p>

              {proj.tech_stack && (
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs space-y-1 mb-4">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Frontend:</span>
                    <span className="text-slate-300 font-medium">{proj.tech_stack.frontend || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Backend:</span>
                    <span className="text-slate-300 font-medium">{proj.tech_stack.backend || 'N/A'}</span>
                  </div>
                </div>
              )}
            </div>

            <button
              onClick={() => onSelectProject(proj.id)}
              className="w-full mt-2 py-2 bg-slate-800 hover:bg-cyan-500/10 hover:text-cyan-400 border border-slate-700 hover:border-cyan-500/30 text-slate-300 rounded-lg text-xs font-semibold transition-all flex items-center justify-center space-x-2"
            >
              <span>View QA Workspace</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
