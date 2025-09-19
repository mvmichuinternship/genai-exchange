from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types
from google.adk.tools import ToolContext
from typing import List, Dict, Any
from google.adk.sessions import InMemorySessionService, Session
from google.adk.runners import Runner

async def retrieve_requirements_context_tool(requirements_input: str = "", tool_context: ToolContext = None):
    """
    Process and analyze requirements input directly instead of retrieving from session state
    """
    if not requirements_input:
        return {
            "status": "error",
            "message": "No requirements input provided. Please provide requirements text to analyze.",
        }

    # Basic analysis of requirements input
    requirements_lines = [line.strip() for line in requirements_input.split('\n') if line.strip()]

    # Simple categorization based on keywords (can be enhanced)
    functional_requirements = []
    non_functional_requirements = []
    business_rules = []

    for line in requirements_lines:
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in ['shall', 'must', 'should', 'function', 'feature']):
            functional_requirements.append(line)
        elif any(keyword in line_lower for keyword in ['performance', 'security', 'usability', 'reliability']):
            non_functional_requirements.append(line)
        elif any(keyword in line_lower for keyword in ['rule', 'policy', 'constraint', 'validation']):
            business_rules.append(line)
        else:
            functional_requirements.append(line)  # Default to functional

    return {
        "status": "success",
        "message": "Requirements input successfully processed",
        "context_data": {
            "original_requirements": requirements_lines,
            "functional_requirements": functional_requirements,
            "non_functional_requirements": non_functional_requirements,
            "business_rules": business_rules,
            "user_stories": [],  # Can be extracted if format is provided
            "acceptance_criteria": [],  # Can be extracted if format is provided
            "integration_points": [],  # Can be identified through analysis
            "critical_flows": [],  # Can be identified through analysis
            "edge_cases_identified": [],  # Can be identified through analysis
            "risk_areas": [],  # Can be identified through analysis
            "analysis_depth": "basic",
            "source_count": len(requirements_lines)
        },
        "context_available": True,
        "requirements_input": requirements_input
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
    - Provide a summary of total test cases
    - Return all the generated test cases as response
    - Generate the test cases in a properly structured format.One test case then a line space and then the next test case.

    Remember: You retrieve context via tool call, but generate all test cases directly in your response!
    """,
    tools=[retrieve_requirements_context_tool],
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_budget=4096)
    ),
)

async def generate_test_cases(session_id: str = None, prompt: str = "", analysis_depth: str = "comprehensive", requirements_input:str = "") -> Dict[str, Any]:
    try:
        # Create or reuse session service
        session_service = InMemorySessionService()

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
        Make use of the requirements for the test case generation: {requirements_input}

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


        return {
            "status": "success",
            "response": response_text,
            "agent_used": "test_case_generator_agent",
            "session_id": session.id,
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "agent_used": "test_case_generator_agent"
        }
