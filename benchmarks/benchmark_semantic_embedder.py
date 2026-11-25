"""Optional CPU sentence-transformers adapter for real semantic retrieval.

Install with pip install historypy[semantic]. The model is public and
loaded lazily so the core package has no mandatory ML dependency.
"""
from __future__ import annotations

import os
from collections.abc import Sequence
from functools import lru_cache

DEFAULT_MODEL_ID = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=2)
def _load_model(model_id: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Install HistoryPy's semantic extra: pip install historypy[semantic]"
        ) from exc
    return SentenceTransformer(model_id, device="cpu")


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """Embed a batch using the configured multilingual model on CPU."""
    model_id = os.environ.get("HISTORYPY_EMBEDDING_MODEL", DEFAULT_MODEL_ID)
    vectors = _load_model(model_id).encode(
        list(texts),
        batch_size=32,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return vectors.tolist()
