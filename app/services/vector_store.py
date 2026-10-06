import faiss
from app.services.embedding_service import embed_texts


class SimpleVectorStore:
    """A tiny wrapper around FAISS: add(items) to store text, search(query) to find similar text."""

    def __init__(self):
        self.index = None
        self.records = []  # parallel list: {"id":..., "text":..., "metadata": {...}}

    def add(self, items: list[dict]):
        """items: list of {"id": str, "text": str, "metadata": dict}"""
        if not items:
            return

        texts = [item["text"] for item in items]
        vectors = embed_texts(texts)

        if self.index is None:
            dimension = vectors.shape[1]
            self.index = faiss.IndexFlatIP(dimension)  # inner product = cosine similarity (vectors are normalized)

        self.index.add(vectors)
        self.records.extend(items)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if self.index is None or len(self.records) == 0:
            return []

        query_vector = embed_texts([query])
        scores, indices = self.index.search(query_vector, min(top_k, len(self.records)))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            record = dict(self.records[idx])
            record["score"] = float(score)
            results.append(record)
        return results
