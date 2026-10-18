"""Public RSS metadata provider for symbol-related market news."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

import feedparser

from data.storage import StorageEngine


class NewsProvider:
    """Fetch public RSS metadata without downloading article bodies."""

    GOOGLE_NEWS_URL = "https://news.google.com/rss/search?q={query}&hl=vi&gl=VN&ceid=VN:vi"
    CAFE_F_RSS_URL = "https://cafef.vn/thi-truong-chung-khoan.rss"

    def __init__(self, storage: StorageEngine | None = None, cache_minutes: int = 30):
        self.storage = storage or StorageEngine()
        self.cache_minutes = cache_minutes

    def get_symbol_news(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        symbol = symbol.upper().strip()
        cached = self.storage.get_cached_news(symbol, self.cache_minutes)
        if cached:
            return cached[:limit]

        query = f"{symbol}+chứng+khoán"
        articles = self._fetch_feed(self.GOOGLE_NEWS_URL.format(query=query), "Google News RSS", symbol)
        articles.extend(self._fetch_feed(self.CAFE_F_RSS_URL, "CafeF RSS", symbol, strict_symbol_match=True))
        articles = self._deduplicate(articles)
        self.storage.replace_cached_news(symbol, articles)
        return articles[:limit]

    def _fetch_feed(self, url: str, source: str, symbol: str, strict_symbol_match: bool = False) -> List[Dict[str, Any]]:
        try:
            parsed = feedparser.parse(url)
            entries = getattr(parsed, "entries", [])
            symbol_pattern = re.compile(rf"(?<![A-Z0-9]){re.escape(symbol)}(?![A-Z0-9])", re.IGNORECASE)
            articles = []
            for entry in entries:
                title = str(entry.get("title", "")).strip()
                summary = str(entry.get("summary", "")).strip()
                link = str(entry.get("link", "")).strip()
                if not title or not link or (strict_symbol_match and not symbol_pattern.search(f"{title} {summary}")):
                    continue
                article_id = hashlib.sha256(f"{source}|{link}".encode("utf-8")).hexdigest()
                articles.append({
                    "article_id": article_id,
                    "symbol": symbol,
                    "title": title,
                    "summary": re.sub(r"<[^>]+>", "", summary)[:500],
                    "source": source,
                    "url": link,
                    "published_at": str(entry.get("published") or entry.get("updated") or "Unknown"),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                })
            return articles
        except Exception as exc:
            print(f"[NewsProvider] Could not fetch {source}: {exc}")
            return []

    @staticmethod
    def _deduplicate(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        unique = {article["article_id"]: article for article in articles}
        return sorted(unique.values(), key=lambda article: article["published_at"], reverse=True)
