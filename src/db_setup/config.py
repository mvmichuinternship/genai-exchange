import os
from typing import Optional

class Settings:
    # Database Configuration
    DB_HOST: str = os.getenv('DB_HOST', 'localhost')
    DB_NAME: str = os.getenv('DB_NAME', 'testgen_db')
    DB_USER: str = os.getenv('DB_USER', 'testgen_user')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD', 'testgen_pass')
    DB_PORT: str = os.getenv('DB_PORT', '5432')

    DATABASE_URL: str = os.getenv(
        'DATABASE_URL',
        f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    )

    # API Configuration
    API_V2_PREFIX: str = "/api/v2"
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'

    # Server Configuration
    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = int(os.getenv('PORT', '8000'))

    # Database Pool Configuration
    DB_MIN_POOL_SIZE: int = int(os.getenv('DB_MIN_POOL_SIZE', '5'))
    DB_MAX_POOL_SIZE: int = int(os.getenv('DB_MAX_POOL_SIZE', '20'))

    # RAG Configuration
    RAG_ENABLED: bool = os.getenv('RAG_ENABLED', 'true').lower() == 'true'
    RAG_CONTEXT_SCOPE: str = os.getenv('RAG_CONTEXT_SCOPE', 'comprehensive')

    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    # Agent Configuration
    DEFAULT_AGENT: str = os.getenv('DEFAULT_AGENT', 'sequential_workflow')
    ANALYSIS_DEPTH: str = os.getenv('ANALYSIS_DEPTH', 'comprehensive')

settings = Settings()
