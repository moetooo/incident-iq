# IncidentIQ API Contract

Version: v1.2
Base path: `/api/v1`
Owner: Agent 3 (backend + coordination)

All timestamps use ISO 8601 UTC with a trailing `Z` (for example
`2026-01-01T10:00:00Z`).
All request and response bodies use JSON (`Content-Type: application/json`).

This document is canonical. The frontend and simulator agents must implement
against it and must not invent incompatible schemas. Breaking changes require
updating this document first.

---

## 0. Conventions

### 0.1 Identifiers

| Entity | Prefix | Example |
|---|---|---|
| Incident | `inc_` | `inc_9f1c2d3e4a5b` |
| Evidence | `ev_` | `ev_1a2b3c4d5e6f` |
| Investigation report | `inv_` | `inv_77aabbccddee` |
| Hypothesis | `hyp_` | `hyp_0f0f0f0f0f0f` |
| Remediation | `rem_` | `rem_abc123def456` |
| Audit entry | `aud_` | `aud_1234abcd5678` |
| Request | `req_` | `req_123` |

IDs are opaque strings. Clients must not infer meaning from the prefix beyond
entity type.

### 0.2 Enum casing

Enum values are **lowercase snake_case** on the wire and in the database:

- Incident status: `triggered`, `investigating`, `hypothesis_formed`,
  `awaiting_approval`, `remediating`, `resolved`
- Severity: `low`, `medium`, `high`, `critical`
- Evidence type: `log`, `metric`, `deployment`, `state`, `event`, `trace`
- Remediation status: `pending_approval`, `approved`, `rejected`, `executing`,
  `success`, `failed`

Unknown values must be rejected with `422` on write and tolerated (kept
verbatim) on read.

### 0.3 Authentication and operator identity

The backend supports two independent mechanisms.

1. **Service authentication (optional).**
   When the backend is started with `API_KEY` set, every request to
   `/api/v1/**` must include the header `X-API-Key: <value>`. Missing or
   invalid keys return `401`. When `API_KEY` is unset the backend runs in
   local demo mode and this check is skipped.

2. **Operator identity (always required for approvals).**
   `POST /api/v1/remediations/{remediation_id}/approve` and
   `.../reject` require the header `X-Operator-Id: <operator identifier>`.
   The value is recorded in the audit trail. Missing header returns `422`.
   The backend never infers an operator identity from request bodies or from
   client-supplied state.

`GET /health` and `GET /api/v1/health` are always unauthenticated.

### 0.4 Request ID

Every response carries the header `X-Request-ID: <req_id>`. The same value is
used in the `request_id` field of error bodies and in structured logs.

### 0.5 Pagination

List endpoints accept `limit` (default `50`, max `200`) and `offset`
(default `0`) and return `{"items": [...], "total": <int>}`.

---

## 1. Health

```http
GET /health
GET /api/v1/health
```

Response `200`:

```json
{
  "status": "ok",
  "service": "IncidentIQ Backend",
  "version": "0.1.0",
  "database": "ok",
  "simulator": "unknown",
  "llm": {
    "provider": "gemini",
    "model": "gemini-3.5-flash-lite",
    "configured": false
  }
}
```

- `status` is `ok` or `degraded`. It is `degraded` when the database is
  unreachable or the simulator is not answering.
- `database`: `ok` | `degraded` | `not_configured`
- `simulator`: `ok` | `degraded` | `unreachable` | `disabled` | `unknown`.
  `degraded` means the simulator is reachable but reports an unhealthy
  simulated service (for example while a failure scenario is active).
- `llm.configured` is `true` only when an API key is present. The backend must
  start and stay healthy without an API key.

The simulator exposes its own `GET /health` at `SIMULATOR_BASE_URL/health`.

---

## 2. Incidents

### 2.1 List incidents

```http
GET /api/v1/incidents?status=&severity=&service=&limit=&offset=
```

All filters are optional. `status` and `severity` must be valid enum values
when supplied.

Response `200`:

```json
{
  "items": [
    {
      "id": "inc_9f1c2d3e4a5b",
      "title": "Payment API timeouts",
      "service": "payment-api",
      "severity": "high",
      "status": "investigating",
      "description": "Payment requests are timing out",
      "created_at": "2026-01-01T10:00:00Z",
      "updated_at": "2026-01-01T10:02:00Z",
      "resolved_at": null
    }
  ],
  "total": 1
}
```

### 2.2 Create incident

```http
POST /api/v1/incidents
```

Request:

