<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Intelligent Test Case Generator

A modular AI-powered test case generation system using FastAPI, Google ADK, and RAG (Retrieval-Augmented Generation) architecture with Google Cloud databases.

## Architecture Overview

```
┌─────────────────────┐    ┌─────────────────────┐    ┌──────────────────────┐
│   Main FastAPI      │    │   Google Cloud      │    │    ADK Agents        │
│   (Controller)      │    │   Databases         │    │   (AI Services)      │
│                     │    │                     │    │                      │
│ • Module Testing    │    │ • Cloud SQL         │    │ • Test Generator     │
│ • ADK Integration   │◄──►│ • Firestore         │◄──►│ • Requirement        │
│ • Document Parser   │    │ • Vector Search     │    │   Analyzer           │
│ • Data Ingestion    │    │ • Memorystore       │    │ • Domain Expert      │
│ • 7 Core Modules    │    │   (Redis)           │    │ • Code Reviewer      │
└─────────────────────┘    └─────────────────────┘    └──────────────────────┘
```


## Features

- **🔧 7 Modular Components**: Document parsing, data ingestion, domain tuning, test generation, software tuning, ALM integration, and traceability
- **🤖 AI-Powered Agents**: Google ADK agents for intelligent test case generation
- **📚 RAG Architecture**: Context-aware test generation using Vertex AI Vector Search
- **☁️ Google Cloud Native**: Fully integrated with Google Cloud database services
- **🧪 Individual Testing**: Each module can be tested independently
- **🚀 Production Ready**: Scalable architecture for enterprise deployment


## Prerequisites

- **Python 3.12+**
- **Google Cloud Project** with billing enabled
- **Google Cloud CLI** installed and configured
- **Git**


## Project Structure

```
intelligent-test-generator/
├── src/                                # Main FastAPI Application
│   ├── main.py                         # FastAPI entry point
│   ├── controller/                     # API Controllers
│   │   ├── module_test_controller.py   # Individual module testing
│   │   └── adk_integration_controller.py # ADK integration
│   ├── modules/                        # 7 Core Business Modules
│   │   ├── document_parser/
│   │   ├── data_ingestion/
│   │   ├── domain_tuning/
│   │   ├── test_generation/
│   │   ├── software_tuning/
│   │   ├── alm_integration/
│   │   └── traceability/
│   ├── core/                          # Database Clients
│   │   ├── cloud_sql_client.py        # Cloud SQL PostgreSQL
│   │   ├── firestore_client.py        # Document storage
│   │   ├── vector_search_client.py    # Vector embeddings
│   │   ├── memorystore_client.py      # Redis caching
│   │   └── database.py                # Database initialization
│   ├── services/
│   │   ├── adk_client.py              # ADK service client
│   │   ├── document_storage.py        # Firestore operations
│   │   ├── vector_service.py          # Vector search operations
│   │   └── cache_service.py           # Redis operations
│   └── api/
│       └── health.py                  # Health checks
│
├── adk_agents/                        # ADK AI Agents
│   ├── test_case_generator/
│   │   └── agent.py                   # Test case generation agent
│   ├── requirement_analyzer/
│   │   └── agent.py                   # Requirement analysis agent
│   ├── domain_expert/
│   │   └── agent.py                   # Domain expertise agent
│   └── code_reviewer/
│       └── agent.py                   # Code review agent
│
├── tests/                             # Test files
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment template
├── main.py                           # Application entry point
└── README.md
```


## Quick Setup Guide

### 1. Clone Repository and Setup Virtual Environment

```bash
# Clone the repository
git clone <your-repository-url>
cd intelligent-test-generator

# Create virtual environment with Python 3.12
python3.12 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Verify Python version
python --version  # Should show Python 3.12.x
```


### 2. Install Dependencies

```bash
# Install all required packages
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
pip list | grep -E "(fastapi|google-adk|google-cloud)"
```


### 3. Google Cloud Setup

#### 3.1 Install and Configure Google Cloud CLI

```bash
# Install Google Cloud CLI (if not already installed)
# macOS:
brew install --cask google-cloud-sdk

# Ubuntu/Debian:
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Windows: Download from https://cloud.google.com/sdk/docs/install

# Authenticate with Google Cloud
gcloud auth login
gcloud auth application-default login

# Set your project
export GOOGLE_CLOUD_PROJECT="your-project-id"
gcloud config set project $GOOGLE_CLOUD_PROJECT
```


