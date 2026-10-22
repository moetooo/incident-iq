import React, { useState } from 'react';
import {
  FileText,
  Activity,
  GitCommit,
  Server,
  Clock,
  ChevronDown,
  ChevronRight,
  Search,
  Info
} from 'lucide-react';

export default function EvidenceTimeline({ evidence = [], isLoading = false, onRunInvestigation }) {
  const [selectedType, setSelectedType] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedItems, setExpandedItems] = useState({});

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
    <div className="bg-surface border border-surface-border rounded-md p-4 shadow-sm" data-testid="evidence-timeline">
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
          <div className="relative">
            <Search className="w-3 h-3 text-text-muted absolute left-2 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search evidence..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-7 pr-2.5 py-1 text-xs rounded-md bg-surface-elevated border border-surface-border text-text-main placeholder-text-muted focus:outline-none focus:border-accent"
            />
          </div>

          <div className="flex items-center gap-0.5 bg-surface-elevated p-0.5 rounded-md border border-surface-border text-xs">
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

      {/* Content */}
      <div className="mt-3">
        {isLoading ? (
          <div className="py-10 text-center text-text-muted">
            <div className="inline-block w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin mb-1.5" />
            <p className="text-xs font-mono">Fetching telemetry evidence...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-8 text-center">
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
          <div className="relative pl-5 space-y-2.5 before:content-[''] before:absolute before:left-2 before:top-2 before:bottom-2 before:w-px before:bg-surface-border">
            {filtered.map((item) => {
              const isExpanded = !!expandedItems[item.id];
              const dateStr = item.timestamp
                ? new Date(item.timestamp).toLocaleTimeString()
                : 'Just now';

              return (
                <div
                  key={item.id}
                  id={item.id}
                  className="relative bg-surface-elevated hover:bg-surface-hover border border-surface-border rounded-md p-2.5 transition-colors"
                >
                  {/* Timeline node icon */}
                  <div className="absolute -left-5 top-2.5 -translate-x-1/2 p-0.5 rounded-full bg-surface border border-surface-border text-text-muted">
                    {getTypeIcon(item.type)}
                  </div>

                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-xs">
                    <div className="flex items-center gap-1.5">
                      <span className={`px-1.5 py-0.2 rounded border uppercase text-[10px] font-mono font-medium ${getTypeBadgeClass(item.type)}`}>
                        {item.type || 'EVIDENCE'}
                      </span>
                      <span className="font-mono text-text-muted bg-surface px-1 py-0.2 rounded border border-surface-border text-[10px]">
                        {item.id}
                      </span>
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
                  <p className="text-xs font-medium text-text-main mt-1.5 font-mono">
                    {item.summary}
                  </p>

                  {/* Details Toggle */}
                  {item.details && Object.keys(item.details).length > 0 && (
                    <div className="mt-2">
                      <button
                        onClick={() => toggleExpand(item.id)}
                        className="flex items-center gap-1 text-[10px] font-mono text-accent hover:underline transition-colors"
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
                          <pre>{JSON.stringify(item.details, null, 2)}</pre>
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
