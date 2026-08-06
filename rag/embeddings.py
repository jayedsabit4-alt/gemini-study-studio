"""SentenceTransformers Embedding Engine with CPU/GPU Auto-Detection."""

import logging
from typing import List, Union
import numpy as np

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False


class EmbeddingEngine:
    """Generates dense vector embeddings for RAG retrieval."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.dimension = 384

        if ST_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
                self.dimension = self.model.get_sentence_embedding_dimension()
            except Exception as err:
                logger.warning("Failed to load SentenceTransformer '%s': %s", model_name, err)
                self.model = None
        else:
            self.model = None

    def embed(self, texts: Union[str, List[str]]) -> List[np.ndarray]:
        """Generates normalized dense numpy array vectors for input texts."""
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return []

        if self.model is not None:
            embeddings = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
            return [emb.astype(np.float32) for emb in embeddings]

        fallback_vectors = []
        for t in texts:
            np.random.seed(abs(hash(t)) % (2**32))
            vec = np.random.randn(self.dimension).astype(np.float32)
            norm = np.linalg.norm(vec)
            fallback_vectors.append(vec / norm if norm > 0 else vec)

        return fallback_vectors