#### 3.2 Enable Required APIs

```bash
# Enable all required Google Cloud APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable redis.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Verify APIs are enabled
gcloud services list --enabled | grep -E "(aiplatform|sql|firestore|redis)"
```


#### 3.3 Create Google Cloud Resources

```bash
# Create Cloud SQL PostgreSQL instance
gcloud sql instances create test-generator-db \
    --database-version=POSTGRES_14 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --storage-type=SSD \
    --storage-size=10GB

# Create database and user
gcloud sql databases create test_generator --instance=test-generator-db

gcloud sql users create testuser \
    --instance=test-generator-db \
    --password=SecurePassword123

# Enable Firestore in Native mode
gcloud firestore databases create --region=us-central1

# Create Memorystore Redis instance
gcloud redis instances create test-generator-cache \
    --region=us-central1 \
    --size=1 \
    --redis-version=redis_7_0

# Get connection details
gcloud sql instances describe test-generator-db
gcloud redis instances describe test-generator-cache --region=us-central1
```


### 4. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit environment file with your configurations
nano .env  # or use your preferred editor
```


#### Sample `.env` Configuration

```env
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
GOOGLE_CLOUD_LOCATION=us-central1

# Cloud SQL Configuration
CLOUD_SQL_CONNECTION_NAME=your-project-id:us-central1:test-generator-db
CLOUD_SQL_DATABASE_NAME=test_generator
CLOUD_SQL_USERNAME=testuser
CLOUD_SQL_PASSWORD=SecurePassword123

# Firestore Configuration
FIRESTORE_DATABASE_ID=(default)

# Vertex AI Vector Search (set up after creating vector index)
VECTOR_SEARCH_ENDPOINT_ID=your-vector-endpoint-id
VECTOR_SEARCH_INDEX_ID=your-vector-index-id
VECTOR_SEARCH_DEPLOYED_INDEX_ID=your-deployed-index-id

# Memorystore Redis Configuration
REDIS_HOST=your-redis-instance-ip
REDIS_PORT=6379
REDIS_PASSWORD=""

# ADK Configuration
GOOGLE_GENAI_USE_VERTEXAI=1

# Application Configuration
SECRET_KEY=your-super-secret-key-here
DEBUG=True
LOG_LEVEL=INFO

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
ADK_SERVICE_PORT=8001
```


### 5. Database Initialization

```bash
# Create database tables (if using SQLAlchemy migrations)
python -c "
from src.core.database import initialize_databases
import asyncio
asyncio.run(initialize_databases())
"

# Or run Alembic migrations (if configured)
alembic upgrade head
```


## Running the Application

### Development Mode (Single Command)

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start the application (runs both FastAPI server and ADK service)
python main.py

# Application will start on:
# 🌟 Main API: http://localhost:8000
# 🤖 ADK Service: http://localhost:8001 (auto-started)
# 📖 API Documentation: http://localhost:8000/docs
```


### Alternative: Manual Service Management

```bash
# Terminal 1: Start main FastAPI application
source venv/bin/activate
cd src
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start ADK service (if not auto-started)
source venv/bin/activate
python -c "
from google.adk.cli.fast_api import get_fast_api_app
import uvicorn

adk_app = get_fast_api_app(agents_dir='adk_agents', web=False)
uvicorn.run(adk_app, host='0.0.0.0', port=8001)
"
```


### Production Mode

```bash
# Install production server
pip install gunicorn

# Run with Gunicorn
gunicorn main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --keep-alive 2
```


## Verifying the Setup

### 1. Health Checks

```bash
# Check main application
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "timestamp": "...", "services": {...}}

# Check ADK service
curl http://localhost:8001/adk/health

# Expected response:
# {"status": "healthy", "service": "adk-agent-service", "available_agents": [...]}
```


### 2. API Documentation

Visit the interactive API documentation:

- **Main API**: http://localhost:8000/docs
- **ADK Service**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8000/redoc


### 3. Test Individual Modules

```bash
# Test document parser
curl -X POST "http://localhost:8000/api/test/document-parser/parse-text" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User should be able to login with email and password",
    "options": {"extract_requirements": true}
  }'

# Test module information
curl http://localhost:8000/api/test/modules/info
```


