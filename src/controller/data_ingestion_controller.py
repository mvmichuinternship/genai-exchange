import logging
from fastapi import APIRouter, File, UploadFile, HTTPException, Form, FastAPI
from fastapi.responses import JSONResponse
from typing import Optional, List
import os
import tempfile
import uuid
from pathlib import Path
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Import RAG helpers
try:
    from helpers.rag_helper import RAGIngestionHelper
    from modules.data_ingestion.factory import VectorStoreFactory
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
try:
    from modules.document_parser.service import DocumentProcessorService
    from modules.document_parser.models import ProcessingResult, DocumentMetadata
    document_service = DocumentProcessorService()
    DOCUMENT_SERVICE_AVAILABLE = True
except ImportError:
    DOCUMENT_SERVICE_AVAILABLE = False
    document_service = None

router = APIRouter()

# Initialize your document processor service
document_service = DocumentProcessorService()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_id: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None)  # JSON string for additional metadata
):
    """
    Upload and process a document based on its file extension
    """
    try:
        # Generate document ID if not provided
        if not document_id:
            document_id = str(uuid.uuid4())

        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        # Get file extension and determine processing method
        file_extension = Path(file.filename).suffix.lower()
        file_type = _determine_file_type(file_extension, file.content_type)

        if not file_type:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_extension}"
            )

        # Create temporary file to store upload
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            # Write uploaded content to temp file
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Process the document based on type
            processing_config = {
                'document_id': document_id,
                'type': file_type,
                'path': temp_file_path,
                'original_filename': file.filename,
                'file_size': len(content)
            }

            # Add any additional metadata
            if metadata:
                import json
                try:
                    additional_metadata = json.loads(metadata)
                    processing_config.update(additional_metadata)
                except json.JSONDecodeError:
                    pass  # Ignore malformed metadata

            # Process the document
            result = await document_service.process_document(processing_config)

            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "document_id": document_id,
                    "file_type": file_type,
                    "original_filename": file.filename,
                    "processing_result": result,
                    "content": result.get('content'),
                    "message": f"Document processed successfully with {result.get('chunks_created', 0)} chunks"
                }
            )

        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@router.post("/upload-batch")
async def upload_documents_batch(
    files: List[UploadFile] = File(...),
    batch_id: Optional[str] = Form(None)
):
    """
    Upload and process multiple documents in batch
    """
    if not batch_id:
        batch_id = str(uuid.uuid4())

    results = []
    for file in files:
        try:
            # Process each file individually
            file_extension = Path(file.filename).suffix.lower()
            file_type = _determine_file_type(file_extension, file.content_type)

            if not file_type:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": f"Unsupported file type: {file_extension}"
                })
                continue

            document_id = f"{batch_id}_{len(results)}"

            # Create temp file and process
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name

            try:
                processing_config = {
                    'document_id': document_id,
                    'type': file_type,
                    'path': temp_file_path,
                    'original_filename': file.filename,
                    'batch_id': batch_id
                }

                result = await document_service.process_document(processing_config)
                results.append({
                    "filename": file.filename,
                    "document_id": document_id,
                    "status": "success",
                    "content": result.get('content'),
                    "chunks_created": result.get('chunks_created', 0)
                })

            finally:
                os.unlink(temp_file_path)

        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "error",
                "error": str(e)
            })

    successful = len([r for r in results if r["status"] == "success"])
    failed = len([r for r in results if r["status"] == "error"])

    return JSONResponse(
        status_code=200,
        content={
            "batch_id": batch_id,
            "total_files": len(files),
            "successful": successful,
            "failed": failed,
            "results": results
        }
    )

