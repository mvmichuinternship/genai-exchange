"""
MCP Tools Registration Module
Registers all MCP tools for Azure DevOps test case generation with schema validation
"""
import os
import json
import logging
from typing import List, Dict, Any
from mcp.types import TextContent
from testcase_schema import test_case_validator, validate_testcase, validate_testcase_batch

logger = logging.getLogger(__name__)

def register_all_tools(mcp, ado_client, vector_service, traceability_manager):
    """Register all MCP tools with the server"""
    
    # Configuration Tools
    @mcp.tool()
    async def configure_ado_connection(
        organization: str,
        project: str, 
        personal_access_token: str
    ) -> List[TextContent]:
        """Configure Azure DevOps connection"""
        try:
            ado_client.configure(organization, project, personal_access_token)
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
        """Fetch user story details from Azure DevOps (raw data, no schema enforcement)"""
        try:
            result = await ado_client.fetch_user_story(user_story_id)
            
            # Store in vector database if configured (future integration)
            if result.get("success") and vector_service and vector_service.is_configured:
                # TODO: Implement vector storage when vector service is ready
                # store_result = await vector_service.store_user_story_context(user_story_id, result)
                # result["vector_storage"] = store_result
                result["vector_storage"] = {"status": "not_implemented", "message": "Vector service integration pending"}
            
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
        testcase_data: Dict[str, Any]
    ) -> List[TextContent]:
        """Create a new test case with schema validation and link to user story"""
        try:
            # Validate test case data against schema
            validation_result = validate_testcase(testcase_data)
            
            if not validation_result.is_valid:
                return [TextContent(type="text", text=json.dumps({
                    "success": False,
                    "error": "Test case schema validation failed",
                    "validation_errors": validation_result.errors,
                    "user_story_id": user_story_id,
                    "schema_help": test_case_validator.get_schema_documentation()
                }, indent=2))]
            
            # Convert validated Pydantic model to dict for ADO API
            validated_testcase = validation_result.validated_data
            testcase_dict = {
                "title": validated_testcase.title,
                "description": validated_testcase.description,
                "steps": [{"action": step.action, "expected": step.expected} for step in validated_testcase.steps],
                "priority": validated_testcase.priority
            }
            
            # Create test case in ADO
            ado_result = await ado_client.create_testcase(user_story_id, testcase_dict)
            
            # If successful, register in traceability manager
            if ado_result.get("success") and traceability_manager.is_initialized:
                test_case_id = ado_result.get("test_case_id")
                if test_case_id:
                    trace_result = await traceability_manager.register_test_case(
                        test_case_id, validated_testcase.title, "Active", [user_story_id], "mcp_generated"
                    )
                    ado_result["traceability"] = trace_result
            
            # Add validation info to result
            ado_result["schema_validation"] = {
                "passed": True,
                "validator_used": True
            }
            
            return [TextContent(type="text", text=json.dumps(ado_result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "user_story_id": user_story_id,
                "message": "Failed to create test case"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def update_testcase(
        testcase_id: int,
        updates: Dict[str, Any]
    ) -> List[TextContent]:
        """Update an existing test case with optional schema validation"""
        try:
            # If updating with complete test case structure, validate schema
            if all(key in updates for key in ["title", "description", "steps"]):
                validation_result = validate_testcase(updates)
                if not validation_result.is_valid:
                    return [TextContent(type="text", text=json.dumps({
                        "success": False,
                        "error": "Test case schema validation failed",
                        "validation_errors": validation_result.errors,
                        "testcase_id": testcase_id,
                        "schema_help": test_case_validator.get_schema_documentation()
                    }, indent=2))]
                
                # Convert validated data if full update
                validated_testcase = validation_result.validated_data
                updates = {
                    "title": validated_testcase.title,
                    "description": validated_testcase.description,
                    "steps": [{"action": step.action, "expected": step.expected} for step in validated_testcase.steps],
                    "priority": validated_testcase.priority if "priority" in updates else None
                }
                # Remove None values
                updates = {k: v for k, v in updates.items() if v is not None}
            
            result = await ado_client.update_testcase(testcase_id, updates)
            
            # Add validation info if schema was used
            if all(key in updates for key in ["title", "description", "steps"]):
                result["schema_validation"] = {"passed": True, "validator_used": True}
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "testcase_id": testcase_id,
                "message": "Failed to update test case"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    # Core Workflow Tool
    @mcp.tool()
    async def generate_testcases_from_story(
        user_story_id: int,
        agent_generated_testcases: List[Dict[str, Any]],
        max_validation_retries: int = 3
    ) -> List[TextContent]:
        """
        Main workflow tool: validate agent-generated test cases and create them in ADO
        This tool expects the agent to have already generated the test cases
        """
        try:
            workflow_result = {
                "success": True,
                "user_story_id": user_story_id,
                "total_submitted": len(agent_generated_testcases),
                "validated_count": 0,
                "created_count": 0,
                "failed_validation": 0,
                "failed_creation": 0,
                "results": [],
                "validation_errors": [],
                "creation_errors": []
            }
            
            created_test_case_ids = []
            
            for i, testcase_data in enumerate(agent_generated_testcases):
                try:
                    # Validate with retry logic
                    validation_result = await test_case_validator.validate_with_retry(
                        testcase_data, "single"
                    )
                    
                    if not validation_result.is_valid:
                        workflow_result["failed_validation"] += 1
                        workflow_result["validation_errors"].append({
                            "index": i,
                            "title": testcase_data.get("title", f"Test Case {i+1}"),
                            "errors": validation_result.errors
                        })
                        continue
                    
                    workflow_result["validated_count"] += 1
                    
                    # Convert validated data for ADO API
                    validated_testcase = validation_result.validated_data
                    testcase_dict = {
                        "title": validated_testcase.title,
                        "description": validated_testcase.description,
                        "steps": [{"action": step.action, "expected": step.expected} for step in validated_testcase.steps],
                        "priority": validated_testcase.priority
                    }
                    
                    # Create in ADO
                    create_result = await ado_client.create_testcase(user_story_id, testcase_dict)
                    
                    if create_result.get("success"):
                        workflow_result["created_count"] += 1
                        test_case_id = create_result.get("test_case_id")
                        created_test_case_ids.append(test_case_id)
                        
                        # Register in traceability
                        if traceability_manager.is_initialized:
                            await traceability_manager.register_test_case(
                                test_case_id,
                                validated_testcase.title,
                                "Active",
                                [user_story_id],
                                "agent_generated_workflow"
                            )
                        
                        workflow_result["results"].append({
                            "index": i,
                            "test_case_id": test_case_id,
                            "title": validated_testcase.title,
                            "validation_passed": True,
                            "creation_passed": True
                        })
                    else:
                        workflow_result["failed_creation"] += 1
                        workflow_result["creation_errors"].append({
                            "index": i,
                            "title": validated_testcase.title,
                            "error": create_result.get("error", "Unknown creation error"),
                            "validation_passed": True,
                            "creation_passed": False
                        })
                
                except Exception as tc_error:
                    workflow_result["failed_validation"] += 1
                    workflow_result["validation_errors"].append({
                        "index": i,
                        "title": testcase_data.get("title", f"Test Case {i+1}"),
                        "error": str(tc_error)
                    })
            
            # Update traceability with batch info
            if created_test_case_ids and traceability_manager.is_initialized:
                await traceability_manager.add_traceability_entry(
                    user_story_id,
                    created_test_case_ids,
                    {
                        "generation_method": "agent_workflow",
                        "total_submitted": workflow_result["total_submitted"],
                        "validation_success_rate": workflow_result["validated_count"] / workflow_result["total_submitted"],
                        "creation_success_rate": workflow_result["created_count"] / max(workflow_result["validated_count"], 1)
                    }
                )
            
            # Overall success depends on having created at least one test case
            workflow_result["success"] = workflow_result["created_count"] > 0
            workflow_result["message"] = f"Workflow completed: {workflow_result['created_count']} test cases created successfully"
            
            if workflow_result["failed_validation"] > 0:
                workflow_result["message"] += f", {workflow_result['failed_validation']} failed validation"
            if workflow_result["failed_creation"] > 0:
                workflow_result["message"] += f", {workflow_result['failed_creation']} failed creation"
            
            return [TextContent(type="text", text=json.dumps(workflow_result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "user_story_id": user_story_id,
                "message": "Failed to execute test case generation workflow"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    # Vector Search Tools (Future Integration - Placeholders)
    @mcp.tool()
    async def search_similar_stories(
        query: str,
        max_results: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[TextContent]:
        """Search for similar user stories using vector similarity (PLACEHOLDER)"""
        # TODO: Implement when vector service is ready
        # This will help agents find similar stories and reuse test patterns
        placeholder_result = {
            "success": False,
            "error": "Vector search not implemented yet",
            "message": "This feature will be available when Google Vertex AI integration is completed",
            "query": query,
            "planned_features": [
                "Store user story embeddings in Vertex AI",
                "Search for similar stories based on content similarity", 
                "Return related test case patterns for reuse",
                "Support semantic search across project history"
            ]
        }
        return [TextContent(type="text", text=json.dumps(placeholder_result, indent=2))]
    
    @mcp.tool()
    async def store_story_embedding(
        user_story_id: int,
        user_story_data: Dict[str, Any],
        additional_context: str = ""
    ) -> List[TextContent]:
        """Store user story embedding for future similarity search (PLACEHOLDER)"""
        # TODO: Implement when vector service is ready
        placeholder_result = {
            "success": False,
            "error": "Vector storage not implemented yet", 
            "message": "This feature will be available when Google Vertex AI integration is completed",
            "user_story_id": user_story_id,
            "planned_features": [
                "Generate embeddings from user story content",
                "Store in Vertex AI Matching Engine or AlloyDB",
                "Enable semantic similarity search",
                "Support incremental updates and versioning"
            ]
        }
        return [TextContent(type="text", text=json.dumps(placeholder_result, indent=2))]
    
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
    
    # Schema Validation Tools
    @mcp.tool()
    async def get_testcase_schema() -> List[TextContent]:
        """Get the test case schema documentation for agent reference"""
        try:
            schema_doc = test_case_validator.get_schema_documentation()
            return [TextContent(type="text", text=json.dumps(schema_doc, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": "Failed to get schema documentation"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    @mcp.tool()
    async def validate_testcase_schema(
        testcase_data: Dict[str, Any]
    ) -> List[TextContent]:
        """Validate test case data against schema without creating it"""
        try:
            validation_result = validate_testcase(testcase_data)
            
            result = {
                "success": True,
                "validation_passed": validation_result.is_valid,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings
            }
            
            if validation_result.is_valid:
                result["message"] = "Test case schema validation passed"
                result["validated_data"] = {
                    "title": validation_result.validated_data.title,
                    "description": validation_result.validated_data.description,
                    "steps_count": len(validation_result.validated_data.steps),
                    "priority": validation_result.validated_data.priority
                }
            else:
                result["message"] = "Test case schema validation failed"
                result["help"] = test_case_validator.get_schema_documentation()
            
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "message": "Failed to validate test case schema"
            }
            return [TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    # System Status Tools
    @mcp.tool()
    async def system_status() -> List[TextContent]:
        """Get comprehensive system status"""
        try:
            from datetime import datetime, timezone
            
            status = {
                "success": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "components": {}
            }
            
            # ADO Client status
            status["components"]["ado_client"] = {
                "configured": ado_client.is_configured,
                "project": ado_client.project if ado_client.is_configured else None,
                "base_url": ado_client.base_url if ado_client.is_configured else None
            }
            
            # Vector Service status (placeholder)
            status["components"]["vector_service"] = {
                "configured": False,
                "service_type": None,
                "message": "Vector service integration pending - placeholder ready"
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
            
            # Schema Validator status
            status["components"]["schema_validator"] = {
                "available": True,
                "max_retries": test_case_validator.max_retries,
                "supported_validations": ["single_testcase", "batch_testcase"]
            }
            
            # Overall health
            critical_components_healthy = (
                ado_client.is_configured and
                traceability_manager.is_initialized
            )
            
            status["overall_health"] = "healthy" if critical_components_healthy else "needs_configuration"
            status["ready_for_test_generation"] = critical_components_healthy
            
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
    
    logger.info("All MCP tools registered successfully")