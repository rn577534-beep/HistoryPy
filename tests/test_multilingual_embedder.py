import sys
import types

from historypy import (
    HistoricalClaim,
    HistoricalDataset,
    SentenceTransformerEmbedder,
    SourceRecord,
    build_multilingual_semantic_index,
)


class FakeSentenceTransformer:
    def __init__(self, model_name, device=None):
        self.model_name = model_name
        self.device = device

    def encode(self, texts, **kwargs):
        assert kwargs["normalize_embeddings"] is True
        return [[1.0, 0.0] for _ in texts]


def test_sentence_transformer_adapter_and_multilingual_index(monkeypatch):
    fake_module = types.ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = FakeSentenceTransformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    dataset = HistoricalDataset(
        sources=(SourceRecord("s1", "Archive", "primary"),),
        claims=(HistoricalClaim("c1", "A documented claim."),),
    )
    index, embedder = build_multilingual_semantic_index(dataset, device="cpu")
    assert index.model_id == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    assert index.dimension == 2
    hits = index.search("ঐতিহাসিক দাবি", embedder=embedder, limit=5)
    assert hits
    assert hits[0].similarity == 1.0


def test_sentence_transformer_adapter_validates_input_before_encoding(monkeypatch):
    fake_module = types.ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = FakeSentenceTransformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    embedder = SentenceTransformerEmbedder()
    assert embedder(()) == ()
    try:
        embedder("not a sequence of text items")
    except TypeError as exc:
        assert "sequence" in str(exc)
    else:
        raise AssertionError("a bare string must be rejected")
