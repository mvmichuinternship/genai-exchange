from .interfaces import VectorStoreInterface, VectorSearchResult
from google.cloud import aiplatform, aiplatform_v1
from vertexai.language_models import TextEmbeddingModel
from typing import List, Dict, Optional

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
                deployed_index_id="test_generation_index_deployed",
                queries=[query_embedding],
                num_neighbors=top_k,
                return_full_datapoint=True
            )

            # 3. Convert to generic format
            results = []
            for neighbor in response[0]:
                content = ""
                metadata_dict = {}

                # Parse restricts - they're Namespace objects with name, allow_tokens, deny_tokens
                for restrict in (neighbor.restricts or []):
                    namespace_name = restrict.name  # Use 'name' not 'namespace'
                    allow_values = restrict.allow_tokens or []  # Use 'allow_tokens' not 'allow_list'

                    # Get the first value if available
                    value = allow_values[0] if allow_values else ""

                    if namespace_name == "content":
                        content = value  # ✅ Get content from restricts
                    else:
                        metadata_dict[namespace_name] = value

                # Only add results that have content
                if content:
                    results.append(VectorSearchResult(
                        content=content,
                        score=1 - neighbor.distance,  # Convert distance to similarity score
                        metadata=metadata_dict,
                        source="vertex_ai"
                    ))
                    print(f"Added result: {content[:100]}...")  # Show first 100 chars

            print(f"Extracted {len(results)} results with content")
            return results

        except Exception as e:
            print(f"Vector search failed: {e}")
            import traceback
            traceback.print_exc()
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

                restricts = [
                aiplatform_v1.types.index.IndexDatapoint.Restriction(
                    namespace="doc_id",
                    allow_list=[metadata.get("doc_id", "")]
                ),
                aiplatform_v1.types.index.IndexDatapoint.Restriction(
                    namespace="doc_type",
                    allow_list=[metadata.get("document_type", "general")]
                ),
                aiplatform_v1.types.index.IndexDatapoint.Restriction(
                    namespace="content",
                    allow_list=[text]
                ),
                aiplatform_v1.types.index.IndexDatapoint.Restriction(
                    namespace="chunk_index",
                    allow_list=[str(i)]
                )
            ]

                datapoint = aiplatform_v1.types.index.IndexDatapoint(
                    datapoint_id=datapoint_id,
                    feature_vector=embedding.values,
                    restricts=restricts
                )
                datapoints.append(datapoint)

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
                    deployed_index_id=f"{self.index_name}",
                    queries=[test_embedding],
                    num_neighbors=1
                )
                return True
        except:
            pass
        return False
