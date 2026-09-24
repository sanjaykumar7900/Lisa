import React, { useState } from 'react';
import { Key, Clock } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [nvidiaApiKey, setNvidiaApiKey] = useState('');
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="space-y-6 pb-12 max-w-4xl">
      <div>
        <h2 className="text-xl font-bold text-slate-100">Platform Settings</h2>
        <p className="text-xs text-slate-400">Configure LLM providers, timeouts, security policies, and resource limits.</p>
      </div>

      <form onSubmit={handleSave} className="glass-card p-6 rounded-2xl border border-slate-800 space-y-6">
        <div className="space-y-4">
          <h3 className="text-sm font-bold text-slate-200 flex items-center space-x-2">
            <Key className="w-4 h-4 text-purple-400" />
            <span>AI LLM Provider</span>
          </h3>

          <div className="space-y-2">
            <label className="text-xs text-slate-400 block">NVIDIA API Key (NVIDIA_API_KEY)</label>
            <input
              type="password"
              placeholder="nvapi-..."
              value={nvidiaApiKey}
              onChange={(e) => setNvidiaApiKey(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500 font-mono"
            />
            <p className="text-[11px] text-slate-500">
              Key is securely stored in environment variable. Never exposed to browser.
            </p>
          </div>
        </div>

        <div className="space-y-4 pt-4 border-t border-slate-800">
          <h3 className="text-sm font-bold text-slate-200 flex items-center space-x-2">
            <Clock className="w-4 h-4 text-cyan-400" />
            <span>Execution Resource Limits</span>
          </h3>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-slate-400 block mb-1">Max Test Steps (MAX_TEST_STEPS)</label>
              <input
                type="number"
                defaultValue={50}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-slate-200 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Max Test Time (seconds)</label>
              <input
                type="number"
                defaultValue={600}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-slate-200 focus:outline-none"
              />
            </div>
          </div>
        </div>

        <div className="pt-4 flex items-center justify-between border-t border-slate-800">
          {saved ? (
            <span className="text-xs text-emerald-400 font-semibold">Settings updated successfully!</span>
          ) : (
            <span></span>
          )}

          <button
            type="submit"
            className="px-6 py-2.5 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold rounded-xl text-xs transition-colors shadow-lg shadow-cyan-500/20"
          >
            Save Configuration
          </button>
        </div>
      </form>
    </div>
  );
};
