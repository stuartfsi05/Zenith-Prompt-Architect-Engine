import pytest

from src.scripts.ingest import _embed_batch_with_retry, _extract_retry_delay


def test_extract_retry_delay_parses_seconds_or_uses_default():
    assert _extract_retry_delay("Please retry in 56.5s.") == 58.5
    assert _extract_retry_delay("retry in 1s") == 5.0
    assert _extract_retry_delay("No hint here", default=65.0) == 65.0


def test_embed_batch_with_retry_retries_on_429_and_succeeds(monkeypatch):
    sleeps = []
    monkeypatch.setattr("src.scripts.ingest.time.sleep", lambda s: sleeps.append(s))

    attempts = {"count": 0}
    sentinel_store = object()

    def fake_from_documents(documents, embedding):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("429 RESOURCE_EXHAUSTED retry in 8s")
        return sentinel_store

    monkeypatch.setattr("src.scripts.ingest.FAISS.from_documents", fake_from_documents)

    result = _embed_batch_with_retry(None, ["doc1"], object(), 1, 2)
    assert result is sentinel_store
    assert attempts["count"] == 2
    assert sleeps == [10.0]


def test_embed_batch_with_retry_raises_immediately_on_non_429(monkeypatch):
    monkeypatch.setattr("src.scripts.ingest.time.sleep", lambda s: None)

    def fail_auth(documents, embedding):
        raise ValueError("403 PERMISSION_DENIED")

    monkeypatch.setattr("src.scripts.ingest.FAISS.from_documents", fail_auth)

    with pytest.raises(ValueError):
        _embed_batch_with_retry(None, ["doc1"], object(), 1, 1)
