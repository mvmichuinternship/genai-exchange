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
            parsed = json.loads(text_content)
            if isinstance(parsed, list):
                test_cases = parsed
            elif isinstance(parsed, dict) and 'test_cases' in parsed:
                test_cases = parsed['test_cases']

        # If direct parsing failed, look for test case patterns
        if not test_cases and 'TC_' in text_content:
            test_case_pattern = r'TC_(\w+)_(\d+)'
            matches = re.findall(test_case_pattern, text_content)

            for category, number in matches:
                test_id = f"TC_{category}_{number}"
                test_cases.append({
                    'test_name': f'Test Case {test_id}',
                    'test_description': f'Generated test case for {category.lower()} testing',
                    'test_steps': ['Navigate to application', 'Perform test action', 'Verify result'],
                    'expected_results': 'Expected behavior should be observed',
                    'test_type': category.lower() if category.lower() in ['functional', 'security', 'edge', 'negative'] else 'functional',
                    'priority': 'high' if category.upper() == 'SEC' else 'medium'
                })

        # If still no test cases, try to extract from structured content
        if not test_cases and isinstance(agent_response, dict) and 'content' in agent_response:
            content = agent_response['content']
            if isinstance(content, list):
                for item in content:
                    if item.get('type') == 'test_case':
                        test_cases.append({
                            'test_name': item.get('name', 'Generated Test'),
                            'test_description': item.get('description', ''),
                            'test_steps': item.get('steps', []),
                            'expected_results': item.get('expected_result', ''),
                            'test_type': item.get('test_type', 'functional'),
                            'priority': item.get('priority', 'medium')
                        })

    except json.JSONDecodeError:
        # If JSON parsing fails, create a default test case
        test_cases = [{
            'test_name': 'Generated Test Case',
            'test_description': 'Test case generated from agent response',
            'test_steps': ['Execute test based on requirements'],
            'expected_results': 'System should behave as expected',
            'test_type': 'functional',
            'priority': 'medium'
        }]
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
