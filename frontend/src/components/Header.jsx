import React from 'react';
import {
  Radio,
  FlaskConical,
  Plus,
  RefreshCw,
  Server,
  Sun,
  Moon
} from 'lucide-react';
import { useTheme } from '../hooks/useTheme';

export default function Header({
  onTriggerDemo,
  onCreateIncident,
  onRefresh,
  backendHealthy,
  isRefreshing
}) {
  const { theme, toggleTheme, isDark } = useTheme();

  return (
    <header className="border-b border-surface-border bg-surface sticky top-0 z-30 transition-colors">
      {/* Slim, understated Demo Environment Notice */}
      <div className="bg-surface-elevated border-b border-surface-border px-4 py-1 text-[11px] font-mono text-text-muted flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <FlaskConical className="w-3.5 h-3.5 text-amber-500" />
          <span>
            <strong className="text-text-sub font-semibold">SIMULATED ENVIRONMENT:</strong> Telemetry and remediation actions run in an isolated sandbox.
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
          <span className="text-[10px] text-text-muted">Simulator Standby</span>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-13 flex items-center justify-between">
        {/* Brand / Logo */}
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-md bg-accent-subtle border border-accent-border text-accent">
            <Radio className="w-4 h-4" />
          </div>
          <div className="flex items-baseline gap-2">
            <h1 className="text-sm font-bold tracking-tight text-text-main flex items-center">
              Incident<span className="text-accent">IQ</span>
            </h1>
            <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-surface-elevated text-text-muted border border-surface-border">
              Observability
            </span>
          </div>
        </div>

        {/* Right actions, theme toggle, and status */}
        <div className="flex items-center gap-2">
          {/* Backend Health Badge */}
          <div
            className={`hidden md:flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono border ${
              backendHealthy
                ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
                : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20'
            }`}
            title={backendHealthy ? 'Backend API responding at /health' : 'Backend API connection failed'}
          >
            <Server className="w-3 h-3" />
            <span>API {backendHealthy ? 'Online' : 'Offline'}</span>
            <span className={`w-1.5 h-1.5 rounded-full ${backendHealthy ? 'bg-emerald-500' : 'bg-rose-500'}`} />
          </div>

          {/* Theme Toggle Button */}
          <button
            onClick={toggleTheme}
            className="p-1.5 text-text-sub hover:text-text-main rounded-md hover:bg-surface-elevated border border-transparent hover:border-surface-border transition-colors"
            title={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
            aria-label="Toggle theme"
            data-testid="theme-toggle-btn"
          >
            {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-text-main" />}
          </button>

          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-1.5 text-text-sub hover:text-text-main rounded-md hover:bg-surface-elevated border border-transparent hover:border-surface-border transition-colors disabled:opacity-50"
            title="Refresh incidents"
            data-testid="header-refresh-btn"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-accent' : ''}`} />
          </button>

          {/* Trigger Scenario Control */}
          <button
            onClick={onTriggerDemo}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-surface-elevated hover:bg-surface-hover text-text-main border border-surface-border transition-colors"
            data-testid="trigger-scenario-modal-btn"
          >
            <FlaskConical className="w-3.5 h-3.5 text-amber-500" />
            <span>Simulate Scenario</span>
          </button>

          {/* New Incident Button */}
          <button
            onClick={onCreateIncident}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-accent hover:bg-accent-hover text-white transition-colors"
            data-testid="create-incident-modal-btn"
          >
            <Plus className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Report Incident</span>
          </button>
        </div>
      </div>
    </header>
  );
}
