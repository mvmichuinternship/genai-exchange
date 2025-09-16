from fastapi import APIRouter, HTTPException, Request
import uuid
import json
from typing import List, Dict, Any, Optional
from ..modules.database.database_manager import db_manager
from ..modules.database.session_service import SessionService
from .adk_integrated_controller import ADKController  # Your existing controller

class SessionAPIController:
    def __init__(self):
        self.adk_controller = ADKController()  # Instance of your existing controller

    # ===============================
    # SESSION MANAGEMENT APIs
    # ===============================

    async def create_session_and_run_workflow(self, request: Request):
        """Create session + run your existing ADK workflow"""
        data = await request.json()
        user_id = data.get('user_id', 'default_user')
        project_name = data.get('project_name', 'New Project')
        user_prompt = data.get('prompt')

        if not user_prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")

        # Generate session ID
        session_id = f"session_{uuid.uuid4().hex[:12]}"

        try:
            # 1. Create session in database
            await db_manager.create_session(session_id, user_id, project_name, user_prompt)

            # 2. Call your existing ADK workflow (no changes to your existing code)
            workflow_response = await self.adk_controller.run_sequential_workflow(user_prompt)

            # 3. Extract and save results to database
            await self._extract_and_save_workflow_results(session_id, workflow_response)

            # 4. Update session status
            await db_manager.update_session_status(session_id, "completed")

            # 5. Return enhanced response
            return {
                **workflow_response,  # Your exact existing response
                "session_id": session_id,
                "user_id": user_id,
                "project_name": project_name,
                "database_saved": True
            }

        except Exception as e:
            await db_manager.update_session_status(session_id, "failed")
            raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")

    async def get_session(self, session_id: str):
        """Get session with summary data"""
        try:
            session_data = await SessionService.get_session_summary(session_id)
            if not session_data:
                raise HTTPException(status_code=404, detail="Session not found")
            return session_data
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def list_user_sessions(self, user_id: str):
        """Get all sessions for a user"""
        try:
            sessions = await SessionService.get_user_sessions(user_id)
            return {
                "user_id": user_id,
                "sessions": sessions,
                "total_count": len(sessions)
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ===============================
    # REQUIREMENTS MANAGEMENT APIs
    # ===============================

    async def get_session_requirements(self, session_id: str):
        """Get requirements for user editing"""
        try:
            requirements = await db_manager.get_requirements(session_id)
            return {
                "session_id": session_id,
                "requirements": requirements,
                "total_count": len(requirements)
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def update_requirements(self, session_id: str, request: Request):
        """Save user-edited requirements"""
        try:
            data = await request.json()
            requirements = data.get('requirements', [])

            if not requirements:
                raise HTTPException(status_code=400, detail="Requirements list is required")

            result = await db_manager.update_requirements(session_id, requirements)
            return {
                **result,
                "message": f"Successfully updated {result['updated_count']} requirements"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def add_new_requirement(self, session_id: str, request: Request):
        """Add new user requirement"""
        try:
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
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def delete_requirement(self, session_id: str, requirement_id: str):
        """Soft delete a requirement"""
        try:
            async with db_manager.pool.acquire() as conn:
                await conn.execute('''
                    UPDATE requirements
                    SET status = 'deleted', updated_at = NOW()
                    WHERE id = $1 AND session_id = $2
                ''', requirement_id, session_id)

            return {
                "status": "deleted",
                "requirement_id": requirement_id,
                "message": "Requirement deleted successfully"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ===============================
    # TEST CASE MANAGEMENT APIs
    # ===============================

    async def get_session_test_cases(self, session_id: str):
        """Get generated test cases with requirement links"""
        try:
            test_cases = await db_manager.get_test_cases(session_id)
            return {
                "session_id": session_id,
                "test_cases": test_cases,
                "total_count": len(test_cases)
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def regenerate_test_cases_for_requirement(self, session_id: str, requirement_id: str):
        """Regenerate test cases for specific requirement"""
        try:
            # Get the requirement (including user edits)
            requirements = await db_manager.get_requirements(session_id)
            target_req = next((r for r in requirements if r['id'] == requirement_id), None)

            if not target_req:
                raise HTTPException(status_code=404, detail="Requirement not found")

            # Call your existing test generation logic for single requirement
            new_test_cases = await self._generate_test_cases_for_requirement(target_req)

            # Save with requirement links
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
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def regenerate_all_test_cases(self, session_id: str):
        """Regenerate all test cases for the session"""
        try:
            # Get all current requirements (including user edits)
            requirements = await db_manager.get_requirements(session_id)

            if not requirements:
                raise HTTPException(status_code=400, detail="No requirements found")

            # Use your existing test generation workflow with updated requirements
            updated_prompt = self._build_prompt_from_requirements(requirements)
            new_workflow_response = await self.adk_controller.run_test_generation_only(updated_prompt)

            # Clear existing test cases and save new ones
            await self._clear_existing_test_cases(session_id)
            await self._extract_and_save_test_cases_only(session_id, new_workflow_response)

            # Get updated test cases
            new_test_cases = await db_manager.get_test_cases(session_id)

            return {
                "status": "regenerated_all",
                "session_id": session_id,
                "new_test_cases_count": len(new_test_cases),
                "message": "All test cases regenerated successfully"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ===============================
    # ANALYTICS & REPORTING APIs
    # ===============================

    async def get_coverage_report(self, session_id: str):
        """Get requirements coverage report"""
        try:
            report = await db_manager.get_coverage_report(session_id)
            return report
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_session_analytics(self, session_id: str):
        """Get session analytics"""
        try:
            session = await db_manager.get_session(session_id)
            requirements = await db_manager.get_requirements(session_id)
            test_cases = await db_manager.get_test_cases(session_id)
            coverage = await db_manager.get_coverage_report(session_id)

            # Calculate additional metrics
            edited_requirements = sum(1 for r in requirements if r.get('edited_content'))
            user_created_requirements = sum(1 for r in requirements if r.get('status') == 'user_created')

            return {
                "session_id": session_id,
                "session_info": session,
                "metrics": {
                    "total_requirements": len(requirements),
                    "edited_requirements": edited_requirements,
                    "user_created_requirements": user_created_requirements,
                    "total_test_cases": len(test_cases),
                    "coverage_percentage": coverage.get('coverage_percentage', 0)
                },
                "coverage_summary": coverage
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ===============================
    # EXPORT APIs
    # ===============================

    async def export_session_data(self, session_id: str, format_type: str = "json"):
        """Export complete session data"""
        try:
            session = await db_manager.get_session(session_id)
            requirements = await db_manager.get_requirements(session_id)
            test_cases = await db_manager.get_test_cases(session_id)

            export_data = {
                "session": session,
                "requirements": requirements,
                "test_cases": test_cases,
                "exported_at": "2025-09-16T18:06:00Z"
            }

            if format_type.lower() == "csv":
                # Convert to CSV format for ALM tools
                return self._convert_to_csv_format(export_data)
            else:
                return export_data

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # ===============================
    # HELPER METHODS
    # ===============================

    async def _extract_and_save_workflow_results(self, session_id: str, workflow_response: dict):
        """Extract and save results from your existing workflow"""
        try:
            # Extract requirements
            requirements = self._extract_requirements_from_workflow(workflow_response.get('workflow_result', []))
            if requirements:
                await db_manager.save_requirements(session_id, requirements)

            # Extract test cases
            test_cases = self._extract_test_cases_from_workflow(workflow_response.get('workflow_result', []))
            if test_cases:
                await db_manager.save_test_cases(session_id, test_cases)

        except Exception as e:
            print(f"Warning: Could not extract workflow results: {e}")

    def _extract_requirements_from_workflow(self, workflow_result: List[dict]) -> List[str]:
        """Extract requirements from requirement_analyzer_agent"""
        requirements = []

        for result in workflow_result:
            if result.get('author') == 'requirement_analyzer_agent':
                actions = result.get('actions', {})
                state_delta = actions.get('stateDelta', {})
                req_context = state_delta.get('analyzed_requirements_context', {})

                if req_context:
                    functional_reqs = req_context.get('requirements_analysis', {}).get('functional_requirements', [])
                    requirements.extend(functional_reqs)

        return requirements

    def _extract_test_cases_from_workflow(self, workflow_result: List[dict]) -> List[dict]:
        """Extract test cases from test_case_generator_agent"""
        test_cases = []

        for result in workflow_result:
            if result.get('author') == 'test_case_generator_agent':
                # Parse test cases from agent output
                # This depends on your agent's exact response format
                # You'll need to customize this based on your agent structure
                pass

        return test_cases

    async def _generate_test_cases_for_requirement(self, requirement: dict) -> List[dict]:
        """Use your existing agent to generate tests for single requirement"""
        # Call your test generation agent with single requirement
        # This depends on your existing agent structure
        return []

    def _build_prompt_from_requirements(self, requirements: List[dict]) -> str:
        """Build prompt from current requirements for regeneration"""
        req_texts = [r.get('edited_content') or r.get('original_content') for r in requirements]
        return f"Generate test cases for these requirements: {'; '.join(req_texts)}"

    async def _clear_existing_test_cases(self, session_id: str):
        """Mark existing test cases as inactive"""
        async with db_manager.pool.acquire() as conn:
            await conn.execute('''
                UPDATE test_cases
                SET status = 'replaced'
                WHERE session_id = $1 AND status = 'active'
            ''', session_id)

    def _convert_to_csv_format(self, export_data: dict) -> dict:
        """Convert export data to CSV-friendly format for ALM tools"""
        # Convert to format suitable for ALM tool import
        return {
            "format": "csv",
            "requirements_csv": "requirement_id,content,type,priority\n...",
            "test_cases_csv": "test_id,name,description,steps,expected_result\n..."
        }

# Create router instance for FastAPI
router = APIRouter()

# Initialize controller
session_controller = SessionAPIController()

# Define routes
@router.post("/sessions")
async def create_session(request: Request):
    return await session_controller.create_session_and_run_workflow(request)

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
