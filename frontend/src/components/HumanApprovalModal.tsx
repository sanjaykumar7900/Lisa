import React from 'react';
import { ShieldAlert, CheckCircle, XCircle } from 'lucide-react';
import type { Bug } from '../types';
import { approveGithubIssue } from '../services/api';

interface HumanApprovalModalProps {
  bug: Bug | null;
  onClose: () => void;
  onApproved: () => void;
}

export const HumanApprovalModal: React.FC<HumanApprovalModalProps> = ({
  bug,
  onClose,
  onApproved
}) => {
  if (!bug) return null;

  const handleApprove = async () => {
    try {
      await approveGithubIssue(bug.id);
      onApproved();
      onClose();
    } catch (err) {
      alert('Error approving GitHub issue');
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="glass-card max-w-lg w-full rounded-2xl p-6 border border-slate-700 shadow-2xl relative">
        <div className="flex items-center space-x-3 text-amber-400 mb-4">
          <ShieldAlert className="w-6 h-6" />
          <h3 className="text-lg font-bold text-slate-100">Human Approval Required</h3>
        </div>

        <p className="text-sm text-slate-300 mb-4">
          LISA Autonomous Agent detected a confirmed defect and prepared a GitHub Issue draft.
          External write actions require explicit human approval.
        </p>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 mb-6 space-y-3">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">Bug ID:</span>
            <span className="text-cyan-400 font-semibold">{bug.bug_id}</span>
          </div>
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">Severity / Priority:</span>
            <span className="text-rose-400 font-bold">{bug.severity} ({bug.priority})</span>
          </div>
          <div className="text-xs">
            <span className="text-slate-400 block mb-1">Issue Title:</span>
            <span className="text-slate-200 font-medium">{bug.title}</span>
          </div>
          <div className="text-xs">
            <span className="text-slate-400 block mb-1">Root Cause Hypothesis:</span>
            <span className="text-slate-400 bg-slate-950 p-2 rounded block">{bug.root_cause}</span>
          </div>
        </div>

        <div className="flex items-center justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm transition-colors flex items-center space-x-2"
          >
            <XCircle className="w-4 h-4" />
            <span>Reject</span>
          </button>

          <button
            onClick={handleApprove}
            className="px-4 py-2 bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold rounded-lg text-sm transition-colors flex items-center space-x-2 shadow-lg shadow-cyan-500/20"
          >
            <CheckCircle className="w-4 h-4" />
            <span>Approve & Create Issue</span>
          </button>
        </div>
      </div>
    </div>
  );
};
