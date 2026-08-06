"""RAG Similarity Retriever Module."""

from typing import Any, Dict, List, Optional
from rag.embeddings import EmbeddingEngine
from rag.vector_store import VectorStore


class Retriever:
    """Executes similarity searches over vector store using embedding engine."""

    def __init__(self, embedding_engine: EmbeddingEngine, vector_store: VectorStore):
        self.embedding_engine = embedding_engine
        self.vector_store = vector_store

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        filename_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Embeds query text and retrieves top-k relevant context chunks."""
        if not query or not query.strip():
            return []

        query_vectors = self.embedding_engine.embed([query])
        if not query_vectors:
            return []

        query_vec = query_vectors[0]
        results = self.vector_store.search(
            query_vector=query_vec, top_k=top_k, filename_filter=filename_filter
        )

        return [chunk for chunk, score in results]
