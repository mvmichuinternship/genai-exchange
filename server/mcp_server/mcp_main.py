"""
Azure DevOps MCP Server - Main Entry Point
Focused on test case generation with schema validation and traceability
"""

import asyncio
import logging
import os
from mcp.server.fastmcp import FastMCP

# Import modular components
from ado_client import ADOClient
# from vector_service import VectorService  # Placeholder for future integration
from traceability_manager import TraceabilityManager
from mcp_tools import register_all_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize MCP Server
mcp = FastMCP("ado-testcase-server")

# Global instances
ado_client = None
vector_service = None
traceability_manager = None

async def initialize_services():
    """Initialize all required services"""
    global ado_client, vector_service, traceability_manager
    
    logger.info("Initializing Azure DevOps MCP Server for test case generation...")
    
    # Initialize core services
    ado_client = ADOClient()
    # vector_service = VectorService()  # Placeholder - will be configured later
    traceability_manager = TraceabilityManager()
    
    # Auto-configure from environment if available
    await auto_configure_from_env()
    
    # Register all MCP tools
    register_all_tools(mcp, ado_client, vector_service, traceability_manager)
    
    logger.info("Azure DevOps MCP Server initialized successfully")
    logger.info("Available tools: configure_ado_connection, fetch_user_story, create_testcase, generate_testcases_from_story, etc.")

async def auto_configure_from_env():
    """Auto-configure services from environment variables if present"""
    global ado_client, traceability_manager
    
    # ADO Configuration
    ado_org = os.getenv("ADO_ORG")
    ado_project = os.getenv("ADO_PROJECT") 
    ado_pat = os.getenv("ADO_PAT")
    
    if ado_org and ado_project and ado_pat:
        try:
            ado_client.configure(ado_org, ado_project, ado_pat)
            test_result = await ado_client.test_connection()
            if test_result.get("success"):
                logger.info(f"ADO client auto-configured for project: {ado_project}")
            else:
                logger.warning(f"ADO auto-configuration failed: {test_result.get('error')}")
        except Exception as e:
            logger.warning(f"Failed to auto-configure ADO: {e}")
    else:
        logger.info("ADO environment variables not found - manual configuration required")
    
    # Traceability Manager
    traceability_file = os.getenv("TRACEABILITY_FILE", "traceability_matrix.json")
    try:
        await traceability_manager.initialize(traceability_file)
        logger.info("Traceability manager auto-initialized")
    except Exception as e:
        logger.warning(f"Failed to auto-initialize traceability manager: {e}")

if __name__ == "__main__":
    # Initialize services
    asyncio.run(initialize_services())
    
    # Start the MCP server
    logger.info("Starting Azure DevOps MCP Server...")
    logger.info("Ready to handle test case generation workflows with schema validation")
    asyncio.run(mcp.run())