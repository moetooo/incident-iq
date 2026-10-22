import React, { useState, useEffect } from 'react';
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
  const [selectedEvidenceId, setSelectedEvidenceId] = useState(null);

  // Synchronize activeTab and selectedEvidenceId with browser URL hash & history
  useEffect(() => {
    const syncFromHash = () => {
      if (typeof window === 'undefined') return;
      const hash = window.location.hash.replace(/^#/, '');
      if (hash) {
        if (hash.startsWith('ev_') || (Array.isArray(evidence) && evidence.some(e => e.id === hash))) {
          setActiveTab('evidence');
          setSelectedEvidenceId(hash);
        } else if (hash === 'rca' || hash === 'evidence' || hash === 'remediation') {
          setActiveTab(hash);
          setSelectedEvidenceId(null);
        }
      } else {
        setSelectedEvidenceId(null);
      }
    };

    syncFromHash();
    window.addEventListener('hashchange', syncFromHash);
    window.addEventListener('popstate', syncFromHash);
    return () => {
      window.removeEventListener('hashchange', syncFromHash);
      window.removeEventListener('popstate', syncFromHash);
    };
  }, [evidence]);

  const handleSelectEvidence = (evId) => {
    setActiveTab('evidence');
    setSelectedEvidenceId(evId);
  };

  const handleTabChange = (tabKey) => {
    setActiveTab(tabKey);
    if (tabKey !== 'evidence') {
      setSelectedEvidenceId(null);
      if (typeof window !== 'undefined' && window.location.hash && window.location.hash.startsWith('#ev_')) {
        window.history.pushState(null, '', window.location.pathname + window.location.search);
      }
    }
  };

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
      <div className="bg-surface border border-surface-border rounded-md p-3.5 sm:p-4 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-3 pb-3 border-b border-surface-border">
          <div className="space-y-1.5 flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-1.5">
              {onBack && (
                <button
                  onClick={onBack}
                  className="flex items-center gap-1 text-xs font-medium text-text-muted hover:text-text-main mr-1 bg-surface-elevated px-2 py-0.5 rounded-md border border-surface-border transition-colors lg:hidden"
                  title="Return to incident list"
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

            <h2 className="text-base sm:text-lg font-semibold text-text-main tracking-tight break-words">
              {incident.title}
            </h2>

            {incident.description && (
              <p className="text-xs text-text-sub max-w-3xl leading-relaxed break-words">
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
        <div className="flex items-center gap-1 sm:gap-1.5 mt-3 text-xs font-medium overflow-x-auto no-scrollbar pb-1 sm:pb-0">
          <button
            onClick={() => handleTabChange('rca')}
            className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-md border transition-colors shrink-0 ${
              activeTab === 'rca'
                ? 'bg-accent-subtle text-accent border-accent-border font-semibold'
                : 'text-text-muted hover:text-text-main border-transparent hover:bg-surface-elevated'
            }`}
            data-testid="tab-rca-btn"
          >
            <Sparkles className="w-3.5 h-3.5 shrink-0" />
            <span className="hidden sm:inline">AI Root-Cause Diagnosis</span>
            <span className="sm:hidden">RCA</span>
            {rcaData?.status === 'completed' && (
              <span className="w-1.5 h-1.5 rounded-full bg-accent" />
            )}
          </button>

          <button
            onClick={() => handleTabChange('evidence')}
            className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-md border transition-colors shrink-0 ${
              activeTab === 'evidence'
                ? 'bg-accent-subtle text-accent border-accent-border font-semibold'
                : 'text-text-muted hover:text-text-main border-transparent hover:bg-surface-elevated'
            }`}
            data-testid="tab-evidence-btn"
          >
            <FileText className="w-3.5 h-3.5 shrink-0" />
            <span className="hidden sm:inline">Telemetry & Evidence ({evidence?.length || 0})</span>
            <span className="sm:hidden">Evidence ({evidence?.length || 0})</span>
          </button>

          <button
            onClick={() => handleTabChange('remediation')}
            className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-md border transition-colors shrink-0 ${
              activeTab === 'remediation'
                ? 'bg-accent-subtle text-accent border-accent-border font-semibold'
                : 'text-text-muted hover:text-text-main border-transparent hover:bg-surface-elevated'
            }`}
            data-testid="tab-remediation-btn"
          >
            <Wrench className="w-3.5 h-3.5 shrink-0" />
            <span className="hidden sm:inline">Remediation Workflow</span>
            <span className="sm:hidden">Remediation</span>
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
            evidence={evidence}
            isInvestigating={isInvestigating}
            investigationError={investigationError}
            onRunInvestigation={onRunInvestigation}
            onSelectEvidence={handleSelectEvidence}
          />
        )}

        {activeTab === 'evidence' && (
          <EvidenceTimeline
            evidence={evidence}
            isLoading={isInvestigating}
            onRunInvestigation={onRunInvestigation}
            selectedEvidenceId={selectedEvidenceId}
            onNavigateTab={handleTabChange}
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
