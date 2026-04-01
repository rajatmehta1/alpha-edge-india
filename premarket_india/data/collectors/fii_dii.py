"""Collector for FII/DII cash and derivatives flow data."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional

import httpx
from loguru import logger

from data.collectors.base import BaseCollector
from data.models import FIIDIIData, FIIDIIHistory


class FIIDIICollector(BaseCollector):
    name = "fii_dii"

    # Moneycontrol FII/DII page for scraping fallback
    MC_FII_URL = "https://www.moneycontrol.com/stocks/marketstats/fii_dii_activity/index.php"

    async def _collect(self) -> Tuple[FIIDIIData, FIIDIIHistory]:
        """Try nsepython first, then moneycontrol scraping, then empty defaults."""
        # Strategy 1: nsepython
        result = await self._try_nsepython()
        if result:
            fii_dii, history = result
            if fii_dii.fresh:
                return fii_dii, history

        logger.info(f"[{self.name}] nsepython failed, trying moneycontrol")

        # Strategy 2: Moneycontrol scraping
        result = await self._try_moneycontrol()
        if result:
            fii_dii, history = result
            if fii_dii.fresh:
                return fii_dii, history

        logger.warning(f"[{self.name}] All strategies failed")
        return self._default()

    async def _try_nsepython(self) -> Optional[Tuple[FIIDIIData, FIIDIIHistory]]:
        """Attempt FII/DII data via nsepython."""
        try:
            from nsepython import fii_data, dii_data

            fii_raw = await self._run_sync(fii_data)
            await asyncio.sleep(1)
            dii_raw = await self._run_sync(dii_data)

            if fii_raw is None or dii_raw is None:
                return None

            now_str = datetime.now(timezone.utc).isoformat()
            today_str = datetime.now().strftime("%Y-%m-%d")

            # nsepython returns DataFrames — extract latest row
            fii_cash_net = 0.0
            dii_cash_net = 0.0
            fii_5d = 0.0
            dii_5d = 0.0

            if hasattr(fii_raw, "iloc") and len(fii_raw) > 0:
                last_row = fii_raw.iloc[-1]
                fii_cash_net = float(last_row.get("Net Value", last_row.get("netValue", 0)))
                # Sum last 5 rows for 5-day total
                if len(fii_raw) >= 5:
                    net_col = "Net Value" if "Net Value" in fii_raw.columns else "netValue"
                    if net_col in fii_raw.columns:
                        fii_5d = float(fii_raw[net_col].tail(5).sum())

            if hasattr(dii_raw, "iloc") and len(dii_raw) > 0:
                last_row = dii_raw.iloc[-1]
                dii_cash_net = float(last_row.get("Net Value", last_row.get("netValue", 0)))
                if len(dii_raw) >= 5:
                    net_col = "Net Value" if "Net Value" in dii_raw.columns else "netValue"
                    if net_col in dii_raw.columns:
                        dii_5d = float(dii_raw[net_col].tail(5).sum())

            fii_dii = FIIDIIData(
                fii_cash_net=round(fii_cash_net, 2),
                dii_cash_net=round(dii_cash_net, 2),
                fii_5d_total=round(fii_5d, 2),
                dii_5d_total=round(dii_5d, 2),
                date=today_str,
                source="nsepython",
                fresh=True,
            )

            history = self._build_history_from_df(fii_raw, dii_raw)
            return fii_dii, history

        except ImportError:
            logger.debug(f"[{self.name}] nsepython not installed")
            return None
        except Exception as exc:
            logger.warning(f"[{self.name}] nsepython error: {exc}")
            return None

    async def _try_moneycontrol(self) -> Optional[Tuple[FIIDIIData, FIIDIIHistory]]:
        """Scrape FII/DII data from Moneycontrol."""
        try:
            from bs4 import BeautifulSoup

            async with httpx.AsyncClient(
                headers=self.NSE_HEADERS, timeout=15.0, follow_redirects=True
            ) as client:
                resp = await client.get(self.MC_FII_URL)
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Moneycontrol has tables with FII/DII data
            tables = soup.find_all("table")
            if not tables:
                return None

            now_str = datetime.now(timezone.utc).isoformat()
            today_str = datetime.now().strftime("%Y-%m-%d")

            fii_cash_net = 0.0
            dii_cash_net = 0.0

            # Parse first table — typically has today's data
            for table in tables[:2]:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 4:
                        label = cells[0].get_text(strip=True).upper()
                        try:
                            net_val = float(
                                cells[-1].get_text(strip=True)
                                .replace(",", "")
                                .replace("(", "-")
                                .replace(")", "")
                            )
                        except (ValueError, IndexError):
                            continue

                        if "FII" in label or "FPI" in label:
                            fii_cash_net = net_val
                        elif "DII" in label:
                            dii_cash_net = net_val

            fii_dii = FIIDIIData(
                fii_cash_net=round(fii_cash_net, 2),
                dii_cash_net=round(dii_cash_net, 2),
                date=today_str,
                source="moneycontrol",
                fresh=True,
            )

            # Build minimal history (only today's data from MC)
            history = FIIDIIHistory(
                dates=[today_str],
                fii_net=[round(fii_cash_net, 2)],
                dii_net=[round(dii_cash_net, 2)],
            )

            return fii_dii, history

        except Exception as exc:
            logger.warning(f"[{self.name}] Moneycontrol scraping error: {exc}")
            return None

    def _build_history_from_df(self, fii_df, dii_df) -> FIIDIIHistory:
        """Build 8-day FII/DII history from nsepython DataFrames."""
        try:
            dates = []
            fii_net_list = []
            dii_net_list = []

            if hasattr(fii_df, "tail") and len(fii_df) >= 1:
                fii_tail = fii_df.tail(8)
                date_col = "date" if "date" in fii_df.columns else fii_df.index.name or None
                net_col = "Net Value" if "Net Value" in fii_df.columns else "netValue"

                for _, row in fii_tail.iterrows():
                    if date_col and date_col in fii_df.columns:
                        dates.append(str(row[date_col]))
                    else:
                        dates.append(str(_.strftime("%Y-%m-%d") if hasattr(_, "strftime") else str(_)))
                    fii_net_list.append(round(float(row.get(net_col, 0)), 2))

            if hasattr(dii_df, "tail") and len(dii_df) >= 1:
                dii_tail = dii_df.tail(8)
                net_col = "Net Value" if "Net Value" in dii_df.columns else "netValue"
                for _, row in dii_tail.iterrows():
                    dii_net_list.append(round(float(row.get(net_col, 0)), 2))

            # Pad if lengths don't match
            max_len = max(len(dates), len(fii_net_list), len(dii_net_list), 1)
            while len(dates) < max_len:
                dates.append("")
            while len(fii_net_list) < max_len:
                fii_net_list.append(0.0)
            while len(dii_net_list) < max_len:
                dii_net_list.append(0.0)

            return FIIDIIHistory(
                dates=dates[:8],
                fii_net=fii_net_list[:8],
                dii_net=dii_net_list[:8],
            )
        except Exception as exc:
            logger.warning(f"[{self.name}] History parsing failed: {exc}")
            return FIIDIIHistory()

    def _default(self) -> Tuple[FIIDIIData, FIIDIIHistory]:
        return FIIDIIData(source="none", fresh=False), FIIDIIHistory()
