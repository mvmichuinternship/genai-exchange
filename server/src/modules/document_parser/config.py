# src/modules/document_parser/config.py
import os
from pydantic import BaseSettings
from typing import List

class DocumentProcessorSettings(BaseSettings):
    """Configuration settings for document processor"""
    
    # Processing settings
    MAX_WORKERS: int = 4
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_FILE_SIZE_MB: int = 50
    
    # Supported file types
    SUPPORTED_EXTENSIONS: List[str] = [".pdf", ".docx", ".doc", ".xml", ".txt"]
    
    # PDF processing
    PDF_DEFAULT_METHOD: str = "pymupdf"  # or "pypdf2"
    
    # Storage settings
    TEMP_DIR: str = "/tmp"
    PERSIST_STATUS: bool = True
    STATUS_CLEANUP_HOURS: int = 24
    
    # Embedding settings (optional)
    ENABLE_EMBEDDINGS: bool = False
    EMBEDDING_PROVIDER: str = "sentence_transformers"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_BATCH_SIZE: int = 32
    
    # Vector store settings (optional)
    VECTOR_STORE_TYPE: str = "chroma"
    VECTOR_STORE_PATH: str = "./chroma_db"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_prefix = "DOC_PROCESSOR_"

# Global settings instance
settings = DocumentProcessorSettings()

# File size validation
def validate_file_size(file_size_bytes: int) -> bool:
    """Validate if file size is within limits"""
    max_size_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    return file_size_bytes <= max_size_bytes

def get_supported_mime_types() -> dict:
    """Get mapping of file extensions to MIME types"""
    return {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.xml': 'text/xml',
        '.txt': 'text/plain'
    }