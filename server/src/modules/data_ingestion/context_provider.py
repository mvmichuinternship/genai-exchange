from typing import List, Dict, Optional
from .interfaces import VectorStoreInterface, VectorSearchResult

class GenericRAGContextProvider:
    """Generic RAG context provider that works with any vector database"""

    def __init__(self, vector_store: VectorStoreInterface):
        self.vector_store = vector_store

    async def get_context_as_text_array(self,
                                      query: str,
                                      context_scope: str = "comprehensive") -> List[str]:
        """
        Fetch RAG context and return as text array for sequential agent
        This is the main method your sequential agent will use
        """
        try:
            # Configure search parameters
            search_params = self._get_search_params(context_scope, query)

            # Search vector database
            results = await self.vector_store.search_context(
                query=search_params["query"],
                top_k=search_params["top_k"],
                filters=search_params.get("filters")
            )

            # Convert to text array format
            context_text_array = self._format_results_as_text_array(results, query)

            return context_text_array

        except Exception as e:
            print(f"RAG context fetch failed: {e}")
            # Return empty array - sequential agent continues without RAG
            return []

    def _get_search_params(self, scope: str, query: str) -> Dict:
        """Configure search based on scope"""
        scope_map = {
            "comprehensive": {"top_k": 20, "query": f"requirements test cases {query}"},
            "focused": {"top_k": 10, "query": f"requirements {query}"},
            "minimal": {"top_k": 5, "query": query}
        }
        return scope_map.get(scope, scope_map["focused"])

    def _format_results_as_text_array(self,
                                    results: List[VectorSearchResult],
                                    original_query: str) -> List[str]:
        """Format search results as text array for sequential agent consumption"""
        if not results:
            return []

        context_array = []

        # Add context header
        context_array.append(f"=== RAG CONTEXT FOR: {original_query} ===")

        # Group by content type
        requirements = []
        test_specs = []
        domain_knowledge = []

        for result in results:
            doc_type = result.metadata.get("document_type", "general").lower()
            formatted_entry = f"[Score: {result.score:.3f}] {result.content}"

            if "requirement" in doc_type:
                requirements.append(formatted_entry)
            elif "test" in doc_type:
                test_specs.append(formatted_entry)
            else:
                domain_knowledge.append(formatted_entry)

        # Add categorized context
        if requirements:
            context_array.append("=== REQUIREMENTS DOCUMENTATION ===")
            context_array.extend(requirements)

        if test_specs:
            context_array.append("=== TEST SPECIFICATIONS ===")
            context_array.extend(test_specs)

        if domain_knowledge:
            context_array.append("=== DOMAIN KNOWLEDGE ===")
            context_array.extend(domain_knowledge)

        context_array.append("=== END RAG CONTEXT ===")

        return context_array
