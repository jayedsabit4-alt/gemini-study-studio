"""Text Chunking Module for Document Ingestion."""

from typing import Any, Dict, List
from config import CHUNK_OVERLAP, CHUNK_SIZE


def create_chunks(
    doc_data: Dict[str, Any],
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> List[Dict[str, Any]]:
    """Splits extracted document text into overlapping chunks with metadata tags."""
    chunks = []
    chunk_id = 0

    pages = doc_data.get("pages", [])
    filename = doc_data.get("filename", "unknown")
    file_type = doc_data.get("file_type", "")

    for page in pages:
        text = page.get("text", "")
        page_num = page.get("page_number", 1)
        sheet_name = page.get("sheet_name")

        if not text.strip():
            continue

        words = text.split()
        if not words:
            continue

        step = max(1, chunk_size - chunk_overlap)
        for i in range(0, len(words), step):
            chunk_words = words[i : i + chunk_size]
            chunk_text = " ".join(chunk_words)

            meta = {
                "filename": filename,
                "file_type": file_type,
                "page_number": page_num,
            }
            if sheet_name:
                meta["sheet_name"] = sheet_name

            chunks.append({
                "chunk_id": f"{filename}_p{page_num}_{chunk_id}",
                "text": chunk_text,
                "metadata": meta,
            })
            chunk_id += 1

    return chunks
