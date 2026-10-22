/**
 * Centralized API Client for IncidentIQ
 * Implements endpoints strictly adhering to docs/api-contract.md
 */

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const DEFAULT_TIMEOUT_MS = 15000;
const DEFAULT_OPERATOR_ID = (import.meta.env.VITE_OPERATOR_ID || 'operator').trim() || 'operator';

export class ApiError extends Error {
  constructor(message, status, code = 'API_ERROR', details = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

/**
 * Robust fetch wrapper with timeout, status checking, and error normalization
 */
async function request(endpoint, options = {}) {
  const { timeout = DEFAULT_TIMEOUT_MS, headers = {}, ...customConfig } = options;
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  const config = {
    ...customConfig,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...headers,
    },
    signal: controller.signal,
  };

  const url = `${BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, config);
    clearTimeout(id);

    // Parse JSON body if present
    let data;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      try {
        data = await response.json();
      } catch (parseErr) {
        throw new ApiError('Malformed JSON response from server', response.status, 'INVALID_JSON');
      }
    } else {
      const text = await response.text();
      data = text ? { message: text } : {};
    }

    if (!response.ok) {
      // Contract specifies { error: { code, message, request_id } }
      const errInfo = data?.error || {};
      const errorMessage = errInfo.message || data?.message || `Request failed with status ${response.status}`;
      const errorCode = errInfo.code || `HTTP_${response.status}`;
      throw new ApiError(errorMessage, response.status, errorCode, data);
    }

    return data;
  } catch (err) {
    clearTimeout(id);
    if (err.name === 'AbortError') {
      throw new ApiError('Request timed out. Please check backend connectivity.', 408, 'TIMEOUT');
    }
    if (err instanceof ApiError) {
      throw err;
    }
    // Network errors (e.g. backend down / connection refused)
    throw new ApiError(
      err.message || 'Unable to connect to backend service',
      0,
      'NETWORK_ERROR'
    );
  }
}

export const api = {
  /**
   * Health check: GET /health
   */
  async checkHealth() {
    return request('/health');
  },

  /**
   * List incidents: GET /api/v1/incidents
   */
  async getIncidents({ status, severity, limit, offset } = {}) {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (severity) params.append('severity', severity);
    if (limit !== undefined) params.append('limit', limit);
    if (offset !== undefined) params.append('offset', offset);

    const queryString = params.toString();
    const endpoint = `/api/v1/incidents${queryString ? `?${queryString}` : ''}`;
    return request(endpoint);
  },

  /**
   * Create incident: POST /api/v1/incidents
   */
  async createIncident({ title, service, severity, description }) {
    return request('/api/v1/incidents', {
      method: 'POST',
      body: JSON.stringify({ title, service, severity, description }),
    });
  },

  /**
   * Get single incident: GET /api/v1/incidents/{incident_id}
   */
  async getIncident(incidentId) {
    return request(`/api/v1/incidents/${encodeURIComponent(incidentId)}`);
  },

  /**
   * Collect evidence & investigate: POST /api/v1/incidents/{incident_id}/investigate
   */
  async investigateIncident(incidentId, { scenario_id } = {}) {
    const body = scenario_id ? { scenario_id } : {};
    return request(`/api/v1/incidents/${encodeURIComponent(incidentId)}/investigate`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  },

  /**
   * Retrieve evidence: GET /api/v1/incidents/{incident_id}/evidence
   */
  async getEvidence(incidentId) {
    return request(`/api/v1/incidents/${encodeURIComponent(incidentId)}/evidence`);
  },

  /**
   * Propose remediation: POST /api/v1/incidents/{incident_id}/remediations
   */
  async createRemediation(incidentId, { action, parameters = {} }) {
    return request(`/api/v1/incidents/${encodeURIComponent(incidentId)}/remediations`, {
      method: 'POST',
      body: JSON.stringify({ action, parameters }),
    });
  },

  /**
   * Approve remediation: POST /api/v1/remediations/{remediation_id}/approve
   * Sends X-Operator-Id header required by backend
   */
  async approveRemediation(remediationId, operatorId = DEFAULT_OPERATOR_ID) {
    const opId = typeof operatorId === 'string' ? operatorId : (operatorId?.operatorId || DEFAULT_OPERATOR_ID);
    return request(`/api/v1/remediations/${encodeURIComponent(remediationId)}/approve`, {
      method: 'POST',
      headers: {
        'X-Operator-Id': opId || DEFAULT_OPERATOR_ID,
      },
    });
  },

  /**
   * Reject remediation: POST /api/v1/remediations/{remediation_id}/reject
   * Sends X-Operator-Id header required by backend
   */
  async rejectRemediation(remediationId, operatorId = DEFAULT_OPERATOR_ID) {
    const opId = typeof operatorId === 'string' ? operatorId : (operatorId?.operatorId || DEFAULT_OPERATOR_ID);
    return request(`/api/v1/remediations/${encodeURIComponent(remediationId)}/reject`, {
      method: 'POST',
      headers: {
        'X-Operator-Id': opId || DEFAULT_OPERATOR_ID,
      },
    });
  },

  /**
   * Helper for triggering a predefined simulated incident scenario
   */
  async triggerDemoIncident(scenarioKey) {
    const scenarios = {
      database_failure: {
        title: 'PostgreSQL connection pool exhaustion & timeouts',
        service: 'payment-api',
        severity: 'critical',
        description: 'Payment microservice reporting active connection spikes and 504 Gateway Timeouts.',
        scenario_id: 'database_failure',
      },
      payment_timeout: {
        title: 'Payment gateway upstream timeout on /checkout/pay',
        service: 'payment-gateway',
        severity: 'high',
        description: 'Third-party PSP webhook latencies exceed 10000ms threshold.',
        scenario_id: 'payment_timeout',
      },
      bad_deployment: {
        title: 'High error rate following release v2.4.1 deployment',
        service: 'auth-service',
        severity: 'high',
        description: 'Elevated 500 internal server error rate immediately post-deployment rollout.',
        scenario_id: 'bad_deployment',
      },
    };

    const target = scenarios[scenarioKey] || scenarios.database_failure;
    const incident = await this.createIncident({
      title: target.title,
      service: target.service,
      severity: target.severity,
      description: target.description,
    });

    return { incident, scenarioId: target.scenario_id };
  },
};
