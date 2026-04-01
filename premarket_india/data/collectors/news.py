"""Collector for market news from RSS feeds with ticker tagging."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List

import feedparser
from loguru import logger

from data.collectors.base import BaseCollector
from data.models import NewsItem
from config.constants import RSS_FEEDS, TICKER_KEYWORDS


class NewsCollector(BaseCollector):
    name = "news"

    async def _collect(self) -> List[NewsItem]:
        """Fetch RSS feeds and filter to last 12 hours with ticker tagging."""
        all_items: List[NewsItem] = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=12)

        for feed_url in RSS_FEEDS:
            try:
                items = await self._fetch_feed(feed_url, cutoff)
                all_items.extend(items)
            except Exception as exc:
                logger.warning(f"[{self.name}] Feed failed {feed_url}: {exc}")
                continue

        # Deduplicate by title (case-insensitive)
        seen_titles = set()
        unique_items = []
        for item in all_items:
            key = item.title.lower().strip()
            if key not in seen_titles:
                seen_titles.add(key)
                unique_items.append(item)

        logger.info(f"[{self.name}] Collected {len(unique_items)} news items from {len(RSS_FEEDS)} feeds")
        return unique_items

    async def _fetch_feed(self, url: str, cutoff: datetime) -> List[NewsItem]:
        """Parse a single RSS feed and return filtered news items."""
        # feedparser is sync
        feed = await self._run_sync(feedparser.parse, url)

        items: List[NewsItem] = []
        source_name = feed.feed.get("title", url)[:30]

        for entry in feed.entries:
            try:
                # Parse published date
                published_dt = self._parse_date(entry)

                # Filter to last 12 hours (if we can parse the date)
                if published_dt and published_dt < cutoff:
                    continue

                title = entry.get("title", "").strip()
                if not title:
                    continue

                # Tag tickers mentioned in headline
                tickers = self._tag_tickers(title)

                # Simple sentiment from title keywords
                sentiment = self._quick_sentiment(title)

                pub_str = (
                    published_dt.isoformat() if published_dt
                    else entry.get("published", "")
                )

                items.append(NewsItem(
                    title=title,
                    source=source_name,
                    published=pub_str,
                    url=entry.get("link", ""),
                    tickers=tickers,
                    sentiment_score=sentiment,
                ))
            except Exception:
                continue

        return items

    def _parse_date(self, entry) -> datetime | None:
        """Try to parse the published date from a feedparser entry."""
        # feedparser provides parsed time tuple
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                from time import mktime
                dt = datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
                return dt
            except Exception:
                pass

        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            try:
                from time import mktime
                dt = datetime.fromtimestamp(mktime(entry.updated_parsed), tz=timezone.utc)
                return dt
            except Exception:
                pass

        return None

    def _tag_tickers(self, title: str) -> List[str]:
        """Match headline text against TICKER_KEYWORDS to tag relevant tickers."""
        title_lower = title.lower()
        matched = []
        for ticker, keywords in TICKER_KEYWORDS.items():
            for kw in keywords:
                if kw in title_lower:
                    matched.append(ticker)
                    break
        return matched

    def _quick_sentiment(self, title: str) -> float:
        """Rule-based quick sentiment score from headline keywords.

        Returns a float in [-1.0, 1.0].
        This is a rough heuristic — the features/sentiment.py module does proper NLP.
        """
        title_lower = title.lower()

        positive = [
            "surge", "rally", "jump", "gain", "rise", "bull", "boom",
            "upgrade", "outperform", "record high", "breakout", "up ",
            "strong", "positive", "buy", "beats estimate", "profit",
        ]
        negative = [
            "crash", "fall", "drop", "slump", "plunge", "bear", "bust",
            "downgrade", "underperform", "sell", "loss", "weak", "negative",
            "miss estimate", "decline", "tumble", "tank", "fears",
        ]

        pos_count = sum(1 for w in positive if w in title_lower)
        neg_count = sum(1 for w in negative if w in title_lower)

        total = pos_count + neg_count
        if total == 0:
            return 0.0

        return round((pos_count - neg_count) / total, 2)

    def _default(self) -> List[NewsItem]:
        return []
