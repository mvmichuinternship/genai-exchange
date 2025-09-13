from fastapi import APIRouter, Form, HTTPException, Request
from typing import List, Dict, Any, Optional
import httpx
import asyncio
import json
import logging

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
                # This is a simple check - you might need to adapt based on ADK's actual API
                return True
            return False
        except:
            return False

def get_adk_client():
    return DirectADKClient()

# ==============================================================================
# ENHANCED ADK AGENT TESTING ENDPOINTS
# ==============================================================================

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

        # Step 2: Try to create a session (this will fail if agent isn't loaded)
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

        # Provide detailed troubleshooting information
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
        "overall_status": "unknown"
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
            "endpoints": {
                "adk_ui": f"{client.adk_base}/",
                "agent_execution": f"{client.adk_base}/run",
                "session_management": f"{client.adk_base}/apps/{{agent}}/users/{{user}}/sessions/{{session}}"
            },
            "test_endpoints": {
                "basic_test": "/api/agents/test-agents/requirements-to-tests",
                "validated_test": "/api/agents/test-agents/validate-and-test",
                "diagnosis": "/api/agents/test-agents/diagnose"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "integration": "direct_adk"
        }