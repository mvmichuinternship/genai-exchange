from fastapi import APIRouter, File, UploadFile, HTTPException, Form, FastAPI
from fastapi.responses import JSONResponse
from typing import Optional, List
import os
import tempfile
import uuid
from pathlib import Path
import mimetypes
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your document parser modules
try:
    from modules.document_parser.service import DocumentProcessorService
    from modules.document_parser.models import ProcessingResult, DocumentMetadata
except ImportError:
    # Fallback for testing - create mock classes
    class DocumentProcessorService:
        async def process_document(self, config):
            return {"success": True, "chunks_created": 5, "document_id": config.get("document_id")}

        async def search_documents(self, query, limit, filters):
            return [{"text": f"Mock result for: {query}", "score": 0.95}]

        async def get_document_status(self, document_id):
            return {"document_id": document_id, "status": "completed", "chunks": 5}

    class ProcessingResult:
        pass

    class DocumentMetadata:
        pass

router = APIRouter(prefix="/api/documents", tags=["Documents"])

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

# Create the FastAPI app at module level (not inside if __name__ == "__main__")
app = FastAPI(title="Document Upload API")
app.include_router(router)

@app.get("/")
async def root():
    return {"message": "Document Upload API is running!"}

# This runs only when the script is executed directly
if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Document Upload API...")
    print("📖 API Docs: http://localhost:8000/docs")
    print("📤 Upload: http://localhost:8000/api/documents/upload")

    uvicorn.run("src.controller.module_test_controller:app", host="0.0.0.0", port=8000, reload=True)
