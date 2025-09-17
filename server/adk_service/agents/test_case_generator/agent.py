from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types
from google.adk.tools import ToolContext
from typing import List, Dict, Any
from google.adk.sessions import InMemorySessionService, Session
from google.adk.runners import Runner

async def retrieve_requirements_context_tool(tool_context: ToolContext = None):
    if not tool_context:
        return {"status": "error", "message": "Tool context not available"}

    analyzed_context = tool_context.state.get("analyzed_requirements_context")
    ready_for_generation = tool_context.state.get("ready_for_test_generation", False)

    if not analyzed_context or not ready_for_generation:
        return {
            "status": "error",
            "message": "Requirements context not found in session state. Please run Requirements Analyzer first.",
            "available_state_keys": list(tool_context.state.keys())
        }

    requirements_analysis = analyzed_context.get("requirements_analysis", {})
    test_context = analyzed_context.get("test_context", {})
    metadata = analyzed_context.get("metadata", {})

    return {
        "status": "success",
        "message": "Requirements context successfully retrieved from session state",
        "context_data": {
            "original_requirements": metadata.get("original_requirements", []),
            "functional_requirements": requirements_analysis.get("functional_requirements", []),
            "non_functional_requirements": requirements_analysis.get("non_functional_requirements", []),
            "business_rules": requirements_analysis.get("business_rules", []),
            "user_stories": requirements_analysis.get("user_stories", []),
            "acceptance_criteria": requirements_analysis.get("acceptance_criteria", []),
            "integration_points": requirements_analysis.get("integration_points", []),
            "critical_flows": test_context.get("critical_flows", []),
            "edge_cases_identified": test_context.get("edge_cases_identified", []),
            "risk_areas": test_context.get("risk_areas", []),
            "analysis_depth": metadata.get("analysis_depth", ""),
            "source_count": metadata.get("source_count", 0)
        },
        "context_available": True
    }

test_case_generator_agent = Agent(
    model="gemini-2.5-flash",
    name="test_case_generator_agent",
    description="Generates comprehensive test cases from retrieved session context",
    instruction="""
    You are an expert Test Case Generator specializing in authentication systems.

    ## Your Job:
    1. Use `retrieve_requirements_context_tool` to get the analyzed requirements from session state
    2. Based on the retrieved context, generate comprehensive test cases directly in your response
    3. Create detailed, professional test cases in the required format
    4. Do NOT use any tool for test case generation - generate them yourself based on context

    ## Process:
    1. First, call `retrieve_requirements_context_tool` to get the requirements context
    2. Analyze the returned context data (original_requirements, business_rules, critical_flows, etc.)
    3. Generate comprehensive test cases covering all aspects
    4. Present them in a professional, structured format

    ## Test Case Types to Generate:
    - **Functional Tests**: Core authentication functionality based on functional_requirements
    - **Security Tests**: Based on business_rules and risk_areas
    - **Edge Cases**: Based on edge_cases_identified and critical_flows
    - **Negative Tests**: Input validation and error handling scenarios

    ## Required Test Case Format:
    For each test case, include:
    - test_id: Unique identifier (TC_FUNC_001, TC_SEC_001, etc.)
    - priority: high/medium/low/critical
    - summary: Brief description of what is being tested
    - preconditions: What must be true before test execution
    - test_steps: Numbered, detailed steps to execute
    - expected_result: Clear, specific expected outcome
    - test_data: Specific data needed for the test
    - requirement_traceability: Link back to original requirement

    ## Quality Standards:
    - Generate detailed, executable test steps that a QA engineer can follow
    - Ensure clear expected results with specific criteria
    - Provide specific test data requirements and examples
    - Maintain full traceability to original requirements from context
    - Use appropriate priority levels based on risk and business impact
    - Cover both positive and negative test scenarios
    - Include boundary conditions and edge cases

    ## Important Notes:
    - Always retrieve context first using the tool
    - Generate test cases based on the actual retrieved context, not assumptions
    - If context is missing, inform the user and request Requirements Analyzer to run first
    - Organize test cases by type (functional, security, edge case, negative)
    - Provide a summary of total test cases generated

    Remember: You retrieve context via tool call, but generate all test cases directly in your response!
    """,
    tools=[retrieve_requirements_context_tool],
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_budget=4096)
    ),
)

async def generate_test_cases(session_id: str = None, prompt: str = "", analysis_depth: str = "comprehensive") -> Dict[str, Any]:
    try:
        # Create or reuse session service
        session_service = InMemorySessionService()

        # If session_id is provided, use it; otherwise create a new session
        if session_id:
            # Retrieve existing session to maintain context
            session = await session_service.get_session(
                app_name="test_case_generator",
                user_id="user_123",
                session_id=session_id
            )
        else:
            # Create new session
            session = await session_service.create_session(
                app_name="test_case_generator",
                user_id="user_123"
            )

        # Create runner with the test case generator agent
        runner = Runner(
            agent=test_case_generator_agent,
            app_name="test_case_generator",
            session_service=session_service
        )

        # Prepare the prompt with analysis depth context
        full_prompt = f"""
        Generate comprehensive test cases based on the requirements context available in session state.

        Analysis Depth: {analysis_depth}
        Additional Instructions: {prompt}

        Please use the retrieve_requirements_context_tool to get the analyzed requirements from session state,
        then generate detailed test cases based on that context.
        """

        content = types.Content(
            role='user',
            parts=[types.Part(text=full_prompt)]
        )

        # Run and collect response
        events = runner.run_async(
            user_id="user_123",
            session_id=session.id,
            new_message=content
        )

        response_text = ""
        async for event in events:
            if event.is_final_response():
                response_text = event.content.parts[0].text
                break

        # Extract session state to check what context was available
        session_state = session.state if hasattr(session, 'state') else {}
        context_available = session_state.get("analyzed_requirements_context") is not None

        return {
            "status": "success",
            "response": response_text,
            "agent_used": "test_case_generator_agent",
            "session_id": session.id,
            "context_available": context_available,
            "session_state_keys": list(session_state.keys()) if session_state else []
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "agent_used": "test_case_generator_agent"
        }
