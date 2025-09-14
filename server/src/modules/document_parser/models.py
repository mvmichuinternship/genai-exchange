from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum

class DocumentType(str, Enum):
    """Supported document types"""
    PDF = "pdf"
    DOCX = "docx"
    DOC = "doc"
    XML = "xml"
    TXT = "txt"
    XLSX = "xlsx"
    XLS = "xls"

class ProcessingStatus(str, Enum):
    """Document processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class DocumentMetadata(BaseModel):
    """Metadata for a document"""
    document_id: str
    source_type: DocumentType
    source_path: str = ""
    original_filename: Optional[str] = None
    file_size: Optional[int] = None
    upload_timestamp: Optional[datetime] = None
    batch_id: Optional[str] = None
    custom_metadata: Optional[Dict[str, Any]] = None

class ChunkMetadata(BaseModel):
    """Metadata for a text chunk"""
    chunk_index: int
    chunk_length: int
    token_count: int
    document_id: str
    source_type: DocumentType
    page_number: Optional[int] = None
    section_title: Optional[str] = None

class TextChunk(BaseModel):
    """A chunk of text with its metadata"""
    text: str
    metadata: ChunkMetadata
    embedding: Optional[List[float]] = None

class ProcessingResult(BaseModel):
    """Result of document processing"""
    status: ProcessingStatus
    document_id: str
    chunks_created: int = 0
    content_length: int = 0
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Optional[DocumentMetadata] = None

class SearchResult(BaseModel):
    """Search result from vector database"""
    text: str
    score: float
    metadata: Dict[str, Any]
    document_id: str
    chunk_index: int

class BatchProcessingResult(BaseModel):
    """Result of batch document processing"""
    batch_id: str
    total_documents: int
    successful: int
    failed: int
    processing_time: Optional[float] = None
    results: List[ProcessingResult]

class DocumentStatus(BaseModel):
    """Current status of a document being processed"""
    document_id: str
    status: ProcessingStatus
    progress: int = Field(ge=0, le=100, description="Progress percentage")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    current_step: Optional[str] = None

class UploadRequest(BaseModel):
    """Request model for document upload"""
    document_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    enable_embeddings: bool = True
    chunk_size: Optional[int] = Field(default=1000, ge=100, le=4000)
    chunk_overlap: Optional[int] = Field(default=200, ge=0, le=1000)

class SearchRequest(BaseModel):
    """Request model for document search"""
    query: str = Field(min_length=1, description="Search query")
    limit: int = Field(default=10, ge=1, le=100)
    document_id: Optional[str] = None
    file_type: Optional[DocumentType] = None
    similarity_threshold: Optional[float] = Field(default=0.7, ge=0.0, le=1.0)
    include_metadata: bool = True

class ServiceStats(BaseModel):
    """Service statistics"""
    total_documents: int
    completed: int
    processing: int
    errors: int
    success_rate: float = Field(ge=0.0, le=1.0)
    embeddings_enabled: bool
    search_enabled: bool
    uptime: Optional[float] = None

# Error response models
class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class ValidationError(BaseModel):
    """Validation error details"""
    field: str
    message: str
    invalid_value: Optional[Any] = None

# Configuration models
class EmbeddingConfig(BaseModel):
    """Configuration for embedding generation"""
    provider: str = Field(default="sentence_transformers")
    model_name: Optional[str] = None
    dimension: Optional[int] = None
    batch_size: int = Field(default=32, ge=1, le=1000)

class VectorStoreConfig(BaseModel):
    """Configuration for vector store"""
    type: str = Field(default="chroma")
    connection_string: Optional[str] = None
    collection_name: str = Field(default="documents")
    persist_directory: Optional[str] = None

class ProcessingConfig(BaseModel):
    """Configuration for document processing"""
    max_workers: int = Field(default=4, ge=1, le=16)
    chunk_size: int = Field(default=1000, ge=100, le=4000)
    chunk_overlap: int = Field(default=200, ge=0, le=1000)
    enable_embeddings: bool = True
    max_file_size_mb: int = Field(default=50, ge=1, le=500)
    supported_types: List[DocumentType] = Field(default_factory=lambda: [
        DocumentType.PDF,
        DocumentType.DOCX,
        DocumentType.DOC,
        DocumentType.XML,
        DocumentType.TXT
    ])

# Response models for API
class UploadResponse(BaseModel):
    """Response for document upload"""
    status: str
    document_id: str
    file_type: DocumentType
    original_filename: str
    processing_result: ProcessingResult
    message: str

class BatchUploadResponse(BaseModel):
    """Response for batch document upload"""
    batch_id: str
    total_files: int
    successful: int
    failed: int
    results: List[Dict[str, Any]]

class SearchResponse(BaseModel):
    """Response for document search"""
    query: str
    results_count: int
    results: List[SearchResult]
    processing_time: Optional[float] = None

class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    service: str
    timestamp: datetime = Field(default_factory=datetime.now)
    version: Optional[str] = None

class SupportedTypesResponse(BaseModel):
    """Response for supported file types"""
    supported_extensions: List[str]
    supported_types: List[DocumentType]
    max_file_size: str
    batch_limit: int
    features: Dict[str, bool] = Field(default_factory=lambda: {
        "embeddings": True,
        "search": True,
        "batch_processing": True,
        "async_processing": True
    })