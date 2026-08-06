try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

def search_similar_chunks(chunks: list, query: str, top_k: int = 3) -> list:
    if not chunks:
        return []

    if SKLEARN_AVAILABLE and len(chunks) > top_k:
        try:
            texts = [c["text"] for c in chunks]
            vectorizer = TfidfVectorizer(stop_words="english")
            matrix = vectorizer.fit_transform(texts + [query])
            sim = cosine_similarity(matrix[-1:], matrix[:-1]).flatten()
            top_idx = sim.argsort()[-top_k:][::-1]
            return [chunks[i] for i in top_idx if sim[i] > 0.05]
        except Exception:
            pass
            
    return chunks[:top_k]