```json
{
  "title": "Payment API timeouts",
  "service": "payment-api",
  "severity": "high",
  "description": "Payment requests are timing out"
}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | yes | 1..200 characters |
| `service` | string | yes | 1..100 characters |
| `severity` | enum | yes | `low` \| `medium` \| `high` \| `critical` |
| `description` | string | no | up to 4000 characters, defaults to `""` |

Response `201`: incident object. New incidents start in status `triggered`.

### 2.3 Get incident

```http
GET /api/v1/incidents/{incident_id}
```

Response `200`: incident object. Unknown ID returns `404` with code
`INCIDENT_NOT_FOUND`.

---

## 3. Evidence

### 3.1 Collect evidence

```http
POST /api/v1/incidents/{incident_id}/evidence
```

Request (optional body):

```json
{
  "scenario_id": "database_failure"
}
```

The backend fetches evidence from the simulator, normalises it, persists it
and returns the stored evidence. Evidence is de-duplicated per incident by a
content fingerprint, so repeated collection does not create duplicates.

Response `200`:

```json
{
  "incident_id": "inc_9f1c2d3e4a5b",
  "collected": 2,
  "stored": 1,
  "items": [
    {
      "id": "ev_1a2b3c4d5e6f",
      "incident_id": "inc_9f1c2d3e4a5b",
      "type": "log",
      "source": "payment-api",
      "timestamp": "2026-01-01T10:00:00Z",
      "summary": "Database connection timeout",
      "details": { "level": "error", "message": "connection timed out" },
      "confidence": 0.9
    }
  ],
  "warnings": []
}
```

`warnings` is non-empty when the simulator is unreachable or returned items
that had to be skipped. Evidence collection never invents evidence: if the
simulator is unreachable the response contains an empty `items` list and a
warning.

### 3.2 List evidence

```http
GET /api/v1/incidents/{incident_id}/evidence
```

Response `200`: `{"items": [evidence object], "total": <int>}`.

---

## 4. Investigation

### 4.1 Run investigation

```http
POST /api/v1/incidents/{incident_id}/investigate
```

Request (optional body):

```json
{
  "scenario_id": "database_failure"
}
```

The pipeline, in order:

1. Load the incident and move it to status `investigating`.
2. Collect evidence from the simulator and persist it.
3. Run the LLM provider (Gemini) when an API key is configured, otherwise run
   the deterministic fallback engine.
4. Validate the provider output with Pydantic and verify every referenced
   evidence ID against the evidence actually collected for this incident.
5. Persist hypotheses and create remediation proposals in status
   `pending_approval` (proposals only, never executed).
6. Move the incident to `hypothesis_formed`, or `awaiting_approval` when a
   remediation proposal exists.

Response `200`:

```json
{
  "id": "inv_77aabbccddee",
  "incident_id": "inc_9f1c2d3e4a5b",
  "status": "completed",
  "summary": "Database connectivity failure is the most likely cause.",
  "root_cause_hypotheses": [
    {
      "id": "hyp_0f0f0f0f0f0f",
      "kind": "root_cause",
      "cause": "Database connection failure",
      "explanation": "Database errors increased during the incident",
      "confidence": 0.85,
      "evidence_ids": ["ev_1a2b3c4d5e6f"],
      "recommended_action_type": "restart_demo_service"
    }
  ],
  "alternative_hypotheses": [],
  "recommended_checks": [
    "Inspect database connectivity and connection-pool configuration"
  ],
  "proposed_remediations": [
    {
      "action": "restart_demo_service",
      "parameters": {},
      "risk_level": "medium",
      "rationale": "Connection pool saturation is indicated by the collected logs."
    }
  ],
  "knowledge_sources": [],
  "evidence_ids": ["ev_1a2b3c4d5e6f"],
  "llm_used": false,
  "provider": "deterministic",
  "model": null,
  "warnings": [],
  "created_at": "2026-01-01T10:03:00Z"
}
```

Rules:

- `status` is `completed`. The pipeline always terminates with a report, even
  when the LLM provider fails.
- `confidence` is a self-reported estimate between `0` and `1`. It is **not** a
  calibrated probability and must be presented as an estimate in the UI.
- `llm_used` is `false` when the deterministic fallback produced the report.
  `provider` is then `deterministic` and `model` is `null`.
- Evidence IDs returned by the provider are verified against the collected
  evidence. Unknown IDs are removed, and a hypothesis that cites no valid
  evidence is discarded and reported in `warnings`.
- `proposed_remediations` are proposals. They are never executed by this
  endpoint.

### 4.2 List investigations

```http
GET /api/v1/incidents/{incident_id}/investigations
```

Response `200`: `{"items": [investigation report], "total": <int>}`,
newest first.

### 4.3 Get investigation

```http
GET /api/v1/incidents/{incident_id}/investigations/{investigation_id}
```

Response `200`: investigation report. Unknown IDs return `404` with code
`INVESTIGATION_NOT_FOUND`.

---

## 5. Remediation

### 5.1 Remediation object

```json
{
  "id": "rem_abc123def456",
  "incident_id": "inc_9f1c2d3e4a5b",
  "action": "rollback_demo_deployment",
  "target_service": "payment-api",
  "parameters": {},
  "risk_level": "medium",
  "requires_human_approval": true,
  "status": "pending_approval",
  "rationale": "A deployment immediately preceded the incident.",
  "approved_by": null,
  "approved_at": null,
  "rejected_by": null,
  "rejected_at": null,
  "executed_at": null,
  "execution_result": null,
  "incident_status": "awaiting_approval",
  "created_at": "2026-01-01T10:04:00Z",
  "updated_at": "2026-01-01T10:04:00Z"
}
```

`incident_status` mirrors the status of the linked incident after the request,
so a client does not need a second request to refresh it.

### 5.2 Allowed actions

Only these actions are accepted. Anything else is rejected with `422` and code
`UNSUPPORTED_ACTION`.

| Action | Required parameters | Optional parameters | Risk | Effect |
|---|---|---|---|---|
| `rollback_demo_deployment` | none | `version` (string) | medium | Rolls the simulator back to the previous demo release. |
| `restart_demo_service` | none | none | medium | Restarts the demo payment service. |
| `scale_demo_instances` | `instances` (int 1..10) | none | low | Changes the demo instance count. |
| `clear_demo_cache` | none | none | low | Clears demo cache entries. |

The allowlist is enforced on the server. The backend never executes shell
commands and never touches systems outside the simulator.

### 5.3 Create remediation proposal

```http
POST /api/v1/incidents/{incident_id}/remediations
```

Request:

```json
{
  "action": "rollback_demo_deployment",
  "parameters": {},
  "rationale": "A deployment immediately preceded the incident."
}
```

Response `201`: remediation object with status `pending_approval`.

Server-side validation:

- The incident must exist (`404`).
- The incident must not already be `resolved` (`409`).
- The action must be on the allowlist (`422`).
- Parameters must match the allowlist definition (`422`).

### 5.4 Approve remediation

```http
POST /api/v1/remediations/{remediation_id}/approve
X-Operator-Id: operator@example.com
```

Request (optional body):

```json
{ "note": "Confirmed with on-call engineer." }
```

Behaviour:

1. Requires `X-Operator-Id` (`422` when missing).
2. The remediation must exist (`404`) and be in status `pending_approval`
   (`409` otherwise). Approval state supplied by the client is ignored.
3. Status becomes `approved`, `approved_by` and `approved_at` are recorded.
4. The approved action is dispatched to the simulator through the allowlisted
   dispatcher.
5. The backend re-checks the simulator health after the dispatch
   (post-remediation verification).
6. Status becomes `success` or `failed`; `executed_at` and `execution_result`
   are recorded.

**Post-remediation verification.** The incident is moved to `resolved` only
when the action was applied **and** the post-remediation health check reports
a healthy service. `execution_result` carries the verification outcome:

```json
{
  "outcome": "success",
  "message": "Restarted payment-api and restored healthy baseline",
  "details": { "restarted": true, "scenario": "normal" },
  "simulator_status": "success",
  "service_healthy": true,
  "service_health_status": "ok",
  "verification_passed": true
}
```

If the action was applied but the service is still unhealthy, the remediation
keeps status `success` (the action was applied), `verification_passed` is
`false`, `verification_message` explains the situation, and the incident stays
open in `awaiting_approval`. The backend never claims a recovery it did not
verify.

Response `200`: the remediation object after execution, including
`execution_result` and the updated incident status.

### 5.5 Reject remediation

```http
POST /api/v1/remediations/{remediation_id}/reject
X-Operator-Id: operator@example.com
```

Request (optional body):

```json
{ "note": "Not related to this incident." }
```

Status becomes `rejected`; `rejected_by` and `rejected_at` are recorded. No
action is dispatched. A remediation that is not `pending_approval` returns
`409`.

### 5.6 Execute an approved remediation

```http
POST /api/v1/remediations/{remediation_id}/execute
```

Only a remediation in status `approved` can be executed (`409` otherwise).
This endpoint exists for retry and manual re-run; `approve` already performs
the dispatch. Response `200`: remediation object.

### 5.7 List remediations

```http
GET /api/v1/incidents/{incident_id}/remediations
```

Response `200`: `{"items": [remediation object], "total": <int>}`.

---

## 6. Simulator integration

The simulator is an independent FastAPI service. The backend reaches it with
`SIMULATOR_BASE_URL` (for example `http://simulator:8001` inside Docker
Compose, `http://127.0.0.1:8001` locally).

