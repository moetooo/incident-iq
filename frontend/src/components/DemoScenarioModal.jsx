import React, { useState } from 'react';
import { X, FlaskConical, Database, Clock, GitCommit, ArrowRight } from 'lucide-react';

export default function DemoScenarioModal({ isOpen, onClose, onTrigger, isTriggering }) {
  const [selectedScenario, setSelectedScenario] = useState('database_failure');

  if (!isOpen) return null;

  const scenarios = [
    {
      id: 'database_failure',
      title: 'Database Connection Pool Exhaustion',
      service: 'payment-api',
      severity: 'critical',
      icon: Database,
      color: 'text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-500/10 border-rose-200 dark:border-rose-500/25',
      description: 'Simulates PostgreSQL max_connections saturation, triggering 504 Gateway Timeouts.',
      evidencePreview: 'Connection pool timeout logs, DB saturation metrics (100% active handles), 504 errors.',
    },
    {
      id: 'payment_timeout',
      title: 'PSP Upstream Gateway Latency Surge',
      service: 'payment-gateway',
      severity: 'high',
      icon: Clock,
      color: 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/25',
      description: 'Injects network latency degradation on PSP outbound requests exceeding client read timeouts.',
      evidencePreview: 'HTTP client timeout traces, response latency p99 spike > 12s, queue backup.',
    },
    {
      id: 'bad_deployment',
      title: 'Faulty Deployment Rollout (v2.4.1)',
      service: 'auth-service',
      severity: 'high',
      icon: GitCommit,
      color: 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-500/10 border-indigo-200 dark:border-indigo-500/25',
      description: 'Rolls out canary deployment with unhandled null exception in token validation middleware.',
      evidencePreview: 'Deployment event v2.4.1 recorded, 500 error rate spike to 38%, NullPointer stacktrace.',
    },
  ];

  const handleTrigger = () => {
    onTrigger(selectedScenario);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
      <div
        className="bg-surface border border-surface-border rounded-lg max-w-lg w-full shadow-lg overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-surface-border bg-surface">
          <div className="flex items-center gap-2">
            <div className="p-1 rounded bg-amber-500/10 text-amber-500 border border-amber-500/25">
              <FlaskConical className="w-4 h-4" />
            </div>
            <div>
              <h3 id="modal-title" className="text-sm font-semibold text-text-main">
                Simulate Incident Scenario
              </h3>
              <p className="text-[11px] text-text-muted">
                Trigger a chaos scenario in the simulated service sandbox.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-main p-1 rounded hover:bg-surface-elevated transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scenarios list */}
        <div className="p-4 space-y-2 max-h-[60vh] overflow-y-auto">
          {scenarios.map((sc) => {
            const isSelected = selectedScenario === sc.id;
            const Icon = sc.icon;
            return (
              <div
                key={sc.id}
                onClick={() => setSelectedScenario(sc.id)}
                className={`p-3 rounded-md border cursor-pointer transition-colors ${
                  isSelected
                    ? 'bg-accent-subtle border-accent ring-1 ring-accent/30'
                    : 'bg-surface-elevated border-surface-border hover:border-border-strong text-text-sub'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className={`p-1.5 rounded border ${sc.color}`}>
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <div>
                      <h4 className="text-xs font-semibold text-text-main">{sc.title}</h4>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-[10px] font-mono text-text-muted">{sc.service}</span>
                        <span className="text-text-muted">&bull;</span>
                        <span className="text-[9px] uppercase font-mono px-1 py-0.2 rounded bg-surface border border-surface-border text-text-sub">
                          {sc.severity}
                        </span>
                      </div>
                    </div>
                  </div>

                  <input
                    type="radio"
                    name="scenario"
                    checked={isSelected}
                    onChange={() => setSelectedScenario(sc.id)}
                    className="mt-1 text-accent focus:ring-accent cursor-pointer"
                  />
                </div>

                <p className="text-[11px] text-text-muted mt-2 leading-relaxed">{sc.description}</p>
                <div className="mt-1.5 pt-1.5 border-t border-surface-border/60 text-[10px] text-text-muted font-mono">
                  <span className="font-semibold text-text-sub">Signature:</span> {sc.evidencePreview}
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-3 bg-surface-elevated border-t border-surface-border">
          <span className="text-[11px] text-text-muted font-mono">
            Target: Simulated Sandbox
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              disabled={isTriggering}
              className="px-2.5 py-1 rounded text-xs font-medium text-text-sub hover:bg-surface transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleTrigger}
              disabled={isTriggering}
              className="flex items-center gap-1.5 px-3 py-1 rounded text-xs font-medium bg-accent hover:bg-accent-hover text-white disabled:opacity-50 transition-colors"
              data-testid="confirm-trigger-scenario-btn"
            >
              <span>{isTriggering ? 'Triggering...' : 'Trigger & Ingest'}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
