import json
import re
from typing import List, Dict, Any

def parse_test_cases_from_agent_response(agent_response: Any) -> List[Dict]:
    """Centralized test case parsing logic"""
    test_cases = []

    if hasattr(agent_response, 'text'):
        text_content = agent_response.text
    elif isinstance(agent_response, dict):
        text_content = agent_response.get('text', str(agent_response))
    else:
        text_content = str(agent_response)

    try:
        # Try to parse as JSON first
        if text_content.strip().startswith('{') or text_content.strip().startswith('['):
            try:
                parsed = json.loads(text_content)
                if isinstance(parsed, list):
                    test_cases = parsed
                elif isinstance(parsed, dict) and 'test_cases' in parsed:
                    test_cases = parsed['test_cases']
                elif isinstance(parsed, dict):
                    # If it's a dict but doesn't have 'test_cases', assume it's a single test case
                    test_cases = [parsed]
            except json.JSONDecodeError as e:
                print(f"JSONDecodeError: {e}")
                pass  # Ignore JSON parsing errors and try other methods


        # If still no test cases, try to extract from structured content
        if not test_cases and isinstance(agent_response, dict) and 'content' in agent_response:
            content = agent_response['content']
            if isinstance(content, list):
                for item in content:
                    # Check for different possible keys for test case data
                    test_name = item.get('test_name') or item.get('name', 'Generated Test')
                    test_description = item.get('test_description') or item.get('description', '')
                    test_steps = item.get('test_steps') or item.get('steps', [])
                    expected_results = item.get('expected_results') or item.get('expected_result', '')
                    test_type = item.get('test_type') or item.get('type', 'functional')
                    priority = item.get('priority', 'medium')

                    test_cases.append({
                        'test_name': test_name,
                        'test_description': test_description,
                        'test_steps': test_steps,
                        'expected_results': expected_results,
                        'test_type': test_type,
                        'priority': priority
                    })
            elif isinstance(content, dict):
                # Handle the case where 'content' is a dictionary representing a single test case
                test_name = content.get('test_name') or content.get('name', 'Generated Test')
                test_description = content.get('test_description') or content.get('description', '')
                test_steps = content.get('test_steps') or content.get('steps', [])
                expected_results = content.get('expected_results') or content.get('expected_result', '')
                test_type = content.get('test_type') or content.get('type', 'functional')
                priority = content.get('priority', 'medium')

                test_cases.append({
                    'test_name': test_name,
                    'test_description': test_description,
                    'test_steps': test_steps,
                    'expected_results': expected_results,
                    'test_type': test_type,
                    'priority': priority
                })

    except Exception as e:
        print(f"Error parsing test cases: {e}")

    return test_cases

def parse_test_cases_from_text(text_content: str) -> List[Dict]:
    """Parse test cases from plain text content"""
    test_cases = []
    try:
        if text_content.strip().startswith('{') or text_content.strip().startswith('['):
            parsed = json.loads(text_content)
            if isinstance(parsed, list):
                test_cases = parsed
            elif isinstance(parsed, dict) and 'test_cases' in parsed:
                test_cases = parsed['test_cases']
    except json.JSONDecodeError:
        pass

    return test_cases

def extract_requirements_from_workflow(workflow_result: List[dict]) -> List[str]:
    """Extract requirements from workflow response"""
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

def extract_test_cases_from_workflow(workflow_result: List[dict]) -> List[dict]:
    """Extract test cases from workflow response"""
    test_cases = []
    for result in workflow_result:
        if result.get('author') == 'test_case_generator_agent':
            content_parts = result.get('content', {}).get('parts', [])
            for part in content_parts:
                if part.get('text'):
                    parsed_tests = parse_test_cases_from_text(part.get('text'))
                    test_cases.extend(parsed_tests)
    return test_cases

def extract_requirements_from_agent_response(agent_response: Any) -> List[str]:
    """Extract requirements from agent response"""
    requirements = []

    if hasattr(agent_response, 'text'):
        text_content = agent_response.text
    elif isinstance(agent_response, dict):
        text_content = agent_response.get('text', str(agent_response))
    else:
        text_content = str(agent_response)

    try:
        requirement_patterns = [
            r'requirement[s]?:\s*(.+?)(?=\n|$)',
            r'REQ-\d+:\s*(.+?)(?=\n|$)',
            r'•\s*(.+?)(?=\n|$)',
            r'-\s*(.+?)(?=\n|$)'
        ]

        for pattern in requirement_patterns:
            matches = re.findall(pattern, text_content, re.IGNORECASE)
            requirements.extend(matches)

    except Exception as e:
        print(f"Error extracting requirements: {e}")

    return requirements[:10] if requirements else ["Default requirement extracted from agent response"]
