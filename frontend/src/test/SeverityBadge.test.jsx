import { describe, it, expect } from 'vitest';
import React from 'react';
import { render, screen } from '@testing-library/react';
import SeverityBadge from '../components/SeverityBadge';

describe('SeverityBadge', () => {
  it('renders critical severity with correct styling and badge', () => {
    render(<SeverityBadge severity="critical" />);
    const badge = screen.getByTestId('severity-badge-critical');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent(/critical/i);
  });

  it('renders high severity correctly', () => {
    render(<SeverityBadge severity="high" />);
    const badge = screen.getByTestId('severity-badge-high');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent(/high/i);
  });

  it('renders low severity correctly', () => {
    render(<SeverityBadge severity="low" />);
    const badge = screen.getByTestId('severity-badge-low');
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveTextContent(/low/i);
  });
});
