import logging
from fastapi import APIRouter, HTTPException, Request
import uuid
import json
from typing import List
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adk_service.agents.requirement_analyzer.agent import (
    requirement_analyzer_agent,
)
from adk_service.agents.test_case_generator.agent import (
    test_case_generator_agent,
    generate_test_cases
)
from modules.database.database_manager import db_manager
from modules.cache.redis_manager import redis_manager
from modules.database.session_service import SessionService
from utils.parsers import (
    parse_test_cases_from_agent_response,
)

# Add your RAG import here - ADJUST THE PATH TO YOUR ACTUAL RAG MODULE
from modules.data_ingestion.rag_tool import get_rag_context_as_text_array_tool

router = APIRouter()
logger = logging.getLogger(__name__)  # ✅ CORRECT LOGGER

class SessionAPIController:
    def __init__(self):
        self.requirement_analyzer = requirement_analyzer_agent
        self.test_case_generator = test_case_generator_agent

    async def create_simple_session(self, request: Request):
        """Create a simple session without running workflow"""
        data = await request.json()
        user_id = data.get('user_id', 'default_user')
        project_name = data.get('project_name', 'New Project')



        session_id = f"session_{uuid.uuid4().hex[:12]}"

        try:
            # Just create the session in database
            await db_manager.create_session(session_id, user_id, project_name, "Session creation")
            await db_manager.update_session_status(session_id, "created")

            return {
                "session_id": session_id,
                "user_id": user_id,
                "project_name": project_name,
                "user_prompt": user_prompt,
                "status": "created",
                "message": "Session created successfully",
                "database_saved": True
            }
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise HTTPException(status_code=500, detail=f"Session creation failed: {str(e)}")

    async def get_session(self, session_id: str):
        cache_key = f"session:{session_id}"
        cached_session = await redis_manager.get(cache_key)

        if cached_session:
            return cached_session
        session_data = await SessionService.get_session_summary(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        await redis_manager.set(cache_key, session_data, ttl=300)
        return session_data

    async def list_user_sessions(self, user_id: str):
        sessions = await SessionService.get_user_sessions(user_id)
        return {
            "user_id": user_id,
            "sessions": sessions,
            "total_count": len(sessions)
        }

    async def get_session_requirements(self, session_id: str):
        cache_key = f"requirements:{session_id}"
        cached_requirements = await redis_manager.get(cache_key)

        if cached_requirements:
            return cached_requirements
        requirements = await db_manager.get_requirements(session_id)
        result =  {
            "session_id": session_id,
            "requirements": requirements,
            "total_count": len(requirements)
        }
        await redis_manager.set(cache_key, result, ttl=120)
        return result

    async def update_requirements(self, session_id: str, request: Request):
        data = await request.json()
        requirements = data.get('requirements', [])
        if not requirements:
            raise HTTPException(status_code=400, detail="Requirements list is required")
        result = await db_manager.update_requirements(session_id, requirements)
        await redis_manager.delete(f"requirements:{session_id}")
        await redis_manager.delete(f"session:{session_id}")
        return {
            **result,
            "message": f"Successfully updated {result['updated_count']} requirements"
        }

    async def add_new_requirement(self, session_id: str, request: Request):
        data = await request.json()
        content = data.get('content')
        req_type = data.get('type', 'functional')
        priority = data.get('priority', 'medium')
        if not content:
            raise HTTPException(status_code=400, detail="Requirement content is required")
        result = await db_manager.add_requirement(session_id, content, req_type)
        return {
            **result,
            "message": "New requirement added successfully"
        }

    async def delete_requirement(self, session_id: str, requirement_id: str):
        try:
            async with db_manager.pool.acquire() as conn:
                await conn.execute('''
                    UPDATE requirements SET status = 'deleted', updated_at = NOW()
                    WHERE id = $1 AND session_id = $2
                ''', requirement_id, session_id)
            return {
                "status": "deleted",
                "requirement_id": requirement_id,
                "message": "Requirement deleted successfully"
            }
        except Exception as e:
            logger.error(f"Failed to delete requirement {requirement_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete requirement: {str(e)}")

    async def get_session_test_cases(self, session_id: str):
        cache_key = f"test_cases:{session_id}"
        cached_test_cases = await redis_manager.get(cache_key)
        if cached_test_cases:
            logger.info(f"✅ Cache hit for test cases: {session_id}")
            return cached_test_cases
        test_cases = await db_manager.get_test_cases(session_id)
        result =  {
            "session_id": session_id,
            "test_cases": test_cases,
            "total_count": len(test_cases)
        }
        await redis_manager.set(cache_key, result, ttl=120)
        return result

    async def regenerate_test_cases_for_requirement(self, session_id: str, requirement_id: str):
        try:
            requirements = await db_manager.get_requirements(session_id)
            target_req = next((r for r in requirements if r['id'] == requirement_id), None)
            if not target_req:
                raise HTTPException(status_code=404, detail="Requirement not found")

            requirement_text = target_req.get('edited_content') or target_req.get('original_content')
            agent_response = await generate_test_cases(
                session_context=None,
                prompt=f"Generate test cases for this requirement: {requirement_text}"
            )

            if agent_response['status'] == 'success':
                new_test_cases = parse_test_cases_from_agent_response(agent_response['response'])
                test_cases_with_links = [{
                    **tc,
                    'requirement_ids': [requirement_id]
                } for tc in new_test_cases]
                await db_manager.save_test_cases(session_id, test_cases_with_links)

                return {
                    "status": "regenerated",
                    "requirement_id": requirement_id,
                    "new_test_cases_count": len(new_test_cases),
                    "message": f"Generated {len(new_test_cases)} new test cases"
                }
            else:
                raise HTTPException(status_code=500, detail=f"Test generation failed: {agent_response['message']}")

        except Exception as e:
            logger.error(f"Failed to regenerate test cases for requirement {requirement_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Test case regeneration failed: {str(e)}")

    async def regenerate_all_test_cases(self, session_id: str):
        try:
            requirements = await db_manager.get_requirements(session_id)
            if not requirements:
                raise HTTPException(status_code=400, detail="No requirements found")

            updated_prompt = self._build_prompt_from_requirements(requirements)
            await self._clear_existing_test_cases(session_id)

            # ✅ CORRECT - Use the actual agent function
            agent_response = await generate_test_cases(session_context=None, prompt=updated_prompt)

            if agent_response['status'] == 'success':
                new_test_cases = parse_test_cases_from_agent_response(agent_response['response'])
                await db_manager.save_test_cases(session_id, new_test_cases)

                return {
                    "status": "regenerated_all",
                    "session_id": session_id,
                    "new_test_cases_count": len(new_test_cases),
                    "message": "All test cases regenerated successfully"
                }
            else:
                raise HTTPException(status_code=500, detail=f"Test regeneration failed: {agent_response['message']}")

        except Exception as e:
            logger.error(f"Failed to regenerate all test cases for session {session_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Test case regeneration failed: {str(e)}")

    async def get_coverage_report(self, session_id: str):
        try:
            report = await db_manager.get_coverage_report(session_id)
            return report
        except Exception as e:
            logger.error(f"Failed to get coverage report for session {session_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    from modules.cache.redis_manager import redis_manager  # Add this import

    async def fetch_and_save_rag_context(self, request: Request):
        """Fetch RAG context and save to database for agent access - Now with Redis caching!"""
        data = await request.json()
        prompt = data.get('prompt')
        session_id = data.get('session_id')
        user_id = data.get('user_id', 'default_user')
        project_name = data.get('project_name', 'RAG Context Session')
        context_scope = data.get('context_scope', 'comprehensive')
        enable_rag = data.get('enable_rag', True)

        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")

        if not session_id:
            session_id = f"rag_session_{uuid.uuid4().hex[:12]}"
            await db_manager.create_session(session_id, user_id, project_name, prompt)

        rag_context_array = []
        from_cache = False  # Track cache usage

        if enable_rag:
            # ✅ CORRECTED - Use session-based cache key for consistency
            cache_key = f"rag_context:{session_id}"
            cached_context = await redis_manager.get(cache_key)

            if cached_context:
                # 🚀 CACHE HIT - Ultra fast response!
                rag_context_array = cached_context
                from_cache = True
                logger.info(f"✅ Using cached RAG context for session {session_id}: {len(rag_context_array)} items")
            else:
                # 💾 CACHE MISS - Fetch from Vector Search (expensive)
                try:
                    rag_context_array = await get_rag_context_as_text_array_tool(
                        query_context=prompt,
                        context_scope=context_scope
                    )

                    # ✅ CORRECTED - Use permanent cache for session-based storage
                    if rag_context_array:
                        await redis_manager.set_permanent(cache_key, rag_context_array)
                        logger.info(f"✅ Permanently cached RAG context for session {session_id}: {len(rag_context_array)} items")
                    else:
                        logger.info("📭 No RAG context retrieved")

                except Exception as rag_error:
                    logger.warning(f"RAG context failed, continuing without: {rag_error}")

        # 📀 SAVE TO DATABASE (unchanged - your existing logic)
        if rag_context_array:
            await db_manager.save_requirements(session_id, rag_context_array)

            async with db_manager.pool.acquire() as conn:
                await conn.execute('''
                    UPDATE requirements
                    SET requirement_type = 'rag_context', priority = 'high'
                    WHERE session_id = $1 AND requirement_type = 'functional'
                ''', session_id)

        await db_manager.update_session_status(session_id, "rag_context_loaded")

        # ✅ ENHANCED RESPONSE with session-consistent information
        return {
            "session_id": session_id,
            "status": "success",
            "prompt": prompt,
            "rag_enabled": enable_rag,
            "rag_items_count": len(rag_context_array),
            "context_scope": context_scope,
            "from_cache": from_cache,
            "cache_key": f"rag_context:{session_id}",  # ✅ ADDED - Return the consistent cache key
            "cache_performance": "🚀 INSTANT" if from_cache else "🔍 FRESH_FETCH",
            "message": f"RAG context {'retrieved from cache' if from_cache else 'fetched and cached'}: {len(rag_context_array)} items",
            "database_saved": True
        }



    async def get_rag_context(self, session_id: str):
        """Get saved RAG context for a session"""
        try:
            async with db_manager.pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT original_content, created_at
                    FROM requirements
                    WHERE session_id = $1 AND requirement_type = 'rag_context'
                    ORDER BY created_at ASC
                ''', session_id)

            rag_items = [dict(row) for row in rows]

            return {
                "session_id": session_id,
                "rag_context": rag_items,
                "total_items": len(rag_items)
            }
        except Exception as e:
            logger.error(f"Failed to retrieve RAG context for session {session_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve RAG context: {str(e)}")

    # ===============================
    # PRIVATE HELPER METHODS
    # ===============================

    def _build_prompt_from_requirements(self, requirements: List[dict]) -> str:
        req_texts = [r.get('edited_content') or r.get('original_content') for r in requirements]
        return f"Generate comprehensive test cases for these requirements: {'; '.join(req_texts)}"

    async def _clear_existing_test_cases(self, session_id: str):
        async with db_manager.pool.acquire() as conn:
            await conn.execute('''
                UPDATE test_cases SET status = 'replaced'
                WHERE session_id = $1 AND status = 'active'
            ''', session_id)

    def _convert_to_csv_format(self, export_data: dict) -> dict:
        return {
            "format": "csv",
            "requirements_csv": "requirement_id,content,type,priority\n...",
            "test_cases_csv": "test_id,name,description,steps,expected_result\n..."
        }

# ===============================
# SESSION CONTROLLER INSTANCE
# ===============================

session_controller = SessionAPIController()

# ===============================
# API ROUTES - FIXED
# ===============================

@router.post("/sessions")
async def create_session(request: Request):
    return await session_controller.create_simple_session(request)

@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    return await session_controller.get_session(session_id)

@router.get("/users/{user_id}/sessions")
async def list_user_sessions(user_id: str):
    return await session_controller.list_user_sessions(user_id)

@router.get("/sessions/{session_id}/requirements")
async def get_requirements(session_id: str):
    return await session_controller.get_session_requirements(session_id)

@router.put("/sessions/{session_id}/requirements")
async def update_requirements(session_id: str, request: Request):
    return await session_controller.update_requirements(session_id, request)

@router.post("/sessions/{session_id}/requirements")
async def add_requirement(session_id: str, request: Request):
    return await session_controller.add_new_requirement(session_id, request)

@router.delete("/sessions/{session_id}/requirements/{requirement_id}")
async def delete_requirement(session_id: str, requirement_id: str):
    return await session_controller.delete_requirement(session_id, requirement_id)

@router.get("/sessions/{session_id}/test-cases")
async def get_test_cases(session_id: str):
    return await session_controller.get_session_test_cases(session_id)

@router.post("/sessions/{session_id}/test-cases/regenerate/{requirement_id}")
async def regenerate_tests(session_id: str, requirement_id: str):
    return await session_controller.regenerate_test_cases_for_requirement(session_id, requirement_id)

@router.post("/sessions/{session_id}/test-cases/regenerate-all")
async def regenerate_all_tests(session_id: str):
    return await session_controller.regenerate_all_test_cases(session_id)

@router.get("/sessions/{session_id}/coverage-report")
async def coverage_report(session_id: str):
    return await session_controller.get_coverage_report(session_id)

@router.get("/sessions/{session_id}/analytics")
async def session_analytics(session_id: str):
    return await session_controller.get_session_analytics(session_id)

@router.get("/sessions/{session_id}/export")
async def export_session(session_id: str, format: str = "json"):
    return await session_controller.export_session_data(session_id, format)

# RAG ENDPOINTS
@router.post("/rag/fetch-and-save")
async def fetch_and_save_rag_context(request: Request):
    return await session_controller.fetch_and_save_rag_context(request)

@router.get("/rag/{session_id}")
async def get_rag_context(session_id: str):
    return await session_controller.get_rag_context(session_id)
