import time
from extractor import ExtractionCache


def test_cache_store_and_retrieve():
    cache = ExtractionCache(ttl_seconds=60)
    data = {"title": "test", "formats": []}
    cache.store("abc123", data)
    assert cache.get("abc123") == data


def test_cache_expiry():
    cache = ExtractionCache(ttl_seconds=1)
    cache.store("abc123", {"title": "test"})
    time.sleep(1.1)
    assert cache.get("abc123") is None


def test_cache_miss():
    cache = ExtractionCache(ttl_seconds=60)
    assert cache.get("nonexistent") is None
