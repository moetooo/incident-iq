from pydantic import BaseModel, Field


class SimulatorMetrics(BaseModel):
    service: str = "payment-api"
    scenario: str
    is_healthy: bool
    request_count: int = Field(default=0, description="Total payment requests processed")
    error_count: int = Field(default=0, description="Failed payment requests")
    error_rate_pct: float = Field(default=0.0, description="Percentage of requests returning errors")
    p95_latency_ms: float = Field(default=45.0, description="95th percentile latency in ms")
    avg_latency_ms: float = Field(default=35.0, description="Average latency in ms")
    active_db_connections: int = Field(default=5, description="Currently checked out DB connections")
    max_db_connections: int = Field(default=50, description="Max pool size")
    db_pool_utilization_pct: float = Field(default=10.0, description="Percentage of connection pool utilized")
