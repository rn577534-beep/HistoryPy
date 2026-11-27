"""Optional sentence-transformers adapter for multilingual semantic retrieval."""
from __future__ import annotations

from collections.abc import Sequence

from historypy.core.dataset import HistoricalDataset
from historypy.research.semantic import SemanticSearchIndex


class SentenceTransformerEmbedder:
    """Lazy optional adapter around sentence-transformers.

    The default model is multilingual. Install with pip install historypy[semantic].
    Model files are downloaded/cached on first use.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        *,
        device: str | None = None,
    ) -> None:
        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError("model_name cannot be empty")
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "Install the optional semantic dependencies with "
                "pip install 'historypy[semantic]'"
            ) from exc
        self.model_name = model_name.strip()
        self.model = SentenceTransformer(self.model_name, device=device)

    def __call__(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        """Encode text batches into normalized Python float vectors."""
        if isinstance(texts, (str, bytes)):
            raise TypeError("texts must be a sequence of strings, not a single string")
        values = tuple(texts)
        if any(not isinstance(value, str) for value in values):
            raise TypeError("all texts must be strings")
        if not values:
            return ()
        vectors = self.model.encode(
            list(values), convert_to_numpy=True, normalize_embeddings=True,
            show_progress_bar=False,
        )
        return tuple(tuple(float(value) for value in vector) for vector in vectors)


def build_multilingual_semantic_index(
    dataset: HistoricalDataset,
    *,
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    device: str | None = None,
    batch_size: int = 64,
) -> tuple[SemanticSearchIndex, SentenceTransformerEmbedder]:
    """Build a multilingual vector index and return its matching embedder."""
    embedder = SentenceTransformerEmbedder(model_name, device=device)
    index = SemanticSearchIndex.build(
        dataset, embedder=embedder, model_id=embedder.model_name,
        batch_size=batch_size,
    )
    return index, embedder


__all__ = ["SentenceTransformerEmbedder", "build_multilingual_semantic_index"]
