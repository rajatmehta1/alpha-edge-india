"""
Alpha Edge — Pre-Market Intelligence Pipeline
Runs daily at 07:00 IST. Generates report by ~07:06 IST.

Usage:
    python main.py
"""

import asyncio
import os
import sys
import webbrowser
from datetime import datetime

# Fix Windows console encoding for Rich
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console(force_terminal=True)


def _unpack_fii(result):
    """Unpack FII/DII collector result (may be tuple or single object)."""
    from data.models import FIIDIIData, FIIDIIHistory
    if isinstance(result, tuple) and len(result) == 2:
        return result
    return (result if isinstance(result, FIIDIIData) else FIIDIIData(), FIIDIIHistory())


async def collect_all_data():
    """Run all collectors in parallel with fallback handling."""
    from data.collectors.market_data import MarketDataCollector
    from data.collectors.nse_stocks import NSEStockCollector
    from data.collectors.options_chain import OptionsChainCollector
    from data.collectors.fii_dii import FIIDIICollector
    from data.collectors.block_deals import BlockDealCollector
    from data.collectors.news import NewsCollector
    from data.collectors.social_sentiment import SocialSentimentCollector
    from data.collectors.tv_analysts import TVAnalystCollector
    from data.models import RawMarketData

    collectors = [
        ("market_data", MarketDataCollector()),
        ("nse_stocks", NSEStockCollector()),
        ("options_chain", OptionsChainCollector()),
        ("fii_dii", FIIDIICollector()),
        ("block_deals", BlockDealCollector()),
        ("news", NewsCollector()),
        ("social_sentiment", SocialSentimentCollector()),
        ("tv_analysts", TVAnalystCollector()),
    ]

    results = {}
    tasks = []
    for name, collector in collectors:
        tasks.append((name, collector.safe_collect()))

    gathered = await asyncio.gather(
        *[t[1] for t in tasks], return_exceptions=True
    )

    for i, (name, _) in enumerate(tasks):
        result = gathered[i]
        if isinstance(result, Exception):
            logger.warning(f"Collector {name} failed: {result}")
            results[name] = None
        else:
            results[name] = result
            logger.info(f"Collector {name} succeeded")

    # Aggregate into RawMarketData
    from data.models import (
        MacroDashboard, FIIDIIData, FIIDIIHistory, OptionsChainData,
    )

    market_result = results.get("market_data")
    if isinstance(market_result, tuple) and len(market_result) == 3:
        macro, nifty_ohlcv, banknifty_ohlcv = market_result
    else:
        macro = market_result if isinstance(market_result, MacroDashboard) else MacroDashboard()
        nifty_ohlcv, banknifty_ohlcv = [], []
    raw = RawMarketData(
        macro=macro,
        nifty_ohlcv=nifty_ohlcv,
        banknifty_ohlcv=banknifty_ohlcv,
        stock_ohlcv=results.get("nse_stocks") or [],
        nifty_options=results.get("options_chain") or OptionsChainData(symbol="NIFTY"),
        fii_dii=_unpack_fii(results.get("fii_dii"))[0],
        fii_dii_history=_unpack_fii(results.get("fii_dii"))[1],
        block_deals=results.get("block_deals") or [],
        news=results.get("news") or [],
        social_data=results.get("social_sentiment") or [],
        tv_calls=results.get("tv_analysts") or [],
    )
    return raw


