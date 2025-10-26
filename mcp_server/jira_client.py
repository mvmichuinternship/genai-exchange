"""
Jira Client Module
Handles all Jira API interactions for user stories and test cases
"""

import aiohttp
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class JiraClient:
    def __init__(self):
        self.base_url = None
        self.email = None
        self.api_token = None
        self.project_key = None
        self.headers = {}
        self.is_configured = False
    
    def configure(self, base_url: str, email: str, api_token: str, project_key: str):
        """Configure Jira connection"""
        self.base_url = base_url.rstrip('/')
        self.email = email
        self.api_token = api_token
        self.project_key = project_key
        
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        self.is_configured = True
        logger.info(f"Jira client configured for project: {project_key}")
    
    async def test_connection(self) -> Dict:
        """Test the Jira connection"""
        if not self.is_configured:
            raise ValueError("Jira client not configured")
        
        url = f"{self.base_url}/rest/api/3/project/{self.project_key}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=self.headers,
                auth=aiohttp.BasicAuth(self.email, self.api_token)
            ) as response:
                result = {
                    "success": response.status == 200,
                    "status_code": response.status,
                    "project_key": self.project_key
                }
                
                if response.status == 200:
                    project_data = await response.json()
                    result["project_info"] = {
                        "id": project_data.get("id"),
                        "key": project_data.get("key"),
                        "name": project_data.get("name"),
                        "description": project_data.get("description", "")
                    }
                else:
                    result["error"] = await response.text()
                
                return result
    
    async def fetch_user_story(self, issue_key: str) -> Dict:
        """Fetch user story/issue details from Jira"""
        if not self.is_configured:
            raise ValueError("Jira client not configured")
        
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        params = {"fields": "*all"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=self.headers,
                params=params,
                auth=aiohttp.BasicAuth(self.email, self.api_token)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"Failed to fetch issue: {error_text}",
                        "status_code": response.status
                    }
                
                issue = await response.json()
                fields = issue.get("fields", {})
                
                #need to remove this log later
                logger.info(f"RAW JIRA FIELDS: {json.dumps(fields, indent=2)}")

                # Extract text from Atlassian Document Format (ADF)
                description_text = self._extract_adf_text(fields.get("description", {}))
                
                user_story_data = {
                    "success": True,
                    "key": issue.get("key"),
                    "id": issue.get("id"),
                    "title": fields.get("summary", ""),
                    "description": description_text,
                    "status": fields.get("status", {}).get("name", ""),
                    "issue_type": fields.get("issuetype", {}).get("name", ""),
                    "assigned_to": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
                    "created_date": fields.get("created", ""),
                    "updated_date": fields.get("updated", ""),
                    "labels": fields.get("labels", []),
                    "priority": fields.get("priority", {}).get("name") if fields.get("priority") else None,
                    "story_points": fields.get("customfield_10016"),  # Adjust field ID for your Jira
                    "acceptance_criteria": self._extract_adf_text(fields.get("customfield_10008", {})),  # Adjust
                    "relations": []
                }
                
                # Extract issue links
                issue_links = fields.get("issuelinks", [])
                for link in issue_links:
                    relation_data = {
                        "link_type": link.get("type", {}).get("name", ""),
                        "inward": link.get("inwardIssue", {}).get("key") if "inwardIssue" in link else None,
                        "outward": link.get("outwardIssue", {}).get("key") if "outwardIssue" in link else None
                    }
                    user_story_data["relations"].append(relation_data)
                
                return user_story_data
    
    async def fetch_testcases(self, story_key: str) -> Dict:
        """Fetch all test cases linked to a user story"""
        if not self.is_configured:
            raise ValueError("Jira client not configured")
        
        # First get the story to find linked test cases
        story = await self.fetch_user_story(story_key)
        
        if not story.get("success"):
            return story
        
        # Search for test cases linked to this story
        jql = f'project = {self.project_key} AND issuetype = Test AND issue in linkedIssues("{story_key}")'
        
        url = f"{self.base_url}/rest/api/3/search"
        params = {
            "jql": jql,
            "fields": "summary,status,priority,created,updated,assignee",
            "maxResults": 100
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=self.headers,
                params=params,
                auth=aiohttp.BasicAuth(self.email, self.api_token)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"Failed to fetch test cases: {error_text}",
                        "status_code": response.status
                    }
                
                data = await response.json()
                issues = data.get("issues", [])
                
                test_cases = []
                for issue in issues:
                    fields = issue.get("fields", {})
                    test_cases.append({
                        "id": issue.get("id"),
                        "key": issue.get("key"),
                        "title": fields.get("summary", ""),
                        "status": fields.get("status", {}).get("name", ""),
                        "priority": fields.get("priority", {}).get("name") if fields.get("priority") else None,
                        "created_date": fields.get("created", ""),
                        "updated_date": fields.get("updated", ""),
                        "assigned_to": fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None
                    })
                
                return {
                    "success": True,
                    "story_key": story_key,
                    "test_case_count": len(test_cases),
                    "test_cases": test_cases
                }
    
 

    # async def create_testcase(self, story_key: str, testcase_data: Dict) -> Dict:
    #     """Create a new test case linked to a user story"""
    #     if not self.is_configured:
    #         raise ValueError("Jira client not configured")
        
    #     # Extract test steps data
    #     test_steps_text = ""
    #     expected_results_text = ""
    #     preconditions_text = testcase_data.get("preconditions", "")
        
    #     if testcase_data.get("steps"):
    #         steps_list = []
    #         expected_list = []
            
    #         for i, step in enumerate(testcase_data["steps"], 1):
    #             action = step.get("action", "")
    #             expected = step.get("expected", "")
    #             steps_list.append(f"{i}. {action}")
    #             expected_list.append(f"{i}. {expected}")
            
    #         test_steps_text = "\n".join(steps_list)
    #         expected_results_text = "\n".join(expected_list)
        
    #     # Fallback: if no structured steps, use description
    #     if not test_steps_text:
    #         test_steps_text = testcase_data.get("description", "")
        
    #     # Format description for the Description field (overview)
    #     description_text = f"{testcase_data.get('description', '')}"
        
    #     # Map priority
    #     # priority_map = {"Critical": "Highest", "High": "High", "Medium": "Medium", "Low": "Low"}
    #     # priority = priority_map.get(testcase_data.get("priority", "Medium"), "Medium")
        
    #     # Create test case issue with custom fields
    #     payload = {
    #         "fields": {
    #             "project": {"key": self.project_key},
    #             "summary": testcase_data.get("title", "Generated Test Case"),
    #             "description": {
    #                 "type": "doc",
    #                 "version": 1,
    #                 "content": [{"type": "paragraph", "content": [{"type": "text", "text": description_text}]}]
    #             },
    #             "issuetype": {"name": "Test"},
    #             # "priority": {"name": priority},
    #             "labels": testcase_data.get("labels", []),
    #             # Custom fields for YOUR Jira project
    #             "customfield_10040": test_steps_text,  # Test Steps
    #             "customfield_10041": expected_results_text,  # Expected Results
    #             "customfield_10042": preconditions_text  # Preconditions
    #         }
    #     }
        
    #     url = f"{self.base_url}/rest/api/3/issue"
        
    #     async with aiohttp.ClientSession() as session:
    #         async with session.post(
    #             url,
    #             headers=self.headers,
    #             json=payload,
    #             auth=aiohttp.BasicAuth(self.email, self.api_token)
    #         ) as response:
    #             if response.status not in [200, 201]:
    #                 error_text = await response.text()
    #                 return {
    #                     "success": False,
    #                     "error": f"Failed to create test case: {error_text}",
    #                     "status_code": response.status
    #                 }
                
    #             test_case = await response.json()
    #             test_case_key = test_case.get("key")
                
    #             # Link to user story
    #             link_result = await self._link_test_case_to_story(test_case_key, story_key)
                
    #             return {
    #                 "success": True,
    #                 "test_case_key": test_case_key,
    #                 "test_case_id": test_case.get("id"),
    #                 "story_key": story_key,
    #                 "link_success": link_result.get("success", False),
    #                 "url": f"{self.base_url}/browse/{test_case_key}"
    #             }

    async def create_testcase(self, story_key: str, testcase_data: Dict) -> Dict:
        """Create a new test case linked to a user story"""
        if not self.is_configured:
            raise ValueError("Jira client not configured")
        
        # Helper function to convert text to ADF format
        def text_to_adf(text: str) -> Dict:
            """Convert plain text to Atlassian Document Format"""
            if not text:
                return {
                    "type": "doc",
                    "version": 1,
                    "content": []
                }
            
            # Split by newlines and create paragraphs
            lines = text.split('\n')
            paragraphs = []
            
            for line in lines:
                if line.strip():  # Skip empty lines
                    paragraphs.append({
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": line
                            }
                        ]
                    })
            
            return {
                "type": "doc",
                "version": 1,
                "content": paragraphs if paragraphs else [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": text}]
                    }
                ]
            }
        
        # Extract and format test steps
        test_steps_text = ""
        expected_results_text = ""
        
        if testcase_data.get("steps"):
            steps_list = []
            expected_list = []
            
            for i, step in enumerate(testcase_data["steps"], 1):
                action = step.get("action", "")
                expected = step.get("expected", "")
                steps_list.append(f"{i}. {action}")
                expected_list.append(f"{i}. {expected}")
            
            test_steps_text = "\n".join(steps_list)
            expected_results_text = "\n".join(expected_list)
        
        # Fallback: if no structured steps, use description
        if not test_steps_text:
            test_steps_text = testcase_data.get("description", "")
        
        # Format description for overview
        description_text = testcase_data.get("description", "No description provided")
        
        # Map priority
        # priority_map = {1: "Highest", 2: "High", 3: "Medium", 4: "Low"}
        # priority = priority_map.get(testcase_data.get("priority", 2), "Medium")
        
        # Create test case issue with custom fields in ADF format
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": testcase_data.get("title", "Generated Test Case"),
                "description": text_to_adf(description_text),  # ADF format
                "issuetype": {"name": "Test"},
                # "priority": {"name": priority},
                "labels": ["test-case", "ai-generated"],
                # Custom fields in ADF format
                "customfield_10040": text_to_adf(test_steps_text),      # Test Steps in ADF
                "customfield_10041": text_to_adf(expected_results_text) # Expected Results in ADF
            }
        }
        
        url = f"{self.base_url}/rest/api/3/issue"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=self.headers,
                json=payload,
                auth=aiohttp.BasicAuth(self.email, self.api_token)
            ) as response:
                if response.status not in [200, 201]:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"Failed to create test case: {error_text}",
                        "status_code": response.status
                    }
                
                test_case = await response.json()
                test_case_key = test_case.get("key")
                
                # Link to user story
                link_result = await self._link_test_case_to_story(test_case_key, story_key)
                
                return {
                    "success": True,
                    "test_case_key": test_case_key,
                    "test_case_id": test_case.get("id"),
                    "story_key": story_key,
                    "link_success": link_result.get("success", False),
                    "url": f"{self.base_url}/browse/{test_case_key}"
                }



    # async def _link_test_case_to_story(self, test_case_key: str, story_key: str) -> Dict:
    #     """Create a link between test case and user story"""
    #     payload = {
    #         "type": {"name": "Tests"},
    #         "inwardIssue": {"key": test_case_key},
    #         "outwardIssue": {"key": story_key}
    #     }
        
    #     url = f"{self.base_url}/rest/api/3/issueLink"
        
    #     async with aiohttp.ClientSession() as session:
    #         async with session.post(
    #             url,
    #             headers=self.headers,
    #             json=payload,
    #             auth=aiohttp.BasicAuth(self.email, self.api_token)
    #         ) as response:
    #             return {
    #                 "success": response.status in [200, 201],
    #                 "status_code": response.status
    #             }
    
    async def _link_test_case_to_story(self, test_case_key: str, story_key: str) -> Dict:
        """Create a link between test case and user story"""
        payload = {
            "type": {"name": "Relates"},
            "inwardIssue": {"key": test_case_key},      
            "outwardIssue": {"key": story_key}  
        }
        
        url = f"{self.base_url}/rest/api/3/issueLink"
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=self.headers,
                json=payload,
                auth=aiohttp.BasicAuth(self.email, self.api_token)
            ) as response:
                
                response_text = await response.text()
                
                if response.status not in [200, 201]:
                    logger.error(f"❌ Link failed: {test_case_key} → {story_key}")
                    logger.error(f"Status Code: {response.status}")
                    logger.error(f"Response Body: {response_text}")
                    
                    # Try to parse error details
                    try:
                        error_json = json.loads(response_text)
                        error_messages = error_json.get("errorMessages", [])
                        errors = error_json.get("errors", {})
                        logger.error(f"Error Messages: {error_messages}")
                        logger.error(f"Field Errors: {errors}")
                    except:
                        pass
                else:
                    logger.info(f"✅ Successfully linked {test_case_key} tests {story_key}")
                
                return {
                    "success": response.status in [200, 201],
                    "status_code": response.status,
                    "error": response_text if response.status not in [200, 201] else None,
                    "test_case_key": test_case_key,
                    "story_key": story_key
                }
    def _extract_adf_text(self, adf: Dict) -> str:
        """Extract plain text from Atlassian Document Format"""
        if not adf or not isinstance(adf, dict):
            return ""
        
        def extract_content(node):
            if isinstance(node, dict):
                if node.get("type") == "text":
                    return node.get("text", "")
                if "content" in node:
                    return " ".join([extract_content(child) for child in node["content"]])
            return ""
        
        return extract_content(adf)