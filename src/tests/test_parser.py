# test_parser.py

import asyncio
import aiohttp
import json
import os
from pathlib import Path

# async def test_document_upload():
#     """Test document upload functionality"""

#     # Test file upload
#     test_file_path = "test_document.txt"  # You'll need to create this

#     # Create a test text file if it doesn't exist
#     if not os.path.exists(test_file_path):
#         with open(test_file_path, 'w') as f:
#             f.write("""
# This is a test document for the ADK document processing system.
# It contains multiple sentences to test text chunking.
# The system should be able to process this file and create chunks.
# Each chunk should respect sentence boundaries and maintain context.
# This helps ensure that search results are meaningful and coherent.
#             """)

#     async with aiohttp.ClientSession() as session:
#         # Test 1: Health check
#         print("Testing health check...")
#         async with session.get('http://localhost:8000/health') as response:
#             if response.status == 200:
#                 data = await response.json()
#                 print(f"✅ Health check passed: {data}")
#             else:
#                 print(f"❌ Health check failed: {response.status}")

#         # Test 2: Get supported types
#         print("\nTesting supported types...")
#         async with session.get('http://localhost:8000/api/documents/supported-types') as response:
#             if response.status == 200:
#                 data = await response.json()
#                 print(f"✅ Supported types: {data}")
#             else:
#                 print(f"❌ Supported types failed: {response.status}")

#         # Test 3: Upload document
#         print("\nTesting document upload...")
#         with open(test_file_path, 'rb') as f:
#             data = aiohttp.FormData()
#             data.add_field('file', f, filename='test_document.txt', content_type='text/plain')
#             data.add_field('document_id', 'test_doc_001')

#             async with session.post('http://localhost:8000/api/documents/upload', data=data) as response:
#                 if response.status == 200:
#                     result = await response.json()
#                     print(f"✅ Upload successful: {result}")
#                     document_id = result.get('document_id')

#                     # Test 4: Check status
#                     print(f"\nChecking status for {document_id}...")
#                     async with session.get(f'http://localhost:8000/api/documents/status/{document_id}') as status_response:
#                         if status_response.status == 200:
#                             status_data = await status_response.json()
#                             print(f"✅ Status check: {status_data}")
#                         else:
#                             print(f"❌ Status check failed: {status_response.status}")

#                 else:
#                     error_text = await response.text()
#                     print(f"❌ Upload failed: {response.status} - {error_text}")

#         # Test 5: Search (if embeddings are enabled)
#         print("\nTesting search...")
#         search_params = {
#             'query': 'test document processing',
#             'limit': 5
#         }
#         async with session.get('http://localhost:8000/api/documents/search', params=search_params) as response:
#             if response.status == 200:
#                 search_results = await response.json()
#                 print(f"✅ Search successful: {search_results}")
#             else:
#                 error_text = await response.text()
#                 print(f"⚠️  Search failed (might be expected if embeddings disabled): {response.status} - {error_text}")

#     # Clean up test file
#     if os.path.exists(test_file_path):
#         os.remove(test_file_path)

def test_processors_directly():
    """Test the document processors directly without API"""
    print("\n=== Testing Document Processors Directly ===")

    from src.modules.document_parser.utils import DocumentProcessor, SmartTextChunker

    # Test text chunker
    chunker = SmartTextChunker(chunk_size=100, overlap=20)

    test_text = """
    This is a test document with multiple sentences. Each sentence should be handled properly.
    The chunker should respect sentence boundaries. It should also handle overlaps correctly.
    This helps maintain context across chunks. The system should work reliably with various text lengths.
    """

    chunks = chunker.chunk_text(test_text, {'document_id': 'test', 'source_type': 'txt'})
    print(f"✅ Created {len(chunks)} chunks from test text")

    for i, chunk in enumerate(chunks):
        print(f"Chunk {i}: {len(chunk['text'])} chars, {chunk['metadata']['token_count']} tokens")
        print(f"Text preview: {chunk['text'][:100]}...")
        print("---")

if __name__ == "__main__":
    print("=== Testing Document Processing System ===\n")

    # Test processors directly first
    test_processors_directly()

    # Test API endpoints
    print("\n=== Testing API Endpoints ===")
    print("Make sure your server is running on http://localhost:8000")
    print("Start it with: python -m src.controller.adk_integrated_controller\n")

    try:
        asyncio.run(test_document_upload())
    except Exception as e:
        print(f"❌ API tests failed: {e}")
        print("Make sure your server is running!")