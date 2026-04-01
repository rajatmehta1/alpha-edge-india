"""Collector for social sentiment data (Stocktwits + simulated fallback)."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from loguru import logger

from data.collectors.base import BaseCollector
from data.models import SentimentData
from config.constants import NIFTY_50_STOCKS


# Top tickers to track sentiment for (most liquid / most discussed)
SENTIMENT_TICKERS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "SBIN", "TATAMOTORS", "BHARTIARTL", "ITC", "BAJFINANCE",
    "ADANIENT", "WIPRO", "HCLTECH", "MARUTI", "LT",
]

# Stocktwits symbol mappings (Indian tickers on Stocktwits)
STOCKTWITS_SYMBOLS = {
    "RELIANCE": "RELIANCE-NS",
    "TCS": "TCS-NS",
    "HDFCBANK": "HDFCBANK-NS",
    "INFY": "INFY",  # US-listed
    "ICICIBANK": "IBN",  # US-listed
    "SBIN": "SBIN-NS",
    "TATAMOTORS": "TTM",  # US-listed
    "BHARTIARTL": "BHARTIARTL-NS",
    "ITC": "ITC-NS",
    "BAJFINANCE": "BAJFINANCE-NS",
    "ADANIENT": "ADANIENT-NS",
    "WIPRO": "WIT",  # US-listed
    "HCLTECH": "HCLTECH-NS",
    "MARUTI": "MARUTI-NS",
    "LT": "LT-NS",
}


class SocialSentimentCollector(BaseCollector):
    name = "social_sentiment"

    STOCKTWITS_API = "https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"

    async def _collect(self) -> List[SentimentData]:
        """Try Stocktwits API (free, no auth), fall back to simulated data."""
        # Strategy 1: Stocktwits
        result = await self._try_stocktwits()
        if result:
            logger.info(f"[{self.name}] Got {len(result)} items from Stocktwits")
            return result

        logger.info(f"[{self.name}] Stocktwits failed, using simulated sentiment")

        # Strategy 2: Simulated data based on random but realistic distributions
        return self._generate_simulated()

    async def _try_stocktwits(self) -> Optional[List[SentimentData]]:
        """Fetch sentiment from Stocktwits free API (no auth required)."""
        try:
            results: List[SentimentData] = []

            async with httpx.AsyncClient(timeout=10.0) as client:
                for ticker, st_symbol in list(STOCKTWITS_SYMBOLS.items())[:8]:
                    try:
                        url = self.STOCKTWITS_API.format(symbol=st_symbol)
                        resp = await client.get(url)

                        if resp.status_code == 429:
                            # Rate limited — use what we have
                            logger.debug(f"[{self.name}] Stocktwits rate limited after {len(results)} items")
                            break

                        if resp.status_code != 200:
                            continue

                        data = resp.json()
                        messages = data.get("messages", [])

                        if not messages:
                            continue

                        bullish = sum(
                            1 for m in messages
                            if m.get("entities", {}).get("sentiment", {}).get("basic") == "Bullish"
                        )
                        bearish = sum(
                            1 for m in messages
                            if m.get("entities", {}).get("sentiment", {}).get("basic") == "Bearish"
                        )
                        total = len(messages)
                        score = (bullish - bearish) / total if total > 0 else 0.0

                        results.append(SentimentData(
                            hashtag=f"#{ticker}",
                            ticker=ticker,
                            count=total,
                            bullish=bullish,
                            bearish=bearish,
                            score=round(score, 2),
                            source="stocktwits",
                        ))

                    except Exception as exc:
                        logger.debug(f"[{self.name}] Stocktwits error for {ticker}: {exc}")
                        continue

            return results if results else None

        except Exception as exc:
            logger.warning(f"[{self.name}] Stocktwits API error: {exc}")
            return None

    def _generate_simulated(self) -> List[SentimentData]:
        """Generate simulated but realistic sentiment data.

        Uses random distributions that mirror typical Indian stock market social chatter.
        The sentiment module in features/ will normalize and weight these appropriately.
        """
        random.seed(datetime.now().toordinal())  # Reproducible per day

        results: List[SentimentData] = []
        for ticker in SENTIMENT_TICKERS:
            # Simulate 20-80 mentions per stock
            count = random.randint(20, 80)
            # Slight bullish bias (reflects typical retail sentiment)
            bullish_ratio = random.uniform(0.35, 0.75)
            bullish = int(count * bullish_ratio)
            bearish = int(count * (1 - bullish_ratio) * 0.7)  # Some are neutral
            score = (bullish - bearish) / count if count > 0 else 0.0

            results.append(SentimentData(
                hashtag=f"#{ticker}",
                ticker=ticker,
                count=count,
                bullish=bullish,
                bearish=bearish,
                score=round(score, 2),
                source="simulated",
            ))

        return results

    def _default(self) -> List[SentimentData]:
        return self._generate_simulated()
