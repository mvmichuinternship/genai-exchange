from google.cloud import aiplatform
import vertexai

class VertexVectorStore:
    def __init__(self, project_id: str, location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        vertexai.init(project=project_id, location=location)

    def create_streaming_index(self, display_name: str, dimensions: int = 768) -> str:
        """Create Vector Search index optimized for frequent updates"""
        index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
            display_name=display_name,
            description="Dynamic RAG Index for Test Generation",
            dimensions=dimensions,
            approximate_neighbors_count=150,
            leaf_node_embedding_count=500,
            leaf_nodes_to_search_percent=7,
            index_update_method="STREAM_UPDATE",  # Critical for frequent updates
            distance_measure_type=aiplatform.matching_engine.matching_engine_index_config.DistanceMeasureType.COSINE_DISTANCE,
        )
        return index.resource_name

    def create_index_endpoint(self, display_name: str) -> str:
        """Create public endpoint for vector search"""
        endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
            display_name=display_name,
            public_endpoint_enabled=True,
            description="RAG Index Endpoint"
        )
        return endpoint.resource_name
