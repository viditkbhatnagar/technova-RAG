"""BGE embedding service with MPS / CPU device selection."""

import torch
from sentence_transformers import SentenceTransformer


_BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def get_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class EmbeddingService:
    def __init__(self, model_name: str = "BAAI/bge-base-en-v1.5"):
        self.model_name = model_name
        self.device = get_device()
        self.model = SentenceTransformer(model_name, device=self.device)
        self.dim = self.model.get_sentence_embedding_dimension()
        print(
            f"[embedder] loaded {model_name} on {self.device} (dim={self.dim})"
        )

    def embed_texts(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Embed a batch of documents. Returns list of float vectors."""
        if not texts:
            return []
        vectors = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query with the BGE retrieval prefix."""
        prefixed = f"{_BGE_QUERY_PREFIX}{query}"
        vector = self.model.encode(
            [prefixed],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )[0]
        return vector.tolist()
