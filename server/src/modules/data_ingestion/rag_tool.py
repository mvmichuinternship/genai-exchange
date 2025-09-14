from google.adk.tools import ToolContext
from typing import List
from .factory import VectorStoreFactory
from .context_provider import GenericRAGContextProvider

# Configuration (you can move this to config file)
VECTOR_STORE_CONFIG = {
    "type": "vertex_ai",  # Change to "opensearch" or "azure_search" later
    "config": {
        "project_id": "celtic-origin-472009-n5",  # From environment
        "index_name": "test-generation-index",
        "endpoint_name": "test-generation-endpoint"
    }
}

async def get_rag_context_as_text_array_tool(
    query_context: str,
    context_scope: str = "comprehensive",
    tool_context: ToolContext = None
) -> List[str]:
    """
    Simple tool that returns RAG context as text array
    This is what your sequential agent will call
    """

    try:
        # Create vector store using factory pattern
        vector_store = VectorStoreFactory.create_vector_store(
            store_type=VECTOR_STORE_CONFIG["type"],
            config=VECTOR_STORE_CONFIG["config"]
        )

        # Create generic context provider
        context_provider = GenericRAGContextProvider(vector_store)

        # Get context as text array
        context_text_array = await context_provider.get_context_as_text_array(
            query=query_context,
            context_scope=context_scope
        )

        # Store in session state if tool_context available
        if tool_context:
            tool_context.state["rag_context_available"] = len(context_text_array) > 0
            tool_context.state["rag_context_count"] = len(context_text_array)

        return context_text_array

    except Exception as e:
        print(f"RAG context fetch failed: {e}")
        # Return empty array - your agents continue without RAG
        return []
