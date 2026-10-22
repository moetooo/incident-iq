# IncidentIQ Payment Service Simulator

A standalone FastAPI microservice that simulates a production payment service (`payment-api`). It generates deterministic telemetry (structured logs, metrics, deployment changes, and service health) for normal operations as well as failure scenarios designed for incident response and root-cause analysis (RCA) in the IncidentIQ platform.

## Features

- **Realistic Telemetry**: Structured JSON logging, timestamped metrics, deployment history, and health states.
- **Deterministic Scenarios**:
  1. `normal`: Healthy baseline operation (~35ms latency, 0% errors, 10% connection pool utilization).
  2. `database_failure`: PostgreSQL connection pool exhaustion (50/50 active connections, connection checkout timeouts, 503 errors).
  3. `payment_timeout`: Downstream banking gateway timeouts (p95 latency spikes to 5200ms, 504 Gateway Timeouts).
  4. `bad_deployment`: Faulty release rollout (`v2.4.1`) introducing unhandled NullPointerException with elevated 500 errors.
- **Reliable Reset**: Restores healthy baseline state and baseline deployment (`v2.4.0`) deterministically.
- **Contract Conforming**: Fully compatible with `docs/api-contract.md` (Sections 1, 6, 8, 9).

## API Endpoints

### Health & Status
- `GET /health`: Returns service health status, scenario, version, and uptime metadata.

### Demo Scenarios
- `GET /demo/scenarios`: Lists available scenarios and which one is active.
- `POST /demo/scenarios/{scenario_id}/trigger`: Activates a scenario (`normal`, `database_failure`, `payment_timeout`, `bad_deployment`).
- `POST /demo/scenarios/reset`: Restores the simulator to healthy baseline (`normal`).

### Telemetry & Internal
- `GET /internal/evidence`: Returns generated evidence items (`log`, `metric`, `deployment`, `state`) with stable IDs for backend RCA referencing.
- `GET /internal/deployments`: Returns deployment history including commit SHA and changelogs.
- `GET /internal/metrics`: Live metrics snapshot (latency, error rate, DB connection utilization).
- `POST /internal/remediations`: Executes allowlisted simulated remediation actions (`rollback_demo_deployment`, `restart_demo_service`, `scale_demo_instances`, `clear_demo_cache`).

### Simulated Payment Traffic
- `POST /payments`: Processes simulated payment requests reflecting active scenario conditions.

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run simulator server
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## Running Tests

```bash
python -m pytest tests -v
```
