"""RAG Engine Orchestrator."""

from datetime import datetime
import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

from config import DEFAULT_TOP_K, MAX_RAG_CONTEXT_CHARS, STORAGE_DIR
from llm.llm_client import generate_response
from llm.prompts import RAG_QA_PROMPT
from rag.chunker import create_chunks
from rag.embeddings import EmbeddingEngine
from rag.parser import extract_file
from rag.retriever import Retriever
from rag.vector_store import VectorStore

logger = logging.getLogger(__name__)


class RAGEngine:
    """Main orchestrator connecting Parsing, Chunking, Embedding, Retrieval, and LLM Execution."""

    def __init__(self):
        self.embedding_engine = EmbeddingEngine()
        self.vector_store = VectorStore(
            dimension=self.embedding_engine.dimension,
            embedding_model_name=self.embedding_engine.model_name,
        )
        self.retriever = Retriever(self.embedding_engine, self.vector_store)
        
        try:
            self.vector_store.load_from_disk(STORAGE_DIR)
        except Exception as err:
            logger.warning(f"Could not load vector store from disk: {err}")

    def _compute_hash(self, file_bytes: bytes) -> str:
        return hashlib.sha256(file_bytes).hexdigest()

    def index_document(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Runs ingestion pipeline: Persistent Hash Check -> Parse -> Empty Guard -> Chunk -> Embed -> Index -> Safe Auto-Save."""
        file_hash = self._compute_hash(file_bytes)

        if file_hash in self.vector_store.indexed_hashes:
            existing_file = self.vector_store.indexed_hashes[file_hash]
            return {
                "filename": filename,
                "status": "skipped",
                "message": f"Document is identical to already indexed file '{existing_file}'.",
                "total_chunks": 0,
            }

        parsed_doc = extract_file(file_bytes, filename)
        chunks = create_chunks(parsed_doc)

        if not chunks:
            return {
                "filename": filename,
                "status": "failed",
                "reason": "No extractable text or readable content found in document.",
                "total_chunks": 0,
                "warnings": parsed_doc.get("warnings", []),
            }

        indexed_at = datetime.now().isoformat()
        for c in chunks:
            c["metadata"]["document_hash"] = file_hash
            c["metadata"]["indexed_at"] = indexed_at
            if parsed_doc.get("warnings"):
                c["metadata"]["warnings"] = parsed_doc["warnings"]

        chunk_texts = [c["text"] for c in chunks]
        embeddings = self.embedding_engine.embed(chunk_texts)

        self.vector_store.add_embeddings(chunks, embeddings)
        self.vector_store.indexed_hashes[file_hash] = filename

        # Wrap save_to_disk inside try-except so disk warnings do not interrupt memory indexing
        try:
            self.vector_store.save_to_disk(STORAGE_DIR)
        except Exception as save_err:
            logger.error(f"Failed to persist vector store to disk for {filename}: {save_err}")

        return {
            "filename": filename,
            "status": "indexed",
            "file_type": parsed_doc["file_type"],
            "total_pages": len(parsed_doc["pages"]),
            "total_chunks": len(chunks),
            "warnings": parsed_doc.get("warnings", []),
        }

    def remove_document(self, filename: str) -> int:
        """Removes a document from vector store and safely saves changes to disk."""
        removed_count = self.vector_store.remove_document(filename)
        try:
            self.vector_store.save_to_disk(STORAGE_DIR)
        except Exception as save_err:
            logger.error(f"Failed to persist document removal for {filename}: {save_err}")
        return removed_count

    def ask_document(
        self,
        api_key: str,
        query: str,
        preferred_model: str = "openrouter/free",
        filename_filter: Optional[str] = None,
        top_k: int = DEFAULT_TOP_K,
        chat_history: Optional[List[Dict[str, str]]] = None,
    ) -> Tuple[bool, Optional[str], str, List[Dict[str, Any]]]:
        """Runs QA pipeline: Retrieve -> Context Length Guard -> Build Prompt -> Call LLM -> Return Output."""
        relevant_chunks = self.retriever.retrieve(
            query=query, top_k=top_k, filename_filter=filename_filter
        )

        if not relevant_chunks:
            return (
                False,
                "The provided study context does not contain sufficient information to answer this question.",
                "N/A",
                [],
            )

        context_segments = []
        current_chars = 0

        for c in relevant_chunks:
            meta = c["metadata"]
            page_info = f" (Page {meta['page_number']})" if meta.get("page_number") else ""
            sheet_info = f" [Sheet: {meta['sheet_name']}]" if meta.get("sheet_name") else ""
            header = f"--- Source: {meta['filename']}{page_info}{sheet_info} ---"
            snippet = f"{header}\n{c['text']}"

            if current_chars + len(snippet) > MAX_RAG_CONTEXT_CHARS:
                break

            context_segments.append(snippet)
            current_chars += len(snippet)

        context_str = "\n\n".join(context_segments)
        user_prompt_content = f"Study Context:\n{context_str}\n\nQuestion: {query}"

        messages = [{"role": "system", "content": RAG_QA_PROMPT}]
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": user_prompt_content})

        success, response_text, used_model = generate_response(
            api_key=api_key,
            messages=messages,
            preferred_model=preferred_model,
        )

        return success, response_text, used_model, relevant_chunks
