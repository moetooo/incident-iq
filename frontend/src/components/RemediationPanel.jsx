import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  Play,
  AlertTriangle,
  Clock,
  Wrench,
  RefreshCw
} from 'lucide-react';

export default function RemediationPanel({
  incident,
  remediation,
  onProposeRemediation,
  onApproveRemediation,
  onRejectRemediation,
  isSubmitting = false
}) {
  const [selectedAction, setSelectedAction] = useState('rollback_demo_deployment');
  const [confirmedSafe, setConfirmedSafe] = useState(false);

  // Available remediation actions for demo environment
  const availableActions = [
    {
      id: 'rollback_demo_deployment',
      name: 'Rollback Deployment',
      risk: 'LOW',
      description: 'Reverts the active service container to the previous stable SHA artifact.',
      service: incident?.service || 'payment-api',
    },
    {
      id: 'scale_connection_pool',
      name: 'Expand Connection Pool',
      risk: 'MEDIUM',
      description: 'Increases max pool limit from 20 to 100 connections and resets dead handles.',
      service: incident?.service || 'payment-api',
    },
    {
      id: 'restart_service_pod',
      name: 'Graceful Service Restart',
      risk: 'LOW',
      description: 'Signals SIGTERM to workers and spawns fresh instances in sandbox.',
      service: incident?.service || 'payment-api',
    },
  ];

  const handlePropose = (e) => {
    e.preventDefault();
    if (isSubmitting) return;
    onProposeRemediation({
      action: selectedAction,
      parameters: { service: incident?.service },
    });
  };

  const handleApproveClick = () => {
    if (!confirmedSafe || isSubmitting || !remediation?.id) return;
    onApproveRemediation(remediation.id);
  };

  const handleRejectClick = () => {
    if (isSubmitting || !remediation?.id) return;
    onRejectRemediation(remediation.id);
  };

  const statusNorm = (remediation?.status || '').toLowerCase();
  const isPending = statusNorm === 'pending_approval';
  const isApproved = statusNorm === 'approved' || statusNorm === 'executing';
  const isSuccess = statusNorm === 'success';
  const isRejected = statusNorm === 'rejected';

  return (
    <div className="bg-surface border border-surface-border rounded-md p-4 shadow-sm" data-testid="remediation-panel">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-surface-border">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-md bg-accent-subtle border border-accent-border text-accent">
            <Wrench className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-text-main flex items-center gap-2">
              <span>Remediation & Human Approval Workflow</span>
              {remediation && (
                <span className="text-[10px] font-mono font-medium px-1.5 py-0.2 rounded bg-surface-elevated text-text-sub border border-surface-border capitalize">
                  {statusNorm.replace('_', ' ')}
                </span>
              )}
            </h3>
            <p className="text-[11px] text-text-muted">
              Remediation execution requires explicit human authorization before dispatch.
            </p>
          </div>
        </div>
      </div>

      <div className="mt-3.5">
        {/* State A: No remediation proposed yet */}
        {!remediation && (
          <div className="space-y-3">
            <p className="text-xs text-text-sub font-medium">
              Target service: <span className="font-mono text-text-main font-semibold">{incident?.service || 'service'}</span>
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              {availableActions.map((act) => {
                const isSelected = selectedAction === act.id;
                return (
                  <div
                    key={act.id}
                    onClick={() => setSelectedAction(act.id)}
                    className={`cursor-pointer p-3 rounded-md border transition-colors text-left ${
                      isSelected
                        ? 'bg-accent-subtle border-accent text-text-main'
                        : 'bg-surface-elevated border-surface-border text-text-sub hover:border-border-strong'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-xs text-text-main">{act.name}</span>
                      <span className={`text-[9px] font-mono px-1 py-0.2 rounded border uppercase font-medium ${
                        act.risk === 'LOW'
                          ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/25'
                          : 'bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-500/25'
                      }`}>
                        {act.risk}
                      </span>
                    </div>
                    <p className="text-[11px] text-text-muted leading-relaxed">{act.description}</p>
                  </div>
                );
              })}
            </div>

            <div className="flex justify-end pt-1">
              <button
                onClick={handlePropose}
                disabled={isSubmitting}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-accent hover:bg-accent-hover text-white disabled:opacity-50 transition-colors"
                data-testid="propose-remediation-btn"
              >
                {isSubmitting ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Play className="w-3.5 h-3.5" />
                )}
                <span>Propose Selected Remediation</span>
              </button>
            </div>
          </div>
        )}

        {/* State B: Remediation Pending Approval */}
        {remediation && isPending && (
          <div className="p-3.5 rounded-md bg-surface-elevated border border-surface-border space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-amber-500 shrink-0" />
                <div>
                  <h4 className="text-xs font-bold text-text-main">
                    Awaiting Human Authorization
                  </h4>
                  <p className="text-[11px] text-text-muted font-mono">
                    ID: {remediation.id} &bull; Action: {remediation.action}
                  </p>
                </div>
              </div>

              <span className="px-2 py-0.5 rounded bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-500/25 text-[10px] font-mono font-semibold uppercase">
                Pending Operator
              </span>
            </div>

            {/* Action Summary Card */}
            <div className="bg-surface p-2.5 rounded-md border border-surface-border text-xs space-y-1.5 font-mono">
              <div className="flex justify-between">
                <span className="text-text-muted">Target Action:</span>
                <span className="font-semibold text-text-main">{remediation.action}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Target Service:</span>
                <span className="text-text-main">{incident?.service || 'payment-api'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Scope:</span>
                <span className="text-emerald-600 dark:text-emerald-400">Simulated Sandbox</span>
              </div>
            </div>

            {/* Safety Confirmation Checkbox */}
            <div className="flex items-center gap-2 pt-1">
              <input
                type="checkbox"
                id="confirm-remediation"
                checked={confirmedSafe}
                onChange={(e) => setConfirmedSafe(e.target.checked)}
                className="w-3.5 h-3.5 rounded border-surface-border text-accent focus:ring-accent bg-surface cursor-pointer"
                data-testid="remediation-confirm-checkbox"
              />
              <label
                htmlFor="confirm-remediation"
                className="text-xs text-text-sub cursor-pointer select-none"
              >
                I confirm explicit authorization of this remediation action in the sandbox.
              </label>
            </div>

            {/* Decision Controls */}
            <div className="flex flex-col-reverse sm:flex-row sm:items-center sm:justify-end gap-2 pt-2 border-t border-surface-border">
              <button
                onClick={handleRejectClick}
                disabled={isSubmitting}
                className="flex items-center justify-center gap-1.5 px-3 py-1.5 sm:py-1 rounded-md text-xs font-medium bg-surface hover:bg-surface-hover text-rose-600 dark:text-rose-400 border border-surface-border transition-colors disabled:opacity-50"
                data-testid="reject-remediation-btn"
              >
                <XCircle className="w-3.5 h-3.5" />
                <span>Reject</span>
              </button>

              <button
                onClick={handleApproveClick}
                disabled={!confirmedSafe || isSubmitting}
                className="flex items-center justify-center gap-1.5 px-3.5 py-1.5 sm:py-1 rounded-md text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                data-testid="approve-remediation-btn"
              >
                {isSubmitting ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <CheckCircle2 className="w-3.5 h-3.5" />
                )}
                <span>Authorize Execution</span>
              </button>
            </div>
          </div>
        )}

        {/* State C: Executed / Approved / Success / Rejected */}
        {remediation && !isPending && (
          <div className="p-3.5 rounded-md bg-surface-elevated border border-surface-border space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {isSuccess || isApproved ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                ) : isRejected ? (
                  <XCircle className="w-4 h-4 text-rose-500" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-amber-500" />
                )}
                <div>
                  <h4 className="text-xs font-semibold text-text-main capitalize">
                    Action {statusNorm.replace('_', ' ')}
                  </h4>
                  <p className="text-[11px] text-text-muted font-mono">
                    {remediation.action} ({remediation.id})
                  </p>
                </div>
              </div>

              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium border uppercase ${
                isSuccess || isApproved
                  ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/25'
                  : 'bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-200 dark:border-rose-500/25'
              }`}>
                {remediation.status}
              </span>
            </div>

            {/* Execution summary result */}
            <div className="bg-surface rounded-md p-2.5 font-mono text-xs text-text-sub border border-surface-border">
              <p className="text-text-muted text-[10px] mb-1 uppercase">Audit Trail Result:</p>
              <pre className="text-text-main text-[11px] whitespace-pre-wrap break-all overflow-x-auto">
                {remediation.result
                  ? JSON.stringify(remediation.result, null, 2)
                  : `Remediation action registered with status: ${remediation.status}.`}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
