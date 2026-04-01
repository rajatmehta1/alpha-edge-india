"""NLP sentiment scoring from social data and news using keyword-based approach."""

from __future__ import annotations

from loguru import logger

from data.models import SentimentData, NewsItem
from features.models import SentimentBundle


# ── Keyword dictionaries for sentiment scoring ──

_BULLISH_KEYWORDS = [
    "bullish", "rally", "breakout", "surge", "upgrade", "outperform",
    "buy", "accumulate", "strong", "positive", "beat", "exceeds",
    "record high", "all-time high", "expansion", "growth", "upside",
    "green", "boom", "momentum", "recovery", "rebound",
]

_BEARISH_KEYWORDS = [
    "bearish", "crash", "breakdown", "plunge", "downgrade", "underperform",
    "sell", "reduce", "weak", "negative", "miss", "below estimate",
    "record low", "contraction", "slowdown", "downside", "recession",
    "red", "bust", "capitulation", "panic", "collapse",
]


def _score_text(text: str) -> float:
    """Score a text string from -1.0 (bearish) to +1.0 (bullish) using keyword matching.

    Returns 0.0 for neutral text.
    """
    text_lower = text.lower()
    bullish_count = sum(1 for kw in _BULLISH_KEYWORDS if kw in text_lower)
    bearish_count = sum(1 for kw in _BEARISH_KEYWORDS if kw in text_lower)

    total = bullish_count + bearish_count
    if total == 0:
        return 0.0

    # Net score normalized to [-1, 1]
    score = (bullish_count - bearish_count) / total
    return round(score, 3)


def _score_social(social_data: list[SentimentData]) -> tuple[float, list[dict]]:
    """Aggregate social sentiment from all sources.

    Returns (overall_score, social_items_for_display).
    """
    if not social_data:
        return 0.0, []

    scores: list[float] = []
    items: list[dict] = []

    for item in social_data:
        # Use pre-computed score if available, otherwise compute from counts
        if item.score != 0.0:
            score = item.score
        elif item.bullish + item.bearish > 0:
            score = (item.bullish - item.bearish) / (item.bullish + item.bearish)
        else:
            score = 0.0

        scores.append(score)
        items.append({
            "hashtag": item.hashtag,
            "ticker": item.ticker,
            "count": item.count,
            "bullish": item.bullish,
            "bearish": item.bearish,
            "score": round(score, 2),
            "source": item.source,
        })

    overall = sum(scores) / len(scores) if scores else 0.0
    return round(overall, 3), items


def _score_news(news: list[NewsItem]) -> float:
    """Aggregate news sentiment from all articles.

    Returns score -1.0 to 1.0.
    """
    if not news:
        return 0.0

    scores: list[float] = []
    for item in news:
        # Use pre-computed sentiment if available
        if item.sentiment_score != 0.0:
            scores.append(item.sentiment_score)
        else:
            # Compute from title
            score = _score_text(item.title)
            scores.append(score)

    return round(sum(scores) / len(scores), 3) if scores else 0.0


def compute_sentiment(
    social_data: list[SentimentData],
    news: list[NewsItem],
) -> SentimentBundle:
    """Compute aggregated sentiment from social media and news.

    Returns SentimentBundle with overall_score, social_items, and news_score.
    """
    logger.info("Computing sentiment analysis")

    social_score, social_items = _score_social(social_data)
    news_score = _score_news(news)

    # Overall = weighted average (news weighted higher — more reliable)
    if social_items and news:
        overall = news_score * 0.6 + social_score * 0.4
    elif news:
        overall = news_score
    elif social_items:
        overall = social_score
    else:
        overall = 0.0

    return SentimentBundle(
        overall_score=round(overall, 3),
        social_items=social_items,
        news_score=round(news_score, 3),
    )