### 6.1 Simulator endpoints the backend calls

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Health probe. |
| `GET` | `/internal/evidence?scenario_id=<id>` | Evidence produced by the current or given scenario. |
| `GET` | `/internal/deployments` | Recent deployment and configuration events. |
| `POST` | `/internal/remediations` | Execute an allowlisted simulated remediation. |

`GET /internal/evidence` response:

```json
{
  "scenario_id": "database_failure",
  "items": [
    {
      "id": "sim_ev_1",
      "type": "log",
      "source": "payment-api",
      "timestamp": "2026-01-01T10:00:00Z",
      "summary": "Database connection timeout",
      "details": { "level": "error" }
    }
  ]
}
```

The backend accepts `items` or `evidence` as the list key and tolerates
missing optional fields (`id`, `details`, `timestamp`, `summary`). The
backend assigns its own `ev_` identifiers and never trusts simulator
identifiers.

`POST /internal/remediations` request:

```json
{
  "action": "rollback_demo_deployment",
  "parameters": {},
  "incident_id": "inc_9f1c2d3e4a5b",
  "remediation_id": "rem_abc123def456"
}
```

Response `200`:

```json
{
  "status": "success",
  "message": "Rolled back payment-api to v2.3.0",
  "details": { "version": "v2.3.0" }
}
```

