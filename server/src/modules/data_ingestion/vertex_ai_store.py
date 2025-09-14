from .interfaces import VectorStoreInterface, VectorSearchResult
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel
from typing import List, Dict, Optional
import json

class VertexAIVectorStore(VectorStoreInterface):
    """WORKING Vertex AI Vector Search implementation"""

    def __init__(self, project_id: str, index_name: str, endpoint_name: str, location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        self.index_name = index_name
        self.endpoint_name = endpoint_name

        # Initialize Vertex AI
        aiplatform.init(project=project_id, location=location)

        # Initialize embedding model
        self.embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-005")

        # Get existing index and endpoint (they should already exist)
        try:
            self.index = aiplatform.MatchingEngineIndex(index_name)
            self.endpoint = aiplatform.MatchingEngineIndexEndpoint(endpoint_name)
        except Exception as e:
            print(f"Warning: Could not load index/endpoint: {e}")
            self.index = None
            self.endpoint = None

    async def search_context(self,
                           query: str,
                           top_k: int = 10,
                           filters: Optional[Dict] = None) -> List[VectorSearchResult]:
        """ACTUAL vector search implementation"""

        if not self.endpoint:
            print("Vector search endpoint not available")
            return []

        try:
            # 1. Generate query embedding
            query_embedding = self.embedding_model.get_embeddings([query])[0].values

            # 2. Search the vector index
            response = self.endpoint.find_neighbors(
                deployed_index_id=f"{self.index_name}_deployed",  # Usually index_name + "_deployed"
                queries=[query_embedding],
                num_neighbors=top_k
            )

            # 3. Convert to generic format
            results = []
            for neighbor in response[0]:  # First query response
                # Extract metadata (you'll need to store this during ingestion)
                metadata = neighbor.datapoint.restricts or {}

                results.append(VectorSearchResult(
                    content=metadata.get("text_content", ""),  # Your stored text
                    score=1 - neighbor.distance,  # Convert distance to similarity score
                    metadata=metadata,
                    source=metadata.get("source", "vertex_ai")
                ))

            return results

        except Exception as e:
            print(f"Vector search failed: {e}")
            return []

    async def ingest_documents(self, text_array: List[str], metadata: Dict) -> Dict:
        """ACTUAL document ingestion implementation"""

        if not self.index:
            return {"status": "error", "message": "Index not available"}

        try:
            # 1. Generate embeddings for all texts
            embeddings = self.embedding_model.get_embeddings(text_array)

            # 2. Prepare datapoints for insertion
            datapoints = []
            for i, (text, embedding) in enumerate(zip(text_array, embeddings)):
                datapoint_id = f"{metadata.get('doc_id', 'unknown')}_{i}"

                # Prepare metadata (restrictions in Vertex AI terminology)
                restricts = {
                    "text_content": text,
                    "doc_id": metadata.get("doc_id", ""),
                    "document_type": metadata.get("document_type", "general"),
                    "chunk_index": str(i)
                }

                datapoints.append({
                    "datapoint_id": datapoint_id,
                    "feature_vector": embedding.values,
                    "restricts": restricts
                })

            # 3. Upsert to index
            self.index.upsert_datapoints(datapoints=datapoints)

            return {
                "status": "success",
                "datapoints_added": len(datapoints),
                "doc_id": metadata.get("doc_id")
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Ingestion failed: {str(e)}"
            }

    async def health_check(self) -> bool:
        """Check if vector store is accessible"""
        try:
            # Simple test - try to search with dummy query
            test_embedding = self.embedding_model.get_embeddings(["test"])[0].values

            if self.endpoint:
                self.endpoint.find_neighbors(
                    deployed_index_id=f"{self.index_name}_deployed",
                    queries=[test_embedding],
                    num_neighbors=1
                )
                return True
        except:
            pass
        return False
