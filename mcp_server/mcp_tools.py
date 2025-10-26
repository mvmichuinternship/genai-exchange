"""
MCP Tools Registration Module
Registers all MCP tools for Azure DevOps test case generation
"""
import os
import json
import logging
import aiohttp
from typing import List, Dict, Any
from mcp.types import TextContent

logger = logging.getLogger(__name__)
organization = os.getenv("ADO_ORG")
project = os.getenv("ADO_PROJECT")
personal_access_token = os.getenv("ADO_PAT")

def register_all_tools(mcp, ado_client, jira_client, vector_service, traceability_manager):
    """Register all MCP tools with the server"""
    
    # Configuration Tools
    @mcp.tool()
    async def configure_ado_connection(
        organization: str = organization,
        project: str = project,
        personal_access_token: str = personal_access_token
    ) -> List[TextContent]:
        """Configure Azure DevOps connection"""
        try:
            ado_client.configure(organization, project, personal_access_token)
            # ado_client.configure()
            test_result = await ado_client.test_connection()
            
            return [TextContent(type="text", text=json.dumps(test_result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": "Failed to configure ADO connection"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def configure_vertex_ai(
        project_id: str,
        location: str,
        index_id: str = None,
        endpoint_id: str = None
    ) -> List[TextContent]:
        """Configure Google Cloud Vertex AI for vector search"""
        try:
            await vector_service.configure_vertex_ai(project_id, location, index_id, endpoint_id)
            test_result = await vector_service.test_connection()
            
            return [TextContent(type="text", text=json.dumps(test_result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": "Failed to configure Vertex AI"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def configure_alloydb(
        project_id: str,
        region: str,
        cluster: str,
        instance: str,
        database: str,
        user: str,
        password: str
    ) -> List[TextContent]:
        """Configure Google Cloud AlloyDB for vector search"""
        try:
            await vector_service.configure_alloydb(project_id, region, cluster, instance, database, user, password)
            test_result = await vector_service.test_connection()
            
            return [TextContent(type="text", text=json.dumps(test_result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": "Failed to configure AlloyDB"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def initialize_traceability_manager(
        persistence_file: str = "traceability_matrix.json"
    ) -> List[TextContent]:
        """Initialize traceability manager"""
        try:
            result = await traceability_manager.initialize(persistence_file)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": "Failed to initialize traceability manager"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    # Core ADO Tools
    @mcp.tool()
    async def fetch_user_story(
        user_story_id: int
    ) -> List[TextContent]:
        """Fetch user story details from Azure DevOps"""
        try:
            result = await ado_client.fetch_user_story(user_story_id)
            
            # If successful, also store in vector database
            if result.get("success") and vector_service.is_configured:
                store_result = await vector_service.store_user_story_context(user_story_id, result)
                result["vector_storage"] = store_result
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "user_story_id": user_story_id,
                "message": "Failed to fetch user story"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def fetch_testcases(
        user_story_id: int
    ) -> List[TextContent]:
        """Get all test cases linked to a user story"""
        try:
            result = await ado_client.fetch_testcases(user_story_id)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "user_story_id": user_story_id,
                "message": "Failed to fetch test cases"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def create_testcase(
        user_story_id: int,
        title: str,
        description: str = "",
        steps: List[Dict[str, str]] = None,
        priority: int = 2,
        area_path: str = None
    ) -> List[TextContent]:
        """Create a new test case linked to a user story"""
        try:
            testcase_data = {
                "title": title,
                "description": description,
                "steps": steps or [],
                "priority": priority,
                "area_path": area_path
            }
            
            # Create test case in ADO
            ado_result = await ado_client.create_testcase(user_story_id, testcase_data)
            
            # If successful, register in traceability manager
            if ado_result.get("success") and traceability_manager.is_initialized:
                test_case_id = ado_result.get("test_case_id")
                if test_case_id:
                    trace_result = await traceability_manager.register_test_case(
                        test_case_id, title, "Active", [user_story_id], "agent_generated"
                    )
                    ado_result["traceability"] = trace_result
            
            return [TextContent(type="text", text=json.dumps(ado_result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "user_story_id": user_story_id,
                "title": title,
                "message": "Failed to create test case"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def update_testcase(
        testcase_id: int,
        title: str = None,
        description: str = None,
        steps: List[Dict[str, str]] = None,
        priority: int = None,
        state: str = None
    ) -> List[TextContent]:
        """Update an existing test case"""
        try:
            updates = {}
            if title is not None:
                updates["title"] = title
            if description is not None:
                updates["description"] = description
            if steps is not None:
                updates["steps"] = steps
            if priority is not None:
                updates["priority"] = priority
            if state is not None:
                updates["state"] = state
            
            result = await ado_client.update_testcase(testcase_id, updates)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "testcase_id": testcase_id,
                "message": "Failed to update test case"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    # Vector Search Tools
    @mcp.tool()
    async def search_similar_stories(
        query: str,
        max_results: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[TextContent]:
        """Search for similar user stories using vector similarity"""
        try:
            result = await vector_service.search_similar_context(query, max_results, similarity_threshold)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "query": query,
                "message": "Failed to search similar stories"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    # Traceability Tools
    @mcp.tool()
    async def traceability_map(
        user_story_id: int = None
    ) -> List[TextContent]:
        """Get traceability matrix between stories and test cases"""
        try:
            result = await traceability_manager.get_traceability_map(user_story_id)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "user_story_id": user_story_id,
                "message": "Failed to get traceability map"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def get_test_cases_for_story(
        user_story_id: int
    ) -> List[TextContent]:
        """Get all test cases linked to a specific user story from traceability matrix"""
        try:
            result = await traceability_manager.get_test_cases_for_story(user_story_id)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "user_story_id": user_story_id,
                "message": "Failed to get test cases for story"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def get_stories_for_test_case(
        test_case_id: int
    ) -> List[TextContent]:
        """Get all user stories linked to a specific test case"""
        try:
            result = await traceability_manager.get_user_stories_for_test_case(test_case_id)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "test_case_id": test_case_id,
                "message": "Failed to get stories for test case"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    # Agent Coordination Tool (main workflow)
    @mcp.tool()
    async def prepare_test_case_context(
        user_story_id: int,
        search_similar: bool = True,
        max_similar_results: int = 3
    ) -> List[TextContent]:
        """
        Prepare comprehensive context for test case generation
        This is the main coordination tool that agents should call first
        """
        try:
            context_data = {
                "user_story_id": user_story_id,
                "workflow_status": "preparing_context",
                "context_sources": []
            }
            
            # 1. Fetch user story from ADO
            user_story_result = await ado_client.fetch_user_story(user_story_id)
            if user_story_result.get("success"):
                context_data["user_story"] = user_story_result
                context_data["context_sources"].append("azure_devops")
                
                # Store in vector DB if configured
                if vector_service.is_configured:
                    store_result = await vector_service.store_user_story_context(user_story_id, user_story_result)
                    context_data["vector_storage"] = store_result
            else:
                context_data["user_story_error"] = user_story_result.get("error")
            
            # 2. Check for existing test cases
            existing_tests_result = await ado_client.fetch_testcases(user_story_id)
            if existing_tests_result.get("success"):
                context_data["existing_test_cases"] = existing_tests_result
                context_data["has_existing_tests"] = existing_tests_result.get("test_case_count", 0) > 0
            
            # 3. Search for similar stories if enabled and vector service is available
            if search_similar and vector_service.is_configured and user_story_result.get("success"):
                search_query = f"{user_story_result.get('title', '')} {user_story_result.get('description', '')[:200]}"
                similar_result = await vector_service.search_similar_context(
                    search_query, max_similar_results, 0.6
                )
                if similar_result.get("success"):
                    context_data["similar_stories"] = similar_result
                    context_data["context_sources"].append("vector_similarity_search")
            
            # 4. Get traceability information
            if traceability_manager.is_initialized:
                trace_result = await traceability_manager.get_test_cases_for_story(user_story_id)
                context_data["traceability_info"] = trace_result
                context_data["context_sources"].append("traceability_matrix")
            
            # 5. Prepare generation recommendations
            recommendations = []
            
            if not context_data.get("has_existing_tests"):
                recommendations.append("No existing test cases found - full test suite generation needed")
            else:
                existing_count = context_data.get("existing_test_cases", {}).get("test_case_count", 0)
                recommendations.append(f"Found {existing_count} existing test cases - consider gap analysis")
            
            if context_data.get("similar_stories", {}).get("total_results", 0) > 0:
                recommendations.append("Similar stories found - can leverage existing test patterns")
            
            # Analyze user story for test case suggestions
            if user_story_result.get("success"):
                story_data = user_story_result
                test_suggestions = []
                
                # Basic suggestions based on user story content
                if story_data.get("acceptance_criteria"):
                    test_suggestions.append("Generate tests based on acceptance criteria")
                
                if story_data.get("description"):
                    test_suggestions.append("Generate functional tests for main scenarios")
                
                # Always suggest these standard test types
                test_suggestions.extend([
                    "Generate positive path tests",
                    "Generate negative path tests", 
                    "Generate boundary/edge case tests",
                    "Consider integration test scenarios"
                ])
                
                context_data["test_generation_suggestions"] = test_suggestions
            
            context_data.update({
                "success": True,
                "workflow_status": "context_ready",
                "recommendations": recommendations,
                "ready_for_generation": user_story_result.get("success", False),
                "context_completeness": {
                    "user_story_fetched": user_story_result.get("success", False),
                    "existing_tests_checked": existing_tests_result.get("success", False),
                    "similar_stories_searched": search_similar and vector_service.is_configured,
                    "traceability_available": traceability_manager.is_initialized
                }
            })
            
            return [TextContent(type="text", text=json.dumps(context_data, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "user_story_id": user_story_id,
                "workflow_status": "context_preparation_failed",
                "message": "Failed to prepare test case context"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    # Batch Operations
    @mcp.tool()
    async def batch_create_testcases(
        user_story_id: int,
        test_cases: List[Dict[str, Any]]
    ) -> List[TextContent]:
        """Create multiple test cases for a user story in batch"""
        try:
            results = {
                "success": True,
                "user_story_id": user_story_id,
                "total_requested": len(test_cases),
                "created_count": 0,
                "failed_count": 0,
                "results": [],
                "errors": []
            }
            
            created_test_case_ids = []
            
            for i, tc_data in enumerate(test_cases):
                try:
                    # Create individual test case
                    create_result = await ado_client.create_testcase(user_story_id, tc_data)
                    
                    if create_result.get("success"):
                        results["created_count"] += 1
                        results["results"].append(create_result)
                        
                        test_case_id = create_result.get("test_case_id")
                        if test_case_id:
                            created_test_case_ids.append(test_case_id)
                            
                            # Register in traceability
                            if traceability_manager.is_initialized:
                                await traceability_manager.register_test_case(
                                    test_case_id,
                                    tc_data.get("title", f"Test Case {i+1}"),
                                    "Active",
                                    [user_story_id],
                                    "batch_agent_generated"
                                )
                    else:
                        results["failed_count"] += 1
                        results["errors"].append({
                            "index": i,
                            "title": tc_data.get("title", f"Test Case {i+1}"),
                            "error": create_result.get("error", "Unknown error")
                        })
                
                except Exception as tc_error:
                    results["failed_count"] += 1
                    results["errors"].append({
                        "index": i,
                        "title": tc_data.get("title", f"Test Case {i+1}"),
                        "error": str(tc_error)
                    })
            
            # Update traceability with all created test cases
            if created_test_case_ids and traceability_manager.is_initialized:
                await traceability_manager.add_traceability_entry(
                    user_story_id, 
                    created_test_case_ids,
                    {"batch_operation": True, "generation_method": "agent_batch"}
                )
            
            results["success"] = results["failed_count"] == 0
            results["message"] = f"Batch operation completed: {results['created_count']} created, {results['failed_count']} failed"
            
            return [TextContent(type="text", text=json.dumps(results, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "user_story_id": user_story_id,
                "message": "Failed to perform batch test case creation"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    # System Status Tools
    @mcp.tool()
    async def system_status() -> List[TextContent]:
        """Get comprehensive system status"""
        try:
            status = {
                "success": True,
                "timestamp": "2024-01-01T00:00:00Z",  # Will be set by actual implementation
                "components": {}
            }
            
            # ADO Client status
            status["components"]["ado_client"] = {
                "configured": ado_client.is_configured,
                "project": ado_client.project,
                "base_url": ado_client.base_url if ado_client.is_configured else None
            }
            
            # Vector Service status
            if vector_service.is_configured:
                vector_stats = await vector_service.get_storage_stats()
                status["components"]["vector_service"] = vector_stats
            else:
                status["components"]["vector_service"] = {
                    "configured": False,
                    "service_type": None
                }
            
            # Traceability Manager status
            if traceability_manager.is_initialized:
                trace_map = await traceability_manager.get_traceability_map()
                status["components"]["traceability_manager"] = {
                    "initialized": True,
                    "summary": trace_map.get("summary", {}),
                    "persistence_file": traceability_manager.persistence_file
                }
            else:
                status["components"]["traceability_manager"] = {
                    "initialized": False
                }
            
            # Overall health
            all_healthy = (
                ado_client.is_configured and
                (vector_service.is_configured or True) and  # Vector service is optional
                traceability_manager.is_initialized
            )
            
            status["overall_health"] = "healthy" if all_healthy else "needs_configuration"
            
            return [TextContent(type="text", text=json.dumps(status, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": "Failed to get system status"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def generate_traceability_report(
        format_type: str = "summary"  # summary, detailed, matrix
    ) -> List[TextContent]:
        """Generate comprehensive traceability report"""
        try:
            result = await traceability_manager.generate_traceability_report(format_type)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "format_type": format_type,
                "message": "Failed to generate traceability report"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    # ========================================
    # JIRA TOOLS
    # ========================================
    
    @mcp.tool()
    async def configure_jira_connection(
        base_url: str,
        email: str,
        api_token: str,
        project_key: str
    ) -> List[TextContent]:
        """Configure Jira connection"""
        try:
            jira_client.configure(base_url, email, api_token, project_key)
            test_result = await jira_client.test_connection()
            return [TextContent(type="text", text=json.dumps(test_result, indent=2))]
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": "Failed to configure Jira connection"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def fetch_jira_issue(issue_key: str) -> List[TextContent]:
        """Fetch Jira issue/story details"""
        try:
            result = await jira_client.fetch_user_story(issue_key)
            
            if result.get("success") and vector_service.is_configured:
                store_result = await vector_service.store_user_story_context(issue_key, result)
                result["vector_storage"] = store_result
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "issue_key": issue_key,
                "message": "Failed to fetch Jira issue"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def fetch_jira_testcases(story_key: str) -> List[TextContent]:
        """Get all test cases linked to a Jira story"""
        try:
            result = await jira_client.fetch_testcases(story_key)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "story_key": story_key,
                "message": "Failed to fetch Jira test cases"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def create_jira_testcase(
        story_key: str,
        title: str,
        description: str = "",
        steps: List[Dict[str, str]] = None,
        priority: str = "Medium",
        labels: List[str] = None
    ) -> List[TextContent]:
        """Create a new Jira test case linked to a story"""
        try:
            testcase_data = {
                "title": title,
                "description": description,
                "steps": steps or [],
                "priority": priority,
                "labels": labels or []
            }
            
            jira_result = await jira_client.create_testcase(story_key, testcase_data)
            
            if jira_result.get("success") and traceability_manager.is_initialized:
                test_case_key = jira_result.get("test_case_key")
                if test_case_key:
                    trace_result = await traceability_manager.register_test_case(
                        test_case_key, title, "Active", [story_key], "jira_agent_generated"
                    )
                    jira_result["traceability"] = trace_result
            
            return [TextContent(type="text", text=json.dumps(jira_result, indent=2))]
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "story_key": story_key,
                "title": title,
                "message": "Failed to create Jira test case"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def batch_create_jira_testcases(
        story_key: str,
        test_cases: List[Dict[str, Any]]
    ) -> List[TextContent]:
        """Create multiple Jira test cases for a story in batch"""
        try:
            results = {
                "success": True,
                "story_key": story_key,
                "total_requested": len(test_cases),
                "created_count": 0,
                "failed_count": 0,
                "results": [],
                "errors": []
            }
            
            created_test_case_keys = []
            
            for i, tc_data in enumerate(test_cases):
                try:
                    create_result = await jira_client.create_testcase(story_key, tc_data)
                    
                    if create_result.get("success"):
                        results["created_count"] += 1
                        results["results"].append(create_result)
                        
                        test_case_key = create_result.get("test_case_key")
                        if test_case_key:
                            created_test_case_keys.append(test_case_key)
                            
                            if traceability_manager.is_initialized:
                                await traceability_manager.register_test_case(
                                    test_case_key,
                                    tc_data.get("title", f"Test Case {i+1}"),
                                    "Active",
                                    [story_key],
                                    "jira_batch_agent_generated"
                                )
                    else:
                        results["failed_count"] += 1
                        results["errors"].append({
                            "index": i,
                            "title": tc_data.get("title", f"Test Case {i+1}"),
                            "error": create_result.get("error", "Unknown error")
                        })
                
                except Exception as tc_error:
                    results["failed_count"] += 1
                    results["errors"].append({
                        "index": i,
                        "title": tc_data.get("title", f"Test Case {i+1}"),
                        "error": str(tc_error)
                    })
            
            if created_test_case_keys and traceability_manager.is_initialized:
                await traceability_manager.add_traceability_entry(
                    story_key, 
                    created_test_case_keys,
                    {"batch_operation": True, "generation_method": "jira_agent_batch", "alm": "jira"}
                )
            
            results["success"] = results["failed_count"] == 0
            results["message"] = f"Batch: {results['created_count']} created, {results['failed_count']} failed"
            
            return [TextContent(type="text", text=json.dumps(results, indent=2))]
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "story_key": story_key,
                "message": "Failed batch Jira test case creation"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def prepare_jira_test_case_context(
        story_key: str,
        search_similar: bool = True,
        max_similar_results: int = 3
    ) -> List[TextContent]:
        """Prepare comprehensive context for Jira test case generation"""
        try:
            context_data = {
                "story_key": story_key,
                "alm_type": "jira",
                "workflow_status": "preparing_context",
                "context_sources": []
            }
            
            story_result = await jira_client.fetch_user_story(story_key)
            if story_result.get("success"):
                context_data["user_story"] = story_result
                context_data["context_sources"].append("jira")
                
                if vector_service.is_configured:
                    store_result = await vector_service.store_user_story_context(story_key, story_result)
                    context_data["vector_storage"] = store_result
            else:
                context_data["user_story_error"] = story_result.get("error")
            
            existing_tests_result = await jira_client.fetch_testcases(story_key)
            if existing_tests_result.get("success"):
                context_data["existing_test_cases"] = existing_tests_result
                context_data["has_existing_tests"] = existing_tests_result.get("test_case_count", 0) > 0
            
            if search_similar and vector_service.is_configured and story_result.get("success"):
                search_query = f"{story_result.get('title', '')} {story_result.get('description', '')[:200]}"
                similar_result = await vector_service.search_similar_context(search_query, max_similar_results, 0.6)
                if similar_result.get("success"):
                    context_data["similar_stories"] = similar_result
                    context_data["context_sources"].append("vector_similarity_search")
            
            if traceability_manager.is_initialized:
                trace_result = await traceability_manager.get_test_cases_for_story(story_key)
                context_data["traceability_info"] = trace_result
                context_data["context_sources"].append("traceability_matrix")
            
            recommendations = []
            if not context_data.get("has_existing_tests"):
                recommendations.append("No existing test cases - full suite needed")
            else:
                count = context_data.get("existing_test_cases", {}).get("test_case_count", 0)
                recommendations.append(f"Found {count} tests - consider gap analysis")
            
            if context_data.get("similar_stories", {}).get("total_results", 0) > 0:
                recommendations.append("Similar stories found - leverage patterns")
            
            if story_result.get("success"):
                test_suggestions = []
                if story_result.get("acceptance_criteria"):
                    test_suggestions.append("Generate tests from acceptance criteria")
                if story_result.get("description"):
                    test_suggestions.append("Generate functional tests")
                test_suggestions.extend([
                    "Generate positive path tests",
                    "Generate negative path tests",
                    "Generate edge case tests"
                ])
                context_data["test_generation_suggestions"] = test_suggestions
            
            context_data.update({
                "success": True,
                "workflow_status": "context_ready",
                "recommendations": recommendations,
                "ready_for_generation": story_result.get("success", False)
            })
            
            return [TextContent(type="text", text=json.dumps(context_data, indent=2))]
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "story_key": story_key,
                "workflow_status": "context_preparation_failed"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
        
    logger.info("All MCP tools registered (ADO + Jira)")  # ← This line should already exist
