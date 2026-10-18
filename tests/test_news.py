from data.news import NewsProvider
from data.storage import StorageEngine


def test_news_cache_round_trip(tmp_path):
    storage = StorageEngine(str(tmp_path / "scanner.db"))
    article = {
        "article_id": "article-1", "symbol": "FPT", "title": "FPT test headline",
        "summary": "RSS metadata only", "source": "Test Source",
        "url": "https://example.com/article-1", "published_at": "2026-10-12T00:00:00+00:00",
        "fetched_at": "2026-10-12T00:00:00+00:00",
    }
    storage.replace_cached_news("FPT", [article])
    cached = storage.get_cached_news("FPT", cache_minutes=60 * 24 * 365)
    assert len(cached) == 1
    assert cached[0]["title"] == "FPT test headline"


def test_news_provider_deduplicates_by_article_id():
    provider = NewsProvider()
    articles = [
        {"article_id": "one", "published_at": "2026-10-11", "title": "A"},
        {"article_id": "one", "published_at": "2026-10-12", "title": "B"},
    ]
    assert provider._deduplicate(articles)[0]["title"] == "B"
