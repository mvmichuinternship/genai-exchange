import logging
from fastapi import APIRouter, HTTPException, Request
from typing import List, Dict

from modules.database.database_manager import db_manager
from modules.cache.redis_manager import redis_manager
from adk_service.agents.test_case_generator.agent import generate_test_cases
from utils.parsers import parse_test_cases_from_agent_response

router = APIRouter()
logger = logging.getLogger(__name__)

class TestCasesController:

    async def generate_test_cases_endpoint(self, request: Request):
        """Generate test cases using the test case generator agent"""
        data = await request.json()
        session_id = data.get('session_id')
        prompt = data.get('prompt', "Generate comprehensive test cases")
        test_types = data.get('test_types', ['functional', 'security', 'edge', 'negative'])

        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID is required for test case generation")

        # Verify session exists
        session = await db_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        requirements_cache_key = f"requirements_analyzed:{session_id}"
        requirements_input = await redis_manager.get(requirements_cache_key)

        try:
            # Enhance prompt with test types
            enhanced_prompt = f"{prompt}\n\nGenerate the following types of test cases: {', '.join(test_types)}"

            # Call the agent function
            agent_response = await generate_test_cases(session_id=session_id, prompt=enhanced_prompt, analysis_depth=None, requirements_input=requirements_input)

            if agent_response['status'] == 'success':
                # Parse test cases from agent response
                test_cases = parse_test_cases_from_agent_response(agent_response['response'])

                if test_cases:
                    await db_manager.save_test_cases(session_id, test_cases)

                await db_manager.update_session_status(session_id, "test_cases_generated")

                return {
                    "session_id": session_id,
                    "status": "success",
                    "test_types_requested": test_types,
                    "generated_test_cases_count": len(test_cases),
                    "test_cases": agent_response['response'],
                    "agent_used": agent_response['agent_used'],
                    "message": "Test cases successfully generated and stored"
                }
            else:
                await db_manager.update_session_status(session_id, "test_generation_failed")
                raise HTTPException(status_code=500, detail=f"Test generation failed: {agent_response['message']}")

        except Exception as e:
            logger.error(f"Test case generation failed for session {session_id}: {e}")
            await db_manager.update_session_status(session_id, "test_generation_failed")
            raise HTTPException(status_code=500, detail=f"Test case generation failed: {str(e)}")

    async def get_test_cases(self, session_id: str):
        """Get test cases for a session"""
        test_cases = await db_manager.get_test_cases(session_id)
        return {
            "session_id": session_id,
            "test_cases": test_cases,
            "total_count": len(test_cases)
        }

    async def regenerate_test_cases(self, session_id: str, request: Request):
        """Regenerate test cases for specific requirements"""
        data = await request.json()
        requirement_ids = data.get('requirement_ids', [])
        test_types = data.get('test_types', ['functional'])

        if requirement_ids:
            # Regenerate for specific requirements
            requirements = await db_manager.get_requirements(session_id)
            target_requirements = [r for r in requirements if r['id'] in requirement_ids]

            if not target_requirements:
                raise HTTPException(status_code=404, detail="No matching requirements found")

            req_texts = [r.get('edited_content') or r.get('original_content') for r in target_requirements]
            prompt = f"Generate test cases for these specific requirements: {'; '.join(req_texts)}"
        else:
            # Regenerate for all requirements
            prompt = "Regenerate all test cases based on existing requirements"

        agent_response = await generate_test_cases(session_context=None, prompt=prompt)

        if agent_response['status'] == 'success':
            new_test_cases = parse_test_cases_from_agent_response(agent_response['response'])

            # Add requirement links if specified
            if requirement_ids:
                test_cases_with_links = [{
                    **tc,
                    'requirement_ids': requirement_ids
                } for tc in new_test_cases]
            else:
                test_cases_with_links = new_test_cases

            await db_manager.save_test_cases(session_id, test_cases_with_links)

            return {
                "session_id": session_id,
                "status": "regenerated",
                "requirement_ids": requirement_ids,
                "new_test_cases_count": len(new_test_cases),
                "test_cases": new_test_cases
            }
        else:
            raise HTTPException(status_code=500, detail=f"Regeneration failed: {agent_response['message']}")

test_cases_controller = TestCasesController()

# Routes
@router.post("/generate")
async def generate_test_cases_endpoint(request: Request):
    return await test_cases_controller.generate_test_cases_endpoint(request)

@router.get("/{session_id}")
async def get_test_cases(session_id: str):
    return await test_cases_controller.get_test_cases(session_id)

@router.post("/{session_id}/regenerate")
async def regenerate_test_cases(session_id: str, request: Request):
    return await test_cases_controller.regenerate_test_cases(session_id, request)
