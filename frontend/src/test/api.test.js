import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { api, ApiError } from '../services/api';

describe('Centralized API Client', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('checkHealth calls /health and parses JSON', async () => {
    const mockHealth = { status: 'ok' };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => mockHealth,
    });

    const res = await api.checkHealth();
    expect(global.fetch).toHaveBeenCalledWith('/health', expect.any(Object));
    expect(res).toEqual(mockHealth);
  });

  it('getIncidents handles filters and query params correctly', async () => {
    const mockList = { items: [{ id: 'inc_1', title: 'DB timeout' }], total: 1 };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => mockList,
    });

    const res = await api.getIncidents({ status: 'investigating', severity: 'high', limit: 10 });
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/incidents?status=investigating&severity=high&limit=10',
      expect.any(Object)
    );
    expect(res).toEqual(mockList);
  });

  it('createIncident sends POST with proper body', async () => {
    const payload = {
      title: 'Payment 504',
      service: 'payment-api',
      severity: 'critical',
      description: 'Upstream gateway down',
    };
    const created = { id: 'inc_999', ...payload, status: 'triggered' };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => created,
    });

    const res = await api.createIncident(payload);
    expect(global.fetch).toHaveBeenCalledWith('/api/v1/incidents', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify(payload),
    }));
    expect(res).toEqual(created);
  });

  it('investigateIncident calls correct endpoint', async () => {
    const rcaResponse = {
      incident_id: 'inc_123',
      status: 'completed',
      root_cause_hypotheses: [
        {
          cause: 'Database pool exhaustion',
          confidence: 0.88,
          evidence_ids: ['ev_1'],
          explanation: 'Connection limit reached',
        },
      ],
      recommendations: ['Restart pool'],
      llm_used: false,
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => rcaResponse,
    });

    const res = await api.investigateIncident('inc_123', { scenario_id: 'database_failure' });
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/incidents/inc_123/investigate',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ scenario_id: 'database_failure' }),
      })
    );
    expect(res).toEqual(rcaResponse);
  });

  it('approveRemediation and rejectRemediation post to remediation endpoints', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => ({ status: 'approved' }),
    });

    const resApprove = await api.approveRemediation('rem_1');
    expect(global.fetch).toHaveBeenCalledWith('/api/v1/remediations/rem_1/approve', expect.objectContaining({
      method: 'POST',
    }));
    expect(resApprove.status).toBe('approved');

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      json: async () => ({ status: 'rejected' }),
    });

    const resReject = await api.rejectRemediation('rem_1');
    expect(global.fetch).toHaveBeenCalledWith('/api/v1/remediations/rem_1/reject', expect.objectContaining({
      method: 'POST',
    }));
    expect(resReject.status).toBe('rejected');
  });

  it('normalizes HTTP errors into ApiError instances', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      headers: { get: () => 'application/json' },
      json: async () => ({
        error: {
          code: 'INCIDENT_NOT_FOUND',
          message: 'Incident does not exist',
          request_id: 'req_123',
        },
      }),
    });

    await expect(api.getIncident('missing_inc')).rejects.toThrow(ApiError);
    try {
      await api.getIncident('missing_inc');
    } catch (err) {
      expect(err.status).toBe(404);
      expect(err.code).toBe('INCIDENT_NOT_FOUND');
      expect(err.message).toBe('Incident does not exist');
    }
  });

  it('handles network failure gracefully', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Failed to fetch'));

    await expect(api.checkHealth()).rejects.toThrow(ApiError);
    try {
      await api.checkHealth();
    } catch (err) {
      expect(err.code).toBe('NETWORK_ERROR');
      expect(err.status).toBe(0);
    }
  });
});
