from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types
from google.adk.tools import ToolContext
from typing import List, Dict, Any

async def analyze_requirements_context_tool(
    text_array: List[str],
    analysis_depth: str = "comprehensive",
    tool_context: ToolContext = None
):
    """
    Analyze requirements and store context in session state
    """

    # Validate input
    if not text_array:
        return {
            "status": "error",
            "message": "No requirements provided for analysis"
        }

    if not tool_context:
        return {
            "status": "error",
            "message": "ToolContext is required for session state storage"
        }

    try:
        # Create structured analysis context
        analyzed_context = {
            "requirements_analysis": {
                "functional_requirements": [f"Functional requirement: {req}" for req in text_array],
                "non_functional_requirements": [
                    "System performance requirements",
                    "Security and authentication requirements",
                    "Usability and accessibility requirements"
                ],
                "business_rules": [
                    "Email format validation required",
                    "Password complexity rules must be enforced",
                    "Account lockout policy after failed attempts"
                ],
                "user_stories": [f"As a user, I want to {req.lower()}" for req in text_array],
                "acceptance_criteria": [
                    "User can successfully authenticate with valid credentials",
                    "Invalid credentials are properly rejected",
                    "Account lockout activates after specified failed attempts"
                ],
                "integration_points": [
                    "Email service for notifications",
                    "User database for credential storage",
                    "Session management service"
                ]
            },
            "test_context": {
                "critical_flows": [
                    "Successful user authentication flow",
                    "Failed authentication and lockout flow",
                    "Password reset and recovery flow"
                ],
                "edge_cases_identified": [
                    "Boundary conditions for failed attempt counting",
                    "Concurrent login attempts",
                    "Password complexity edge cases"
                ],
                "risk_areas": [
                    "Security vulnerabilities in authentication",
                    "Account lockout mechanism reliability",
                    "Session management security"
                ]
            },
            "metadata": {
                "analysis_depth": analysis_depth,
                "source_count": len(text_array),
                "original_requirements": text_array
            }
        }

        # Store in session state using ToolContext.state (NOT tool_context.session.state)
        tool_context.state["analyzed_requirements_context"] = analyzed_context
        tool_context.state["ready_for_test_generation"] = True

        return {
            "status": "success",
            "message": f"Successfully analyzed {len(text_array)} requirements",
            "analysis_summary": analyzed_context["metadata"],
            "context_stored_in_session": True
        }

    except AttributeError as e:
        return {
            "status": "error",
            "message": f"ToolContext error: {str(e)}. Make sure you're using tool_context.state, not tool_context.session.state"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Requirements analysis failed: {str(e)}"
        }

# Requirements Analyzer Agent
requirement_analyzer_agent = Agent(
    model="gemini-2.5-flash-lite",
    name="requirement_analyzer_agent",
    description="Analyzes requirements and stores context in session state",
    instruction="""
    You are an expert Requirements Analyzer specializing in authentication systems.

    ## Your Job:
    1. Take textual requirements as input
    2. Analyze them thoroughly using domain expertise
    3. Store structured context in session state for the Test Case Generator
    4. Focus on security, usability, and reliability aspects

    ## Key Process:
    - Use `analyze_requirements_context_tool` to process the requirements
    - The tool will automatically store the analysis in session state
    - This context will be available to the next agent in the sequential workflow

    ## Analysis Focus:
    - Extract functional and non-functional requirements
    - Identify security requirements and business rules
    - Map critical user flows and edge cases
    - Identify integration points and risk areas

    ## Important:
    - Always pass the ToolContext parameter when calling the tool
    - The tool uses tool_context.state (not tool_context.session.state)
    - Verify successful context storage before completing the task

    Always use the tool to ensure proper context storage for the next agent.
    """,
    tools=[analyze_requirements_context_tool],
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=3072,
        )
    ),
)