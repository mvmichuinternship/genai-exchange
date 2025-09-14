from .vector_db import VertexVectorStore
from .embedding_service import EmbeddingService
from .models import RAGDocument, SearchResult
from typing import List, Dict, Optional
import logging

class RAGService:
    def __init__(self, project_id: str, index_name: str, endpoint_name: str):
        self.vector_store = VertexVectorStore(project_id)
        self.embedding_service = EmbeddingService()
        self.index_name = index_name
        self.endpoint_name = endpoint_name

    async def ingest_text_array(self, text_array: List[str],
                               document_metadata: Dict) -> Dict:
        """Main ingestion method for your text arrays"""
        try:
            # Generate embeddings
            embeddings = await self.embedding_service.embed_text_array(
                text_array, document_metadata
            )

            # Store in vector database
            results = await self._store_embeddings(embeddings)

            logging.info(f"Ingested {len(embeddings)} chunks for document {document_metadata.get('doc_id')}")

            return {
                "status": "success",
                "chunks_processed": len(embeddings),
                "document_id": document_metadata.get('doc_id'),
                "ingestion_results": results
            }

        except Exception as e:
            logging.error(f"Ingestion failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def update_document(self, doc_id: str, new_text_array: List[str],
                             metadata: Dict) -> Dict:
        """Update existing document with new text array"""
        # Delete existing chunks
        await self._delete_document_chunks(doc_id)

        # Ingest new content
        return await self.ingest_text_array(new_text_array, metadata)

    async def search_context(self, query: str, top_k: int = 10,
                           filters: Optional[Dict] = None) -> List[SearchResult]:
        """Retrieve relevant context for agent reasoning"""
        # Generate query embedding
        query_embedding = self.embedding_service.model.get_embeddings([query])

        # Perform vector search
        results = await self._vector_search(
            query_embedding.values, top_k, filters
        )

        return [SearchResult(**result) for result in results]
