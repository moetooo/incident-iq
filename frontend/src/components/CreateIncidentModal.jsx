import React, { useState } from 'react';
import { X, Plus, AlertCircle } from 'lucide-react';

export default function CreateIncidentModal({ isOpen, onClose, onCreate, isCreating }) {
  const [title, setTitle] = useState('');
  const [service, setService] = useState('payment-api');
  const [severity, setSeverity] = useState('high');
  const [description, setDescription] = useState('');
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('Title is required');
      return;
    }
    if (!service.trim()) {
      setError('Service name is required');
      return;
    }
    setError('');
    onCreate({
      title: title.trim(),
      service: service.trim(),
      severity,
      description: description.trim() || 'No description provided.',
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
      <div
        className="bg-surface border border-surface-border rounded-lg max-w-md w-full shadow-lg overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-incident-title"
      >
        <div className="flex items-center justify-between p-4 border-b border-surface-border bg-surface">
          <div className="flex items-center gap-2">
            <div className="p-1 rounded bg-accent-subtle text-accent border border-accent-border">
              <Plus className="w-4 h-4" />
            </div>
            <div>
              <h3 id="create-incident-title" className="text-sm font-semibold text-text-main">
                Report Production Incident
              </h3>
              <p className="text-[11px] text-text-muted">
                Create an incident record in the investigation queue.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-main p-1 rounded hover:bg-surface-elevated transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-3">
          {error && (
            <div className="p-2.5 rounded-md bg-rose-500/10 border border-rose-500/25 text-rose-700 dark:text-rose-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 dark:text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-text-sub mb-1">
              Incident Title <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Payment Gateway upstream 504 timeouts"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-2.5 py-1.5 rounded-md bg-surface-elevated border border-surface-border text-text-main text-xs placeholder-text-muted focus:outline-none focus:border-accent"
              data-testid="incident-title-input"
            />
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <div>
              <label className="block text-xs font-medium text-text-sub mb-1">
                Affected Service <span className="text-rose-500">*</span>
              </label>
              <select
                value={service}
                onChange={(e) => setService(e.target.value)}
                className="w-full px-2 py-1.5 rounded-md bg-surface-elevated border border-surface-border text-text-main text-xs focus:outline-none focus:border-accent"
                data-testid="incident-service-select"
              >
                <option value="payment-api">payment-api</option>
                <option value="payment-gateway">payment-gateway</option>
                <option value="auth-service">auth-service</option>
                <option value="order-service">order-service</option>
                <option value="notification-service">notification-service</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-text-sub mb-1">
                Severity Level <span className="text-rose-500">*</span>
              </label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="w-full px-2 py-1.5 rounded-md bg-surface-elevated border border-surface-border text-text-main text-xs focus:outline-none focus:border-accent"
                data-testid="incident-severity-select"
              >
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-text-sub mb-1">
              Initial Symptoms / Details
            </label>
            <textarea
              rows={3}
              placeholder="Detail observed symptoms and telemetry sources..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-2.5 py-1.5 rounded-md bg-surface-elevated border border-surface-border text-text-main text-xs placeholder-text-muted focus:outline-none focus:border-accent resize-none"
              data-testid="incident-desc-input"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-surface-border">
            <button
              type="button"
              onClick={onClose}
              disabled={isCreating}
              className="px-2.5 py-1 rounded text-xs font-medium text-text-sub hover:bg-surface-elevated transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isCreating}
              className="px-3 py-1 rounded text-xs font-medium bg-accent hover:bg-accent-hover text-white disabled:opacity-50 transition-colors"
              data-testid="submit-create-incident-btn"
            >
              {isCreating ? 'Creating...' : 'Create Incident'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
