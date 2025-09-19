import asyncio
from typing import List, Dict, Optional, Any
from pathlib import Path
import json
import logging
from src.modules.data_ingestion.factory import VectorStoreFactory

logger = logging.getLogger(__name__)

class RAGIngestionHelper:
    """Helper class for RAG document ingestion"""

    def __init__(self, vector_store_config: Dict = None):
        self.vector_store_config = vector_store_config or {
            "type": "vertex_ai",
            "config": {
                "project_id": "celtic-origin-472009-n5",
                "index_name": "projects/195472357560/locations/us-central1/indexes/5689930892298944512",
                "endpoint_name": "projects/195472357560/locations/us-central1/indexEndpoints/5490892899392421888"
            }
        }

    async def ingest_processing_result_to_rag(self,
                                            processing_result: Dict,
                                            document_id: str,
                                            document_type: str,
                                            file_info: Dict,
                                            additional_metadata: Dict = None) -> Dict:
        """
        Ingest document processing result to RAG vector store

        Args:
            processing_result: Result from DocumentProcessorService
            document_id: Unique document identifier
            document_type: Type of document (requirements, test_specs, etc.)
            file_info: Original file information
            additional_metadata: Extra metadata to include

        Returns:
            Dict with ingestion results
        """
        try:
            # Extract text chunks from processing result
            text_chunks = self._extract_rag_chunks_from_processing_result(processing_result)

            if not text_chunks:
                return {
                    "status": "warning",
                    "message": "No text chunks extracted for RAG ingestion",
                    "rag_chunks_created": 0
                }

            # Prepare RAG metadata
            rag_metadata = self._prepare_rag_metadata(
                document_id, document_type, file_info,
                processing_result, additional_metadata
            )

            # Get vector store and ingest
            vector_store = VectorStoreFactory.create_vector_store(
                store_type=self.vector_store_config["type"],
                config=self.vector_store_config["config"]
            )

            ingestion_result = await vector_store.ingest_documents(text_chunks, rag_metadata)

            return {
                "status": "success",
                "rag_chunks_created": len(text_chunks),
                "sample_chunks": text_chunks[:2] if text_chunks else [],
                "ingestion_result": ingestion_result,
                "vector_store_type": self.vector_store_config["type"]
            }

        except Exception as e:
            logger.error(f"RAG ingestion failed: {str(e)}")
            return {
                "status": "error",
                "message": f"RAG ingestion failed: {str(e)}",
                "rag_chunks_created": 0
            }

    def _extract_rag_chunks_from_processing_result(self, processing_result: Dict) -> List[str]:
        """Extract and optimize text chunks for RAG from processing result"""
        content = processing_result.get('content', [])

        if isinstance(content, list):
            # Join lines and split into RAG-optimized chunks
            full_text = '\n'.join(str(line) for line in content if str(line).strip())
            return self._split_text_into_rag_chunks(full_text)
        elif isinstance(content, str):
            return self._split_text_into_rag_chunks(content)
        else:
            return []

    def _split_text_into_rag_chunks(self, text: str, max_chunk_size: int = 500) -> List[str]:
        """Split text into optimal chunks for RAG vector search"""
        if len(text) <= max_chunk_size:
            return [text] if text.strip() else []

        # Split by paragraphs first (double newlines)
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # If adding this paragraph would exceed max size
            if len(current_chunk) + len(paragraph) + 2 > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = paragraph
                else:
                    # Paragraph is too long, split by sentences
                    sentences = self._split_by_sentences(paragraph)
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) + 1 > max_chunk_size:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                            current_chunk = sentence
                        else:
                            current_chunk += " " + sentence if current_chunk else sentence
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph

        if current_chunk:
            chunks.append(current_chunk.strip())

        return [chunk for chunk in chunks if chunk.strip()]

    def _split_by_sentences(self, text: str) -> List[str]:
        """Split text by sentences"""
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _prepare_rag_metadata(self,
                            document_id: str,
                            document_type: str,
                            file_info: Dict,
                            processing_result: Dict,
                            additional_metadata: Dict = None) -> Dict:
        """Prepare comprehensive metadata for RAG ingestion"""
        rag_metadata = {
            "doc_id": document_id,
            "document_type": document_type,
            "original_filename": file_info.get("filename", "unknown"),
            "file_type": file_info.get("file_type", "unknown"),
            "file_size": file_info.get("file_size", 0),
            "processed_chunks": processing_result.get('chunks_created', 0),
            "processing_metadata": processing_result.get('metadata', {}),
            "ingested_at": asyncio.get_event_loop().time()
        }

        # Add additional metadata if provided
        if additional_metadata:
            rag_metadata.update(additional_metadata)

        return rag_metadata

class DocumentUploadHelper:
    """Helper class for document upload and file processing"""

    @staticmethod
    def determine_file_type(file_extension: str, content_type: str) -> Optional[str]:
        """Determine file type from extension and content type"""
        type_mapping = {
            '.pdf': 'pdf',
            '.docx': 'docx',
            '.doc': 'doc',
            '.xml': 'xml',
            '.txt': 'txt',
        }

        content_type_mapping = {
            'application/pdf': 'pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'application/msword': 'doc',
            'text/xml': 'xml',
            'application/xml': 'xml',
            'text/plain': 'txt'
        }

        file_type = type_mapping.get(file_extension.lower())
        if not file_type and content_type:
            file_type = content_type_mapping.get(content_type.lower())

        return file_type

    @staticmethod
    def prepare_processing_config(document_id: str,
                                file_type: str,
                                file_path: str,
                                filename: str,
                                file_size: int,
                                metadata_str: Optional[str] = None) -> Dict:
        """Prepare configuration for document processing"""
        processing_config = {
            'document_id': document_id,
            'type': file_type,
            'path': file_path,
            'original_filename': filename,
            'file_size': file_size
        }

        # Add additional metadata if provided
        if metadata_str:
            try:
                additional_metadata = json.loads(metadata_str)
                processing_config.update(additional_metadata)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON metadata provided: {metadata_str}")

        return processing_config

    @staticmethod
    def validate_file(filename: str, content_type: str, file_size: int, max_size_mb: int = 50) -> Dict:
        """Validate uploaded file"""
        if not filename:
            return {"valid": False, "error": "No filename provided"}

        file_extension = Path(filename).suffix.lower()
        file_type = DocumentUploadHelper.determine_file_type(file_extension, content_type)

        if not file_type:
            return {
                "valid": False,
                "error": f"Unsupported file type: {file_extension}",
                "supported_types": [".pdf", ".docx", ".doc", ".xml", ".txt"]
            }

        max_size_bytes = max_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            return {
                "valid": False,
                "error": f"File size ({file_size} bytes) exceeds maximum allowed ({max_size_bytes} bytes)"
            }

        return {
            "valid": True,
            "file_type": file_type,
            "file_extension": file_extension
        }
