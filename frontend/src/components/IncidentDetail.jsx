import React, { useState } from 'react';
import {
  ArrowLeft,
  Clock,
  Sparkles,
  FileText,
  Wrench,
  AlertCircle
} from 'lucide-react';
import SeverityBadge from './SeverityBadge';
import StatusBadge from './StatusBadge';
import AIInvestigationPanel from './AIInvestigationPanel';
import EvidenceTimeline from './EvidenceTimeline';
import RemediationPanel from './RemediationPanel';

export default function IncidentDetail({
  incident,
  evidence,
  rcaData,
  remediation,
  isLoading,
  isInvestigating,
  investigationError,
  isSubmittingRemediation,
  onBack,
  onRunInvestigation,
  onProposeRemediation,
  onApproveRemediation,
  onRejectRemediation,
}) {
  const [activeTab, setActiveTab] = useState('rca'); // 'rca' | 'evidence' | 'remediation'

  if (isLoading) {
    return (
      <div className="bg-surface border border-surface-border rounded-md p-10 text-center text-text-muted">
        <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin mx-auto mb-2" />
        <p className="text-xs font-mono">Loading incident telemetry & correlation...</p>
      </div>
    );
  }

  if (!incident) {
    return (
      <div className="bg-surface border border-surface-border rounded-md p-10 text-center">
        <AlertCircle className="w-6 h-6 text-text-muted mx-auto mb-2" />
        <h4 className="text-xs font-semibold text-text-sub">No Incident Selected</h4>
        <p className="text-[11px] text-text-muted mt-0.5">
          Select an incident from the master list or trigger a simulated scenario.
        </p>
        {onBack && (
          <button
            onClick={onBack}
            className="mt-3 px-2.5 py-1 rounded-md text-xs font-medium bg-surface-elevated text-text-main hover:bg-surface-hover border border-surface-border"
          >
            Back to List
          </button>
        )}
      </div>
    );
  }

  const dateStr = incident.created_at
    ? new Date(incident.created_at).toLocaleString()
    : 'Unknown';

  return (
    <div className="space-y-4" data-testid="incident-detail">
      {/* Top Incident Summary Panel */}
      <div className="bg-surface border border-surface-border rounded-md p-4 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-3 pb-3 border-b border-surface-border">
          <div className="space-y-1.5 flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-1.5">
              {onBack && (
                <button
                  onClick={onBack}
                  className="flex items-center gap-1 text-xs font-medium text-text-muted hover:text-text-main mr-1 bg-surface-elevated px-2 py-0.5 rounded-md border border-surface-border transition-colors"
                >
                  <ArrowLeft className="w-3 h-3" />
                  <span>List</span>
                </button>
              )}
              <span className="font-mono text-xs font-bold text-text-muted bg-surface-elevated px-2 py-0.5 rounded border border-surface-border">
                {incident.id}
              </span>
              <SeverityBadge severity={incident.severity} />
              <StatusBadge status={incident.status} />
              <span className="text-[11px] font-mono text-text-sub bg-surface-elevated px-2 py-0.5 rounded border border-surface-border">
                {incident.service}
              </span>
            </div>

            <h2 className="text-base font-semibold text-text-main tracking-tight">
              {incident.title}
            </h2>

            {incident.description && (
              <p className="text-xs text-text-sub max-w-3xl leading-relaxed">
                {incident.description}
              </p>
            )}
          </div>

          <div className="flex flex-col sm:items-end gap-1 text-[11px] text-text-muted font-mono shrink-0">
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3 text-text-muted" />
              <span>Created: {dateStr}</span>
            </div>
            <div className="flex items-center gap-1 text-[10px] text-text-muted">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              <span>Sandbox Telemetry Stream</span>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-1.5 mt-3 text-xs font-medium">
          <button
            onClick={() => setActiveTab('rca')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border transition-colors ${
              activeTab === 'rca'
                ? 'bg-accent-subtle text-accent border-accent-border font-semibold'
                : 'text-text-muted hover:text-text-main border-transparent hover:bg-surface-elevated'
            }`}
            data-testid="tab-rca-btn"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Root-Cause Diagnosis</span>
            {rcaData?.status === 'completed' && (
              <span className="w-1.5 h-1.5 rounded-full bg-accent" />
            )}
          </button>

          <button
            onClick={() => setActiveTab('evidence')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border transition-colors ${
              activeTab === 'evidence'
                ? 'bg-accent-subtle text-accent border-accent-border font-semibold'
                : 'text-text-muted hover:text-text-main border-transparent hover:bg-surface-elevated'
            }`}
            data-testid="tab-evidence-btn"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Telemetry & Evidence ({evidence?.length || 0})</span>
          </button>

          <button
            onClick={() => setActiveTab('remediation')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border transition-colors ${
              activeTab === 'remediation'
                ? 'bg-accent-subtle text-accent border-accent-border font-semibold'
                : 'text-text-muted hover:text-text-main border-transparent hover:bg-surface-elevated'
            }`}
            data-testid="tab-remediation-btn"
          >
            <Wrench className="w-3.5 h-3.5" />
            <span>Remediation Workflow</span>
            {remediation?.status === 'pending_approval' && (
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
            )}
          </button>
        </div>
      </div>

      {/* Active Tab Panel */}
      <div>
        {activeTab === 'rca' && (
          <AIInvestigationPanel
            rcaData={rcaData}
            isInvestigating={isInvestigating}
            investigationError={investigationError}
            onRunInvestigation={onRunInvestigation}
          />
        )}

        {activeTab === 'evidence' && (
          <EvidenceTimeline
            evidence={evidence}
            isLoading={isInvestigating}
            onRunInvestigation={onRunInvestigation}
          />
        )}

        {activeTab === 'remediation' && (
          <RemediationPanel
            incident={incident}
            remediation={remediation}
            onProposeRemediation={onProposeRemediation}
            onApproveRemediation={onApproveRemediation}
            onRejectRemediation={onRejectRemediation}
            isSubmitting={isSubmittingRemediation}
          />
        )}
      </div>
    </div>
  );
}
