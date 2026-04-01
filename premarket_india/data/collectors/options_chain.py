"""Collector for Nifty options chain data from NSE."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

import httpx
from loguru import logger

from data.collectors.base import BaseCollector
from data.models import OptionsChainData, OptionStrike


class OptionsChainCollector(BaseCollector):
    name = "options_chain"
    timeout = 45

    NSE_OPTIONS_URL = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    NSE_BASE_URL = "https://www.nseindia.com"

    async def _collect(self) -> OptionsChainData:
        """Try nsepython first, fall back to direct NSE API with browser headers."""
        # Strategy 1: nsepython
        result = await self._try_nsepython()
        if result and result.strikes:
            return result

        logger.info(f"[{self.name}] nsepython failed, trying direct NSE API")

        # Strategy 2: Direct NSE API with session cookies
        result = await self._try_nse_direct()
        if result and result.strikes:
            return result

        logger.warning(f"[{self.name}] All strategies failed, returning empty data")
        return self._default()

    async def _try_nsepython(self) -> Optional[OptionsChainData]:
        """Attempt collection via nsepython library."""
        try:
            from nsepython import option_chain

            # nsepython is sync — run in thread
            raw = await self._run_sync(option_chain, "NIFTY")

            if raw is None:
                return None

            # nsepython returns a dict with 'records' key
            records = raw.get("records", {}) if isinstance(raw, dict) else {}
            data_rows = records.get("data", [])
            spot = records.get("underlyingValue", 0.0)

            if not data_rows:
                return None

            strikes = self._parse_nse_records(data_rows)
            now_str = datetime.now(timezone.utc).isoformat()

            return OptionsChainData(
                symbol="NIFTY",
                spot_price=float(spot),
                strikes=strikes,
                timestamp=now_str,
                source="nsepython",
                fresh=True,
            )
        except ImportError:
            logger.debug(f"[{self.name}] nsepython not installed")
            return None
        except Exception as exc:
            logger.warning(f"[{self.name}] nsepython error: {exc}")
            return None

    async def _try_nse_direct(self) -> Optional[OptionsChainData]:
        """Direct NSE API call with browser-like session handling."""
        try:
            async with httpx.AsyncClient(
                headers=self.NSE_HEADERS,
                follow_redirects=True,
                timeout=20.0,
            ) as client:
                # Step 1: Hit base URL to get session cookies
                await client.get(self.NSE_BASE_URL)
                await asyncio.sleep(2)  # Respect NSE rate limits

                # Step 2: Fetch options chain API
                resp = await client.get(self.NSE_OPTIONS_URL)
                resp.raise_for_status()

                raw = resp.json()
                records = raw.get("records", {})
                data_rows = records.get("data", [])
                spot = records.get("underlyingValue", 0.0)

                if not data_rows:
                    return None

                strikes = self._parse_nse_records(data_rows)
                now_str = datetime.now(timezone.utc).isoformat()

                return OptionsChainData(
                    symbol="NIFTY",
                    spot_price=float(spot),
                    strikes=strikes,
                    timestamp=now_str,
                    source="nse_direct",
                    fresh=True,
                )
        except Exception as exc:
            logger.warning(f"[{self.name}] NSE direct API error: {exc}")
            return None

    def _parse_nse_records(self, data_rows: list) -> list[OptionStrike]:
        """Parse NSE option chain data rows into OptionStrike models."""
        strikes = []
        for row in data_rows:
            try:
                strike_price = float(row.get("strikePrice", 0))
                ce = row.get("CE", {})
                pe = row.get("PE", {})

                strikes.append(OptionStrike(
                    strike=strike_price,
                    call_oi=int(ce.get("openInterest", 0)),
                    put_oi=int(pe.get("openInterest", 0)),
                    call_oi_change=int(ce.get("changeinOpenInterest", 0)),
                    put_oi_change=int(pe.get("changeinOpenInterest", 0)),
                    call_volume=int(ce.get("totalTradedVolume", 0)),
                    put_volume=int(pe.get("totalTradedVolume", 0)),
                    call_iv=float(ce["impliedVolatility"]) if ce.get("impliedVolatility") else None,
                    put_iv=float(pe["impliedVolatility"]) if pe.get("impliedVolatility") else None,
                    call_ltp=float(ce.get("lastPrice", 0)),
                    put_ltp=float(pe.get("lastPrice", 0)),
                ))
            except (KeyError, ValueError, TypeError) as exc:
                continue  # Skip malformed rows

        return strikes

    def _default(self) -> OptionsChainData:
        return OptionsChainData(
            symbol="NIFTY",
            source="none",
            fresh=False,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
