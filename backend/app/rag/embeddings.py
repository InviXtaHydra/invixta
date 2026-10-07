"""Text → vector. An embedding model maps text to a point in a 384-dimensional space where texts
with similar meaning end up close together, which is what makes semantic search work."""

import threading
from functools import lru_cache
from typing import TYPE_CHECKING, Protocol

from app.core.config import get_settings

if TYPE_CHECKING:
    from fastembed import TextEmbedding


class Embedder(Protocol):
    def embed_query(self, text: str) -> list[float]: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class FastEmbedEmbedder:
    """Local BGE-small model via fastembed (ONNX on CPU): free, no API key, ~5 ms per sentence.

    BGE uses an instruction prefix for queries ("Represent this sentence for searching relevant
    passages: …"); fastembed's query_embed/passage_embed apply it for us. Vectors are normalised,
    so cosine similarity equals the dot product.
    """

    def __init__(self, model_name: str, cache_dir: str | None = None) -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir
        self._model: "TextEmbedding | None" = None
        self._lock = threading.Lock()

    def _load(self) -> "TextEmbedding":
        if self._model is None:
            with self._lock:  # load once, even with concurrent requests
                if self._model is None:
                    from fastembed import TextEmbedding

                    self._model = TextEmbedding(self.model_name, cache_dir=self.cache_dir)
        return self._model

    def embed_query(self, text: str) -> list[float]:
        return [float(x) for x in next(iter(self._load().query_embed([text])))]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(x) for x in vec] for vec in self._load().passage_embed(texts)]


@lru_cache
def get_embedder() -> Embedder:
    settings = get_settings()
    return FastEmbedEmbedder(settings.embedding_model, settings.embedding_cache_dir)
