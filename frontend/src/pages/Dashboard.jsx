import React, { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  Clock,
  ShieldAlert,
  CheckCircle2,
  Server,
  FlaskConical,
  AlertCircle,
  Play
} from 'lucide-react';
import { api, ApiError } from '../services/api';
import Header from '../components/Header';
import MetricCard from '../components/MetricCard';
import IncidentList from '../components/IncidentList';
import IncidentDetail from '../components/IncidentDetail';
import DemoScenarioModal from '../components/DemoScenarioModal';
import CreateIncidentModal from '../components/CreateIncidentModal';

export default function Dashboard() {
  const [incidents, setIncidents] = useState([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState(null);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [evidence, setEvidence] = useState([]);
  const [rcaData, setRcaData] = useState(null);
  const [remediation, setRemediation] = useState(null);

  // Loading & Action states
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [isSubmittingRemediation, setIsSubmittingRemediation] = useState(false);
  const [isTriggeringDemo, setIsTriggeringDemo] = useState(false);
  const [isCreatingIncident, setIsCreatingIncident] = useState(false);

  // Status & Error states
  const [backendHealthy, setBackendHealthy] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [investigationError, setInvestigationError] = useState(null);

  // Modals
  const [isDemoModalOpen, setIsDemoModalOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Health check
  const verifyBackend = useCallback(async () => {
    try {
      await api.checkHealth();
      setBackendHealthy(true);
      return true;
    } catch {
      setBackendHealthy(false);
      return false;
    }
  }, []);

  // Fetch incidents list
  const loadIncidents = useCallback(async (quiet = false) => {
    if (!quiet) setIsLoadingList(true);
    setErrorMessage(null);

    try {
      await verifyBackend();
      const res = await api.getIncidents();
      const items = res?.items || [];
      setIncidents(items);

      if (items.length > 0 && !selectedIncidentId) {
        setSelectedIncidentId(items[0].id);
      }
    } catch (err) {
      if (err.code !== 'NETWORK_ERROR') {
        setErrorMessage(err.message);
      }
    } finally {
      if (!quiet) setIsLoadingList(false);
    }
  }, [selectedIncidentId, verifyBackend]);

  // Load single incident details and telemetry
  const loadIncidentDetail = useCallback(async (id) => {
    if (!id) return;
    setIsLoadingDetail(true);
    setInvestigationError(null);

    try {
      const inc = await api.getIncident(id);
      setSelectedIncident(inc);

      try {
        const evRes = await api.getEvidence(id);
        setEvidence(evRes?.items || []);
      } catch {
        setEvidence([]);
      }

      setRcaData(null);
      setRemediation(null);
    } catch (err) {
      setErrorMessage(`Failed to load incident ${id}: ${err.message}`);
    } finally {
      setIsLoadingDetail(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadIncidents();
  }, [loadIncidents]);

  // Load detail when selected ID changes
  useEffect(() => {
    if (selectedIncidentId) {
      loadIncidentDetail(selectedIncidentId);
    } else {
      setSelectedIncident(null);
      setEvidence([]);
      setRcaData(null);
      setRemediation(null);
    }
  }, [selectedIncidentId, loadIncidentDetail]);

  // Refresh handler
  const handleRefresh = async () => {
    setIsRefreshing(true);
    await loadIncidents(true);
    if (selectedIncidentId) {
      await loadIncidentDetail(selectedIncidentId);
    }
    setIsRefreshing(false);
  };

  // Run AI investigation
  const handleRunInvestigation = async () => {
    if (!selectedIncidentId || isInvestigating) return;
    setIsInvestigating(true);
    setInvestigationError(null);

    try {
      const result = await api.investigateIncident(selectedIncidentId);
      setRcaData(result);

      const evRes = await api.getEvidence(selectedIncidentId);
      setEvidence(evRes?.items || []);

      const updatedInc = await api.getIncident(selectedIncidentId);
      setSelectedIncident(updatedInc);
      loadIncidents(true);
    } catch (err) {
      setInvestigationError(err.message || 'Investigation engine failed to correlate telemetry');
    } finally {
      setIsInvestigating(false);
    }
  };

  // Propose remediation
  const handleProposeRemediation = async ({ action, parameters }) => {
    if (!selectedIncidentId || isSubmittingRemediation) return;
    setIsSubmittingRemediation(true);

    try {
      const res = await api.createRemediation(selectedIncidentId, { action, parameters });
      setRemediation(res);
      loadIncidents(true);
    } catch (err) {
      setErrorMessage(`Failed to propose remediation: ${err.message}`);
    } finally {
      setIsSubmittingRemediation(false);
    }
  };

  // Approve remediation
  const handleApproveRemediation = async (remediationId) => {
    if (isSubmittingRemediation) return;
    setIsSubmittingRemediation(true);

    try {
      const res = await api.approveRemediation(remediationId);
      setRemediation((prev) => ({
        ...prev,
        status: res?.status || 'approved',
        result: res,
      }));
      loadIncidents(true);
      if (selectedIncidentId) loadIncidentDetail(selectedIncidentId);
    } catch (err) {
      setErrorMessage(`Authorization failed: ${err.message}`);
    } finally {
      setIsSubmittingRemediation(false);
    }
  };

  // Reject remediation
  const handleRejectRemediation = async (remediationId) => {
    if (isSubmittingRemediation) return;
    setIsSubmittingRemediation(true);

    try {
      const res = await api.rejectRemediation(remediationId);
      setRemediation((prev) => ({
        ...prev,
        status: res?.status || 'rejected',
        result: res,
      }));
      loadIncidents(true);
    } catch (err) {
      setErrorMessage(`Failed to reject remediation: ${err.message}`);
    } finally {
      setIsSubmittingRemediation(false);
    }
  };

  // Trigger demo scenario
  const handleTriggerDemoScenario = async (scenarioKey) => {
    setIsTriggeringDemo(true);
    setErrorMessage(null);

    try {
      const { incident, scenarioId } = await api.triggerDemoIncident(scenarioKey);
      setIsDemoModalOpen(false);

      await loadIncidents(true);
      if (incident?.id) {
        setSelectedIncidentId(incident.id);
        setTimeout(async () => {
          try {
            setIsInvestigating(true);
            const res = await api.investigateIncident(incident.id, { scenario_id: scenarioId });
            setRcaData(res);
            const evRes = await api.getEvidence(incident.id);
            setEvidence(evRes?.items || []);
          } catch {
            // non-fatal auto investigation
          } finally {
            setIsInvestigating(false);
          }
        }, 300);
      }
    } catch (err) {
      setErrorMessage(`Simulation trigger failed: ${err.message}`);
    } finally {
      setIsTriggeringDemo(false);
    }
  };

  // Create manual incident
  const handleCreateIncident = async (payload) => {
    setIsCreatingIncident(true);
    setErrorMessage(null);

    try {
      const created = await api.createIncident(payload);
      setIsCreateModalOpen(false);
      await loadIncidents(true);
      if (created?.id) {
        setSelectedIncidentId(created.id);
      }
    } catch (err) {
      setErrorMessage(`Failed to create incident: ${err.message}`);
    } finally {
      setIsCreatingIncident(false);
    }
  };

  // Computed metrics
  const totalCount = incidents.length;
  const criticalHighCount = incidents.filter((i) => {
    const s = (i.severity || '').toLowerCase();
    return s === 'critical' || s === 'high';
  }).length;
  const investigatingCount = incidents.filter((i) => {
    const st = (i.status || '').toLowerCase();
    return st === 'investigating' || st === 'hypothesis formed';
  }).length;
  const resolvedCount = incidents.filter((i) => (i.status || '').toLowerCase() === 'resolved').length;

  return (
    <div className="min-h-screen flex flex-col bg-app text-text-main transition-colors">
      {/* Navigation Header */}
      <Header
        onTriggerDemo={() => setIsDemoModalOpen(true)}
        onCreateIncident={() => setIsCreateModalOpen(true)}
        onRefresh={handleRefresh}
        backendHealthy={backendHealthy}
        isRefreshing={isRefreshing}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-5 space-y-4">
        {/* Compact Backend Offline Banner */}
        {!backendHealthy && !isLoadingList && (
          <div className="p-3 rounded-md bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/25 text-amber-800 dark:text-amber-400 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 text-xs">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-amber-500 shrink-0" />
              <span>
                <strong>Backend Unreachable:</strong> API server offline at <code className="font-mono text-[11px] bg-surface px-1 py-0.2 rounded border border-surface-border">http://localhost:8000</code>.
              </span>
            </div>
            <button
              onClick={handleRefresh}
              className="px-2.5 py-0.5 rounded text-[11px] font-medium bg-surface text-text-main border border-surface-border hover:bg-surface-elevated transition-colors shrink-0"
            >
              Retry
            </button>
          </div>
        )}

        {/* Global Error Banner (Only shown if non-offline error occurred) */}
        {errorMessage && (
          <div className="p-2.5 rounded-md bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/25 text-rose-800 dark:text-rose-400 flex items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 dark:text-rose-400" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-[11px] text-text-muted hover:text-text-main font-mono px-1.5 py-0.2 rounded bg-surface border border-surface-border"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Metrics Row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <MetricCard
            title="Total Incidents"
            value={totalCount}
            subtitle="Cataloged in session"
            icon={Activity}
            color="neutral"
          />
          <MetricCard
            title="Active / Investigating"
            value={investigatingCount}
            subtitle="Telemetry correlation"
            icon={Clock}
            color="blue"
          />
          <MetricCard
            title="Critical & High"
            value={criticalHighCount}
            subtitle="High blast radius"
            icon={ShieldAlert}
            color="critical"
          />
          <MetricCard
            title="Resolved Incidents"
            value={resolvedCount}
            subtitle="Verified recovery"
            icon={CheckCircle2}
            color="emerald"
          />
        </div>

        {/* Compact Simulator Bar (No loud gradient) */}
        <div className="bg-surface border border-surface-border rounded-md p-3 flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-xs">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-md bg-surface-elevated text-text-muted border border-surface-border">
              <FlaskConical className="w-4 h-4 text-amber-500" />
            </div>
            <div>
              <h3 className="text-xs font-semibold text-text-main">
                Failure Injection Engine
              </h3>
              <p className="text-[11px] text-text-muted">
                Inject deterministic simulated anomalies to evaluate correlation and mitigation latency.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <button
              onClick={() => handleTriggerDemoScenario('database_failure')}
              disabled={isTriggeringDemo}
              className="px-2.5 py-1 rounded-md text-xs font-medium bg-surface-elevated hover:bg-surface-hover border border-surface-border text-text-main transition-colors flex items-center gap-1.5"
            >
              <Play className="w-3 h-3 text-rose-500" />
              <span>DB Pool Failure</span>
            </button>
            <button
              onClick={() => handleTriggerDemoScenario('payment_timeout')}
              disabled={isTriggeringDemo}
              className="px-2.5 py-1 rounded-md text-xs font-medium bg-surface-elevated hover:bg-surface-hover border border-surface-border text-text-main transition-colors flex items-center gap-1.5"
            >
              <Play className="w-3 h-3 text-amber-500" />
              <span>PSP Latency Surge</span>
            </button>
            <button
              onClick={() => handleTriggerDemoScenario('bad_deployment')}
              disabled={isTriggeringDemo}
              className="px-2.5 py-1 rounded-md text-xs font-medium bg-surface-elevated hover:bg-surface-hover border border-surface-border text-text-main transition-colors flex items-center gap-1.5"
            >
              <Play className="w-3 h-3 text-indigo-500" />
              <span>Bad Deployment v2.4</span>
            </button>
          </div>
        </div>

        {/* Master-Detail Observability Workspace */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
          {/* Master List Column */}
          <div className="lg:col-span-5 space-y-3">
            <IncidentList
              incidents={incidents}
              selectedIncidentId={selectedIncidentId}
              onSelectIncident={(id) => {
                setSelectedIncidentId(id);
                if (typeof window !== 'undefined' && window.innerWidth < 1024) {
                  const el = document.getElementById('incident-detail-section');
                  if (el) {
                    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                  }
                }
              }}
              isLoading={isLoadingList}
              onTriggerDemo={() => setIsDemoModalOpen(true)}
            />
          </div>

          {/* Incident Detail Column */}
          <div id="incident-detail-section" className="lg:col-span-7">
            <IncidentDetail
              incident={selectedIncident}
              evidence={evidence}
              rcaData={rcaData}
              remediation={remediation}
              isLoading={isLoadingDetail}
              isInvestigating={isInvestigating}
              investigationError={investigationError}
              isSubmittingRemediation={isSubmittingRemediation}
              onBack={() => {
                setSelectedIncidentId(null);
                if (typeof window !== 'undefined') {
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                }
              }}
              onRunInvestigation={handleRunInvestigation}
              onProposeRemediation={handleProposeRemediation}
              onApproveRemediation={handleApproveRemediation}
              onRejectRemediation={handleRejectRemediation}
            />
          </div>
        </div>
      </main>

      {/* Understated Footer */}
      <footer className="border-t border-surface-border py-3 bg-surface text-[11px] text-text-muted font-mono transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-1.5">
          <span>IncidentIQ &bull; Enterprise Observability & Root-Cause Remediation</span>
          <span>Simulated Sandbox Environment</span>
        </div>
      </footer>

      {/* Dialogs */}
      <DemoScenarioModal
        isOpen={isDemoModalOpen}
        onClose={() => setIsDemoModalOpen(false)}
        onTrigger={handleTriggerDemoScenario}
        isTriggering={isTriggeringDemo}
      />

      <CreateIncidentModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={handleCreateIncident}
        isCreating={isCreatingIncident}
      />
    </div>
  );
}
