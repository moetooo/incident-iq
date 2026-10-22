from typing import List, Optional
from pydantic import BaseModel, Field


class DeploymentItem(BaseModel):
    id: str = Field(description="Unique deployment ID")
    version: str = Field(description="Service release version")
    service: str = Field(default="payment-api", description="Service name")
    deployed_at: str = Field(description="ISO 8601 UTC timestamp")
    deployed_by: str = Field(description="Operator or pipeline that triggered deploy")
    status: str = Field(description="Deployment status (active, rolled_back, failed)")
    commit_sha: str = Field(description="Git commit hash")
    changelog: str = Field(description="Summary of changes in this release")


class DeploymentListResponse(BaseModel):
    items: List[DeploymentItem]
    total: int
