"""Vector Store Engine using Binary FAISS Serialization, Persistent Hashes, and Atomic Metadata Storage."""

from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False


class VectorStore:
    """Decoupled vector storage, atomic index persistence, and similarity retrieval."""

    def __init__(self, dimension: int = 384, embedding_model_name: str = "all-MiniLM-L6-v2"):
        self.dimension = dimension
        self.embedding_model_name = embedding_model_name
        self.chunks: List[Dict[str, Any]] = []
        self.indexed_hashes: Dict[str, str] = {}
        self.vector_matrix: Optional[np.ndarray] = None
        
        if FAISS_AVAILABLE:
            self.index = faiss.IndexFlatIP(dimension)
        else:
            self.index = None

    def add_embeddings(self, chunks: List[Dict[str, Any]], embeddings: List[np.ndarray]):
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: Received {len(chunks)} chunks but {len(embeddings)} embeddings."
            )
        if not chunks:
            return

        new_vectors = []
        start_id = len(self.chunks)

        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            norm = np.linalg.norm(emb)
            norm_emb = (emb / norm) if norm > 0 else emb
            vector_id = start_id + idx

            chunk_entry = {
                "vector_id": vector_id,
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "metadata": chunk["metadata"],
            }
            self.chunks.append(chunk_entry)
            new_vectors.append(norm_emb)

        vec_array = np.array(new_vectors, dtype=np.float32)

        if self.vector_matrix is None:
            self.vector_matrix = vec_array
        else:
            self.vector_matrix = np.vstack([self.vector_matrix, vec_array])

        if self.index is not None:
            self.index.add(vec_array)

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 4,
        filename_filter: Optional[str] = None,
    ) -> List[Tuple[Dict[str, Any], float]]:
        if not self.chunks or self.vector_matrix is None:
            return []

        norm_q = np.linalg.norm(query_vector)
        q_vec = (query_vector / norm_q) if norm_q > 0 else query_vector
        q_vec = np.array([q_vec], dtype=np.float32)

        filtered_entries = [
            (i, c) for i, c in enumerate(self.chunks)
            if filename_filter is None or c["metadata"].get("filename") == filename_filter
        ]

        if not filtered_entries:
            return []

        if self.index is not None and filename_filter is None:
            scores, indices = self.index.search(q_vec, min(top_k, len(self.chunks)))
            results = []
            for idx, score in zip(indices[0], scores[0]):
                if 0 <= idx < len(self.chunks):
                    results.append((self.chunks[idx], float(score)))
            return results

        indices = [item[0] for item in filtered_entries]
        cand_vectors = self.vector_matrix[indices]

        sims = np.dot(cand_vectors, q_vec.T).flatten()
        top_sub_indices = np.argsort(sims)[-top_k:][::-1]

        results = []
        for sub_idx in top_sub_indices:
            real_idx = indices[sub_idx]
            results.append((self.chunks[real_idx], float(sims[sub_idx])))

        return results

    def remove_document(self, filename: str) -> int:
        if not self.chunks:
            return 0

        keep_entries = []
        keep_vectors = []
        removed_count = 0

        for idx, chunk in enumerate(self.chunks):
            if chunk["metadata"].get("filename") == filename:
                removed_count += 1
            else:
                keep_entries.append(chunk)
                if self.vector_matrix is not None:
                    keep_vectors.append(self.vector_matrix[idx])

        if removed_count == 0:
            return 0

        self.chunks = []
        for new_id, chunk in enumerate(keep_entries):
            chunk["vector_id"] = new_id
            self.chunks.append(chunk)

        hashes_to_delete = [h for h, f in self.indexed_hashes.items() if f == filename]
        for h in hashes_to_delete:
            del self.indexed_hashes[h]

        if keep_vectors:
            self.vector_matrix = np.array(keep_vectors, dtype=np.float32)
            if self.index is not None:
                self.index.reset()
                self.index.add(self.vector_matrix)
        else:
            self.vector_matrix = None
            if self.index is not None:
                self.index.reset()

        return removed_count

    def save_to_disk(self, storage_dir: Path, prefix: str = "rag_store"):
        """Saves metadata JSON, persistent hashes, config manifest, and binary FAISS index to disk atomically using temp files."""
        storage_dir.mkdir(parents=True, exist_ok=True)
        meta_path = storage_dir / f"{prefix}_metadata.json"
        config_path = storage_dir / f"{prefix}_config.json"
        index_path = storage_dir / f"{prefix}_faiss.index"
        matrix_path = storage_dir / f"{prefix}_vectors.npy"

        meta_tmp = storage_dir / f"{prefix}_metadata.tmp"
        config_tmp = storage_dir / f"{prefix}_config.tmp"
        index_tmp = storage_dir / f"{prefix}_faiss.tmp"
        matrix_tmp = storage_dir / f"{prefix}_vectors.tmp.npy"

        config_data = {
            "embedding_model": self.embedding_model_name,
            "dimension": self.dimension,
            "total_chunks": len(self.chunks),
            "indexed_hashes": self.indexed_hashes,
            "updated_at": datetime.now().isoformat(),
        }
        
        with open(config_tmp, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)

        with open(meta_tmp, "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, ensure_ascii=False, indent=2)

        if self.index is not None and FAISS_AVAILABLE:
            faiss.write_index(self.index, str(index_tmp))

        if self.vector_matrix is not None:
            np.save(matrix_tmp, self.vector_matrix)

        config_tmp.replace(config_path)
        meta_tmp.replace(meta_path)
        if index_tmp.exists():
            index_tmp.replace(index_path)
        if matrix_tmp.exists():
            matrix_tmp.replace(matrix_path)

    def load_from_disk(self, storage_dir: Path, prefix: str = "rag_store"):
        """Loads metadata JSON, persistent hashes, config manifest, and binary FAISS index with strict model, dimension, shape, and count validation."""
        meta_path = storage_dir / f"{prefix}_metadata.json"
        config_path = storage_dir / f"{prefix}_config.json"
        index_path = storage_dir / f"{prefix}_faiss.index"
        matrix_path = storage_dir / f"{prefix}_vectors.npy"

        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                
                saved_model = cfg.get("embedding_model")
                saved_dim = cfg.get("dimension")

                if saved_model and saved_model != self.embedding_model_name:
                    raise ValueError(
                        f"Embedding model mismatch: Store was created with '{saved_model}', "
                        f"but current model is '{self.embedding_model_name}'."
                    )
                if saved_dim and saved_dim != self.dimension:
                    raise ValueError(
                        f"Dimension mismatch: Store expects {self.dimension} dimensions, "
                        f"but stored index has {saved_dim} dimensions."
                    )

                self.indexed_hashes = cfg.get("indexed_hashes", {})

        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                self.chunks = json.load(f)

        if matrix_path.exists():
            self.vector_matrix = np.load(matrix_path, allow_pickle=False)
            if (
                self.vector_matrix.ndim != 2
                or self.vector_matrix.shape[1] != self.dimension
            ):
                self.clear()
                raise ValueError(
                    f"Invalid vector matrix shape: {self.vector_matrix.shape}. "
                    f"Expected (*, {self.dimension}). Store cleared."
                )

        if FAISS_AVAILABLE and index_path.exists():
            self.index = faiss.read_index(str(index_path))
            if self.index.d != self.dimension:
                self.clear()
                raise ValueError(
                    f"FAISS index internal dimension ({self.index.d}) mismatch with expected model dimension ({self.dimension}). Store cleared."
                )

        vector_count = 0
        if self.index is not None:
            vector_count = self.index.ntotal
        elif self.vector_matrix is not None:
            vector_count = self.vector_matrix.shape[0]

        if len(self.chunks) != vector_count:
            self.clear()
            raise ValueError(
                f"Corrupted vector store: Found {len(self.chunks)} metadata chunks but {vector_count} vectors. Store cleared."
            )

    def clear(self):
        self.chunks.clear()
        self.indexed_hashes.clear()
        if self.index is not None:
            self.index.reset()
        self.vector_matrix = None
