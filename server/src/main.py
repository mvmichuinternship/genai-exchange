from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import warnings
from contextlib import asynccontextmanager

# Suppress ADK experimental warnings
warnings.filterwarnings("ignore", message=".*EXPERIMENTAL.*")
warnings.filterwarnings("ignore", message=".*TracerProvider.*")

# Import ADK after suppressing warnings
from google.adk.cli.fast_api import get_fast_api_app

# Import your controller
from controller.adk_integrated_controller import adk_test_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

# Create the main FastAPI app
app = FastAPI(
    title="Intelligent Test Case Generator - Direct ADK Integration",
    description="Direct communication with ADK agents",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the correct agents directory path - FIXED to look in sibling directory
# Current structure: server/src/main.py and server/adk_service/agents/
current_dir = os.path.dirname(__file__)  # server/src/
parent_dir = os.path.dirname(current_dir)  # server/
agents_dir = os.path.join(parent_dir, "adk_service", "agents")  # server/adk_service/agents/

# Create and mount ADK app
try:
    print(f"📁 Loading ADK agents from: {agents_dir}")
    print(f"📁 Directory exists: {os.path.exists(agents_dir)}")
    print(f"📁 Current working directory: {os.getcwd()}")
    print(f"📁 Script location: {current_dir}")
    print(f"📁 Parent directory: {parent_dir}")

    # List agents found
    if os.path.exists(agents_dir):
        print(f"✅ Agents directory found!")
        for item in os.listdir(agents_dir):
            agent_path = os.path.join(agents_dir, item)
            if os.path.isdir(agent_path):
                print(f"🤖 Found agent directory: {item}")
                # Check if it has the required files
                init_file = os.path.join(agent_path, "__init__.py")
                agent_file = os.path.join(agent_path, "agent.py")
                print(f"   - __init__.py exists: {os.path.exists(init_file)}")
                print(f"   - agent.py exists: {os.path.exists(agent_file)}")
    else:
        print(f"❌ Agents directory not found at: {agents_dir}")
        print("📂 Looking for alternative paths...")

        # Try some alternative paths
        alt_paths = [
            os.path.join(current_dir, "adk_service", "agents"),
            os.path.join(os.getcwd(), "adk_service", "agents"),
            os.path.join(parent_dir, "adk_service"),
            os.path.join(current_dir, "..", "adk_service", "agents")
        ]

        for alt_path in alt_paths:
            abs_alt_path = os.path.abspath(alt_path)
            print(f"   Trying: {abs_alt_path} -> {os.path.exists(abs_alt_path)}")

    adk_app = get_fast_api_app(
        agents_dir=agents_dir,
        web=True  # Enable web UI
    )

    # Mount ADK app as sub-application
    app.mount("/adk", adk_app)
    print("✅ ADK app created and mounted successfully at /adk")

except Exception as e:
    print(f"❌ Error creating ADK app: {e}")
    print("Continuing without ADK integration...")

# Include your controller
app.include_router(adk_test_router, prefix="/api/agents", tags=["adk-agent-testing"])

@app.get("/")
async def root():
    return {
        "message": "Intelligent Test Case Generator - Direct ADK Integration",
        "status": "✅ Running",
        "agents_directory": agents_dir,
        "test_endpoints": {
            "complete_workflow": "/api/agents/test-agents/requirements-to-tests",
            "validate_and_test": "/api/agents/test-agents/validate-and-test",
            "diagnose": "/api/agents/test-agents/diagnose",
            "health_check": "/api/agents/test-agents/health"
        },
        "adk_endpoints": {
            "web_ui": "/adk",
            "agents_api": "/adk/apps/",
            "run_agent": "/adk/run"
        },
        "services": {
            "api_docs": "/docs",
            "adk_web_ui": "/adk"
        }
    }

@app.get("/status")
async def get_status():
    """Get application status"""
    agents_found = []
    if os.path.exists(agents_dir):
        agents_found = [
            item for item in os.listdir(agents_dir)
            if os.path.isdir(os.path.join(agents_dir, item))
        ]

    return {
        "application": "running",
        "adk_integration": "enabled",
        "agents_directory": agents_dir,
        "agents_directory_exists": os.path.exists(agents_dir),
        "agents_found": agents_found,
        "working_directory": os.getcwd(),
        "script_location": os.path.dirname(__file__)
    }

@app.get("/debug-paths")
async def debug_paths():
    """Debug endpoint to check all relevant paths"""
    current_dir = os.path.dirname(__file__)
    parent_dir = os.path.dirname(current_dir)

    return {
        "current_working_directory": os.getcwd(),
        "script_location": current_dir,
        "parent_directory": parent_dir,
        "configured_agents_dir": agents_dir,
        "agents_dir_exists": os.path.exists(agents_dir),
        "alternative_paths": {
            path: os.path.exists(path) for path in [
                os.path.join(current_dir, "adk_service", "agents"),
                os.path.join(os.getcwd(), "adk_service", "agents"),
                os.path.join(parent_dir, "adk_service"),
                os.path.join(current_dir, "..", "adk_service", "agents")
            ]
        },
        "directory_contents": {
            "current_dir": os.listdir(current_dir) if os.path.exists(current_dir) else [],
            "parent_dir": os.listdir(parent_dir) if os.path.exists(parent_dir) else [],
            "working_dir": os.listdir(os.getcwd()) if os.path.exists(os.getcwd()) else []
        }
    }

if __name__ == "__main__":
    print("🚀 Starting Intelligent Test Case Generator...")
    print(f"📍 Working from: {os.getcwd()}")
    print(f"📍 Script at: {os.path.dirname(__file__)}")
    print(f"📍 Looking for agents at: {agents_dir}")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)