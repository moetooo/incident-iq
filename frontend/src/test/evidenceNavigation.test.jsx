import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import IncidentDetail from '../components/IncidentDetail';
import AIInvestigationPanel from '../components/AIInvestigationPanel';
import EvidenceTimeline from '../components/EvidenceTimeline';

describe('Evidence Link Navigation & URL-State Synchronization', () => {
  const mockIncident = {
    id: 'inc_test_100',
    title: 'Payment DB Outage',
    service: 'payment-api',
    severity: 'critical',
    status: 'investigating',
    created_at: new Date().toISOString(),
  };

  const mockEvidence = [
    {
      id: 'ev_f6d9e18571cd',
      source: 'database',
      timestamp: new Date().toISOString(),
      details: {
        event: 'pool_exhaustion',
        active_connections: 100,
        message: 'Max connection limit reached: 100/100 handles saturated',
      },
    },
    {
      id: 'ev_log_2',
      source: 'app_logs',
      timestamp: new Date().toISOString(),
      details: {
        log_level: 'ERROR',
        message: 'HTTP 504 Gateway Timeout while acquiring DB client',
      },
    },
  ];

  const mockRcaData = {
    incident_id: 'inc_test_100',
    status: 'completed',
    root_cause_hypotheses: [
      {
        cause: 'Database connection pool saturation',
        confidence: 0.95,
        evidence_ids: ['ev_f6d9e18571cd', 'ev_log_2'],
        explanation: 'PostgreSQL connection handles exhausted during payment traffic surge.',
      },
    ],
    recommendations: ['Expand connection pool to 100', 'Restart connection pooler'],
    llm_used: true,
  };

  beforeEach(() => {
    // Reset window hash and mock scrollIntoView
    window.location.hash = '';
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    window.location.hash = '';
    vi.restoreAllMocks();
  });

  it('REGRESSION FIX: clicking an evidence ID link on RCA screen updates URL AND immediately renders evidence in visible UI', async () => {
    render(
      <IncidentDetail
        incident={mockIncident}
        evidence={mockEvidence}
        rcaData={mockRcaData}
        isLoading={false}
      />
    );

    // Initial state: on RCA tab
    expect(screen.getByText(/Database connection pool saturation/i)).toBeInTheDocument();
    // The evidence detail text (e.g. "Max connection limit reached") should NOT be visible yet
    expect(screen.queryByText(/Max connection limit reached/i)).not.toBeInTheDocument();

    // Find the supporting evidence link chip for ev_f6d9e18571cd
    const evidenceChip = screen.getByTestId('evidence-link-ev_f6d9e18571cd');
    expect(evidenceChip).toBeInTheDocument();
    expect(evidenceChip.getAttribute('href')).toBe('#ev_f6d9e18571cd');

    // Click the evidence link
    fireEvent.click(evidenceChip);

    // 1. URL hash must be updated
    expect(window.location.hash).toBe('#ev_f6d9e18571cd');

    // 2. Visible UI must immediately transition to Evidence tab and render target evidence
    await waitFor(() => {
      // The evidence timeline container should now be active
      expect(screen.getByTestId('evidence-timeline')).toBeInTheDocument();
      // The selected evidence item must be visible and automatically expanded
      expect(screen.getByText(/Max connection limit reached: 100\/100 handles saturated/i)).toBeInTheDocument();
      // The target reference banner should indicate it was selected from RCA
      expect(screen.getByText(/Viewing supporting evidence/i)).toBeInTheDocument();
    });

    // 3. scrollIntoView was called for the targeted evidence element
    await waitFor(() => {
      expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
    });
  });

  it('supports direct URL navigation: landing on page with #ev_... hash immediately displays evidence detail', () => {
    window.location.hash = '#ev_log_2';

    render(
      <IncidentDetail
        incident={mockIncident}
        evidence={mockEvidence}
        rcaData={mockRcaData}
        isLoading={false}
      />
    );

    // Should immediately open Evidence tab because hash is #ev_log_2
    expect(screen.getByTestId('evidence-timeline')).toBeInTheDocument();
    // ev_log_2 details should be visible
    expect(screen.getByText(/HTTP 504 Gateway Timeout while acquiring DB client/i)).toBeInTheDocument();
  });

  it('supports browser Back and Forward navigation via popstate/hashchange', async () => {
    render(
      <IncidentDetail
        incident={mockIncident}
        evidence={mockEvidence}
        rcaData={mockRcaData}
        isLoading={false}
      />
    );

    // Click to navigate to ev_f6d9e18571cd
    const evidenceChip = screen.getByTestId('evidence-link-ev_f6d9e18571cd');
    fireEvent.click(evidenceChip);

    expect(screen.getByText(/Max connection limit reached/i)).toBeInTheDocument();

    // Simulate browser Back button: hash changed to #rca
    act(() => {
      window.location.hash = '#rca';
      window.dispatchEvent(new HashChangeEvent('hashchange'));
    });

    await waitFor(() => {
      expect(screen.getByText(/Database connection pool saturation/i)).toBeInTheDocument();
    });

    // Simulate browser Forward button: hash changed back to #ev_f6d9e18571cd
    act(() => {
      window.location.hash = '#ev_f6d9e18571cd';
      window.dispatchEvent(new HashChangeEvent('hashchange'));
    });

    await waitFor(() => {
      expect(screen.getByTestId('evidence-timeline')).toBeInTheDocument();
      expect(screen.getByText(/Max connection limit reached/i)).toBeInTheDocument();
    });
  });

  it('switching from one evidence item to another updates the displayed evidence', async () => {
    window.location.hash = '#ev_f6d9e18571cd';

    render(
      <IncidentDetail
        incident={mockIncident}
        evidence={mockEvidence}
        rcaData={mockRcaData}
        isLoading={false}
      />
    );

    expect(screen.getByText(/Max connection limit reached/i)).toBeInTheDocument();

    // Now switch hash to second evidence item #ev_log_2
    act(() => {
      window.location.hash = '#ev_log_2';
      window.dispatchEvent(new HashChangeEvent('hashchange'));
    });

    await waitFor(() => {
      expect(screen.getByText(/HTTP 504 Gateway Timeout while acquiring DB client/i)).toBeInTheDocument();
    });
  });

  it('Back to RCA button in Evidence Timeline returns to RCA tab and cleans URL hash', async () => {
    window.location.hash = '#ev_f6d9e18571cd';

    render(
      <IncidentDetail
        incident={mockIncident}
        evidence={mockEvidence}
        rcaData={mockRcaData}
        isLoading={false}
      />
    );

    expect(screen.getByTestId('evidence-timeline')).toBeInTheDocument();
    const backBtn = screen.getByTestId('back-to-rca-btn');
    expect(backBtn).toBeInTheDocument();

    fireEvent.click(backBtn);

    await waitFor(() => {
      expect(screen.getByText(/Database connection pool saturation/i)).toBeInTheDocument();
    });
    expect(window.location.hash).toBe('');
  });

  it('clicking tabs directly clears the evidence hash if leaving evidence tab', () => {
    window.location.hash = '#ev_f6d9e18571cd';

    render(
      <IncidentDetail
        incident={mockIncident}
        evidence={mockEvidence}
        rcaData={mockRcaData}
        isLoading={false}
      />
    );

    const rcaTabBtn = screen.getByTestId('tab-rca-btn');
    fireEvent.click(rcaTabBtn);

    expect(screen.getByText(/Database connection pool saturation/i)).toBeInTheDocument();
    expect(window.location.hash).toBe('');
  });

  it('VERIFIES EXACT REPORTED DEFECT: clicking ev_d94400618a65 navigates to Evidence tab, expands card, and displays details', async () => {
    const incidentWithD944 = {
      id: 'inc_817c5f53c801',
      title: 'False recovery probe',
      service: 'payment-api',
      severity: 'high',
      status: 'awaiting approval',
    };

    const evidenceWithD944 = [
      {
        id: 'ev_9625dd8d25c4',
        type: 'deployment',
        source: 'payment-api',
        summary: 'Stable baseline release with resilient payment retries',
      },
      {
        id: 'ev_d94400618a65',
        type: 'state',
        source: 'payment-api',
        summary: 'Service payment-api is fully healthy and operational',
        details: {
          status: 'UP',
          checks: { database: 'UP', cache: 'UP', payment_gateway: 'UP' },
          version: 'v2.4.0',
        },
      },
    ];

    const rcaWithD944 = {
      incident_id: 'inc_817c5f53c801',
      status: 'completed',
      root_cause_hypotheses: [
        {
          cause: 'Recovery failure after probe validation',
          confidence: 0.88,
          evidence_ids: ['ev_d94400618a65'],
          explanation: 'State verification probe confirmed healthy baseline services.',
        },
      ],
      recommendations: ['Authorize rollback execution'],
    };

    render(
      <IncidentDetail
        incident={incidentWithD944}
        evidence={evidenceWithD944}
        rcaData={rcaWithD944}
        isLoading={false}
      />
    );

    // Initial state: On RCA tab
    expect(screen.getByText(/Recovery failure after probe validation/i)).toBeInTheDocument();
    expect(screen.queryByText(/Service payment-api is fully healthy and operational/i)).not.toBeInTheDocument();

    const linkEl = screen.getByTestId('evidence-link-ev_d94400618a65');
    expect(linkEl).toBeInTheDocument();
    fireEvent.click(linkEl);

    // Verify URL hash updated
    expect(window.location.hash).toBe('#ev_d94400618a65');

    // Verify Evidence tab is active, card is visible and auto-expanded with payload
    await waitFor(() => {
      expect(screen.getByTestId('evidence-timeline')).toBeInTheDocument();
      expect(screen.getByText(/Service payment-api is fully healthy and operational/i)).toBeInTheDocument();
      expect(screen.getByText(/"database": "UP"/i)).toBeInTheDocument();
      expect(screen.getByTestId('target-evidence-banner')).toBeInTheDocument();
    });
  });

  it('HANDLES MISSING EVIDENCE SAFELY: clicking an unrecorded evidence ID renders explicit missing record banner', async () => {
    const rcaWithMissing = {
      incident_id: 'inc_test_100',
      status: 'completed',
      root_cause_hypotheses: [
        {
          cause: 'Heuristic anomaly',
          confidence: 0.7,
          evidence_ids: ['ev_missing_record_xyz'],
          explanation: 'Synthetic hypothesis pointing to an evicted evidence ID.',
        },
      ],
    };

    render(
      <IncidentDetail
        incident={mockIncident}
        evidence={mockEvidence}
        rcaData={rcaWithMissing}
        isLoading={false}
      />
    );

    const missingLink = screen.getByTestId('evidence-link-ev_missing_record_xyz');
    fireEvent.click(missingLink);

    expect(window.location.hash).toBe('#ev_missing_record_xyz');

    await waitFor(() => {
      expect(screen.getByTestId('evidence-timeline')).toBeInTheDocument();
      expect(screen.getByTestId('missing-evidence-banner')).toBeInTheDocument();
      expect(screen.getByText(/ev_missing_record_xyz/i)).toBeInTheDocument();
      expect(screen.getByText(/was not found among the 2 telemetry records/i)).toBeInTheDocument();
    });
  });
});
