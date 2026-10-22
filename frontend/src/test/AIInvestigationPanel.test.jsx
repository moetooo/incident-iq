import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import AIInvestigationPanel from '../components/AIInvestigationPanel';

describe('AIInvestigationPanel', () => {
  it('renders unstarted state with call to action', () => {
    const onRun = vi.fn();
    render(<AIInvestigationPanel rcaData={null} onRunInvestigation={onRun} />);
    expect(screen.getByText(/No Diagnosis Formed Yet/i)).toBeInTheDocument();
    expect(screen.getByTestId('run-investigation-btn')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('run-investigation-btn'));
    expect(onRun).toHaveBeenCalled();
  });

  it('renders investigating state with animated loader', () => {
    render(<AIInvestigationPanel isInvestigating={true} />);
    expect(screen.getByText(/Analyzing Service Telemetry/i)).toBeInTheDocument();
  });

  it('renders error state with retry button', () => {
    const onRun = vi.fn();
    render(
      <AIInvestigationPanel
        investigationError="Connection to simulator timed out"
        onRunInvestigation={onRun}
      />
    );
    expect(screen.getByText(/Investigation Failed/i)).toBeInTheDocument();
    expect(screen.getByText(/Connection to simulator timed out/i)).toBeInTheDocument();
    fireEvent.click(screen.getByText(/Retry Investigation/i));
    expect(onRun).toHaveBeenCalled();
  });

  it('renders completed RCA diagnosis with primary hypothesis, confidence, and evidence links', () => {
    const mockRca = {
      incident_id: 'inc_123',
      status: 'completed',
      root_cause_hypotheses: [
        {
          cause: 'Database connection pool saturation',
          confidence: 0.92,
          evidence_ids: ['ev_log_1', 'ev_metric_2'],
          explanation: 'Connection count hit 100% capacity during traffic surge.',
        },
        {
          cause: 'Slow query execution',
          confidence: 0.45,
          evidence_ids: ['ev_log_3'],
          explanation: 'Table scan detected on orders table.',
        },
      ],
      recommendations: [
        'Scale PostgreSQL connection pool to 200 handles',
        'Verify database replica health',
      ],
      llm_used: true,
    };

    render(<AIInvestigationPanel rcaData={mockRca} />);

    expect(screen.getByText(/Database connection pool saturation/i)).toBeInTheDocument();
    expect(screen.getByText('92%')).toBeInTheDocument();
    expect(screen.getByText('ev_log_1')).toBeInTheDocument();
    expect(screen.getByText('ev_metric_2')).toBeInTheDocument();
    expect(screen.getByText(/Scale PostgreSQL connection pool/i)).toBeInTheDocument();
    expect(screen.getByText(/LLM Inference Active/i)).toBeInTheDocument();
    expect(screen.getByText(/Slow query execution/i)).toBeInTheDocument();
  });

  it('renders recommended_checks when provided by backend', () => {
    const mockRca = {
      incident_id: 'inc_456',
      status: 'completed',
      root_cause_hypotheses: [
        {
          cause: 'Upstream gateway timeout',
          confidence: 0.85,
        },
      ],
      recommended_checks: [
        'Check upstream PSP status dashboard',
        'Verify egress NAT gateway metrics',
      ],
      recommendations: [
        'Ignored fallback recommendation',
      ],
    };

    render(<AIInvestigationPanel rcaData={mockRca} />);
    expect(screen.getByText(/Check upstream PSP status dashboard/i)).toBeInTheDocument();
    expect(screen.getByText(/Verify egress NAT gateway metrics/i)).toBeInTheDocument();
    expect(screen.queryByText(/Ignored fallback recommendation/i)).not.toBeInTheDocument();
  });

  it('falls back to recommendations when recommended_checks is absent', () => {
    const mockRca = {
      incident_id: 'inc_789',
      status: 'completed',
      root_cause_hypotheses: [
        {
          cause: 'Cache miss storm',
          confidence: 0.76,
        },
      ],
      recommendations: [
        'Warm cache keys before traffic ramp',
      ],
    };

    render(<AIInvestigationPanel rcaData={mockRca} />);
    expect(screen.getByText(/Warm cache keys before traffic ramp/i)).toBeInTheDocument();
  });

  it('renders explicit alternative_hypotheses even when root_cause_hypotheses has only one item', () => {
    const mockRca = {
      incident_id: 'inc_101',
      status: 'completed',
      root_cause_hypotheses: [
        {
          cause: 'Primary: Auth token validation failure',
          confidence: 0.95,
        },
      ],
      alternative_hypotheses: [
        {
          cause: 'Alternative: Redis cluster partition',
          confidence: 0.4,
          explanation: 'Split-brain suspicion in cache tier.',
        },
        {
          cause: 'Alternative: TLS handshake expiration',
          confidence: 0.25,
          explanation: 'Cert renewal timer elapsed.',
        },
      ],
    };

    render(<AIInvestigationPanel rcaData={mockRca} />);
    expect(screen.getByText(/Primary: Auth token validation failure/i)).toBeInTheDocument();
    expect(screen.getByText(/Alternative: Redis cluster partition/i)).toBeInTheDocument();
    expect(screen.getByText(/Alternative: TLS handshake expiration/i)).toBeInTheDocument();
    expect(screen.getByText('40%')).toBeInTheDocument();
    expect(screen.getByText('25%')).toBeInTheDocument();
  });

  it('handles missing or empty optional fields safely without crashing', () => {
    const sparseRca = {
      incident_id: 'inc_empty',
      status: 'completed',
      // No root_cause_hypotheses, alternative_hypotheses, recommended_checks, or recommendations
    };

    const { container } = render(<AIInvestigationPanel rcaData={sparseRca} />);
    expect(container).toBeInTheDocument();
    expect(screen.getByText(/Diagnosis Complete/i)).toBeInTheDocument();
    expect(screen.getByText(/No specific hypothesis was returned by the correlation engine/i)).toBeInTheDocument();
  });
});
