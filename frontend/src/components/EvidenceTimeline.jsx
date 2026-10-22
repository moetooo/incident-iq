import React, { useState, useEffect } from 'react';
import {
  FileText,
  Activity,
  GitCommit,
  Server,
  Clock,
  ChevronDown,
  ChevronRight,
  Search,
  Info,
  Sparkles
} from 'lucide-react';

export default function EvidenceTimeline({
  evidence = [],
  isLoading = false,
  onRunInvestigation,
  selectedEvidenceId = null,
  onNavigateTab
}) {
  const [selectedType, setSelectedType] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedItems, setExpandedItems] = useState({});

  // Auto-expand and scroll to selected evidence item
  useEffect(() => {
    if (selectedEvidenceId) {
      setExpandedItems((prev) => ({ ...prev, [selectedEvidenceId]: true }));
      const found = (evidence || []).find((e) => e.id === selectedEvidenceId);
      if (found) {
        if (selectedType !== 'all' && (found.type || '').toLowerCase() !== selectedType.toLowerCase()) {
          setSelectedType('all');
        }
        if (searchQuery) {
          const q = searchQuery.toLowerCase();
          const matches =
            (found.summary || '').toLowerCase().includes(q) ||
            (found.source || '').toLowerCase().includes(q) ||
            (found.id || '').toLowerCase().includes(q);
          if (!matches) {
            setSearchQuery('');
          }
        }
      }
      const timer = setTimeout(() => {
        const el = document.getElementById(selectedEvidenceId);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 60);
      return () => clearTimeout(timer);
    }
  }, [selectedEvidenceId, evidence]);

  const toggleExpand = (id) => {
    setExpandedItems((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const getTypeIcon = (type) => {
    const norm = (type || '').toLowerCase();
    switch (norm) {
      case 'log':
        return <FileText className="w-3.5 h-3.5 text-blue-500" />;
      case 'metric':
        return <Activity className="w-3.5 h-3.5 text-indigo-500" />;
      case 'deployment':
        return <GitCommit className="w-3.5 h-3.5 text-emerald-500" />;
      case 'state':
        return <Server className="w-3.5 h-3.5 text-amber-500" />;
      default:
        return <Info className="w-3.5 h-3.5 text-text-muted" />;
    }
  };

  const getTypeBadgeClass = (type) => {
    const norm = (type || '').toLowerCase();
    switch (norm) {
      case 'log':
        return 'bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-500/25';
      case 'metric':
        return 'bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 border-indigo-200 dark:border-indigo-500/25';
      case 'deployment':
        return 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/25';
      case 'state':
        return 'bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-500/25';
      default:
        return 'bg-surface-elevated text-text-muted border-surface-border';
    }
  };

  // Filter evidence items
  const filtered = (evidence || []).filter((item) => {
    const matchesType = selectedType === 'all' || (item.type || '').toLowerCase() === selectedType;
    const query = searchQuery.toLowerCase();
    const matchesSearch =
      !query ||
      (item.summary || '').toLowerCase().includes(query) ||
      (item.source || '').toLowerCase().includes(query) ||
      (item.id || '').toLowerCase().includes(query) ||
      JSON.stringify(item.details || {}).toLowerCase().includes(query);
    return matchesType && matchesSearch;
  });

  return (
    <div className="bg-surface border border-surface-border rounded-md p-3.5 sm:p-4 shadow-sm" data-testid="evidence-timeline">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-surface-border">
        <div>
          <h3 className="text-sm font-semibold text-text-main flex items-center gap-2">
            <span>Telemetry & Evidence Timeline</span>
            <span className="text-[10px] font-mono font-normal px-1.5 py-0.2 rounded bg-surface-elevated text-text-muted border border-surface-border">
              {evidence.length} items
            </span>
          </h3>
          <p className="text-[11px] text-text-muted">
            Chronological log traces, metrics, deployments, and node states.
          </p>
        </div>

        {/* Filter controls */}
        <div className="flex flex-wrap items-center gap-1.5">
          <div className="relative flex-1 sm:flex-initial">
            <Search className="w-3 h-3 text-text-muted absolute left-2 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search evidence..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full sm:w-auto pl-7 pr-2.5 py-1 text-xs rounded-md bg-surface-elevated border border-surface-border text-text-main placeholder-text-muted focus:outline-none focus:border-accent"
            />
          </div>

          <div className="flex items-center gap-0.5 bg-surface-elevated p-0.5 rounded-md border border-surface-border text-xs overflow-x-auto no-scrollbar">
            {['all', 'log', 'metric', 'deployment', 'state'].map((t) => (
              <button
                key={t}
                onClick={() => setSelectedType(t)}
                className={`px-1.5 py-0.5 rounded text-[11px] capitalize transition-colors ${
                  selectedType === t
                    ? 'bg-accent text-white font-medium'
                    : 'text-text-muted hover:text-text-main'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Target Evidence Selection Banner */}
      {selectedEvidenceId && (() => {
        const matchedItem = Array.isArray(evidence) ? evidence.find((e) => e.id === selectedEvidenceId) : null;
        if (matchedItem) {
          return (
            <div className="mt-3 p-2.5 rounded-md bg-accent-subtle/50 border border-accent-border flex items-center justify-between gap-2 text-xs" data-testid="target-evidence-banner">
              <div className="flex items-center gap-2 min-w-0">
                <Sparkles className="w-4 h-4 text-accent shrink-0" />
                <span className="text-text-main truncate">
                  Viewing supporting evidence <strong className="font-mono text-accent font-semibold">{selectedEvidenceId}</strong> ({matchedItem.type || 'record'}) referenced in RCA.
                </span>
              </div>
              {onNavigateTab && (
                <button
                  onClick={() => onNavigateTab('rca')}
                  className="px-2 py-0.5 rounded text-[11px] font-medium bg-surface text-text-main border border-surface-border hover:bg-surface-elevated shrink-0 transition-colors"
                  data-testid="back-to-rca-btn"
                >
                  Back to RCA
                </button>
              )}
            </div>
          );
        }
        return (
          <div className="mt-3 p-2.5 rounded-md bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/25 flex items-center justify-between gap-2 text-xs text-amber-800 dark:text-amber-400" data-testid="missing-evidence-banner">
            <div className="flex items-center gap-2 min-w-0">
              <Info className="w-4 h-4 text-amber-500 shrink-0" />
              <span>
                Referenced evidence <strong className="font-mono font-semibold">{selectedEvidenceId}</strong> was not found among the {evidence?.length || 0} telemetry records for this incident.
              </span>
            </div>
            {onNavigateTab && (
              <button
                onClick={() => onNavigateTab('rca')}
                className="px-2 py-0.5 rounded text-[11px] font-medium bg-surface text-text-main border border-surface-border hover:bg-surface-elevated shrink-0 transition-colors"
                data-testid="back-to-rca-btn"
              >
                Back to RCA
              </button>
            )}
          </div>
        );
      })()}

      {/* Content */}
      <div className="mt-3">
        {isLoading ? (
          <div className="py-10 text-center text-text-muted">
            <div className="inline-block w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin mb-1.5" />
            <p className="text-xs font-mono">Fetching telemetry evidence...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-8 text-center px-4">
            <Info className="w-6 h-6 text-text-muted mx-auto mb-1.5" />
            <p className="text-xs font-medium text-text-sub">No evidence recorded yet</p>
            <p className="text-[11px] text-text-muted mt-0.5 max-w-xs mx-auto">
              Run an investigation to trigger telemetry extraction from the simulator.
            </p>
            {onRunInvestigation && (
              <button
                onClick={onRunInvestigation}
                className="mt-2.5 px-2.5 py-1 rounded-md text-xs font-medium bg-accent hover:bg-accent-hover text-white transition-colors"
              >
                Start Telemetry Collection
              </button>
            )}
          </div>
        ) : (
          <div className="relative pl-5 sm:pl-6 space-y-2.5 before:content-[''] before:absolute before:left-2 before:top-2 before:bottom-2 before:w-px before:bg-surface-border">
            {filtered.map((item) => {
              const isExpanded = !!expandedItems[item.id];
              const isSelected = item.id === selectedEvidenceId;
              const dateStr = item.timestamp
                ? new Date(item.timestamp).toLocaleTimeString()
                : 'Just now';

              return (
                <div
                  key={item.id}
                  id={item.id}
                  className={`relative rounded-md p-2.5 sm:p-3 transition-all duration-200 border ${
                    isSelected
                      ? 'bg-accent-subtle/30 dark:bg-accent-subtle/15 border-accent ring-2 ring-accent/30 evidence-target-highlight'
                      : 'bg-surface-elevated hover:bg-surface-hover border-surface-border'
                  }`}
                  data-testid={`evidence-item-${item.id}`}
                >
                  {/* Timeline node icon */}
                  <div className="absolute -left-5 sm:-left-6 top-3 -translate-x-1/2 p-0.5 rounded-full bg-surface border border-surface-border text-text-muted">
                    {getTypeIcon(item.type)}
                  </div>

                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-xs">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className={`px-1.5 py-0.2 rounded border uppercase text-[10px] font-mono font-medium ${getTypeBadgeClass(item.type)}`}>
                        {item.type || 'EVIDENCE'}
                      </span>
                      <span className="font-mono text-text-muted bg-surface px-1 py-0.2 rounded border border-surface-border text-[10px]">
                        {item.id}
                      </span>
                      {isSelected && (
                        <span className="inline-flex items-center gap-0.5 px-1.5 py-0.2 rounded bg-accent text-white font-mono text-[9px] uppercase font-semibold">
                          <Sparkles className="w-2.5 h-2.5" />
                          RCA Reference
                        </span>
                      )}
                      <span className="text-text-sub font-mono text-[11px]">
                        [{item.source || 'system'}]
                      </span>
                    </div>
                    <div className="flex items-center gap-1 text-text-muted text-[10px] font-mono">
                      <Clock className="w-3 h-3" />
                      <span>{dateStr}</span>
                    </div>
                  </div>

                  {/* Summary */}
                  <p className="text-xs font-medium text-text-main mt-1.5 font-mono break-words">
                    {item.summary}
                  </p>

                  {/* Details Toggle */}
                  {item.details && Object.keys(item.details).length > 0 && (
                    <div className="mt-2">
                      <button
                        onClick={() => toggleExpand(item.id)}
                        className="flex items-center gap-1 text-[10px] font-mono text-accent hover:underline transition-colors focus:outline-none"
                      >
                        {isExpanded ? (
                          <>
                            <ChevronDown className="w-3 h-3" />
                            <span>Hide payload</span>
                          </>
                        ) : (
                          <>
                            <ChevronRight className="w-3 h-3" />
                            <span>View raw payload ({Object.keys(item.details).length} fields)</span>
                          </>
                        )}
                      </button>

                      {isExpanded && (
                        <div className="mt-1.5 p-2 bg-surface rounded border border-surface-border font-mono text-[11px] text-text-sub overflow-x-auto">
                          <pre className="whitespace-pre-wrap break-all sm:whitespace-pre sm:break-normal">
                            {JSON.stringify(item.details, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
