"""
Azure DevOps MCP Server - Main Entry Point
Focused on test case generation and traceability with user stories
"""

import asyncio
import logging
from mcp.server.fastmcp import FastMCP

# Import modular components
from ado_client import ADOClient
from vector_service import VectorService
from traceability_manager import TraceabilityManager
from mcp_tools import register_all_tools

# Configure logging
logging.basicConfig(level=logging.INFO)
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
    
    logger.info("Initializing Azure DevOps MCP Server...")
    
    # Initialize services (will be configured via tools)
    ado_client = ADOClient()
    vector_service = VectorService()
    traceability_manager = TraceabilityManager()
    
    # Register all MCP tools
    register_all_tools(mcp, ado_client, vector_service, traceability_manager)
    
    logger.info("Azure DevOps MCP Server initialized successfully")

if __name__ == "__main__":
    asyncio.run(initialize_services())
    logger.info("Starting Azure DevOps MCP Server for test case generation...")
    asyncio.run(mcp.run())