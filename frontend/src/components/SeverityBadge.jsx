import React from 'react';
import { AlertCircle, AlertTriangle, Info, ShieldAlert } from 'lucide-react';

export default function SeverityBadge({ severity = 'medium', size = 'sm' }) {
  const norm = (severity || '').toLowerCase();

  const configs = {
    critical: {
      bg: 'bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-200 dark:border-rose-500/25',
      icon: ShieldAlert,
      label: 'Critical',
    },
    high: {
      bg: 'bg-amber-50 dark:bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-500/25',
      icon: AlertTriangle,
      label: 'High',
    },
    medium: {
      bg: 'bg-yellow-50 dark:bg-yellow-500/10 text-yellow-800 dark:text-yellow-400 border-yellow-200 dark:border-yellow-500/25',
      icon: AlertCircle,
      label: 'Medium',
    },
    low: {
      bg: 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/25',
      icon: Info,
      label: 'Low',
    },
  };

  const current = configs[norm] || configs.medium;
  const IconComponent = current.icon;
  const sizeClasses = size === 'xs' ? 'px-1.5 py-0.2 text-[10px]' : 'px-2 py-0.5 text-[11px]';

  return (
    <span
      className={`inline-flex items-center gap-1 rounded border font-mono font-medium uppercase tracking-wide ${current.bg} ${sizeClasses}`}
      data-testid={`severity-badge-${norm}`}
    >
      <IconComponent className="w-3 h-3" />
      {current.label}
    </span>
  );
}
