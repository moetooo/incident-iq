import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import IncidentList from '../components/IncidentList';

describe('IncidentList', () => {
  const incidentsMock = [
    {
      id: 'inc_1',
      title: 'Postgres connection pool exhausted',
      service: 'payment-api',
      severity: 'critical',
      status: 'investigating',
      created_at: '2026-01-01T10:00:00Z',
    },
    {
      id: 'inc_2',
      title: 'High latency on auth service',
      service: 'auth-service',
      severity: 'high',
      status: 'resolved',
      created_at: '2026-01-01T11:00:00Z',
    },
    {
      id: 'inc_3',
      title: 'Minor disk space alert',
      service: 'storage-node',
      severity: 'low',
      status: 'triggered',
      created_at: '2026-01-01T12:00:00Z',
    },
  ];

  it('renders list of incidents with badges and titles', () => {
    const onSelect = vi.fn();
    render(<IncidentList incidents={incidentsMock} onSelectIncident={onSelect} />);

    expect(screen.getByText('Postgres connection pool exhausted')).toBeInTheDocument();
    expect(screen.getByText('High latency on auth service')).toBeInTheDocument();
    expect(screen.getByText('Minor disk space alert')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('incident-row-inc_1'));
    expect(onSelect).toHaveBeenCalledWith('inc_1');
  });

  it('filters incidents by search query', () => {
    render(<IncidentList incidents={incidentsMock} onSelectIncident={() => {}} />);

    const searchInput = screen.getByTestId('search-incidents-input');
    fireEvent.change(searchInput, { target: { value: 'Postgres' } });

    expect(screen.getByText('Postgres connection pool exhausted')).toBeInTheDocument();
    expect(screen.queryByText('High latency on auth service')).not.toBeInTheDocument();
  });

  it('filters incidents by severity dropdown', () => {
    render(<IncidentList incidents={incidentsMock} onSelectIncident={() => {}} />);

    const severitySelect = screen.getByTestId('filter-severity-select');
    fireEvent.change(severitySelect, { target: { value: 'critical' } });

    expect(screen.getByText('Postgres connection pool exhausted')).toBeInTheDocument();
    expect(screen.queryByText('High latency on auth service')).not.toBeInTheDocument();
    expect(screen.queryByText('Minor disk space alert')).not.toBeInTheDocument();
  });

  it('filters incidents by status dropdown', () => {
    render(<IncidentList incidents={incidentsMock} onSelectIncident={() => {}} />);

    const statusSelect = screen.getByTestId('filter-status-select');
    fireEvent.change(statusSelect, { target: { value: 'resolved' } });

    expect(screen.getByText('High latency on auth service')).toBeInTheDocument();
    expect(screen.queryByText('Postgres connection pool exhausted')).not.toBeInTheDocument();
  });

  it('shows empty state when list is empty and offers simulation trigger', () => {
    const onTriggerDemo = vi.fn();
    render(<IncidentList incidents={[]} onTriggerDemo={onTriggerDemo} />);

    expect(screen.getByText(/No Incidents Found/i)).toBeInTheDocument();
    const demoBtn = screen.getByRole('button', { name: /Simulate Demo Incident/i });
    expect(demoBtn).toBeInTheDocument();

    fireEvent.click(demoBtn);
    expect(onTriggerDemo).toHaveBeenCalled();
  });
});
