from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai import types
from google.adk.tools import ToolContext
from typing import List, Dict, Any


async def retrieve_requirements_context_tool(
    tool_context: ToolContext = None
):
    """
    Retrieve requirements context from session state - agent will generate test cases based on this
    """

    if not tool_context:
        return {
            "status": "error",
            "message": "Tool context not available"
        }

    # Retrieve context from session state using ToolContext.state
    analyzed_context = tool_context.state.get("analyzed_requirements_context")
    ready_for_generation = tool_context.state.get("ready_for_test_generation", False)

    if not analyzed_context or not ready_for_generation:
        return {
            "status": "error",
            "message": "Requirements context not found in session state. Please run Requirements Analyzer first.",
            "available_state_keys": list(tool_context.state.keys())
        }

    # Extract and return all relevant data for the agent to use
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


# Test Case Generator Agent
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
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=4096,
        )
    ),
)