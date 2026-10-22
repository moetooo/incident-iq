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
});
