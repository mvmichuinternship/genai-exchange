#!/usr/bin/env python3
"""
One-time setup script for Vertex AI Vector Search
Run this before using the upload-with-rag endpoint
"""

import asyncio
from google.cloud import aiplatform
from modules.data_ingestion.vector_db import VertexVectorStore

async def setup_vertex_vector_search():
    """Create and deploy Vertex AI Vector Search resources"""

    # Configuration
    PROJECT_ID = "celtic-origin-472009-n5"
    LOCATION = "us-central1"
    INDEX_DISPLAY_NAME = "test-generation-index"
    ENDPOINT_DISPLAY_NAME = "test-generation-endpoint"

    print(f"Setting up Vertex AI Vector Search for project: {PROJECT_ID}")

    try:
        # Initialize Vertex AI
        aiplatform.init(project=PROJECT_ID, location=LOCATION)

        # Create vector store helper
        vector_store = VertexVectorStore(PROJECT_ID, LOCATION)

        # Step 1: Create Vector Search Index
        print("\n1. Creating Vector Search Index...")
        index_resource_name = vector_store.create_streaming_index(
            display_name=INDEX_DISPLAY_NAME,
            dimensions=768  # text-embedding-005 uses 768 dimensions
        )
        print(f"✓ Index created: {index_resource_name}")

        # Step 2: Create Index Endpoint
        print("\n2. Creating Index Endpoint...")
        endpoint_resource_name = vector_store.create_index_endpoint(
            display_name=ENDPOINT_DISPLAY_NAME
        )
        print(f"✓ Endpoint created: {endpoint_resource_name}")

        # Step 3: Deploy Index to Endpoint
        print("\n3. Deploying Index to Endpoint...")
        print("⚠️  This step takes 10-20 minutes. Please wait...")

        endpoint = aiplatform.MatchingEngineIndexEndpoint(endpoint_resource_name)
        index = aiplatform.MatchingEngineIndex(index_resource_name)

        # FIX: Use underscores instead of hyphens
        deployed_index_id = "test_generation_index_deployed"  # Valid ID

        deployed_index = endpoint.deploy_index(
            index=index,
            deployed_index_id=deployed_index_id,
            display_name=f"{INDEX_DISPLAY_NAME}_deployment"
        )


        print("✓ Index deployed successfully!")

        # Display configuration to update
        print("\n" + "="*60)
        print("SETUP COMPLETE! 🎉")
        print("="*60)
        print("\nUpdate your rag_tool.py configuration:")
        print("VECTOR_STORE_CONFIG = {")
        print('    "type": "vertex_ai",')
        print('    "config": {')
        print(f'        "project_id": "{PROJECT_ID}",')
        print(f'        "index_name": "{index_resource_name}",')
        print(f'        "endpoint_name": "{endpoint_resource_name}"')
        print('    }')
        print("}")

        return {"status": "success", "index": index_resource_name, "endpoint": endpoint_resource_name}

    except Exception as e:
        print(f"❌ Setup failed: {str(e)}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    result = asyncio.run(setup_vertex_vector_search())
