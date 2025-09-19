from typing import Dict, Any
from .interfaces import VectorStoreInterface
from .vertex_ai_store import VertexAIVectorStore

class VectorStoreFactory:
    """Factory to create different vector store implementations"""

    @staticmethod
    def create_vector_store(store_type: str, config: Dict[str, Any]) -> VectorStoreInterface:
        """Create vector store based on configuration"""

        if store_type.lower() == "vertex_ai":
            return VertexAIVectorStore(
                project_id=config["project_id"],
                index_name=config["index_name"],
                endpoint_name=config["endpoint_name"]
            )

        elif store_type.lower() == "opensearch":
            raise NotImplementedError("Open Search not implemented yet")

        elif store_type.lower() == "azure_search":
            # return AzureSearchVectorStore(...)  # Future implementation
            raise NotImplementedError("Azure Search not implemented yet")

        else:
            raise ValueError(f"Unsupported vector store type: {store_type}")
