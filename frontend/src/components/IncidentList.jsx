import React, { useState } from 'react';
import {
  Search,
  Clock,
  AlertCircle,
  FlaskConical,
  ChevronRight,
  RefreshCw
} from 'lucide-react';
import SeverityBadge from './SeverityBadge';
import StatusBadge from './StatusBadge';

export default function IncidentList({
  incidents = [],
  selectedIncidentId,
  onSelectIncident,
  isLoading,
  onTriggerDemo
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');

  const filteredIncidents = incidents.filter((inc) => {
    const q = searchQuery.toLowerCase();
    const matchesSearch =
      !q ||
      (inc.title || '').toLowerCase().includes(q) ||
      (inc.service || '').toLowerCase().includes(q) ||
      (inc.id || '').toLowerCase().includes(q);

    const matchesSeverity =
      severityFilter === 'all' ||
      (inc.severity || '').toLowerCase() === severityFilter.toLowerCase();

    const matchesStatus =
      statusFilter === 'all' ||
      (inc.status || '').toLowerCase() === statusFilter.toLowerCase();

    return matchesSearch && matchesSeverity && matchesStatus;
  });

  return (
    <div className="bg-surface border border-surface-border rounded-md shadow-sm overflow-hidden" data-testid="incident-list">
      {/* Search and Filters Header */}
      <div className="p-3 border-b border-surface-border space-y-2 bg-surface">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 text-text-muted absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter by title, service, ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 rounded-md bg-surface-elevated border border-surface-border text-text-main text-xs placeholder-text-muted focus:outline-none focus:border-accent"
              data-testid="search-incidents-input"
            />
          </div>

          <div className="flex items-center gap-1.5">
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="px-2 py-1.5 rounded-md bg-surface-elevated border border-surface-border text-text-main text-xs focus:outline-none focus:border-accent"
              data-testid="filter-severity-select"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-2 py-1.5 rounded-md bg-surface-elevated border border-surface-border text-text-main text-xs focus:outline-none focus:border-accent"
              data-testid="filter-status-select"
            >
              <option value="all">All Statuses</option>
              <option value="triggered">Triggered</option>
              <option value="investigating">Investigating</option>
              <option value="hypothesis formed">Hypothesis Formed</option>
              <option value="awaiting approval">Awaiting Approval</option>
              <option value="remediating">Remediating</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
        </div>
      </div>

      {/* Incident List Rows */}
      <div>
        {isLoading ? (
          <div className="py-12 text-center text-text-muted">
            <RefreshCw className="w-4 h-4 text-accent animate-spin mx-auto mb-2" />
            <p className="text-xs font-mono">Loading incident telemetry...</p>
          </div>
        ) : filteredIncidents.length === 0 ? (
          <div className="py-10 text-center px-4">
            <AlertCircle className="w-5 h-5 text-text-muted mx-auto mb-1.5" />
            <h4 className="text-xs font-semibold text-text-sub">No incidents found</h4>
            <p className="text-[11px] text-text-muted mt-0.5 max-w-xs mx-auto">
              {incidents.length === 0
                ? 'No active incidents currently logged. Trigger a scenario to start diagnosis.'
                : 'No incidents match the active search query or filters.'}
            </p>
            {incidents.length === 0 && onTriggerDemo && (
              <button
                onClick={onTriggerDemo}
                className="mt-3 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-surface-elevated hover:bg-surface-hover text-text-main border border-surface-border transition-colors"
              >
                <FlaskConical className="w-3.5 h-3.5 text-amber-500" />
                <span>Simulate Demo Incident</span>
              </button>
            )}
          </div>
        ) : (
          <div className="divide-y divide-surface-border">
            {filteredIncidents.map((incident) => {
              const isSelected = selectedIncidentId === incident.id;
              const dateStr = incident.created_at
                ? new Date(incident.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                : 'Recent';

              return (
                <div
                  key={incident.id}
                  onClick={() => onSelectIncident(incident.id)}
                  className={`p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-surface-hover border-l-2 border-l-accent'
                      : 'hover:bg-surface-hover/70'
                  }`}
                  data-testid={`incident-row-${incident.id}`}
                >
                  <div className="space-y-1 flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="font-mono text-[10px] font-semibold text-text-muted bg-surface-elevated px-1.5 py-0.2 rounded border border-surface-border">
                        {incident.id}
                      </span>
                      <SeverityBadge severity={incident.severity} size="xs" />
                      <StatusBadge status={incident.status} />
                      <span className="text-[10px] font-mono text-text-sub bg-surface-elevated px-1.5 py-0.2 rounded border border-surface-border">
                        {incident.service}
                      </span>
                    </div>

                    <h4 className="text-xs font-medium text-text-main truncate">
                      {incident.title}
                    </h4>

                    {incident.description && (
                      <p className="text-[11px] text-text-muted line-clamp-1">
                        {incident.description}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center justify-between sm:justify-end gap-2 shrink-0">
                    <div className="flex items-center gap-1 text-[10px] font-mono text-text-muted">
                      <Clock className="w-3 h-3 text-text-muted" />
                      <span>{dateStr}</span>
                    </div>
                    <ChevronRight className={`w-3.5 h-3.5 text-text-muted transition-transform ${isSelected ? 'rotate-90 text-accent' : ''}`} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
