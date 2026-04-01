"""Collector for block and bulk deals from NSE/BSE."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import httpx
from loguru import logger

from data.collectors.base import BaseCollector
from data.models import BlockDeal


class BlockDealCollector(BaseCollector):
    name = "block_deals"

    NSE_BLOCK_URL = "https://www.nseindia.com/api/block-deal"
    NSE_BULK_URL = "https://www.nseindia.com/api/bulk-deal-data"
    NSE_BASE_URL = "https://www.nseindia.com"

    async def _collect(self) -> List[BlockDeal]:
        """Try jugaad-data first, then NSE direct API, then web scraping."""
        # Strategy 1: jugaad-data
        result = await self._try_jugaad()
        if result:
            return result

        logger.info(f"[{self.name}] jugaad-data failed, trying NSE API")

        # Strategy 2: Direct NSE API
        result = await self._try_nse_api()
        if result:
            return result

        logger.warning(f"[{self.name}] All strategies failed")
        return self._default()

    async def _try_jugaad(self) -> Optional[List[BlockDeal]]:
        """Attempt collection via jugaad-data library."""
        try:
            from jugaad_data.nse import NSELive

            nse = NSELive()
            today = datetime.now()

            # jugaad-data is sync
            block_raw = await self._run_sync(nse.block_deals)

            deals: List[BlockDeal] = []

            if block_raw and isinstance(block_raw, list):
                for item in block_raw:
                    try:
                        deals.append(BlockDeal(
                            ticker=str(item.get("symbol", "UNKNOWN")),
                            quantity=int(item.get("quantity", 0)),
                            price=float(item.get("price", 0)),
                            deal_type="Block",
                            buyer_seller=item.get("clientName", None),
                            date=today.strftime("%Y-%m-%d"),
                            source="jugaad_data",
                        ))
                    except (KeyError, ValueError, TypeError):
                        continue

            if deals:
                logger.info(f"[{self.name}] Got {len(deals)} block deals from jugaad-data")
                return deals

            return None

        except ImportError:
            logger.debug(f"[{self.name}] jugaad-data not installed")
            return None
        except Exception as exc:
            logger.warning(f"[{self.name}] jugaad-data error: {exc}")
            return None

    async def _try_nse_api(self) -> Optional[List[BlockDeal]]:
        """Direct NSE API for block/bulk deals with session handling."""
        try:
            async with httpx.AsyncClient(
                headers=self.NSE_HEADERS,
                follow_redirects=True,
                timeout=20.0,
            ) as client:
                # Get session cookies
                await client.get(self.NSE_BASE_URL)
                await asyncio.sleep(2)

                deals: List[BlockDeal] = []
                today_str = datetime.now().strftime("%Y-%m-%d")

                # Fetch block deals
                try:
                    resp = await client.get(self.NSE_BLOCK_URL)
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in (data if isinstance(data, list) else data.get("data", [])):
                            try:
                                deals.append(BlockDeal(
                                    ticker=str(item.get("symbol", "UNKNOWN")),
                                    quantity=int(item.get("quantity", 0)),
                                    price=float(item.get("price", 0)),
                                    deal_type="Block",
                                    buyer_seller=item.get("clientName", None),
                                    date=today_str,
                                    source="nse_api",
                                ))
                            except (KeyError, ValueError, TypeError):
                                continue
                except Exception as exc:
                    logger.debug(f"[{self.name}] Block deals API error: {exc}")

                await asyncio.sleep(1)

                # Fetch bulk deals
                try:
                    resp = await client.get(self.NSE_BULK_URL)
                    if resp.status_code == 200:
                        data = resp.json()
                        for item in (data if isinstance(data, list) else data.get("data", [])):
                            try:
                                deals.append(BlockDeal(
                                    ticker=str(item.get("symbol", "UNKNOWN")),
                                    quantity=int(item.get("quantity", 0)),
                                    price=float(item.get("price", 0)),
                                    deal_type="Bulk",
                                    buyer_seller=item.get("clientName", None),
                                    date=today_str,
                                    source="nse_api",
                                ))
                            except (KeyError, ValueError, TypeError):
                                continue
                except Exception as exc:
                    logger.debug(f"[{self.name}] Bulk deals API error: {exc}")

                if deals:
                    logger.info(f"[{self.name}] Got {len(deals)} deals from NSE API")
                    return deals

            return None

        except Exception as exc:
            logger.warning(f"[{self.name}] NSE API error: {exc}")
            return None

    def _default(self) -> List[BlockDeal]:
        return []
