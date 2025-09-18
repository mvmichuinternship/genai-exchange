from google.adk.tools import ToolContext
from typing import List
from .factory import VectorStoreFactory
from .context_provider import GenericRAGContextProvider

# Configuration (you can move this to config file)
VECTOR_STORE_CONFIG = {
    "type": "vertex_ai",
    "config": {
        "project_id": "celtic-origin-472009-n5",
        "index_name": "projects/195472357560/locations/us-central1/indexes/5689930892298944512",
        "endpoint_name": "projects/195472357560/locations/us-central1/indexEndpoints/5490892899392421888"
    }
}

async def get_rag_context_as_text_array_tool(
    query_context: str,
    context_scope: str = "comprehensive",
    tool_context: ToolContext = None
) -> List[str]:
    """
    Search existing vector index for relevant context
    """
    try:
        # CORRECT: Connect to existing vector store with data
        vector_store = VectorStoreFactory.create_vector_store(
            store_type=VECTOR_STORE_CONFIG["type"],
            config=VECTOR_STORE_CONFIG["config"]
        )

        # IMPORTANT: This should SEARCH the existing index, not create new data
        context_provider = GenericRAGContextProvider(vector_store)

        # This calls vector_store.search_context() - the key method
        context_text_array = await context_provider.get_context_as_text_array(
            query=query_context,
            context_scope=context_scope
        )

        # Debug: Log what we found
        print(f"RAG search for '{query_context}' found {len(context_text_array)} results")

        if tool_context:
            tool_context.state["rag_context_available"] = len(context_text_array) > 0
            tool_context.state["rag_context_count"] = len(context_text_array)

        return context_text_array

    except Exception as e:
        print(f"RAG context search failed: {e}")
        return []
