import logging
from fastapi import APIRouter, HTTPException, Request
import uuid
from typing import List

from modules.database.database_manager import db_manager
from adk_service.agents.requirement_analyzer.agent import analyze_requirements
from utils.parsers import extract_requirements_from_agent_response

router = APIRouter()
logger = logging.getLogger(__name__)

class RequirementsController:

    async def analyze_requirements_endpoint(self, request: Request):
        """Analyze requirements using the requirement analyzer agent"""
        data = await request.json()
        user_id = data.get('user_id', 'default_user')
        project_name = data.get('project_name', 'Requirements Analysis')
        session_id = data.get('session_id')
        requirements_input = data.get('requirements', [])
        analysis_depth = data.get('analysis_depth', 'comprehensive')

        if not requirements_input:
            raise HTTPException(status_code=400, detail="Requirements input is required")

        if not session_id:
            session_id = f"req_session_{uuid.uuid4().hex[:12]}"
            await db_manager.create_session(session_id, user_id, project_name, "Requirements Analysis")

        try:
            # Call the agent function
            agent_response = await analyze_requirements(requirements_input, analysis_depth)

            if agent_response['status'] == 'success':
                # Extract requirements from agent response
                extracted_requirements = extract_requirements_from_agent_response(agent_response['response'])

                # Save to database
                if extracted_requirements:
                    await db_manager.save_requirements(session_id, extracted_requirements)

                await db_manager.update_session_status(session_id, "requirements_analyzed")

                return {
                    "session_id": session_id,
                    "status": "success",
                    "analysis_depth": analysis_depth,
                    "original_input_count": len(requirements_input),
                    "analyzed_requirements_count": len(extracted_requirements),
                    "requirements": agent_response,
                    "agent_used": agent_response['agent_used'],
                    "message": "Requirements successfully analyzed and stored"
                }
            else:
                await db_manager.update_session_status(session_id, "analysis_failed")
                raise HTTPException(status_code=500, detail=f"Analysis failed: {agent_response['message']}")

        except Exception as e:
            logger.error(f"Requirements analysis failed for session {session_id}: {e}")
            await db_manager.update_session_status(session_id, "analysis_failed")
            raise HTTPException(status_code=500, detail=f"Requirements analysis failed: {str(e)}")

    async def get_requirements(self, session_id: str):
        """Get requirements for a session"""
        requirements = await db_manager.get_requirements(session_id)
        return {
            "session_id": session_id,
            "requirements": requirements,
            "total_count": len(requirements)
        }

    async def update_requirements(self, session_id: str, request: Request):
        """Update requirements after user edits"""
        data = await request.json()
        requirements = data.get('requirements', [])

        if not requirements:
            raise HTTPException(status_code=400, detail="Requirements list is required")

        result = await db_manager.update_requirements(session_id, requirements)
        return {
            **result,
            "message": f"Successfully updated {result['updated_count']} requirements"
        }

requirements_controller = RequirementsController()

# Routes
@router.post("/analyze")
async def analyze_requirements_endpoint(request: Request):
    return await requirements_controller.analyze_requirements_endpoint(request)

@router.get("/{session_id}")
async def get_requirements(session_id: str):
    return await requirements_controller.get_requirements(session_id)

@router.put("/{session_id}")
async def update_requirements(session_id: str, request: Request):
    return await requirements_controller.update_requirements(session_id, request)