The backend treats any non-2xx response or transport error as a failed
execution and records it. It never retries with a different action.

**Required simulator behaviour for the allowlisted actions.** The simulator
must implement `POST /internal/remediations` and apply the action to its
simulated state:

| `action` | Expected simulator behaviour |
|---|---|
| `rollback_demo_deployment` | Move the service back to the previous stable release (simulator version `v2.4.0`). `parameters.version` may request a specific version. |
| `restart_demo_service` | Reset the simulated service to a healthy baseline and clear the degraded scenario state. |
| `scale_demo_instances` | Set the simulated instance count to `parameters.instances` (1..10). |
| `clear_demo_cache` | Clear the simulated cache entries. |

A successful response must use `"status": "success"` (also accepted:
`ok`, `applied`, `completed`, `succeeded`). Any other status is recorded as a
failed execution.

Until this endpoint exists, approving a remediation records a failed execution
with a clear message and leaves the incident open. This is deliberate: the
backend never fabricates a successful remediation.

### 6.2 Demo control endpoints (simulator only)

These remain simulator concerns and are **not** proxied by the backend:

```http
POST /demo/scenarios/{scenario_id}/trigger
POST /demo/scenarios/reset
GET  /demo/scenarios
```

Suggested scenarios: `normal`, `payment_timeout`, `database_failure`,
`bad_deployment`.

### 6.3 Docker service names

| Service | Container name | Internal URL |
|---|---|---|
| PostgreSQL | `incidentiq-db` | `postgresql+psycopg://incidentiq:incidentiq@db:5432/incidentiq` |
| Backend | `incidentiq-backend` | `http://backend:8000` |
| Simulator | `incidentiq-simulator` | `http://simulator:8001` |
| Frontend | `incidentiq-frontend` | `http://frontend:5173` |

Compose service names are `db`, `backend`, `simulator`, `frontend`.

---

## 7. Error format

```json
{
  "error": {
    "code": "INCIDENT_NOT_FOUND",
    "message": "Incident does not exist",
    "request_id": "req_123",
    "details": {}
  }
}
```

`details` is optional and omitted when empty.

| Code | HTTP | Meaning |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Request body or query failed validation. |
| `UNAUTHORIZED` | 401 | Missing or invalid `X-API-Key`. |
| `FORBIDDEN` | 403 | Operator is not allowed to perform the action. |
| `NOT_FOUND` | 404 | Generic missing resource. |
| `INCIDENT_NOT_FOUND` | 404 | Unknown incident. |
| `EVIDENCE_NOT_FOUND` | 404 | Unknown evidence. |
| `INVESTIGATION_NOT_FOUND` | 404 | Unknown investigation. |
| `REMEDIATION_NOT_FOUND` | 404 | Unknown remediation. |
| `CONFLICT` | 409 | Invalid state transition. |
| `UNSUPPORTED_ACTION` | 422 | Action is not on the allowlist. |
| `INVALID_PARAMETERS` | 422 | Action parameters failed validation. |
| `SIMULATOR_UNAVAILABLE` | 503 | Simulator could not be reached. |
| `INTERNAL_ERROR` | 500 | Unexpected server error. |

---

## 8. Contract rules

- The backend owns this contract.
- Frontend and simulator agents must not invent incompatible schemas.
- Keep response field names consistent.
- Validate all requests and responses.
- Update this document before making breaking API changes.
- Additive fields are allowed; renaming or removing fields is breaking.

## 9. Change log

- **v1.2** — Canonical contract for Agent 3 implementation. Enum casing fixed
  to lowercase. Added evidence collection endpoint, investigation report
  object and endpoints, remediation lifecycle details, operator identity
  header, simulator evidence/remediation request shapes, Docker service names.
- **v1.0** — Initial planning contract.
