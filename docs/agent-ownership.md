# Agent Ownership and Working Boundaries

This document defines the strict ownership domains, boundaries, interface contracts, git commit attribution, and handoff protocols for the three autonomous AI agents developing **IncidentIQ**.

---

## 1. Agent Matrix and Directory Ownership

| Agent | Technology Stack | Primary Directory | Scope & Domain |
|---|---|---|---|
| **Agent 1: Antigravity Frontend** | React, Vite, JavaScript, Tailwind CSS | `frontend/` | UI/UX, incident dashboard, evidence timelines, RCA views, approval workflows, API client integration |
| **Agent 2: Antigravity Simulator** | Python 3.11+, FastAPI, Pydantic | `simulator/` | Production simulator, chaos/failure injection engine, synthetic telemetry (logs, metrics, deployments), control/remediation targets |
| **Agent 3: Kilo Code Backend** | Python 3.11+, FastAPI, Pydantic, SQLAlchemy, PostgreSQL, Alembic | `backend/` | Core REST API, investigation orchestration, RCA evidence correlation, AI integration, human approval enforcement, database migrations, remediation dispatcher |

---

## 2. Boundaries and Permissions

### Strict Boundaries
1. **Directory Isolation**:
   - Agent 1 modifies **only** `frontend/`.
   - Agent 2 modifies **only** `simulator/`.
   - Agent 3 modifies **only** `backend/`.
2. **Shared Assets (`docs/`, `infra/`, root files)**:
   - Root configuration (`docker-compose.yml`, `.env.example`, `.gitignore`) and documentation (`docs/`) represent shared contracts.
   - Any modifications to endpoints, data models, or environment variables **must** be reflected in `docs/api-contract.md` and `docs/data-model.md`.
3. **No Cross-Directory Imports**:
   - `frontend/` must never import directly from `backend/` or `simulator/`. All communication happens via HTTP JSON APIs as specified in `docs/api-contract.md`.
   - `backend/` and `simulator/` are isolated microservices communicating over HTTP REST/JSON.

---

## 3. Git Commit and Agent Attribution Rules

Every agent must identify its work using its assigned agent ID.

### Agent identities
- Agent 1: Antigravity Frontend
- Agent 2: Antigravity Simulator
- Agent 3: Kilo Code Backend and Coordinator

### Commit message format
Use Conventional Commits with agent attribution:

`<type>(<scope>): <description> [Agent N]`

Examples:
- `feat(frontend): add incident dashboard [Agent 1]`
- `feat(simulator): add database failure scenario [Agent 2]`
- `feat(backend): implement incident API [Agent 3]`
- `test(backend): cover incident creation [Agent 3]`
- `fix(simulator): correct failure reset [Agent 2]`
- `docs(architecture): define service boundaries [Agent 3]`

Allowed types:
`feat`, `fix`, `test`, `refactor`, `docs`, `chore`, `build`, `ci`

### Git commit rules
1. Each agent commits only files within its ownership.
2. Never commit another agent's uncommitted changes.
3. Inspect `git status` and `git diff` before committing.
4. Stage specific files instead of blindly staging everything.
5. Never commit secrets, `.env` files, credentials, or generated artifacts.
6. Do not rewrite shared history or force-push without authorization.
7. Report the commit hash and tests executed after each commit.
8. Agent 3 coordinates merges and integration.

### Code comment rules
- Use comments to explain non-obvious decisions, constraints, and safety requirements.
- Do not add Agent 1, Agent 2, or Agent 3 to every code comment.
- Use agent attribution in comments only when ownership or a handoff needs clarification.

Example:
```python
# Agent 2: Deterministic scenario for testing database connection failures.
```

Prefer Git history for authorship and attribution. Comments should explain the code, not duplicate commit metadata.

### Handoff format
Each agent reports:
- Agent ID
- Summary of changes
- Files changed
- Commit hash
- Tests executed and actual results
- Known issues
- Integration requirements

---

## 5. Shared Contract Coordination

`docs/architecture.md`, `docs/api-contract.md` and `docs/data-model.md` are the
canonical contracts. Agent 3 owns them.

### 5.1 Change protocol
1. The owning agent never silently changes a shared contract. Agent 3 updates
   the canonical document first, then implements.
2. Every breaking change increments the contract version and adds a change log
   entry.
3. Additive fields are allowed without a version bump; renamed or removed
   fields are breaking.
4. A contract change is announced to Agent 1 and Agent 2 explicitly. Local
   copies of the documents inside `frontend/docs/`, `simulator/docs/` and
   `backend/docs/` are **not** updated automatically and must not be treated
   as authoritative.

### 5.2 Cross-component mismatch handling
- If Agent 1 or Agent 2 observes a mismatch with the canonical contract, the
  mismatch is reported to Agent 3 as a blocking integration issue. The agent
  does not change the contract unilaterally.
- If Agent 3 changes a contract while other agents are working, the change is
  communicated in the handoff report with the exact affected endpoints and
  fields.

### 5.3 Authority table

| Contract area | Authority | Consumers |
|---|---|---|
| API paths, methods, schemas | Agent 3 | Agent 1, Agent 2 |
| Incident / evidence / hypothesis / remediation models | Agent 3 | Agent 1, Agent 2 |
| Simulator evidence and remediation payloads | Agent 3 defines the shape, Agent 2 implements it | Agent 3 |
| Simulator scenario catalogue and demo controls | Agent 2 | Agent 1, Agent 3 |
| UI behaviour and layout | Agent 1 | Agent 3 |
| LLM provider, model and prompt | Agent 3 | Agent 1 (display only) |

### 5.4 Known coordination notes
- `docs/` and `.kilo/` are excluded by the root `.gitignore`. Contract updates
  are therefore local to this working copy and must be communicated
  explicitly until the ignore rule changes.
- The frontend must read the backend API base URL from `VITE_API_BASE_URL` and
  must never receive `GEMINI_API_KEY`.