async def run_pipeline():
    """Full pipeline: Ingest -> Compute -> AI -> Render -> Deliver."""
    from config.settings import settings
    from storage.database import init_db, get_session_count
    from features.pipeline import run_feature_pipeline
    from agents.graph import run_agents
    from report.renderer import ReportRenderer
    from report.chart_data import prepare_all_chart_data as prepare_chart_data
    from features.models import ReportMetadata

    start = datetime.now()
    logger.info(f"Alpha Edge Pipeline Started at {start.strftime('%H:%M:%S IST')}")

    # Initialize database
    init_db()

    # Check for first run — auto-backfill
    session_count = get_session_count()
    if session_count < 100:
        console.print(f"[bold yellow]Only {session_count} historical sessions found.[/]")
        if session_count == 0:
            console.print("[yellow]Running initial data backfill (5-10 minutes)...[/]")
            console.print("[dim]This only happens on first run.[/]")
            try:
                from scripts.backfill_history import run_backfill
                await run_backfill()
                console.print("[bold green]Backfill complete.[/]")
            except Exception as e:
                logger.warning(f"Backfill failed: {e}. Continuing without historical data.")
        else:
            console.print("[dim]Pattern matching will improve as more data accumulates.[/]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]{task.description}"),
        console=console,
    ) as progress:

        # Stage 1: Data Ingestion (parallel)
        task = progress.add_task("Collecting market data...", total=None)
        raw_data = await collect_all_data()
        progress.update(task, description="Data collected")

        # Stage 2: Feature Engineering
        task = progress.add_task("Computing features...", total=None)
        features = run_feature_pipeline(raw_data)
        progress.update(task, description="Features computed")

        # Stage 3: Store snapshot
        task = progress.add_task("Storing snapshot...", total=None)
        try:
            from storage.database import store_daily_snapshot
            from datetime import date as date_cls
            macro = features.macro
            store_daily_snapshot(
                date=date_cls.today().isoformat(),
                gap_pct=features.gap_stats.expected_gap_pct,
                crude_change=macro.brent_crude.change_pct if macro else 0,
                dow_change=macro.dow_futures.change_pct if macro else 0,
                usdinr_change=macro.usdinr.change_pct if macro else 0,
                vix=macro.india_vix.value if macro else 0,
                pcr=features.options.pcr_near_atm,
                fii_net=macro.fii_net.value if macro else 0,
                dii_net=macro.dii_net.value if macro else 0,
                day_of_week=date_cls.today().weekday(),
                is_expiry_week=features.expiry.is_expiry_week,
                rsi_14=features.nifty_levels.rsi,
                atr_pct=(features.nifty_levels.atr / features.nifty_levels.prev_close * 100) if features.nifty_levels.prev_close > 0 else 0,
                volume_ratio=1.0,
            )
        except Exception as e:
            logger.warning(f"Snapshot storage failed: {e}")
        progress.update(task, description="Snapshot stored")

        # Stage 4: AI Agent Orchestration
        task = progress.add_task("AI agents generating narratives...", total=None)
        narratives = await asyncio.to_thread(run_agents, features)
        progress.update(task, description="Narratives generated")

        # Stage 5: Report Rendering
        task = progress.add_task("Rendering report...", total=None)
        chart_data = prepare_chart_data(features)

        elapsed = (datetime.now() - start).total_seconds()
        features.metadata = ReportMetadata(
            signal_count=_count_signals(raw_data),
            pattern_match_count=sum(
                pm.total_matches for pm in features.pattern_matches
            ),
            contagion_chain_count=len(features.contagion_chain.orders),
            correlation_anomalies=len(features.correlations.anomalies),
            pipeline_duration=elapsed,
            generated_at=datetime.now().strftime("%H:%M IST"),
        )

        renderer = ReportRenderer()
        html_report = renderer.render(features, narratives, chart_data)
        report_path = renderer.save(html_report)
        progress.update(task, description=f"Report saved: {report_path}")

    elapsed = (datetime.now() - start).total_seconds()
    logger.info(f"Pipeline complete in {elapsed:.1f}s")
    console.print(f"\n[bold green]Report ready: {report_path}[/]")
    console.print(f"[dim]Pipeline completed in {elapsed:.1f} seconds[/]")

    # Open in browser
    try:
        absolute_path = os.path.abspath(report_path)
        webbrowser.open(f"file://{absolute_path}")
        logger.info(f"Report opened in browser: {absolute_path}")
    except Exception:
        pass

    return report_path


def _count_signals(raw_data) -> int:
    """Count total raw data points collected."""
    count = 0
    count += len(raw_data.stock_ohlcv)
    count += len(raw_data.nifty_options.strikes)
    count += len(raw_data.block_deals)
    count += len(raw_data.news)
    count += len(raw_data.social_data)
    count += len(raw_data.tv_calls)
    # Count macro data points
    for field in ["sgx_nifty", "dow_futures", "brent_crude", "usdinr", "india_vix", "fii_net", "dii_net"]:
        dp = getattr(raw_data.macro, field, None)
        if dp and dp.fresh:
            count += 1
    return max(count, 1)


if __name__ == "__main__":
    asyncio.run(run_pipeline())
