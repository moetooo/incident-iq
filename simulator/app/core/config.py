from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class SimulatorSettings(BaseSettings):
    """Configuration settings for IncidentIQ Payment API Simulator."""
    
    SERVICE_NAME: str = "payment-api"
    SIMULATOR_HOST: str = "0.0.0.0"
    SIMULATOR_PORT: int = 8001
    SIMULATOR_ENV: str = "development"
    SIMULATOR_VERSION: str = "v2.4.0"
    BAD_DEPLOYMENT_VERSION: str = "v2.4.1"
    
    DATABASE_MAX_CONNECTIONS: int = 50
    DATABASE_NORMAL_CONNECTIONS: int = 5
    
    CORS_ORIGINS: List[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = SimulatorSettings()
