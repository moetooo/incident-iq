import threading
import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from app.core.config import settings
from app.core.logging import logger
from app.core.errors import UnsupportedActionError, InvalidParametersError
from app.models.scenario import ScenarioId, ScenarioStatus
from app.models.evidence import EvidenceItem, EvidenceType
from app.models.deployment import DeploymentItem
from app.models.metrics import SimulatorMetrics
from app.models.payment import PaymentRequest, PaymentResponse

ALLOWED_REMEDIATION_ACTIONS = frozenset({
    "rollback_demo_deployment",
    "restart_demo_service",
    "scale_demo_instances",
    "clear_demo_cache"
})


class SimulatorStateService:
    """Manages simulator state, scenarios, telemetry, and deterministic evidence generation."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._current_scenario: ScenarioId = ScenarioId.NORMAL
        self._activated_at: str = datetime.now(timezone.utc).isoformat()
        self._current_version: str = settings.SIMULATOR_VERSION
        
        # Telemetry storage
        self._evidence: List[EvidenceItem] = []
        self._deployments: List[DeploymentItem] = []
        
        # Runtime request metrics
        self._request_count: int = 0
        self._error_count: int = 0

        # Simulated operational resources
        self._instance_count: int = 2
        self._cache_cleared_at: Optional[str] = None
        
        # Initialize default healthy state
        self._initialize_healthy_state()

    def _initialize_healthy_state(self) -> None:
        """Sets the baseline healthy state and telemetry."""
        now_iso = datetime.now(timezone.utc).isoformat()
        self._current_scenario = ScenarioId.NORMAL
        self._activated_at = now_iso
        self._current_version = settings.SIMULATOR_VERSION
        self._request_count = 1250
        self._error_count = 0
        self._instance_count = 2
        self._cache_cleared_at = None

        self._deployments = [
            DeploymentItem(
                id="dep_v240_stable",
                version=settings.SIMULATOR_VERSION,
                service=settings.SERVICE_NAME,
                deployed_at="2026-10-20T10:00:00Z",
                deployed_by="ci/cd-pipeline",
                status="active",
                commit_sha="c7b1e42",
                changelog="Stable baseline release with resilient payment retries"
            )
        ]

        self._evidence = self._create_healthy_evidence(now_iso)

    def _create_healthy_evidence(self, timestamp_iso: str) -> List[EvidenceItem]:
        """Generates evidence items for normal healthy state."""
        return [
            EvidenceItem(
                id="ev_normal_state",
                type=EvidenceType.STATE.value,
                source=settings.SERVICE_NAME,
                timestamp=timestamp_iso,
                summary="Service payment-api is fully healthy and operational",
                details={
                    "status": "UP",
                    "scenario": ScenarioId.NORMAL.value,
                    "version": settings.SIMULATOR_VERSION,
                    "checks": {
                        "database": "UP",
                        "payment_gateway": "UP",
                        "cache": "UP"
                    }
                }
            ),
            EvidenceItem(
                id="ev_normal_metrics",
                type=EvidenceType.METRIC.value,
                source=settings.SERVICE_NAME,
                timestamp=timestamp_iso,
                summary="Payment API metrics within normal operating limits",
                details={
                    "error_rate_pct": 0.0,
                    "p95_latency_ms": 45.0,
                    "avg_latency_ms": 32.0,
                    "active_db_connections": settings.DATABASE_NORMAL_CONNECTIONS,
                    "max_db_connections": settings.DATABASE_MAX_CONNECTIONS,
                    "db_pool_utilization_pct": 10.0
                }
            ),
            EvidenceItem(
                id="ev_normal_log",
                type=EvidenceType.LOG.value,
                source=settings.SERVICE_NAME,
                timestamp=timestamp_iso,
                summary="Payment transactions processed successfully",
                details={
                    "level": "INFO",
                    "request_id": "req_pay_healthy_001",
                    "message": "Payment captured successfully for customer cust_demo",
                    "http_status": 200,
                    "duration_ms": 34.2
                }
            )
        ]

    def _sync_deployment_statuses(self) -> None:
        """Synchronizes deployment record statuses with the active version."""
        for d in self._deployments:
            if d.version == self._current_version:
                d.status = "active"
            elif d.id == "dep_v241_faulty":
                d.status = "rolled_back"
            else:
                d.status = "superseded"

    def get_current_scenario(self) -> ScenarioId:
        with self._lock:
            return self._current_scenario

    def get_health_status(self) -> Dict[str, Any]:
        with self._lock:
            is_healthy = self._current_scenario == ScenarioId.NORMAL
            return {
                "status": "ok" if is_healthy else "degraded",
                "service": settings.SERVICE_NAME,
                "scenario": self._current_scenario.value,
                "version": self._current_version,
                "healthy": is_healthy,
                "active_since": self._activated_at
            }

    def trigger_scenario(self, scenario_id: ScenarioId) -> ScenarioStatus:
        """Triggers an incident scenario and generates deterministic evidence."""
        with self._lock:
            now_iso = datetime.now(timezone.utc).isoformat()
            self._current_scenario = scenario_id
            self._activated_at = now_iso

            if scenario_id == ScenarioId.NORMAL:
                self._current_version = settings.SIMULATOR_VERSION
                self._error_count = 0
                self._evidence = self._create_healthy_evidence(now_iso)
                self._sync_deployment_statuses()
                return ScenarioStatus(
                    scenario_id=scenario_id,
                    title="Healthy Payment API",
                    description="Standard normal payment processing state",
                    is_healthy=True,
                    status="active",
                    activated_at=now_iso,
                    details={"version": self._current_version}
                )

            elif scenario_id == ScenarioId.DATABASE_FAILURE:
                self._current_version = settings.SIMULATOR_VERSION
                self._error_count = 48
                self._sync_deployment_statuses()
                self._evidence = [
                    EvidenceItem(
                        id="ev_db_pool_exhausted",
                        type=EvidenceType.METRIC.value,
                        source=settings.SERVICE_NAME,
                        timestamp=now_iso,
                        summary="PostgreSQL connection pool exhausted: 50/50 connections active (100% saturation)",
                        details={
                            "active_db_connections": settings.DATABASE_MAX_CONNECTIONS,
                            "max_db_connections": settings.DATABASE_MAX_CONNECTIONS,
                            "db_pool_utilization_pct": 100.0,
                            "waiting_threads": 42,
                            "pool_name": "PaymentHikariCP"
                        }
                    ),
                    EvidenceItem(
                        id="ev_db_timeout_log",
                        type=EvidenceType.LOG.value,
                        source=settings.SERVICE_NAME,
                        timestamp=now_iso,
                        summary="ConnectionCheckoutTimeoutException: Timeout waiting for idle connection from pool after 30000ms",
                        details={
                            "level": "ERROR",
                            "request_id": "req_db_timeout_104",
                            "exception": "org.postgresql.util.PSQLException: Connection checkout timeout",
                            "stack_trace": "at com.zaxxer.hikari.pool.HikariPool.getConnection(HikariPool.java:197)\n at com.incidentiq.payment.repository.PaymentRepository.save(PaymentRepository.java:45)",
                            "http_status": 503
                        }
                    ),
                    EvidenceItem(
                        id="ev_db_fatal_log",
                        type=EvidenceType.LOG.value,
                        source=settings.SERVICE_NAME,
                        timestamp=now_iso,
                        summary="OperationalError: FATAL: remaining connection slots are reserved for non-replication superuser connections",
                        details={
                            "level": "ERROR",
                            "request_id": "req_db_fatal_105",
                            "source_ip": "10.0.4.12",
                            "http_status": 500
                        }
                    ),
                    EvidenceItem(
                        id="ev_db_state_degraded",
                        type=EvidenceType.STATE.value,
                        source=settings.SERVICE_NAME,
                        timestamp=now_iso,
                        summary="Database health probe failed: connection pool saturated",
                        details={
                            "status": "DOWN",
                            "subsystem": "PostgreSQL",
                            "last_successful_ping": "5 minutes ago"
                        }
                    )
                ]
                return ScenarioStatus(
                    scenario_id=scenario_id,
                    title="Database Connection Pool Exhaustion",
                    description="Database connection pool saturated (50/50) resulting in connection checkout timeouts and payment transaction failures",
                    is_healthy=False,
                    status="active",
                    activated_at=now_iso,
                    details={"pool_utilization_pct": 100.0}
                )

            elif scenario_id == ScenarioId.PAYMENT_TIMEOUT:
                self._current_version = settings.SIMULATOR_VERSION
                self._error_count = 35
                self._sync_deployment_statuses()
                self._evidence = [
                    EvidenceItem(
                        id="ev_payment_latency_metric",
                        type=EvidenceType.METRIC.value,
                        source=settings.SERVICE_NAME,
                        timestamp=now_iso,
                        summary="Payment request p95 latency spiked to 5200ms exceeding 2000ms SLA",
                        details={
                            "p95_latency_ms": 5200.0,
                            "p99_latency_ms": 6800.0,
                            "avg_latency_ms": 4850.0,
                            "sla_threshold_ms": 2000.0,
                            "timeout_rate_pct": 65.0
                        }
                    ),
                    EvidenceItem(
                        id="ev_gateway_timeout_log",
                        type=EvidenceType.LOG.value,
                        source=settings.SERVICE_NAME,
                        timestamp=now_iso,
                        summary="GatewayTimeout: Downstream payment processor banking-gateway.internal timed out after 5000ms",
                        details={
                            "level": "ERROR",
                            "request_id": "req_pay_timeout_981",
                            "downstream_service": "banking-gateway.internal",
                            "configured_timeout_ms": 5000,
                            "http_status": 504
                        }
                    ),
                    EvidenceItem(
                        id="ev_deadline_exceeded_log",
                        type=EvidenceType.LOG.value,
                        source=settings.SERVICE_NAME,
                        timestamp=now_iso,
                        summary="ClientRequestTimeout: Payment processing deadline exceeded for correlation_id req_pay_timeout_981",
                        details={
                            "level": "WARN",
                            "request_id": "req_pay_timeout_982",
                            "message": "Transaction aborted due to gateway timeout",
                            "http_status": 504
                        }
                    ),
                    EvidenceItem(
                        id="ev_payment_timeout_state",
                        type=EvidenceType.STATE.value,
                        source=settings.SERVICE_NAME,
                        timestamp=now_iso,
                        summary="Service payment-api is degraded: SLA violation on payment processing latency",
                        details={
                            "status": "DEGRADED",
                            "subsystem": "downstream-banking-gateway",
                            "active_timeouts": 35
                        }
                    )
                ]
                return ScenarioStatus(
                    scenario_id=scenario_id,
                    title="Payment Gateway Timeout",
                    description="Elevated latency and request timeouts communicating with downstream banking processor",
                    is_healthy=False,
                    status="active",
                    activated_at=now_iso,
                    details={"p95_latency_ms": 5200.0}
                )

            elif scenario_id == ScenarioId.BAD_DEPLOYMENT:
                self._current_version = settings.BAD_DEPLOYMENT_VERSION
                self._error_count = 62
                
                bad_deploy = next(
                    (d for d in self._deployments if d.id == "dep_v241_faulty"),
                    None
                )
                if bad_deploy is None:
                    bad_deploy = DeploymentItem(
                        id="dep_v241_faulty",
                        version=settings.BAD_DEPLOYMENT_VERSION,
                        service=settings.SERVICE_NAME,
                        deployed_at=now_iso,
                        deployed_by="ci/cd-pipeline",
                        status="active",
                        commit_sha="8f92a11",
                        changelog="Release v2.4.1: Refactored payment token validator and security header parser"
                    )
                    self._deployments.insert(0, bad_deploy)
                self._sync_deployment_statuses()

                self._evidence = [
                    EvidenceItem(
                        id="ev_bad_deploy_event",
                        type=EvidenceType.DEPLOYMENT.value,
                        source=settings.SERVICE_NAME,
                        timestamp=now_iso,
                        summary=f"Deployment {settings.BAD_DEPLOYMENT_VERSION} released by ci/cd-pipeline",
                        details={
                            "deployment_id": bad_deploy.id,
                            "version": settings.BAD_DEPLOYMENT_VERSION,
                            "commit_sha": bad_deploy.commit_sha,
                            "changelog": bad_deploy.changelog
                        }
                    ),
                    EvidenceItem(
                        id="ev_bad_deploy_error_metric",
                        type=EvidenceType.METRIC.value,
                        source=settings.SERVICE_NAME,
                        timestamp=now_iso,
                        summary=f"HTTP 500 error rate surged to 42.0% immediately following {settings.BAD_DEPLOYMENT_VERSION} rollout",
                        details={
                            "error_rate_pct": 42.0,
                            "baseline_error_rate_pct": 0.0,
                            "affected_endpoints": ["/payments"],
                            "http_500_count": 62
                        }
                    ),
                    EvidenceItem(
                        id="ev_bad_deploy_nullpointer_log",
                        type=EvidenceType.LOG.value,
                        source=settings.SERVICE_NAME,
                        timestamp=now_iso,
                        summary="NullPointerException in TokenValidationFilter during payment authorization",
                        details={
                            "level": "ERROR",
                            "request_id": "req_deploy_err_312",
                            "exception": "java.lang.NullPointerException: Cannot invoke 'String.trim()' because 'token' is null",
                            "stack_trace": "at com.incidentiq.payment.security.TokenValidationFilter.doFilter(TokenValidationFilter.java:84)\n at jakarta.servlet.FilterChain.doFilter(FilterChain.java:134)",
                            "http_status": 500
                        }
                    ),
                    EvidenceItem(
                        id="ev_bad_deploy_state",
                        type=EvidenceType.STATE.value,
                        source=settings.SERVICE_NAME,
                        timestamp=now_iso,
                        summary=f"Service running unstable build {settings.BAD_DEPLOYMENT_VERSION}",
                        details={
                            "status": "UNSTABLE",
                            "active_version": settings.BAD_DEPLOYMENT_VERSION,
                            "previous_version": settings.SIMULATOR_VERSION
                        }
                    )
                ]
                return ScenarioStatus(
                    scenario_id=scenario_id,
                    title="Defective Deployment Rollout",
                    description=f"Recent deployment of {settings.BAD_DEPLOYMENT_VERSION} introduces unhandled NullPointerException causing elevated 500 errors",
                    is_healthy=False,
                    status="active",
                    activated_at=now_iso,
                    details={"version": settings.BAD_DEPLOYMENT_VERSION, "error_rate_pct": 42.0}
                )

            raise ValueError(f"Unknown scenario_id: {scenario_id}")

    def reset(self) -> None:
        """Resets the simulator to a known healthy state."""
        with self._lock:
            logger.info("Resetting simulator to healthy baseline state")
            self._initialize_healthy_state()

    def get_evidence(
        self,
        scenario_id: Optional[str] = None,
        evidence_type: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[EvidenceItem]:
        """Returns filtered evidence items matching criteria."""
        with self._lock:
            items = list(self._evidence)
            if evidence_type:
                items = [it for it in items if it.type == evidence_type]
            if limit and limit > 0:
                items = items[:limit]
            return items

    def get_deployments(self) -> List[DeploymentItem]:
        with self._lock:
            return list(self._deployments)

    def get_metrics(self) -> SimulatorMetrics:
        """Computes current snapshot of simulator metrics."""
        with self._lock:
            scenario = self._current_scenario
            is_healthy = scenario == ScenarioId.NORMAL

            if scenario == ScenarioId.NORMAL:
                return SimulatorMetrics(
                    service=settings.SERVICE_NAME,
                    scenario=scenario.value,
                    is_healthy=True,
                    request_count=self._request_count,
                    error_count=self._error_count,
                    error_rate_pct=0.0,
                    p95_latency_ms=45.0,
                    avg_latency_ms=32.0,
                    active_db_connections=settings.DATABASE_NORMAL_CONNECTIONS,
                    max_db_connections=settings.DATABASE_MAX_CONNECTIONS,
                    db_pool_utilization_pct=10.0
                )
            elif scenario == ScenarioId.DATABASE_FAILURE:
                return SimulatorMetrics(
                    service=settings.SERVICE_NAME,
                    scenario=scenario.value,
                    is_healthy=False,
                    request_count=self._request_count,
                    error_count=self._error_count,
                    error_rate_pct=85.0,
                    p95_latency_ms=850.0,
                    avg_latency_ms=620.0,
                    active_db_connections=settings.DATABASE_MAX_CONNECTIONS,
                    max_db_connections=settings.DATABASE_MAX_CONNECTIONS,
                    db_pool_utilization_pct=100.0
                )
            elif scenario == ScenarioId.PAYMENT_TIMEOUT:
                return SimulatorMetrics(
                    service=settings.SERVICE_NAME,
                    scenario=scenario.value,
                    is_healthy=False,
                    request_count=self._request_count,
                    error_count=self._error_count,
                    error_rate_pct=65.0,
                    p95_latency_ms=5200.0,
                    avg_latency_ms=4850.0,
                    active_db_connections=12,
                    max_db_connections=settings.DATABASE_MAX_CONNECTIONS,
                    db_pool_utilization_pct=24.0
                )
            elif scenario == ScenarioId.BAD_DEPLOYMENT:
                return SimulatorMetrics(
                    service=settings.SERVICE_NAME,
                    scenario=scenario.value,
                    is_healthy=False,
                    request_count=self._request_count,
                    error_count=self._error_count,
                    error_rate_pct=42.0,
                    p95_latency_ms=65.0,
                    avg_latency_ms=48.0,
                    active_db_connections=8,
                    max_db_connections=settings.DATABASE_MAX_CONNECTIONS,
                    db_pool_utilization_pct=16.0
                )
            
            return SimulatorMetrics(
                service=settings.SERVICE_NAME,
                scenario=scenario.value,
                is_healthy=is_healthy,
                request_count=self._request_count,
                error_count=self._error_count,
                error_rate_pct=0.0,
                p95_latency_ms=45.0,
                avg_latency_ms=32.0,
                active_db_connections=settings.DATABASE_NORMAL_CONNECTIONS,
                max_db_connections=settings.DATABASE_MAX_CONNECTIONS,
                db_pool_utilization_pct=10.0
            )

    def process_payment(self, request: PaymentRequest) -> PaymentResponse:
        """Simulates payment transaction logic based on current active scenario."""
        with self._lock:
            self._request_count += 1
            scenario = self._current_scenario
            
        req_id = f"tx_{uuid.uuid4().hex[:10]}"

        if scenario == ScenarioId.NORMAL:
            latency = request.simulate_delay_ms or 35.0
            return PaymentResponse(
                transaction_id=req_id,
                status="approved",
                amount=request.amount,
                currency=request.currency,
                latency_ms=float(latency),
                message="Payment processed successfully"
            )

        elif scenario == ScenarioId.DATABASE_FAILURE:
            with self._lock:
                self._error_count += 1
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503,
                detail="Database connection pool exhausted: could not acquire connection"
            )

        elif scenario == ScenarioId.PAYMENT_TIMEOUT:
            with self._lock:
                self._error_count += 1
            from fastapi import HTTPException
            raise HTTPException(
                status_code=504,
                detail="Downstream payment gateway timed out after 5000ms"
            )

        elif scenario == ScenarioId.BAD_DEPLOYMENT:
            with self._lock:
                self._error_count += 1
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail="InternalServerError: NullPointerException in TokenValidationFilter"
            )

        return PaymentResponse(
            transaction_id=req_id,
            status="approved",
            amount=request.amount,
            currency=request.currency,
            latency_ms=35.0,
            message="Payment completed"
        )

    def get_instance_count(self) -> int:
        with self._lock:
            return self._instance_count

    def get_cache_cleared_at(self) -> Optional[str]:
        with self._lock:
            return self._cache_cleared_at

    def execute_remediation(self, action: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Executes an allowlisted simulated remediation action against current simulator state."""
        params = dict(parameters or {})

        if action not in ALLOWED_REMEDIATION_ACTIONS:
            raise UnsupportedActionError(
                action=action,
                allowed_actions=list(ALLOWED_REMEDIATION_ACTIONS)
            )

        if action == "rollback_demo_deployment":
            if "version" in params:
                val = params["version"]
                if not isinstance(val, str) or not val.strip():
                    raise InvalidParametersError(
                        f"Parameter 'version' of action '{action}' must be a non-empty string",
                        details={"action": action, "parameter": "version"}
                    )
                target_version = val.strip()
            else:
                target_version = settings.SIMULATOR_VERSION

            if params.get("simulate_failure") is True:
                return {
                    "status": "failed",
                    "message": f"Simulated rollback failure for {settings.SERVICE_NAME}",
                    "details": {"error": "Deployment rollback hook timed out"}
                }

            with self._lock:
                now_iso = datetime.now(timezone.utc).isoformat()
                self._current_version = target_version

                # Update deployment statuses
                for d in self._deployments:
                    if d.id == "dep_v241_faulty":
                        d.status = "rolled_back"
                    elif d.version == target_version:
                        d.status = "active"
                    else:
                        d.status = "superseded"

                # If target version wasn't recorded, add it
                if not any(d.version == target_version for d in self._deployments):
                    self._deployments.insert(
                        0,
                        DeploymentItem(
                            id=f"dep_{target_version.replace('.', '')}_restored",
                            version=target_version,
                            service=settings.SERVICE_NAME,
                            deployed_at=now_iso,
                            deployed_by="remediation-controller",
                            status="active",
                            commit_sha="c7b1e42",
                            changelog=f"Restored release {target_version} via remediation"
                        )
                    )

                self._current_scenario = ScenarioId.NORMAL
                self._error_count = 0
                self._activated_at = now_iso
                self._evidence = self._create_healthy_evidence(now_iso)

                logger.info(
                    f"Remediation executed: {action} -> version {target_version}",
                    extra={"extra_data": {"action": action, "target_version": target_version}}
                )

                return {
                    "status": "success",
                    "message": f"Rolled back {settings.SERVICE_NAME} to {target_version}",
                    "details": {"version": target_version}
                }

        elif action == "restart_demo_service":
            if params.get("simulate_failure") is True:
                return {
                    "status": "failed",
                    "message": f"Simulated restart failure for {settings.SERVICE_NAME}",
                    "details": {"error": "Process supervisor failed to restart service"}
                }

            with self._lock:
                now_iso = datetime.now(timezone.utc).isoformat()
                self._current_scenario = ScenarioId.NORMAL
                self._current_version = settings.SIMULATOR_VERSION
                self._error_count = 0
                self._activated_at = now_iso
                self._sync_deployment_statuses()
                self._evidence = self._create_healthy_evidence(now_iso)

                logger.info(
                    f"Remediation executed: {action} -> healthy baseline",
                    extra={"extra_data": {"action": action}}
                )

                return {
                    "status": "success",
                    "message": f"Restarted {settings.SERVICE_NAME} and restored healthy baseline",
                    "details": {"restarted": True, "scenario": "normal"}
                }

        elif action == "scale_demo_instances":
            if "instances" not in params:
                raise InvalidParametersError(
                    f"Missing required parameter 'instances' for action '{action}'",
                    details={"action": action, "missing_parameters": ["instances"]}
                )

            val = params["instances"]
            if isinstance(val, bool) or not isinstance(val, int):
                raise InvalidParametersError(
                    f"Parameter 'instances' of action '{action}' must be an integer",
                    details={"action": action, "parameter": "instances"}
                )

            if not (1 <= val <= 10):
                raise InvalidParametersError(
                    f"Parameter 'instances' of action '{action}' must be between 1 and 10",
                    details={"action": action, "parameter": "instances"}
                )

            if params.get("simulate_failure") is True:
                return {
                    "status": "failed",
                    "message": f"Simulated scaling failure for {settings.SERVICE_NAME}",
                    "details": {"error": "Resource quota exceeded for instance scaling"}
                }

            with self._lock:
                self._instance_count = val

                logger.info(
                    f"Remediation executed: {action} -> {val} instances",
                    extra={"extra_data": {"action": action, "instances": val}}
                )

                return {
                    "status": "success",
                    "message": f"Scaled {settings.SERVICE_NAME} to {val} instances",
                    "details": {"instances": val}
                }

        elif action == "clear_demo_cache":
            if params.get("simulate_failure") is True:
                return {
                    "status": "failed",
                    "message": f"Simulated cache clear failure for {settings.SERVICE_NAME}",
                    "details": {"error": "Cache cluster unreachable"}
                }

            with self._lock:
                now_iso = datetime.now(timezone.utc).isoformat()
                self._cache_cleared_at = now_iso

                logger.info(
                    f"Remediation executed: {action}",
                    extra={"extra_data": {"action": action}}
                )

                return {
                    "status": "success",
                    "message": f"Cleared cache for {settings.SERVICE_NAME}",
                    "details": {"cleared": True}
                }


# Singleton instance for the simulator service
simulator_state_service = SimulatorStateService()
