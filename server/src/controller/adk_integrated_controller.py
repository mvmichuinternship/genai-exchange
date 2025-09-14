from fastapi import APIRouter, Form, HTTPException, Request, File, UploadFile
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from pathlib import Path
import httpx
import asyncio
import json
import logging
import os
import tempfile
import uuid

from modules.data_ingestion.rag_tool import get_rag_context_as_text_array_tool

# Import document processor service
try:
    from modules.document_parser.service import DocumentProcessorService
    document_service = DocumentProcessorService()
    DOCUMENT_SERVICE_AVAILABLE = True
except ImportError:
    DOCUMENT_SERVICE_AVAILABLE = False
    document_service = None

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

adk_test_router = APIRouter()

class DirectADKClient:
    """Enhanced client to communicate with ADK agents directly integrated into main app"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.adk_base = f"{base_url}/adk"
        self.client = httpx.AsyncClient(timeout=300.0)

    async def create_session(self, agent_name: str, user_id: str) -> str:
        """Create session with integrated ADK agent"""
        session_id = f"{user_id}_{agent_name}_{int(asyncio.get_event_loop().time())}"

        try:
            response = await self.client.post(
                f"{self.adk_base}/apps/{agent_name}/users/{user_id}/sessions/{session_id}",
                json={"state": {}}
            )

            if response.status_code != 200:
                logger.error(f"Session creation failed: {response.status_code} - {response.text}")
                raise Exception(f"Failed to create session: {response.status_code} - {response.text}")

            return session_id

        except httpx.RequestError as e:
            logger.error(f"Request error during session creation: {e}")
            raise Exception(f"Network error creating session: {str(e)}")

    async def send_message(self, agent_name: str, user_id: str, session_id: str, message: str) -> Dict[str, Any]:
        """Send message to integrated ADK agent"""
        payload = {
            "app_name": agent_name,
            "user_id": user_id,
            "session_id": session_id,
            "new_message": {
                "role": "user",
                "parts": [{"text": message}]
            }
        }

        try:
            response = await self.client.post(f"{self.adk_base}/run", json=payload)

            if response.status_code != 200:
                logger.error(f"Agent execution failed: {response.status_code} - {response.text}")
                raise Exception(f"Agent execution failed: {response.status_code} - {response.text}")

            return response.json()

        except httpx.RequestError as e:
            logger.error(f"Request error during message sending: {e}")
            raise Exception(f"Network error sending message: {str(e)}")

    async def check_agent_availability(self, agent_name: str) -> bool:
        """Check if an agent is available"""
        try:
            response = await self.client.get(f"{self.adk_base}/apps")
            if response.status_code == 200:
                return True
            return False
        except:
            return False

def get_adk_client():
    return DirectADKClient()

def _determine_file_type(file_extension: str, content_type: str) -> Optional[str]:
    """Determine the file type based on extension and content type"""
    type_mapping = {
        '.pdf': 'pdf',
        '.docx': 'docx',
        '.doc': 'doc',
        '.xml': 'xml',
        '.txt': 'txt',
        '.xlsx': 'xlsx',
        '.xls': 'xls',
        '.pptx': 'pptx',
        '.ppt': 'ppt'
    }

    content_type_mapping = {
        'application/pdf': 'pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/msword': 'doc',
        'text/xml': 'xml',
        'application/xml': 'xml',
        'text/plain': 'txt'
    }

    file_type = type_mapping.get(file_extension)
    if not file_type and content_type:
        file_type = content_type_mapping.get(content_type)

    return file_type

# ==============================================================================
# ENHANCED ADK AGENT TESTING ENDPOINTS
# ==============================================================================

@adk_test_router.post("/test-agents/requirements-to-tests-rag")
async def test_requirements_to_tests_with_rag(
    prompt: str = Form(..., description="Your input prompt with requirements"),
    enable_rag: bool = Form(True, description="Enable RAG context enhancement")
):
    """
    SINGLE RAG-ENHANCED ENDPOINT
    Uses your existing RAG implementation to enhance the sequential workflow
    """
    try:
        client = DirectADKClient()
        user_id = "rag_workflow_user"
        agent_name = "sequential_workflow"

        # Step 1: Get RAG context using your existing RAG tool
        rag_context_array = []
        if enable_rag:
            try:
                rag_context_array = await get_rag_context_as_text_array_tool(
                    query_context=prompt,
                    context_scope="comprehensive"
                )
                logger.info(f"RAG context retrieved: {len(rag_context_array)} items")
            except Exception as rag_error:
                logger.warning(f"RAG context failed, continuing without: {rag_error}")

        # Step 2: Create session
        session_id = await client.create_session(agent_name, user_id)

        # Step 3: Combine prompt with RAG context
        enhanced_message = prompt
        if rag_context_array:
            rag_context_text = "\n".join(rag_context_array)
            enhanced_message = f"{prompt}\n\n=== ADDITIONAL CONTEXT ===\n{rag_context_text}"

        # Step 4: Send to sequential workflow
        result = await client.send_message(
            agent_name=agent_name,
            user_id=user_id,
            session_id=session_id,
            message=enhanced_message
        )

        return {
            "status": "success",
            "test_type": "rag_enhanced_workflow",
            "your_prompt": prompt,
            "rag_context_loaded": len(rag_context_array),
            "rag_enabled": enable_rag,
            "session_id": session_id,
            "workflow_result": result,
            "agent_used": agent_name,
            "integration": "direct_adk_with_rag"
        }

    except Exception as e:
        logger.error(f"RAG workflow failed: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": "RAG workflow execution failed",
            "details": str(e),
            "rag_enabled": enable_rag
        })

@adk_test_router.post("/test-agents/ingest-documents")
async def ingest_documents_to_vector_store(
    texts: str = Form(..., description="JSON array of text chunks: [\"text1\", \"text2\"]"),
    doc_id: str = Form(..., description="Document ID for this batch"),
    document_type: str = Form("general", description="Type: requirements, test_specs, domain_knowledge")
):
    """
    SIMPLE DOCUMENT INGESTION
    Add documents to your vector store for RAG
    texts should be a JSON string like: ["text1", "text2", "text3"]
    """
    try:
        if not RAG_AVAILABLE:
            raise HTTPException(status_code=503, detail="RAG system not available")

        # Parse JSON string to list
        try:
            text_list = json.loads(texts)
            if not isinstance(text_list, list):
                raise ValueError("texts must be a JSON array")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="texts must be valid JSON array")

        # Get vector store using your existing config
        VECTOR_STORE_CONFIG = {
            "type": "vertex_ai",
            "config": {
                "project_id": "celtic-origin-472009-n5",  # Update this
                "index_name": "test-generation-index",
                "endpoint_name": "test-generation-endpoint"
            }
        }

        vector_store = VectorStoreFactory.create_vector_store(
            store_type=VECTOR_STORE_CONFIG["type"],
            config=VECTOR_STORE_CONFIG["config"]
        )

        # Prepare metadata
        metadata = {
            "doc_id": doc_id,
            "document_type": document_type,
            "ingested_at": asyncio.get_event_loop().time()
        }

        # Ingest documents
        result = await vector_store.ingest_documents(text_list, metadata)

        return {
            "status": "success",
            "ingestion_result": result,
            "documents_ingested": len(text_list),
            "doc_id": doc_id,
            "document_type": document_type
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "error": "Document ingestion failed",
            "details": str(e)
        })

@adk_test_router.post("/test-agents/upload-with-rag")
async def upload_document_with_rag_ingestion(
    file: UploadFile = File(...),
    document_id: Optional[str] = Form(None),
    document_type: str = Form("general", description="Type: requirements, test_specs, domain_knowledge"),
    metadata: Optional[str] = Form(None),
    enable_rag: bool = Form(True, description="Enable RAG vector store ingestion")
):
    """
    Upload and process document with optional RAG ingestion
    Uses your existing document processing + adds RAG capabilities
    """
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

        try:
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
                    pass

            # Process using existing document service
            result = await document_service.process_document(processing_config)

            # Step 2: RAG ingestion
            rag_result = {"status": "disabled", "message": "RAG not enabled"}

            if enable_rag and RAG_AVAILABLE:
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

                except Exception as rag_error:
                    rag_result = {
                        "status": "error",
                        "message": f"RAG ingestion failed: {str(rag_error)}",
                        "rag_chunks_created": 0
                    }
            elif enable_rag and not RAG_AVAILABLE:
                rag_result = {
                    "status": "unavailable",
                    "message": "RAG system not available - missing dependencies"
                }

            # Return combined result
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "document_id": document_id,
                    "file_type": file_type,
                    "original_filename": file.filename,
                    "processing_result": result,
                    "content": result.get('content'),
                    "rag_ingestion": rag_result,
                    "message": f"Document processed with {result.get('chunks_created', 0)} chunks" +
                              (f" and {rag_result.get('rag_chunks_created', 0)} RAG chunks" if rag_result.get('status') == 'success' else "")
                }
            )

        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@adk_test_router.post("/test-agents/requirements-to-tests")
async def test_requirements_to_tests_workflow(
    prompt: str = Form(..., description="Your input prompt with requirements"),
    detailed_output: bool = Form(False, description="Request detailed step-by-step output")
):
    """
    TEST THE COMPLETE WORKFLOW - Enhanced Version
    Input: Your prompt → Sequential Workflow → Detailed Response
    """
    try:
        client = DirectADKClient()
        user_id = "workflow_test_user"
        agent_name = "sequential_workflow"

        # Check if agent is available first
        if not await client.check_agent_availability(agent_name):
            logger.warning(f"Agent {agent_name} may not be available")

        # Create session
        session_id = await client.create_session(agent_name, user_id)
        logger.info(f"Created session {session_id} for agent {agent_name}")

        # Enhanced prompt based on user preference
        if detailed_output:
            enhanced_prompt = f"""
            {prompt}

            Please provide detailed output showing:
            1. Requirements Analysis Phase:
               - Identified functional requirements
               - Identified non-functional requirements
               - Any assumptions or clarifications needed
               - Structured analysis results

            2. Test Case Generation Phase:
               - Test scenarios derived from requirements
               - Expected outcomes for each test case
               - Edge cases and boundary conditions
               - Test data requirements

            Please clearly separate and label each phase of your work.
            """
        else:
            enhanced_prompt = prompt

        # Send message to sequential workflow
        result = await client.send_message(
            agent_name=agent_name,
            user_id=user_id,
            session_id=session_id,
            message=enhanced_prompt
        )

        logger.info(f"Successfully processed workflow for session {session_id}")

        return {
            "status": "success",
            "test_type": "complete_workflow_enhanced",
            "your_prompt": prompt,
            "detailed_output_requested": detailed_output,
            "session_id": session_id,
            "workflow_result": result,
            "agent_used": agent_name,
            "integration": "direct_adk",
            "timestamp": asyncio.get_event_loop().time()
        }

    except Exception as e:
        logger.error(f"Workflow test failed: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "error": "Workflow execution failed",
            "details": str(e),
            "agent": agent_name,
            "troubleshooting": {
                "check_1": "Verify sequential_workflow agent is properly configured",
                "check_2": "Ensure requirement_analyzer_agent and test_case_generator_agent exist",
                "check_3": "Check ADK service is running on /adk endpoints",
                "check_4": "Verify agent imports are correct in sequential_workflow/agent.py"
            }
        })

@adk_test_router.post("/test-agents/validate-and-test")
async def validate_and_test_workflow(
    prompt: str = Form(..., description="Your input prompt with requirements")
):
    """
    VALIDATE SETUP THEN TEST WORKFLOW
    First validates that all components are working, then runs the test
    """
    try:
        client = DirectADKClient()
        user_id = "validation_user"
        agent_name = "sequential_workflow"

        # Step 1: Validate ADK is accessible
        adk_health = await client.client.get(f"{client.adk_base}/")
        if adk_health.status_code != 200:
            raise Exception(f"ADK service not accessible: {adk_health.status_code}")

        # Step 2: Try to create a session
        try:
            session_id = await client.create_session(agent_name, user_id)
        except Exception as session_error:
            raise Exception(f"Agent loading failed: {str(session_error)}")

        # Step 3: Send a simple test message first
        test_result = await client.send_message(
            agent_name=agent_name,
            user_id=user_id,
            session_id=session_id,
            message="Please confirm you are working and describe your capabilities briefly."
        )

        # Step 4: Now send the actual prompt
        main_result = await client.send_message(
            agent_name=agent_name,
            user_id=user_id,
            session_id=session_id,
            message=prompt
        )

        return {
            "status": "success",
            "test_type": "validated_workflow",
            "validation_steps": {
                "adk_accessible": "✓ ADK service responding",
                "agent_loadable": "✓ Sequential workflow agent loaded",
                "basic_communication": "✓ Agent responding to messages",
                "full_processing": "✓ Completed your request"
            },
            "your_prompt": prompt,
            "session_id": session_id,
            "test_response": test_result,
            "main_response": main_result,
            "integration": "direct_adk"
        }

    except Exception as e:
        logger.error(f"Validation and test failed: {str(e)}")

        error_details = {
            "error": str(e),
            "troubleshooting_steps": [
                "1. Check if /adk endpoint is accessible",
                "2. Verify sequential_workflow agent exists in correct directory",
                "3. Ensure __init__.py files export root_agent correctly",
                "4. Validate import paths in sequential_workflow/agent.py",
                "5. Check ADK logs for agent loading errors"
            ],
            "required_file_structure": {
                "sequential_workflow": "adk_service/agents/sequential_workflow/",
                "files_needed": [
                    "__init__.py (exports root_agent)",
                    "agent.py (defines root_agent)",
                    "../requirement_analyzer/agent.py",
                    "../test_case_generator/agent.py"
                ]
            }
        }

        raise HTTPException(status_code=500, detail=error_details)

@adk_test_router.get("/test-agents/diagnose")
async def diagnose_agent_setup():
    """
    COMPREHENSIVE DIAGNOSIS OF AGENT SETUP
    Checks all components and provides detailed status
    """
    diagnosis = {
        "timestamp": asyncio.get_event_loop().time(),
        "checks": {},
        "overall_status": "unknown",
        "system_availability": {
            "document_service": DOCUMENT_SERVICE_AVAILABLE,
            "rag_system": RAG_AVAILABLE
        }
    }

    try:
        client = DirectADKClient()

        # Check 1: ADK Base Accessibility
        try:
            adk_response = await client.client.get(f"{client.adk_base}/")
            diagnosis["checks"]["adk_accessible"] = {
                "status": "✓ PASS" if adk_response.status_code == 200 else "✗ FAIL",
                "details": f"Status: {adk_response.status_code}"
            }
        except Exception as e:
            diagnosis["checks"]["adk_accessible"] = {
                "status": "✗ FAIL",
                "details": f"Error: {str(e)}"
            }

        # Check 2: Try to create session (tests agent loading)
        try:
            session_id = await client.create_session("sequential_workflow", "diagnostic_user")
            diagnosis["checks"]["agent_loading"] = {
                "status": "✓ PASS",
                "details": f"Successfully created session: {session_id}"
            }

            # Check 3: Basic communication
            try:
                response = await client.send_message(
                    "sequential_workflow",
                    "diagnostic_user",
                    session_id,
                    "Hello, please respond with a brief status message."
                )
                diagnosis["checks"]["agent_communication"] = {
                    "status": "✓ PASS",
                    "details": "Agent responded successfully"
                }
                diagnosis["overall_status"] = "healthy"
            except Exception as e:
                diagnosis["checks"]["agent_communication"] = {
                    "status": "✗ FAIL",
                    "details": f"Communication error: {str(e)}"
                }
                diagnosis["overall_status"] = "partially_working"

        except Exception as e:
            diagnosis["checks"]["agent_loading"] = {
                "status": "✗ FAIL",
                "details": f"Session creation failed: {str(e)}"
            }
            diagnosis["checks"]["agent_communication"] = {
                "status": "⚠ SKIPPED",
                "details": "Cannot test communication without successful session creation"
            }
            diagnosis["overall_status"] = "agent_loading_failed"

        return diagnosis

    except Exception as e:
        diagnosis["overall_status"] = "system_error"
        diagnosis["system_error"] = str(e)
        return diagnosis

@adk_test_router.get("/test-agents/health")
async def check_agents_health():
    """Enhanced health check with more details"""
    try:
        client = DirectADKClient()
        response = await client.client.get(f"{client.adk_base}/")

        return {
            "status": "healthy" if response.status_code == 200 else "unhealthy",
            "adk_status_code": response.status_code,
            "integration": "direct_adk",
            "primary_agent": "sequential_workflow",
            "system_availability": {
                "document_service": DOCUMENT_SERVICE_AVAILABLE,
                "rag_system": RAG_AVAILABLE
            },
            "endpoints": {
                "adk_ui": f"{client.adk_base}/",
                "agent_execution": f"{client.adk_base}/run",
                "session_management": f"{client.adk_base}/apps/{{agent}}/users/{{user}}/sessions/{{session}}"
            },
            "test_endpoints": {
                "basic_test": "/api/agents/test-agents/requirements-to-tests",
                "rag_enhanced_test": "/api/agents/test-agents/requirements-to-tests-rag",
                "upload_with_rag": "/upload-with-rag",
                "diagnosis": "/api/agents/test-agents/diagnose"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "integration": "direct_adk",
            "system_availability": {
                "document_service": DOCUMENT_SERVICE_AVAILABLE,
                "rag_system": RAG_AVAILABLE
            }
        }
