"""
Azure DevOps Client Module
Handles all ADO API interactions for user stories and test cases
"""

import aiohttp
import json
import base64
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class ADOClient:
    def __init__(self):
        self.base_url = None
        self.project = None
        self.personal_access_token = None
        self.headers = {}
        self.is_configured = False

    def configure(self, organization: str, project: str, personal_access_token: str):
        """Configure Azure DevOps connection"""
        self.base_url = f"https://dev.azure.com/{organization}"
        self.project = project
        self.personal_access_token = personal_access_token

        # Create auth header
        auth_string = f":{personal_access_token}"
        b64_auth = base64.b64encode(auth_string.encode()).decode()

        self.headers = {
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        self.is_configured = True
        logger.info(f"ADO client configured for project: {project}")

    async def test_connection(self) -> Dict:
        """Test the ADO connection"""
        if not self.is_configured:
            raise ValueError("ADO client not configured")

        url = f"{self.base_url}/_apis/projects/{self.project}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                result = {
                    "success": response.status == 200,
                    "status_code": response.status,
                    "project": self.project
                }

                if response.status == 200:
                    project_data = await response.json()
                    result["project_info"] = {
                        "id": project_data.get("id"),
                        "name": project_data.get("name"),
                        "description": project_data.get("description"),
                        "url": project_data.get("url")
                    }
                else:
                    result["error"] = await response.text()

                return result

    async def fetch_user_story(self, user_story_id: int) -> Dict:
        """Fetch user story details from ADO"""
        if not self.is_configured:
            raise ValueError("ADO client not configured")

        url = f"{self.base_url}/{self.project}/_apis/wit/workitems/{user_story_id}"
        params = {
            "$expand": "relations",
            "api-version": "7.1-preview.3"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"Failed to fetch user story: {error_text}",
                        "status_code": response.status
                    }

                work_item = await response.json()
                fields = work_item.get("fields", {})

                user_story_data = {
                    "success": True,
                    "id": work_item.get("id"),
                    "title": fields.get("System.Title"),
                    "description": fields.get("System.Description", ""),
                    "state": fields.get("System.State"),
                    "work_item_type": fields.get("System.WorkItemType"),
                    "assigned_to": fields.get("System.AssignedTo", {}).get("displayName") if fields.get("System.AssignedTo") else None,
                    "created_date": fields.get("System.CreatedDate"),
                    "changed_date": fields.get("System.ChangedDate"),
                    "area_path": fields.get("System.AreaPath"),
                    "iteration_path": fields.get("System.IterationPath"),
                    "tags": fields.get("System.Tags", ""),
                    "priority": fields.get("Microsoft.VSTS.Common.Priority"),
                    "business_value": fields.get("Microsoft.VSTS.Common.BusinessValue"),
                    "acceptance_criteria": fields.get("Microsoft.VSTS.Common.AcceptanceCriteria", ""),
                    "story_points": fields.get("Microsoft.VSTS.Scheduling.StoryPoints"),
                    "relations": []
                }

                # Extract relations (linked work items)
                relations = work_item.get("relations", [])
                for relation in relations:
                    if relation.get("rel") in ["System.LinkTypes.Hierarchy-Forward", "Microsoft.VSTS.Common.TestedBy-Forward"]:
                        user_story_data["relations"].append({
                            "rel": relation.get("rel"),
                            "url": relation.get("url"),
                            "attributes": relation.get("attributes", {})
                        })

                return user_story_data

    async def fetch_testcases(self, user_story_id: int) -> Dict:
        """Fetch all test cases linked to a user story"""
        if not self.is_configured:
            return {
                "success": False,
                "error": "ADO client not configured",
                "error_code": "NOT_CONFIGURED"
            }

        try:
            # First get the user story to find linked test cases
            user_story = await self.fetch_user_story(user_story_id)

            if not user_story.get("success"):
                return user_story

            # Extract test case IDs from relations with correct relation types
            test_case_ids = []
            relations = user_story.get("relations", [])

            logger.info(f"Found {len(relations)} relations for user story {user_story_id}")

            for relation in relations:
                rel_type = relation.get("rel", "")
                logger.debug(f"Checking relation type: {rel_type}")

                # Check for both possible TestedBy relation directions
                if rel_type in [
                    "Microsoft.VSTS.Common.TestedBy-Forward",
                    "Microsoft.VSTS.Common.TestedBy-Reverse"
                ]:
                    url = relation.get("url", "")
                    logger.debug(f"Found TestedBy relation with URL: {url}")

                    if "workitems/" in url:
                        try:
                            # Extract work item ID from URL
                            tc_id = url.split("workitems/")[-1]
                            # Remove any query parameters
                            tc_id = tc_id.split("?")[0]
                            test_case_ids.append(int(tc_id))
                            logger.info(f"Extracted test case ID: {tc_id}")
                        except (ValueError, IndexError) as e:
                            logger.warning(f"Failed to extract test case ID from URL {url}: {e}")

            logger.info(f"Found {len(test_case_ids)} test case IDs: {test_case_ids}")

            # Fetch details for each test case
            test_cases = []
            failed_fetches = []

            for tc_id in test_case_ids:
                try:
                    tc_data = await self._fetch_test_case_details(tc_id)
                    if tc_data.get("success"):
                        test_cases.append(tc_data)
                    else:
                        failed_fetches.append({
                            "test_case_id": tc_id,
                            "error": tc_data.get("error", "Unknown error")
                        })
                except Exception as e:
                    logger.error(f"Exception fetching test case {tc_id}: {e}")
                    failed_fetches.append({
                        "test_case_id": tc_id,
                        "error": str(e)
                    })

            result = {
                "success": True,
                "user_story_id": user_story_id,
                "test_case_count": len(test_cases),
                "test_cases": test_cases,
                "total_relations_checked": len(relations),
                "test_case_ids_found": test_case_ids
            }

            if failed_fetches:
                result["failed_fetches"] = failed_fetches
                result["warning"] = f"{len(failed_fetches)} test cases could not be fetched"

            return result

        except Exception as e:
            logger.error(f"Unexpected error fetching test cases for user story {user_story_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_story_id": user_story_id,
                "error_code": "UNEXPECTED_ERROR"
            }


    async def _fetch_test_case_details(self, test_case_id: int) -> Dict:
        """Fetch individual test case details"""
        url = f"{self.base_url}/{self.project}/_apis/wit/workitems/{test_case_id}"
        params = {"api-version": "7.1-preview.3"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status != 200:
                    return {
                        "success": False,
                        "error": f"Failed to fetch test case {test_case_id}",
                        "test_case_id": test_case_id
                    }

                work_item = await response.json()
                fields = work_item.get("fields", {})

                return {
                    "success": True,
                    "id": test_case_id,
                    "title": fields.get("System.Title"),
                    "state": fields.get("System.State"),
                    "priority": fields.get("Microsoft.VSTS.Common.Priority"),
                    "test_steps": fields.get("Microsoft.VSTS.TCM.Steps", ""),
                    "created_date": fields.get("System.CreatedDate"),
                    "changed_date": fields.get("System.ChangedDate"),
                    "assigned_to": fields.get("System.AssignedTo", {}).get("displayName") if fields.get("System.AssignedTo") else None
                }

    async def create_testcase(self, user_story_id: int, testcase_data: Dict) -> Dict:
        """Create a new test case linked to a user story with enhanced error handling"""
        if not self.is_configured:
            return {
                "success": False,
                "error": "ADO client not configured",
                "error_code": "NOT_CONFIGURED"
            }

        try:
            # Validate required fields
            if not testcase_data.get("title"):
                return {
                    "success": False,
                    "error": "Test case title is required",
                    "error_code": "MISSING_TITLE"
                }

            # Prepare test case work item
            test_case_fields = [
                {
                    "op": "add",
                    "path": "/fields/System.Title",
                    "value": testcase_data.get("title")
                },
                {
                    "op": "add",
                    "path": "/fields/System.WorkItemType",
                    "value": "Test Case"
                },
                {
                    "op": "add",
                    "path": "/fields/Microsoft.VSTS.Common.Priority",
                    "value": testcase_data.get("priority", 2)
                },
                {
                    "op": "add",
                    "path": "/fields/System.AreaPath",
                    "value": testcase_data.get("area_path", self.project)
                }
            ]

            # Add test steps if provided
            if testcase_data.get("steps"):
                steps_xml = self._format_test_steps(testcase_data["steps"])
                logger.info(f"Generated test steps XML: {steps_xml}")
                test_case_fields.append({
                    "op": "add",
                    "path": "/fields/Microsoft.VSTS.TCM.Steps",
                    "value": steps_xml
                })
            else:
                logger.warning(f"Creating test case without steps for user story {user_story_id}")

            # Add description if provided
            if testcase_data.get("description"):
                test_case_fields.append({
                    "op": "add",
                    "path": "/fields/System.Description",
                    "value": testcase_data["description"]
                })

            # Create the test case
            url = f"{self.base_url}/{self.project}/_apis/wit/workitems/$Test%20Case"
            params = {"api-version": "7.1-preview.3"}

            async with aiohttp.ClientSession() as session:
                async with session.patch(
                    url,
                    headers={**self.headers, "Content-Type": "application/json-patch+json"},
                    json=test_case_fields,
                    params=params
                ) as response:

                    if response.status not in [200, 201]:
                        error_text = await response.text()
                        logger.error(f"ADO API error creating test case: {error_text}")
                        return {
                            "success": False,
                            "error": f"ADO API failed to create test case: {error_text}",
                            "status_code": response.status,
                            "error_code": "ADO_API_ERROR",
                            "user_story_id": user_story_id
                        }

                    test_case = await response.json()
                    test_case_id = test_case.get("id")

                    if not test_case_id:
                        return {
                            "success": False,
                            "error": "No test case ID returned from ADO",
                            "error_code": "INVALID_RESPONSE"
                        }

                    # Link the test case to the user story
                    link_result = await self._link_test_case_to_user_story(test_case_id, user_story_id)

                    result = {
                        "success": True,
                        "test_case_id": test_case_id,
                        "title": test_case.get("fields", {}).get("System.Title"),
                        "user_story_id": user_story_id,
                        "link_success": link_result.get("success", False),
                        "url": test_case.get("url"),
                        "created_date": test_case.get("fields", {}).get("System.CreatedDate")
                    }

                    if not link_result.get("success"):
                        result["link_warning"] = link_result.get("error", "Failed to link to user story")
                        logger.warning(f"Test case {test_case_id} created but linking to user story {user_story_id} failed")

                    return result

        except Exception as e:
            logger.error(f"Unexpected error creating test case: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "error_code": "UNEXPECTED_ERROR",
                "user_story_id": user_story_id
            }

    async def _link_test_case_to_user_story(self, test_case_id: int, user_story_id: int) -> Dict:
        """Create a link between test case and user story"""
        link_data = [
            {
                "op": "add",
                "path": "/relations/-",
                "value": {
                    "rel": "Microsoft.VSTS.Common.TestedBy-Reverse",
                    "url": f"{self.base_url}/{self.project}/_apis/wit/workitems/{user_story_id}",
                    "attributes": {
                        "comment": "Tests user story"
                    }
                }
            }
        ]

        url = f"{self.base_url}/{self.project}/_apis/wit/workitems/{test_case_id}"
        params = {"api-version": "7.1-preview.3"}

        async with aiohttp.ClientSession() as session:
            async with session.patch(
                url,
                headers={**self.headers, "Content-Type": "application/json-patch+json"},
                json=link_data,
                params=params
            ) as response:

                return {
                    "success": response.status in [200, 201],
                    "status_code": response.status,
                    "error": await response.text() if response.status not in [200, 201] else None
                }

    async def update_testcase(self, testcase_id: int, updates: Dict) -> Dict:
        """Update an existing test case"""
        if not self.is_configured:
            raise ValueError("ADO client not configured")

        # Build update operations
        update_operations = []

        if "title" in updates:
            update_operations.append({
                "op": "replace",
                "path": "/fields/System.Title",
                "value": updates["title"]
            })

        if "description" in updates:
            update_operations.append({
                "op": "replace",
                "path": "/fields/System.Description",
                "value": updates["description"]
            })

        if "priority" in updates:
            update_operations.append({
                "op": "replace",
                "path": "/fields/Microsoft.VSTS.Common.Priority",
                "value": updates["priority"]
            })

        if "steps" in updates:
            steps_xml = self._format_test_steps(updates["steps"])
            logger.info(f"Updating test steps XML: {steps_xml}")
            update_operations.append({
                "op": "replace",
                "path": "/fields/Microsoft.VSTS.TCM.Steps",
                "value": steps_xml
            })

        if "state" in updates:
            update_operations.append({
                "op": "replace",
                "path": "/fields/System.State",
                "value": updates["state"]
            })

        # Apply updates
        url = f"{self.base_url}/{self.project}/_apis/wit/workitems/{testcase_id}"
        params = {"api-version": "7.1-preview.3"}

        async with aiohttp.ClientSession() as session:
            async with session.patch(
                url,
                headers={**self.headers, "Content-Type": "application/json-patch+json"},
                json=update_operations,
                params=params
            ) as response:

                if response.status not in [200, 201]:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"Failed to update test case: {error_text}",
                        "status_code": response.status
                    }

                updated_item = await response.json()
                fields = updated_item.get("fields", {})

                return {
                    "success": True,
                    "test_case_id": testcase_id,
                    "title": fields.get("System.Title"),
                    "state": fields.get("System.State"),
                    "changed_date": fields.get("System.ChangedDate"),
                    "updated_fields": list(updates.keys())
                }

    def _format_test_steps(self, steps: List[Dict]) -> str:
        """Format test steps into ADO XML format"""
        from xml.sax.saxutils import escape

        if not steps:
            return ""

        last_step_id = len(steps)
        xml_parts = [f'<steps id="0" last="{last_step_id}">']

        for i, step in enumerate(steps, 1):
            action = escape(step.get("action", "").strip())
            expected = escape(step.get("expected", "").strip())

            # Use ValidateStep when there's an expected result, ActionStep otherwise
            step_type = "ValidateStep" if expected else "ActionStep"

            xml_parts.append(
                f'<step id="{i}" type="{step_type}">'
                f'<parameterizedString isformatted="true">{action}</parameterizedString>'
                f'<parameterizedString isformatted="true">{expected}</parameterizedString>'
                f'<description/></step>'
            )

        xml_parts.append('</steps>')
        return ''.join(xml_parts)

    async def search_work_items(self, query: str, work_item_types: List[str] = None) -> Dict:
        """Search for work items using WIQL"""
        if not self.is_configured:
            raise ValueError("ADO client not configured")

        # Build WIQL query
        wiql_query = f"""
        SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType]
        FROM WorkItems
        WHERE [System.TeamProject] = '{self.project}'
        AND [System.Title] CONTAINS '{query}'
        """

        if work_item_types:
            types_str = "', '".join(work_item_types)
            wiql_query += f" AND [System.WorkItemType] IN ('{types_str}')"

        wiql_query += " ORDER BY [System.ChangedDate] DESC"

        # Execute query
        url = f"{self.base_url}/{self.project}/_apis/wit/wiql"
        params = {"api-version": "7.1-preview.2"}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=self.headers,
                json={"query": wiql_query},
                params=params
            ) as response:

                if response.status != 200:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"Search failed: {error_text}",
                        "status_code": response.status
                    }

                result = await response.json()
                work_items = result.get("workItems", [])

                return {
                    "success": True,
                    "query": query,
                    "total_results": len(work_items),
                    "work_items": [
                        {
                            "id": item.get("id"),
                            "url": item.get("url")
                        } for item in work_items
                    ]
                }