### 4. Test AI Agent Integration

```bash
# Test test case generation
curl -X POST "http://localhost:8000/api/adk/generate-test-cases" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "requirements=User login functionality with email and password validation&coverage_level=comprehensive"

# Test requirement analysis
curl -X POST "http://localhost:8000/api/adk/analyze-requirements" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "requirements=The system shall allow users to create, read, update and delete customer records"
```


## Available API Endpoints

### Module Testing Endpoints

```
GET    /api/test/health                          # System health check
GET    /api/test/modules/info                    # Module information

POST   /api/test/document-parser/parse-file      # Parse uploaded file
POST   /api/test/document-parser/parse-text      # Parse text content

POST   /api/test/data-ingestion/embed-and-store  # Create embeddings
POST   /api/test/data-ingestion/query-vectors    # Search vectors

POST   /api/test/domain-tuning/apply-compliance  # Apply domain rules
POST   /api/test/software-tuning/configure       # Configure tech stack

POST   /api/test/alm-integration/sync             # Sync with ALM tools
POST   /api/test/traceability/build-matrix       # Build traceability
```


### ADK Integration Endpoints

```
POST   /api/adk/generate-test-cases              # Generate test cases via AI
POST   /api/adk/analyze-requirements             # Analyze requirements via AI
POST   /api/adk/domain-expertise                 # Get domain expertise
GET    /api/adk/health                          # ADK service health
```


## Development Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Install new dependencies
pip install package-name
pip freeze > requirements.txt

# Run tests
python -m pytest tests/ -v

# Format code
pip install black isort
black .
isort .

# Type checking
pip install mypy
mypy src/

# Start development server with auto-reload
python main.py
```


## Deployment

### Google Cloud Run Deployment

```bash
# Build and deploy
gcloud run deploy intelligent-test-generator \
    --source . \
    --port 8000 \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars GOOGLE_GENAI_USE_VERTEXAI=1 \
    --set-env-vars GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT \
    --memory 2Gi \
    --cpu 2 \
    --timeout 900 \
    --max-instances 10

# Get deployment URL
gcloud run services describe intelligent-test-generator \
    --region us-central1 \
    --format="value(status.url)"
```


## Troubleshooting

### Common Issues

#### 1. Virtual Environment Issues

```bash
# Recreate virtual environment
rm -rf venv
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```


#### 2. Google Cloud Authentication

```bash
# Re-authenticate
gcloud auth revoke --all
gcloud auth login
gcloud auth application-default login

# Verify credentials
gcloud auth list
gcloud config list
```


#### 3. Database Connection Issues

```bash
# Test Cloud SQL connection
gcloud sql connect test-generator-db --user=testuser --quiet

# Check Redis instance status
gcloud redis instances describe test-generator-cache --region=us-central1
```


#### 4. Port Conflicts

```bash
# Check what's using ports
lsof -i :8000
lsof -i :8001

# Kill processes if needed
kill -9 <PID>

# Use different ports
API_PORT=8000 ADK_SERVICE_PORT=8081 python main.py
```


#### 5. Import Errors

```bash
# Ensure you're in the project root directory
pwd  # Should show .../intelligent-test-generator

# Verify virtual environment is activated
which python  # Should show .../venv/bin/python

# Check PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```


### Logging and Debugging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python main.py

# View application logs
tail -f logs/app.log

# Check Google Cloud logs
gcloud logging read "resource.type=cloud_run_revision" --limit=50
```


## Next Steps

1. **Configure Vector Search**: Set up Vertex AI Vector Search index for RAG functionality
2. **Add Authentication**: Implement user authentication and authorization
3. **Customize Agents**: Modify ADK agents in `adk_agents/` directory for your specific needs
4. **Add More Modules**: Extend the system with additional modules as needed
5. **Set Up CI/CD**: Configure automated testing and deployment pipelines

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Review Google Cloud documentation
3. Check ADK documentation at https://google.github.io/adk-docs/
4. Open an issue in the project repository

***

## Quick Start Summary

```bash
# 1. Setup
git clone <repo-url> && cd intelligent-test-generator
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your Google Cloud settings

# 3. Run
python main.py

# 4. Test
curl http://localhost:8000/health
open http://localhost:8000/docs
```

🎉 **You're ready to start generating intelligent test cases!** 🚀

