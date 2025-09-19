import asyncio
from typing import Dict, List, Optional, Any
import logging
from concurrent.futures import ThreadPoolExecutor
import time

from .utils import DocumentProcessor, SmartTextChunker
from .models import ProcessingResult, DocumentMetadata

class DocumentProcessorService:
    def __init__(self, max_workers: int = 4):
        self.document_processor = DocumentProcessor()
        self.text_chunker = SmartTextChunker()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.logger = logging.getLogger(__name__)

        # Store processing status (in production, use Redis or a database)
        self.processing_status = {}

        # Initialize embedding generator and vector store if needed
        # You can configure these based on your requirements
        self.embedding_generator = None
        self.vector_store = None

    async def process_document(self, config: Dict) -> Dict:
        """
        Process a single document asynchronously
        """
        document_id = config['document_id']

        # Update status to processing
        self.processing_status[document_id] = {
            'status': 'processing',
            'started_at': time.time(),
            'progress': 0
        }

        try:
            # Run the CPU-intensive processing in a thread pool
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._process_document_sync,
                config
            )

            # Update status to completed
            self.processing_status[document_id].update({
                'status': 'completed',
                'completed_at': time.time(),
                'progress': 100,
                'result': result
            })

            return result

        except Exception as e:
            self.logger.error(f"Error processing document {document_id}: {str(e)}")

            # Update status to error
            self.processing_status[document_id].update({
                'status': 'error',
                'error': str(e),
                'progress': 0
            })

            raise e

    def _process_document_sync(self, config: Dict) -> Dict:
        """
        Synchronous document processing (runs in thread pool)
        """
        document_id = config['document_id']
        file_type = config['type']
        file_path = config['path']

        try:
            # Extract content based on file type
            if file_type == 'pdf':
                content = self.document_processor.process_pdf(file_path)
            elif file_type == 'docx':
                content = self.document_processor.process_word_doc(file_path)
            elif file_type == 'doc':
                content = self.document_processor.process_word_doc(file_path)
            elif file_type == 'xml':
                content = self.document_processor.process_xml(file_path)
            elif file_type == 'txt':
                content = self._process_text_file(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")

            # Update progress
            if document_id in self.processing_status:
                self.processing_status[document_id]['progress'] = 30

            # Chunk the text
            metadata = {
                'document_id': document_id,
                'source_type': file_type,
                'source_path': config.get('original_filename', ''),
                'file_size': config.get('file_size', 0)
            }

            chunks = self.text_chunker.chunk_text(content.get('text', ''), metadata)

            # Update progress
            if document_id in self.processing_status:
                self.processing_status[document_id]['progress'] = 60

            # If you have embedding generation and vector store configured
            if self.embedding_generator and self.vector_store:
                # Generate embeddings
                chunk_texts = [chunk['text'] for chunk in chunks]
                embeddings = self.embedding_generator.generate_embeddings(chunk_texts)

                # Combine chunks with embeddings
                documents_with_embeddings = []
                for chunk, embedding in zip(chunks, embeddings):
                    chunk['embedding'] = embedding
                    documents_with_embeddings.append(chunk)

                # Store in vector database
                self.vector_store.add_documents(documents_with_embeddings)

                # Update progress
                if document_id in self.processing_status:
                    self.processing_status[document_id]['progress'] = 90

            return {
                'status': 'success',
                'document_id': document_id,
                'chunks_created': len(chunks),
                'content': content.get('text', '').split('\n'),
                'metadata': metadata,
                'processing_info': {
                    'file_type': file_type,
                    'original_filename': config.get('original_filename'),
                    'file_size': config.get('file_size', 0)
                }
            }

        except Exception as e:
            self.logger.error(f"Error in sync processing for {document_id}: {str(e)}")
            raise e

    def _process_text_file(self, file_path: str) -> Dict:
        """
        Process plain text files
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            return {
                'text': content,
                'metadata': {
                    'file_size': len(content),
                    'line_count': content.count('\n') + 1
                }
            }
        except UnicodeDecodeError:
            # Try different encodings
            for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        content = file.read()
                    return {
                        'text': content,
                        'metadata': {
                            'encoding_used': encoding,
                            'file_size': len(content),
                            'line_count': content.count('\n') + 1
                        }
                    }
                except UnicodeDecodeError:
                    continue

            raise ValueError("Could not decode text file with any supported encoding")

    async def process_multiple_documents(self, configs: List[Dict]) -> Dict:
        """
        Process multiple documents concurrently
        """
        results = []

        # Process documents concurrently
        tasks = [self.process_document(config) for config in configs]

        for i, task in enumerate(asyncio.as_completed(tasks)):
            try:
                result = await task
                results.append(result)
                self.logger.info(f"Processed document {i+1}/{len(configs)}: {result['document_id']}")
            except Exception as e:
                self.logger.error(f"Failed to process document {i+1}/{len(configs)}: {str(e)}")
                results.append({
                    'status': 'error',
                    'error': str(e),
                    'document_id': configs[i].get('document_id', 'unknown')
                })

        successful = len([r for r in results if r.get('status') == 'success'])
        failed = len([r for r in results if r.get('status') == 'error'])

        return {
            'total_processed': len(results),
            'successful': successful,
            'failed': failed,
            'results': results
        }

    async def search_documents(self, query: str, limit: int = 10, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Search through processed documents
        """
        if not self.vector_store:
            raise ValueError("Vector store not configured. Cannot perform search.")

        try:
            # Generate embedding for the query
            if not self.embedding_generator:
                raise ValueError("Embedding generator not configured. Cannot perform search.")

            query_embedding = self.embedding_generator.generate_embeddings([query])[0]

            # Search in vector store
            results = self.vector_store.search(query_embedding, limit)

            # Apply additional filters if provided
            if filters:
                filtered_results = []
                for result in results:
                    match = True
                    for key, value in filters.items():
                        if result.get('metadata', {}).get(key) != value:
                            match = False
                            break
                    if match:
                        filtered_results.append(result)
                results = filtered_results

            return results

        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            raise e

    async def get_document_status(self, document_id: str) -> Dict:
        """
        Get the processing status of a document
        """
        if document_id not in self.processing_status:
            raise ValueError(f"Document {document_id} not found")

        status = self.processing_status[document_id].copy()

        # Calculate processing time if completed
        if status['status'] == 'completed' and 'completed_at' in status:
            status['processing_time'] = status['completed_at'] - status['started_at']
        elif status['status'] == 'processing':
            status['current_processing_time'] = time.time() - status['started_at']

        return status

    def configure_embeddings_and_vector_store(self, embedding_config: Dict, vector_store_config: Dict):
        """
        Configure embedding generator and vector store
        """
        # Import here to avoid circular imports and allow optional dependencies
        try:
            from src.modules.data_ingestion.embedding_generator import EmbeddingGenerator
            from src.modules.data_ingestion.vector_stores import get_vector_store

            self.embedding_generator = EmbeddingGenerator(**embedding_config)
            self.vector_store = get_vector_store(**vector_store_config)

        except ImportError as e:
            self.logger.warning(f"Could not import embedding/vector store modules: {e}")
            self.logger.warning("Search functionality will be disabled")

    def cleanup_old_status(self, max_age_hours: int = 24):
        """
        Clean up old processing status entries
        """
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)

        to_remove = []
        for doc_id, status in self.processing_status.items():
            if status['started_at'] < cutoff_time:
                to_remove.append(doc_id)

        for doc_id in to_remove:
            del self.processing_status[doc_id]

        self.logger.info(f"Cleaned up {len(to_remove)} old status entries")

    def get_service_stats(self) -> Dict:
        """
        Get service statistics
        """
        total_docs = len(self.processing_status)
        completed = len([s for s in self.processing_status.values() if s['status'] == 'completed'])
        processing = len([s for s in self.processing_status.values() if s['status'] == 'processing'])
        errors = len([s for s in self.processing_status.values() if s['status'] == 'error'])

        return {
            'total_documents': total_docs,
            'completed': completed,
            'processing': processing,
            'errors': errors,
            'success_rate': completed / total_docs if total_docs > 0 else 0,
            'embeddings_enabled': self.embedding_generator is not None,
            'search_enabled': self.vector_store is not None
        }
