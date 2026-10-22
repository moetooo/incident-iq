import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import RemediationPanel from '../components/RemediationPanel';

describe('RemediationPanel', () => {
  const incidentMock = {
    id: 'inc_123',
    service: 'payment-api',
  };

  it('renders available options when no remediation is proposed', () => {
    const onPropose = vi.fn();
    render(
      <RemediationPanel
        incident={incidentMock}
        remediation={null}
        onProposeRemediation={onPropose}
      />
    );

    expect(screen.getByText(/Rollback Deployment/i)).toBeInTheDocument();
    expect(screen.getByTestId('propose-remediation-btn')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('propose-remediation-btn'));
    expect(onPropose).toHaveBeenCalledWith(
      expect.objectContaining({ action: 'rollback_demo_deployment' })
    );
  });

  it('requires explicit confirmation before allowing approval', () => {
    const onApprove = vi.fn();
    const onReject = vi.fn();
    const remediationPending = {
      id: 'rem_100',
      action: 'rollback_demo_deployment',
      status: 'pending_approval',
    };

    render(
      <RemediationPanel
        incident={incidentMock}
        remediation={remediationPending}
        onApproveRemediation={onApprove}
        onRejectRemediation={onReject}
      />
    );

    const approveBtn = screen.getByTestId('approve-remediation-btn');
    const confirmCheckbox = screen.getByTestId('remediation-confirm-checkbox');

    // Initially disabled to prevent accidental clicks
    expect(approveBtn).toBeDisabled();

    // Check confirmation
    fireEvent.click(confirmCheckbox);
    expect(approveBtn).not.toBeDisabled();

    // Trigger approve
    fireEvent.click(approveBtn);
    expect(onApprove).toHaveBeenCalledWith('rem_100');
  });

  it('allows rejection without confirmation', () => {
    const onReject = vi.fn();
    const remediationPending = {
      id: 'rem_100',
      action: 'rollback_demo_deployment',
      status: 'pending_approval',
    };

    render(
      <RemediationPanel
        incident={incidentMock}
        remediation={remediationPending}
        onRejectRemediation={onReject}
      />
    );

    const rejectBtn = screen.getByTestId('reject-remediation-btn');
    fireEvent.click(rejectBtn);
    expect(onReject).toHaveBeenCalledWith('rem_100');
  });

  it('displays execution audit result when completed', () => {
    const remediationSuccess = {
      id: 'rem_100',
      action: 'rollback_demo_deployment',
      status: 'success',
      result: { executed_by: 'operator_demo', rollback_sha: 'v2.4.0' },
    };

    render(
      <RemediationPanel
        incident={incidentMock}
        remediation={remediationSuccess}
      />
    );

    expect(screen.getByText(/Action success/i)).toBeInTheDocument();
    expect(screen.getByText(/rollback_sha/i)).toBeInTheDocument();
  });
});
