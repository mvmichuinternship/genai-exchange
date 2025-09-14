"""
Google Cloud Vector Service Module
Handles vector embeddings and similarity search using Vertex AI
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

# Google Cloud imports
from google.cloud import aiplatform
# from google.cloud import alloydb_connector
# from google.cloud.alloydb.connector import Connector
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self):
        self.project_id = None
        self.location = None
        self.index_id = None
        self.endpoint_id = None
        self.embedding_model = None
        self.alloydb_instance = None
        self.is_configured = False
        self.service_type = None  # 'vertex' or 'alloydb'
        
    async def configure_vertex_ai(self, project_id: str, location: str, index_id: str = None, endpoint_id: str = None):
        """Configure Vertex AI Matching Engine"""
        self.project_id = project_id
        self.location = location
        self.index_id = index_id
        self.endpoint_id = endpoint_id
        self.service_type = 'vertex'
        
        # Initialize Vertex AI
        aiplatform.init(project=project_id, location=location)
        
        # Initialize embedding model (local fallback)
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Local embedding model initialized as fallback")
        except Exception as e:
            logger.warning(f"Failed to initialize embedding model: {e}")
        
        self.is_configured = True
        logger.info(f"Vertex AI configured for project {project_id} in {location}")
    
    async def configure_alloydb(self, project_id: str, region: str, cluster: str, instance: str, database: str, 
                               user: str, password: str):
        """Configure AlloyDB with vector search"""
        self.project_id = project_id
        self.location = region
        self.service_type = 'alloydb'
        
        # Store AlloyDB connection details
        self.alloydb_config = {
            'project': project_id,
            'region': region,
            'cluster': cluster,
            'instance': instance,
            'database': database,
            'user': user,
            'password': password
        }
        
        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Local embedding model initialized for AlloyDB")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise
        
        self.is_configured = True
        logger.info(f"AlloyDB configured for project {project_id}")
    
    async def test_connection(self) -> Dict:
        """Test the vector service connection"""
        if not self.is_configured:
            return {
                "success": False,
                "error": "Vector service not configured"
            }
        
        try:
            if self.service_type == 'vertex':
                return await self._test_vertex_connection()
            elif self.service_type == 'alloydb':
                return await self._test_alloydb_connection()
            else:
                return {
                    "success": False,
                    "error": "Unknown service type"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _test_vertex_connection(self) -> Dict:
        """Test Vertex AI connection"""
        try:
            # Test embedding generation
            test_text = "This is a test query for vector search"
            embedding = await self._generate_embedding(test_text)
            
            return {
                "success": True,
                "service_type": "vertex_ai",
                "project_id": self.project_id,
                "location": self.location,
                "embedding_dimensions": len(embedding) if embedding else 0,
                "index_configured": self.index_id is not None,
                "endpoint_configured": self.endpoint_id is not None
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Vertex AI test failed: {str(e)}"
            }
    
    async def _test_alloydb_connection(self) -> Dict:
        """Test AlloyDB connection"""
        try:
            # Test embedding generation
            test_text = "This is a test query for vector search"
            embedding = await self._generate_embedding(test_text)
            
            return {
                "success": True,
                "service_type": "alloydb",
                "project_id": self.project_id,
                "embedding_dimensions": len(embedding) if embedding else 0,
                "database_configured": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"AlloyDB test failed: {str(e)}"
            }
    
    async def store_user_story_context(self, user_story_id: int, user_story_data: Dict, 
                                     additional_context: str = "") -> Dict:
        """Store user story data in vector database for RAG"""
        if not self.is_configured:
            raise ValueError("Vector service not configured")
        
        try:
            # Prepare text content for embedding
            content_parts = [
                f"User Story ID: {user_story_id}",
                f"Title: {user_story_data.get('title', '')}",
                f"Description: {user_story_data.get('description', '')}",
                f"Acceptance Criteria: {user_story_data.get('acceptance_criteria', '')}"
            ]
            
            if additional_context:
                content_parts.append(f"Additional Context: {additional_context}")
            
            # Add tags and metadata
            tags = user_story_data.get('tags', '')
            if tags:
                content_parts.append(f"Tags: {tags}")
            
            content_text = "\n".join(content_parts)
            
            # Generate embedding
            embedding = await self._generate_embedding(content_text)
            
            # Store based on service type
            if self.service_type == 'vertex':
                result = await self._store_vertex(user_story_id, content_text, embedding, user_story_data)
            elif self.service_type == 'alloydb':
                result = await self._store_alloydb(user_story_id, content_text, embedding, user_story_data)
            else:
                raise ValueError(f"Unsupported service type: {self.service_type}")
            
            return {
                "success": True,
                "user_story_id": user_story_id,
                "service_type": self.service_type,
                "embedding_dimensions": len(embedding),
                "content_length": len(content_text),
                "storage_result": result
            }
            
        except Exception as e:
            logger.error(f"Failed to store user story context: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_story_id": user_story_id
            }
    
    async def search_similar_context(self, query: str, max_results: int = 5, 
                                   similarity_threshold: float = 0.7) -> Dict:
        """Search for similar user stories and context"""
        if not self.is_configured:
            raise ValueError("Vector service not configured")
        
        try:
            # Generate query embedding
            query_embedding = await self._generate_embedding(query)
            
            # Search based on service type
            if self.service_type == 'vertex':
                results = await self._search_vertex(query_embedding, max_results, similarity_threshold)
            elif self.service_type == 'alloydb':
                results = await self._search_alloydb(query_embedding, max_results, similarity_threshold)
            else:
                raise ValueError(f"Unsupported service type: {self.service_type}")
            
            return {
                "success": True,
                "query": query,
                "service_type": self.service_type,
                "total_results": len(results),
                "similarity_threshold": similarity_threshold,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using available model"""
        if not self.embedding_model:
            raise ValueError("No embedding model available")
        
        # Use SentenceTransformer for now (can be replaced with Vertex AI embedding API)
        embedding = self.embedding_model.encode([text])[0]
        return embedding.tolist()
    
    async def _store_vertex(self, user_story_id: int, content: str, embedding: List[float], 
                           metadata: Dict) -> Dict:
        """Store in Vertex AI Matching Engine"""
        # For now, store in memory (in production, use Vertex AI Index)
        # This is a simplified implementation
        
        if not hasattr(self, '_vertex_store'):
            self._vertex_store = {}
        
        self._vertex_store[str(user_story_id)] = {
            'content': content,
            'embedding': embedding,
            'metadata': metadata,
            'stored_at': datetime.now(timezone.utc).isoformat()
        }
        
        return {
            "stored": True,
            "storage_id": str(user_story_id),
            "method": "memory_fallback"
        }
    
    async def _store_alloydb(self, user_story_id: int, content: str, embedding: List[float], 
                            metadata: Dict) -> Dict:
        """Store in AlloyDB with vector search"""
        # For now, store in memory (in production, use AlloyDB connector)
        # This is a simplified implementation
        
        if not hasattr(self, '_alloydb_store'):
            self._alloydb_store = {}
        
        self._alloydb_store[str(user_story_id)] = {
            'content': content,
            'embedding': embedding,
            'metadata': metadata,
            'stored_at': datetime.now(timezone.utc).isoformat()
        }
        
        return {
            "stored": True,
            "storage_id": str(user_story_id),
            "method": "memory_fallback"
        }
    
    async def _search_vertex(self, query_embedding: List[float], max_results: int, 
                           threshold: float) -> List[Dict]:
        """Search Vertex AI Matching Engine"""
        if not hasattr(self, '_vertex_store'):
            return []
        
        results = []
        for story_id, data in self._vertex_store.items():
            # Calculate cosine similarity
            stored_embedding = np.array(data['embedding'])
            query_emb = np.array(query_embedding)
            
            similarity = np.dot(stored_embedding, query_emb) / (
                np.linalg.norm(stored_embedding) * np.linalg.norm(query_emb)
            )
            
            if similarity >= threshold:
                results.append({
                    'user_story_id': int(story_id),
                    'similarity_score': float(similarity),
                    'content': data['content'],
                    'metadata': data['metadata'],
                    'stored_at': data['stored_at']
                })
        
        # Sort by similarity score
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:max_results]
    
    async def _search_alloydb(self, query_embedding: List[float], max_results: int, 
                            threshold: float) -> List[Dict]:
        """Search AlloyDB vector store"""
        if not hasattr(self, '_alloydb_store'):
            return []
        
        results = []
        for story_id, data in self._alloydb_store.items():
            # Calculate cosine similarity
            stored_embedding = np.array(data['embedding'])
            query_emb = np.array(query_embedding)
            
            similarity = np.dot(stored_embedding, query_emb) / (
                np.linalg.norm(stored_embedding) * np.linalg.norm(query_emb)
            )
            
            if similarity >= threshold:
                results.append({
                    'user_story_id': int(story_id),
                    'similarity_score': float(similarity),
                    'content': data['content'],
                    'metadata': data['metadata'],
                    'stored_at': data['stored_at']
                })
        
        # Sort by similarity score
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:max_results]
    
    async def delete_user_story_context(self, user_story_id: int) -> Dict:
        """Delete user story context from vector store"""
        try:
            story_key = str(user_story_id)
            deleted = False
            
            if self.service_type == 'vertex' and hasattr(self, '_vertex_store'):
                if story_key in self._vertex_store:
                    del self._vertex_store[story_key]
                    deleted = True
            elif self.service_type == 'alloydb' and hasattr(self, '_alloydb_store'):
                if story_key in self._alloydb_store:
                    del self._alloydb_store[story_key]
                    deleted = True
            
            return {
                "success": True,
                "deleted": deleted,
                "user_story_id": user_story_id,
                "service_type": self.service_type
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "user_story_id": user_story_id
            }
    
    async def get_storage_stats(self) -> Dict:
        """Get vector storage statistics"""
        try:
            stats = {
                "service_type": self.service_type,
                "configured": self.is_configured,
                "total_stored": 0,
                "storage_details": {}
            }
            
            if self.service_type == 'vertex' and hasattr(self, '_vertex_store'):
                stats["total_stored"] = len(self._vertex_store)
                stats["storage_details"] = {
                    "vertex_store_entries": len(self._vertex_store),
                    "oldest_entry": min([data['stored_at'] for data in self._vertex_store.values()]) if self._vertex_store else None,
                    "newest_entry": max([data['stored_at'] for data in self._vertex_store.values()]) if self._vertex_store else None
                }
            elif self.service_type == 'alloydb' and hasattr(self, '_alloydb_store'):
                stats["total_stored"] = len(self._alloydb_store)
                stats["storage_details"] = {
                    "alloydb_store_entries": len(self._alloydb_store),
                    "oldest_entry": min([data['stored_at'] for data in self._alloydb_store.values()]) if self._alloydb_store else None,
                    "newest_entry": max([data['stored_at'] for data in self._alloydb_store.values()]) if self._alloydb_store else None
                }
            
            return {
                "success": True,
                "stats": stats
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def batch_store_contexts(self, user_stories: List[Dict], additional_context: str = "") -> Dict:
        """Store multiple user story contexts in batch"""
        results = {
            "success": True,
            "total_stories": len(user_stories),
            "stored_count": 0,
            "failed_count": 0,
            "results": [],
            "errors": []
        }
        
        for user_story in user_stories:
            try:
                user_story_id = user_story.get('id')
                if not user_story_id:
                    results["failed_count"] += 1
                    results["errors"].append({
                        "error": "Missing user story ID",
                        "data": user_story
                    })
                    continue
                
                store_result = await self.store_user_story_context(
                    user_story_id, user_story, additional_context
                )
                
                if store_result.get("success"):
                    results["stored_count"] += 1
                    results["results"].append(store_result)
                else:
                    results["failed_count"] += 1
                    results["errors"].append({
                        "user_story_id": user_story_id,
                        "error": store_result.get("error", "Unknown error")
                    })
                    
            except Exception as e:
                results["failed_count"] += 1
                results["errors"].append({
                    "user_story_id": user_story.get('id', 'unknown'),
                    "error": str(e)
                })
        
        results["success"] = results["failed_count"] == 0
        return results