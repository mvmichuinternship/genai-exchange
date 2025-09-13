from google.adk.agents import SequentialAgent
from google.genai import types

# Import your individual agents
from requirement_analyzer.agent import requirement_analyzer_agent
from test_case_generator.agent import test_case_generator_agent

# Sequential workflow agent
root_agent = SequentialAgent(
    name="sequential_workflow",
    description="Sequential workflow: Requirements Analysis → Test Case Generation with shared context",
    sub_agents=[
        requirement_analyzer_agent,
        test_case_generator_agent
    ]
)