@router.post("/upload-with-rag")
async def upload_document_with_rag_ingestion(
    file: UploadFile = File(...),
    document_id: Optional[str] = Form(None),
    document_type: str = Form("general", description="Type: requirements, test_specs, domain_knowledge"),
    metadata: Optional[str] = Form(None),
    enable_rag: bool = Form(True, description="Enable RAG vector store ingestion"),
    fail_on_rag_error: bool = Form(False, description="Fail entire request if RAG ingestion fails")
):
    """
    Upload and process document with optional RAG ingestion
    IMPROVED: Proper error handling and status codes
    """
    document_processing_success = False
    rag_ingestion_success = False
    temp_file_path = None

    try:
        if not DOCUMENT_SERVICE_AVAILABLE:
            raise HTTPException(status_code=503, detail="Document processing service not available")

        # Generate document ID if not provided
        if not document_id:
            document_id = str(uuid.uuid4())

        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        file_extension = Path(file.filename).suffix.lower()
        file_type = _determine_file_type(file_extension, file.content_type)

        if not file_type:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_extension}"
            )

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # Step 1: Process document using existing service
        processing_config = {
            'document_id': document_id,
            'type': file_type,
            'path': temp_file_path,
            'original_filename': file.filename,
            'file_size': len(content)
        }

        # Add metadata
        if metadata:
            try:
                additional_metadata = json.loads(metadata)
                processing_config.update(additional_metadata)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON metadata for document {document_id}")

        # Step 1: Document Processing (MUST succeed)
        try:
            result = await document_service.process_document(processing_config)
            document_processing_success = True
            logger.info(f"Document processing successful for {document_id}")
        except Exception as doc_error:
            logger.error(f"Document processing failed for {document_id}: {str(doc_error)}")
            raise HTTPException(
                status_code=500,
                detail=f"Document processing failed: {str(doc_error)}"
            )

        # Step 2: RAG Ingestion (Optional, configurable failure behavior)
        rag_result = {"status": "disabled", "message": "RAG not enabled"}

        if enable_rag:
            if not RAG_AVAILABLE:
                error_msg = "RAG system not available - missing dependencies"
                logger.error(error_msg)
                if fail_on_rag_error:
                    raise HTTPException(status_code=503, detail=error_msg)
                else:
                    rag_result = {"status": "unavailable", "message": error_msg}
            else:
                try:
                    # Initialize RAG helper
                    rag_helper = RAGIngestionHelper()

                    # Prepare file info
                    file_info = {
                        "filename": file.filename,
                        "file_type": file_type,
                        "file_size": len(content)
                    }

                    # Parse additional metadata for RAG
                    additional_rag_metadata = {}
                    if metadata:
                        try:
                            additional_rag_metadata = json.loads(metadata)
                        except json.JSONDecodeError:
                            pass

                    # Ingest to RAG
                    rag_result = await rag_helper.ingest_processing_result_to_rag(
                        processing_result=result,
                        document_id=document_id,
                        document_type=document_type,
                        file_info=file_info,
                        additional_metadata=additional_rag_metadata
                    )

                    if rag_result.get("status") == "success":
                        rag_ingestion_success = True
                        logger.info(f"RAG ingestion successful for {document_id}")
                    else:
                        error_msg = f"RAG ingestion failed: {rag_result.get('message', 'Unknown error')}"
                        logger.error(error_msg)
                        if fail_on_rag_error:
                            raise HTTPException(status_code=500, detail=error_msg)

                except Exception as rag_error:
                    error_msg = f"RAG ingestion failed: {str(rag_error)}"
                    logger.error(error_msg)

                    if fail_on_rag_error:
                        raise HTTPException(status_code=500, detail=error_msg)
                    else:
                        rag_result = {
                            "status": "error",
                            "message": error_msg,
                            "rag_chunks_created": 0
                        }

        if document_processing_success and (not enable_rag or rag_ingestion_success):
            status_code = 200
            overall_status = "success"
        elif document_processing_success and enable_rag and not rag_ingestion_success:
            status_code = 207
            overall_status = "partial_success"
        else:
            status_code = 500
            overall_status = "failure"

        response_content = {
            "status": overall_status,
            "document_id": document_id,
            "file_type": file_type,
            "original_filename": file.filename,
            "processing_result": result,
            "content": result.get('content'),
            "rag_ingestion": rag_result,
            "components": {
                "document_processing": "success" if document_processing_success else "failed",
                "rag_ingestion": "success" if rag_ingestion_success else ("failed" if enable_rag else "disabled")
            },
            "message": f"Document processed with {result.get('chunks_created', 0)} chunks" +
                      (f" and {rag_result.get('rag_chunks_created', 0)} RAG chunks" if rag_result.get('status') == 'success' else "")
        }

        return JSONResponse(
            status_code=status_code,
            content=response_content
        )

    except HTTPException:
        # Re-raise HTTP exceptions (they already have proper status codes)
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing document {document_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file {temp_file_path}: {cleanup_error}")

@router.get("/search")
async def search_documents(
    query: str,
    limit: int = 10,
    document_id: Optional[str] = None,
    file_type: Optional[str] = None
):
    """
    Search through processed documents
    """
    try:
        filters = {}
        if document_id:
            filters['document_id'] = document_id
        if file_type:
            filters['source_type'] = file_type

        results = await document_service.search_documents(query, limit, filters)

        return JSONResponse(
            status_code=200,
            content={
                "query": query,
                "results_count": len(results),
                "results": results
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/status/{document_id}")
async def get_document_status(document_id: str):
    """
    Get processing status of a specific document
    """
    try:
        status = await document_service.get_document_status(document_id)
        return JSONResponse(status_code=200, content=status)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Document not found: {str(e)}")

def _determine_file_type(file_extension: str, content_type: str) -> Optional[str]:
    """
    Determine the file type based on extension and content type
    """
    # Define supported file types
    type_mapping = {
        # PDF files
        '.pdf': 'pdf',

        # Word documents
        '.docx': 'docx',
        '.doc': 'doc',

        # XML files
        '.xml': 'xml',

        # Text files
        '.txt': 'txt',

        # Excel files (if you want to support them)
        '.xlsx': 'xlsx',
        '.xls': 'xls',

        # PowerPoint (if needed)
        '.pptx': 'pptx',
        '.ppt': 'ppt'
    }

    # Also check content type as backup
    content_type_mapping = {
        'application/pdf': 'pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/msword': 'doc',
        'text/xml': 'xml',
        'application/xml': 'xml',
        'text/plain': 'txt'
    }

    # Try extension first, then content type
    file_type = type_mapping.get(file_extension)
    if not file_type and content_type:
        file_type = content_type_mapping.get(content_type)

    return file_type

# Health check endpoint
@router.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "document_parser"}

# Get supported file types
@router.get("/supported-types")
async def get_supported_types():
    """
    Get list of supported file types
    """
    return {
        "supported_extensions": [".pdf", ".docx", ".doc", ".xml", ".txt"],
        "supported_types": ["pdf", "docx", "doc", "xml", "txt"],
        "max_file_size": "50MB",  # Configure as needed
        "batch_limit": 10
    }

