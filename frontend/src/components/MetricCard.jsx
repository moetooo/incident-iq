import React from 'react';

export default function MetricCard({ title, value, subtitle, icon: Icon, color = 'neutral' }) {
  const colorMap = {
    neutral: 'text-text-sub bg-surface-elevated border-surface-border',
    brand: 'text-accent bg-accent-subtle border-accent-border',
    critical: 'text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-500/10 border-rose-200 dark:border-rose-500/20',
    amber: 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/20',
    emerald: 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20',
    blue: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-500/10 border-blue-200 dark:border-blue-500/20',
  };

  const currentStyles = colorMap[color] || colorMap.neutral;

  return (
    <div className="bg-surface border border-surface-border rounded-md p-3.5 flex items-start justify-between transition-colors">
      <div>
        <p className="text-[11px] font-medium text-text-muted uppercase tracking-wider">{title}</p>
        <p className="text-xl font-bold text-text-main mt-1 font-mono tracking-tight">{value}</p>
        {subtitle && (
          <p className="text-[11px] text-text-muted mt-0.5">
            {subtitle}
          </p>
        )}
      </div>
      {Icon && (
        <div className={`p-1.5 rounded-md border ${currentStyles}`}>
          <Icon className="w-4 h-4" />
        </div>
      )}
    </div>
  );
}
