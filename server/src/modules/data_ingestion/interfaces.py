from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

@dataclass
class VectorSearchResult:
    """Generic result structure for any vector database"""
    content: str
    score: float
    metadata: Dict[str, Any]
    source: Optional[str] = None

class VectorStoreInterface(ABC):
    """Generic interface for any vector database implementation"""

    @abstractmethod
    async def search_context(self,
                           query: str,
                           top_k: int = 10,
                           filters: Optional[Dict] = None) -> List[VectorSearchResult]:
        """Search and return relevant context"""
        pass

    @abstractmethod
    async def ingest_documents(self,
                             text_array: List[str],
                             metadata: Dict) -> Dict:
        """Ingest documents into vector store"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if vector store is available"""
        pass
