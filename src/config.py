import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Application
    app_name: str = "TestGen Backend"
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Database
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: str = os.getenv("DB_NAME", "testgen_db")
    db_user: str = os.getenv("DB_USER", "testgen_user")
    db_password: str = os.getenv("DB_PASSWORD", "")

    # Redis
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_password: Optional[str] = os.getenv("REDIS_PASSWORD")

    # Google Cloud
    gcp_project_id: str = os.getenv("GCP_PROJECT_ID", "")
    cloud_sql_connection_name: Optional[str] = os.getenv("CLOUD_SQL_CONNECTION_NAME")

    @property
    def database_url(self) -> str:
        if self.environment == "production" and self.cloud_sql_connection_name:
            return f"postgresql://{self.db_user}:{self.db_password}@/{self.db_name}?host=/cloudsql/{self.cloud_sql_connection_name}"
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
