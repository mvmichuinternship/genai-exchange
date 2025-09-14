from vertexai.language_models import TextEmbeddingModel
from typing import List, Dict
import datetime
import asyncio

class EmbeddingService:
    def __init__(self, model_name: str = "text-embedding-005"):
        self.model = TextEmbeddingModel.from_pretrained(model_name)

    async def embed_text_array(self, text_array: List[str],
                              metadata: Dict) -> List[Dict]:
        """Convert text array to embeddings with metadata"""
        embeddings = []

        for idx, text in enumerate(text_array):
            # Generate embedding
            embedding_result = self.model.get_embeddings([text])

            # Prepare document for vector store
            doc = {
                "id": f"{metadata.get('doc_id', 'unknown')}_{idx}",
                "text": text,
                "embedding": embedding_result.values,
                "metadata": {
                    **metadata,
                    "chunk_index": idx,
                    "chunk_size": len(text),
                    "timestamp": datetime.now().isoformat()
                }
            }
            embeddings.append(doc)

        return embeddings

    def batch_embed_documents(self, documents: List[Dict]) -> List[Dict]:
        """Batch process multiple documents efficiently"""
        all_embeddings = []

        for doc in documents:
            text_array = doc.get('text_chunks', [])
            metadata = doc.get('metadata', {})

            doc_embeddings = asyncio.run(
                self.embed_text_array(text_array, metadata)
            )
            all_embeddings.extend(doc_embeddings)

        return all_embeddings
