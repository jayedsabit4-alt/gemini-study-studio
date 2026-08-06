from rag.vector_store import search_similar_chunks

def retrieve_rag_context(documents: list, query: str, chunk_size: int = 500) -> str:
    chunks = []
    for doc in documents:
        content = doc.get("text", "")
        for i in range(0, len(content), chunk_size):
            chunk = content[i : i + chunk_size + 100]
            if len(chunk.strip()) > 50:
                chunks.append({"source": doc["name"], "text": chunk})

    retrieved = search_similar_chunks(chunks, query)
    if not retrieved:
        return ""
    return "\n\n".join([f"--- Snippet from {c['source']} ---\n{c['text']}" for c in retrieved])
