import React from 'react';
import {
  Sparkles,
  BrainCircuit,
  AlertTriangle,
  CheckCircle2,
  Layers,
  ExternalLink,
  ShieldAlert,
  Cpu,
  RefreshCw,
  Lightbulb,
  FileCheck
} from 'lucide-react';

export default function AIInvestigationPanel({
  rcaData,
  isInvestigating = false,
  investigationError = null,
  onRunInvestigation
}) {
  const hypotheses = rcaData?.root_cause_hypotheses || [];
  const primaryHypothesis = hypotheses[0];
  const alternativeHypotheses = hypotheses.slice(1);
  const recommendations = rcaData?.recommendations || [];
  const isCompleted = rcaData?.status === 'completed';
  const llmUsed = !!rcaData?.llm_used;

  return (
    <div className="bg-surface border border-surface-border rounded-md p-4 shadow-sm" data-testid="ai-investigation-panel">
      {/* Panel Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-surface-border">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-md bg-accent-subtle border border-accent-border text-accent">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-text-main flex items-center gap-2">
              <span>Root-Cause Analysis (RCA)</span>
              {isCompleted && (
                <span className="text-[10px] font-mono font-medium px-1.5 py-0.2 rounded bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20">
                  Diagnosis Complete
                </span>
              )}
            </h3>
            <p className="text-[11px] text-text-muted">
              Causal hypothesis generation and telemetry correlation.
            </p>
          </div>
        </div>

        {/* Engine mode pill & trigger button */}
        <div className="flex items-center gap-2">
          {rcaData && (
            <div
              className="flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono border bg-surface-elevated text-text-sub border-surface-border"
            >
              <Cpu className="w-3 h-3 text-text-muted" />
              <span>{llmUsed ? 'LLM Inference Active' : 'Deterministic Correlation'}</span>
            </div>
          )}

          <button
            onClick={onRunInvestigation}
            disabled={isInvestigating}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-accent hover:bg-accent-hover text-white disabled:opacity-50 transition-colors"
            data-testid="run-investigation-btn"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isInvestigating ? 'animate-spin' : ''}`} />
            <span>{isInvestigating ? 'Correlating...' : (isCompleted ? 'Re-run Analysis' : 'Run Investigation')}</span>
          </button>
        </div>
      </div>

      {/* Body States */}
      <div className="mt-4">
        {/* State 1: In Progress */}
        {isInvestigating && (
          <div className="py-10 text-center bg-surface-elevated rounded-md border border-surface-border">
            <BrainCircuit className="w-7 h-7 text-accent mx-auto animate-pulse mb-2" />
            <h4 className="text-xs font-semibold text-text-main">Analyzing Service Telemetry</h4>
            <p className="text-[11px] text-text-muted mt-0.5 max-w-sm mx-auto">
              Correlating error traces, metric anomalies, and deployment records...
            </p>
            <div className="w-36 h-1 bg-surface-border rounded-full mx-auto mt-3 overflow-hidden">
              <div className="w-full h-full bg-accent rounded-full animate-pulse" />
            </div>
          </div>
        )}

        {/* State 2: Error in investigation */}
        {!isInvestigating && investigationError && (
          <div className="p-3.5 rounded-md bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/25 text-rose-700 dark:text-rose-400">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-rose-600 dark:text-rose-400" />
              <div>
                <h4 className="text-xs font-semibold">Investigation Failed</h4>
                <p className="text-[11px] mt-0.5 opacity-90">{investigationError}</p>
                <button
                  onClick={onRunInvestigation}
                  className="mt-2 px-2 py-0.5 rounded bg-surface border border-surface-border text-text-main text-[11px] font-medium hover:bg-surface-elevated transition-colors"
                >
                  Retry Investigation
                </button>
              </div>
            </div>
          </div>
        )}

        {/* State 3: Not Started */}
        {!isInvestigating && !investigationError && !rcaData && (
          <div className="py-8 text-center bg-surface-elevated rounded-md border border-surface-border">
            <BrainCircuit className="w-6 h-6 text-text-muted mx-auto mb-1.5" />
            <h4 className="text-xs font-semibold text-text-sub">No Diagnosis Formed Yet</h4>
            <p className="text-[11px] text-text-muted mt-0.5 max-w-xs mx-auto">
              Run investigation to collect telemetry from the simulator and calculate root-cause probabilities.
            </p>
          </div>
        )}

        {/* State 4: Diagnosis Completed */}
        {!isInvestigating && !investigationError && isCompleted && (
          <div className="space-y-4">
            {/* Primary Hypothesis Card */}
            {primaryHypothesis ? (
              <div className="p-3.5 rounded-md bg-surface-elevated border border-surface-border">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-surface-border">
                  <span className="text-[11px] font-mono uppercase font-semibold text-text-sub tracking-wider flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                    Leading Root-Cause Hypothesis
                  </span>

                  {/* Confidence meter */}
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-text-muted">Confidence:</span>
                    <div className="w-20 bg-surface border border-surface-border rounded-full h-1.5 overflow-hidden">
                      <div
                        className="bg-accent h-full rounded-full"
                        style={{ width: `${Math.round((primaryHypothesis.confidence || 0) * 100)}%` }}
                      />
                    </div>
                    <span className="text-xs font-mono font-bold text-text-main">
                      {Math.round((primaryHypothesis.confidence || 0) * 100)}%
                    </span>
                  </div>
                </div>

                <div className="mt-2.5">
                  <h4 className="text-sm font-bold text-text-main font-mono">
                    {primaryHypothesis.cause}
                  </h4>
                  <p className="text-xs text-text-sub mt-1 leading-relaxed">
                    {primaryHypothesis.explanation}
                  </p>
                </div>

                {/* Supporting evidence references */}
                {primaryHypothesis.evidence_ids && primaryHypothesis.evidence_ids.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-surface-border flex flex-wrap items-center gap-1.5">
                    <span className="text-[11px] text-text-muted font-mono">Supporting Evidence:</span>
                    {primaryHypothesis.evidence_ids.map((evId) => (
                      <a
                        key={evId}
                        href={`#${evId}`}
                        className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono bg-surface text-text-main border border-surface-border hover:border-accent transition-colors"
                      >
                        <span>{evId}</span>
                        <ExternalLink className="w-2.5 h-2.5 text-text-muted" />
                      </a>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-text-muted">No specific hypothesis was returned by the correlation engine.</p>
            )}

            {/* Alternative Hypotheses */}
            {alternativeHypotheses.length > 0 && (
              <div className="space-y-1.5">
                <h4 className="text-[11px] font-mono uppercase text-text-muted tracking-wider flex items-center gap-1">
                  <Layers className="w-3 h-3 text-text-muted" />
                  Alternative Hypotheses Evaluated ({alternativeHypotheses.length})
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {alternativeHypotheses.map((alt, idx) => (
                    <div key={idx} className="p-2.5 bg-surface-elevated border border-surface-border rounded-md">
                      <div className="flex items-center justify-between text-xs mb-0.5">
                        <span className="font-semibold text-text-main font-mono text-[11px]">{alt.cause}</span>
                        <span className="text-[10px] font-mono text-text-muted">
                          {Math.round((alt.confidence || 0) * 100)}%
                        </span>
                      </div>
                      <p className="text-[11px] text-text-muted line-clamp-2">{alt.explanation}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recommended Operational Checks */}
            {recommendations.length > 0 && (
              <div className="space-y-1.5">
                <h4 className="text-[11px] font-mono uppercase text-text-muted tracking-wider flex items-center gap-1">
                  <Lightbulb className="w-3 h-3 text-amber-500" />
                  Recommended Operational Validations
                </h4>
                <div className="space-y-1">
                  {recommendations.map((rec, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-2 p-2 rounded-md bg-surface-elevated border border-surface-border text-xs text-text-sub"
                    >
                      <FileCheck className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                      <span className="text-[11px]">{rec}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Understated Disclaimer */}
            <div className="p-2 rounded-md bg-surface-elevated border border-surface-border text-[10px] text-text-muted flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-text-muted shrink-0" />
              <span>
                Confidence scores are automated heuristic estimates. Validate against service health metrics before initiating recovery.
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
