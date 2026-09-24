import React, { useEffect, useState, useRef } from 'react';
import { Terminal, CheckCircle2, XCircle, AlertTriangle, Loader2 } from 'lucide-react';

interface LogMessage {
  timestamp: string;
  run_id: string;
  message: string;
  status: 'info' | 'success' | 'warning' | 'error' | 'running';
}

interface LiveLogViewerProps {
  runId?: string;
  initialLogs?: LogMessage[];
}

export const LiveLogViewer: React.FC<LiveLogViewerProps> = ({ runId, initialLogs = [] }) => {
  const [logs, setLogs] = useState<LogMessage[]>(initialLogs);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!runId) return;

    // If we already have a WS for this exact run, don't recreate
    // We keep the connection open as long as the component mounts
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/api/v1/ws/runs/${runId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('LISA Live Console connected to', wsUrl);
    };

    ws.onmessage = (event) => {
      try {
        const payload: LogMessage = JSON.parse(event.data);
        setLogs((prev) => [...prev, payload]);
      } catch (err) {
        console.error('Error parsing WS message:', err);
      }
    };

    ws.onerror = (e) => console.error('WS error', e);
    ws.onclose = () => console.log('LISA Live Console disconnected');

    return () => {
      ws.close();
    };
    // Intentionally include runId so we reconnect when it changes,
    // but we don't reset logs — we append to existing state.
  }, [runId]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-2xl font-mono text-sm">
      {/* Terminal Header */}
      <div className="bg-slate-900 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Terminal className="w-4 h-4 text-cyan-400" />
          <span className="text-slate-300 font-semibold text-xs tracking-wider uppercase">
            LISA Live Execution Console {runId ? `[${runId}]` : ''}
          </span>
        </div>
        <div className="flex items-center space-x-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80"></span>
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80"></span>
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80"></span>
        </div>
      </div>

      {/* Terminal Body */}
      <div className="p-4 h-80 overflow-y-auto space-y-2 bg-slate-950/90 text-slate-300">
        {logs.length === 0 ? (
          <div className="text-slate-600 text-xs italic py-8 text-center">
            Awaiting live execution events...
          </div>
        ) : (
          logs.map((log, index) => {
            let statusIcon = <span className="text-cyan-400">›</span>;
            let textColor = 'text-slate-300';

            if (log.status === 'success') {
              statusIcon = <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 inline" />;
              textColor = 'text-emerald-300';
            } else if (log.status === 'error') {
              statusIcon = <XCircle className="w-4 h-4 text-rose-400 shrink-0 inline" />;
              textColor = 'text-rose-300 font-semibold';
            } else if (log.status === 'warning') {
              statusIcon = <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 inline" />;
              textColor = 'text-amber-300';
            } else if (log.status === 'running') {
              statusIcon = <Loader2 className="w-4 h-4 text-cyan-400 animate-spin shrink-0 inline" />;
              textColor = 'text-cyan-300';
            }

            return (
              <div key={index} className="flex items-start space-x-2 text-xs leading-relaxed">
                <span className="text-slate-600 select-none">[{log.timestamp}]</span>
                <span className="mt-0.5">{statusIcon}</span>
                <span className={textColor}>{log.message}</span>
              </div>
            );
          })
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );
};
