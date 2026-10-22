import React from 'react';
import { Clock, PlayCircle, CheckCircle2, ShieldCheck, Wrench, AlertOctagon } from 'lucide-react';

export default function StatusBadge({ status = 'triggered' }) {
  const norm = (status || '').toLowerCase().replace(/_/g, ' ');

  const configs = {
    triggered: {
      bg: 'bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-200 dark:border-rose-500/25',
      icon: AlertOctagon,
      label: 'Triggered',
    },
    investigating: {
      bg: 'bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-500/25',
      icon: PlayCircle,
      label: 'Investigating',
    },
    'hypothesis formed': {
      bg: 'bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 border-indigo-200 dark:border-indigo-500/25',
      icon: Clock,
      label: 'Hypothesis Formed',
    },
    'awaiting approval': {
      bg: 'bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-500/25',
      icon: ShieldCheck,
      label: 'Awaiting Approval',
    },
    remediating: {
      bg: 'bg-sky-50 dark:bg-sky-500/10 text-sky-700 dark:text-sky-400 border-sky-200 dark:border-sky-500/25',
      icon: Wrench,
      label: 'Remediating',
    },
    resolved: {
      bg: 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/25',
      icon: CheckCircle2,
      label: 'Resolved',
    },
  };

  const current = configs[norm] || {
    bg: 'bg-surface-elevated text-text-sub border-surface-border',
    icon: Clock,
    label: norm.charAt(0).toUpperCase() + norm.slice(1),
  };

  const IconComponent = current.icon;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[11px] font-medium ${current.bg}`}
      data-testid="status-badge"
    >
      <IconComponent className="w-3 h-3" />
      {current.label}
    </span>
  );
}
