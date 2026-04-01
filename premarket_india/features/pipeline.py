"""Feature pipeline: master orchestrator calling all 15 feature modules in dependency order.

Each module is wrapped in try/except for graceful degradation — if one fails,
the pipeline continues with defaults for that section.
"""

from __future__ import annotations

import time
from datetime import datetime
from loguru import logger

from data.models import RawMarketData
from features.models import (
    ComputedFeatures,
    TechnicalLevels,
    OptionsAnalytics,
    GapStatistics,
    SectorFlow,
    CorrelationMatrix,
    SentimentBundle,
    PatternMatch,
    GapUpCandidate,
    AvoidFlag,
    ExpiryAnalysis,
    ContagionChain,
    RiskSizing,
    CalendarEvent,
    WatchlistAlert,
    ReportMetadata,
    SectionStatus,
)


def run_feature_pipeline(raw: RawMarketData) -> ComputedFeatures:
    """Run all 15 feature engineering modules in dependency order.

    Order:
      1. technical       — needs: OHLCV data
      2. options_analytics — needs: options chain data
      3. gap_analysis     — needs: technical levels, macro data
      4. sector_rotation  — needs: stock data, FII/DII flows
      5. stock_screener   — needs: gap_analysis, options_analytics, sector_rotation
      6. correlation      — needs: macro data, historical prices
      7. pattern_matching — needs: stock_screener output, historical fingerprints
      8. avoid_list       — needs: stock data, options, block deals, news
      9. expiry_analysis  — needs: options_analytics, gap_analysis
     10. contagion_chain  — needs: macro data catalyst detection
     11. confidence_score — needs: ALL of the above
     12. risk_sizing      — needs: confidence_score, VIX, ATR
     13. events_calendar  — needs: date, earnings calendar
     14. watchlist_queue  — needs: stock_screener, nifty levels, expiry
     15. sentiment        — needs: social data, news data

    Each module is wrapped in try/except — if one fails, we continue with defaults.
    """
    pipeline_start = time.time()
    logger.info("=" * 60)
    logger.info("FEATURE PIPELINE START")
    logger.info("=" * 60)

    status = SectionStatus()
    sections_ok = 0
    sections_degraded = 0

    # Initialize with defaults
    nifty_levels = TechnicalLevels()
    banknifty_levels = TechnicalLevels()
    options = OptionsAnalytics()
    gap_stats = GapStatistics()
    sector_flows: list[SectorFlow] = []
    correlations = CorrelationMatrix()
    sentiment = SentimentBundle()
    pattern_matches_list: list[PatternMatch] = []
    gap_up_candidates: list[GapUpCandidate] = []
    avoid_flags: list[AvoidFlag] = []
    expiry = ExpiryAnalysis()
    contagion = ContagionChain()
    confidence = 50
    risk = RiskSizing()
    events: list[CalendarEvent] = []
    watchlist: list[WatchlistAlert] = []

    # ── 1. Technical levels ──
    try:
        from features.technical import compute_all_technical
        nifty_levels, banknifty_levels = compute_all_technical(
            nifty_ohlcv=raw.nifty_ohlcv,
            banknifty_ohlcv=raw.banknifty_ohlcv,
            expected_nifty_open=raw.macro.expected_nifty_open,
            expected_banknifty_open=raw.macro.expected_banknifty_open,
        )
        status.mark_ok("technical")
        sections_ok += 1
        logger.info("[1/15] Technical levels: OK")
    except Exception as e:
        status.mark_degraded("technical", str(e))
        sections_degraded += 1
        logger.error(f"[1/15] Technical levels FAILED: {e}")

    # ── 2. Options analytics ──
    try:
        from features.options_analytics import compute_options_analytics
        # Extract Nifty close prices from history
        nifty_closes = [row.get("Close", row.get("close", 0)) for row in raw.nifty_ohlcv]
        options = compute_options_analytics(
            nifty_options=raw.nifty_options,
            banknifty_options=raw.banknifty_options,
            nifty_close_prices=nifty_closes,
        )
        status.mark_ok("options_analytics")
        sections_ok += 1
        logger.info("[2/15] Options analytics: OK")
    except Exception as e:
        status.mark_degraded("options_analytics", str(e))
        sections_degraded += 1
        logger.error(f"[2/15] Options analytics FAILED: {e}")

    # ── 3. Gap analysis ──
    try:
        from features.gap_analysis import compute_gap_analysis
        gap_stats = compute_gap_analysis(
            prev_close=nifty_levels.prev_close,
            expected_open=nifty_levels.expected_open,
            vix=raw.macro.india_vix.value,
            is_expiry_week=False,  # Will be refined after expiry module
        )
        status.mark_ok("gap_analysis")
        sections_ok += 1
        logger.info("[3/15] Gap analysis: OK")
    except Exception as e:
        status.mark_degraded("gap_analysis", str(e))
        sections_degraded += 1
        logger.error(f"[3/15] Gap analysis FAILED: {e}")

    # ── 4. Sector rotation ──
    try:
        from features.sector_rotation import compute_sector_rotation
        sector_flows = compute_sector_rotation(
            stocks=raw.stock_ohlcv,
            fii_dii=raw.fii_dii,
            crude_change_pct=raw.macro.brent_crude.change_pct,
            usdinr_change_pct=raw.macro.usdinr.change_pct,
        )
        status.mark_ok("sector_rotation")
        sections_ok += 1
        logger.info("[4/15] Sector rotation: OK")
    except Exception as e:
        status.mark_degraded("sector_rotation", str(e))
        sections_degraded += 1
        logger.error(f"[4/15] Sector rotation FAILED: {e}")

    # ── 5. Sentiment (moved up — needed before confidence_score) ──
    try:
        from features.sentiment import compute_sentiment
        sentiment = compute_sentiment(
            social_data=raw.social_data,
            news=raw.news,
        )
        status.mark_ok("sentiment")
        sections_ok += 1
        logger.info("[5/15] Sentiment: OK")
    except Exception as e:
        status.mark_degraded("sentiment", str(e))
        sections_degraded += 1
        logger.error(f"[5/15] Sentiment FAILED: {e}")

    # ── 6. Avoid list ──
    try:
        from features.avoid_list import compute_avoid_list
        avoid_flags = compute_avoid_list(
            stocks=raw.stock_ohlcv,
            options_data=raw.nifty_options,
            block_deals=raw.block_deals,
            news=raw.news,
        )
        status.mark_ok("avoid_list")
        sections_ok += 1
        logger.info("[6/15] Avoid list: OK")
    except Exception as e:
        status.mark_degraded("avoid_list", str(e))
        sections_degraded += 1
        logger.error(f"[6/15] Avoid list FAILED: {e}")

    # ── 7. Stock screener ──
    try:
        from features.stock_screener import compute_stock_screener
        gap_up_candidates = compute_stock_screener(
            stocks=raw.stock_ohlcv,
            macro=raw.macro,
            fii_dii=raw.fii_dii,
            avoid_list=avoid_flags,
            pattern_matches=None,  # Pattern matching runs after screener
            top_n=3,
        )
        status.mark_ok("stock_screener")
        sections_ok += 1
        logger.info("[7/15] Stock screener: OK")
    except Exception as e:
        status.mark_degraded("stock_screener", str(e))
        sections_degraded += 1
        logger.error(f"[7/15] Stock screener FAILED: {e}")

    # ── 8. Correlation ──
    try:
        from features.correlation import compute_correlation_matrix
        correlations = compute_correlation_matrix(
            macro_history=raw.macro_history,
        )
        status.mark_ok("correlation")
        sections_ok += 1
        logger.info("[8/15] Correlation matrix: OK")
    except Exception as e:
        status.mark_degraded("correlation", str(e))
        sections_degraded += 1
        logger.error(f"[8/15] Correlation matrix FAILED: {e}")

    # ── 9. Pattern matching ──
    try:
        from features.pattern_matching import compute_pattern_match
        # Build today's feature dict from computed data
        today_features = {
            "gap_pct": gap_stats.expected_gap_pct,
            "crude_change_pct": raw.macro.brent_crude.change_pct,
            "vix": raw.macro.india_vix.value,
            "pcr": options.pcr_near_atm,
            "fii_net": raw.fii_dii.fii_cash_net,
            "dow_change_pct": raw.macro.dow_futures.change_pct,
            "usdinr_change_pct": raw.macro.usdinr.change_pct,
            "rsi": nifty_levels.rsi,
            "atr_pct": (nifty_levels.atr / nifty_levels.prev_close * 100) if nifty_levels.prev_close > 0 else 1.0,
            "volume_ratio": 1.0,  # Would come from market data
        }

        # Historical sessions would come from SQLite — pass empty for now
        # (backfill_history.py must run first to populate this)
        historical_sessions: list[dict] = []

        nifty_pattern = compute_pattern_match(
            today_features=today_features,
            historical_sessions=historical_sessions,
        )
        pattern_matches_list = [nifty_pattern]

        # Update gap-up candidates with pattern data
        for cand in gap_up_candidates:
            cand.pattern_match = nifty_pattern

        status.mark_ok("pattern_matching")
        sections_ok += 1
        logger.info("[9/15] Pattern matching: OK")
    except Exception as e:
        status.mark_degraded("pattern_matching", str(e))
        sections_degraded += 1
        logger.error(f"[9/15] Pattern matching FAILED: {e}")

    # ── 10. Expiry analysis ──
    try:
        from features.expiry_analysis import compute_expiry_analysis
        expiry = compute_expiry_analysis(
            nifty_options=raw.nifty_options,
            banknifty_options=raw.banknifty_options,
            max_pain_nifty=options.max_pain_nifty,
            max_pain_banknifty=options.max_pain_banknifty,
            pcr_nifty=options.pcr_near_atm,
            vix=raw.macro.india_vix.value,
        )
        status.mark_ok("expiry_analysis")
        sections_ok += 1
        logger.info("[10/15] Expiry analysis: OK")

        # Recompute gap analysis with correct expiry info if needed
        if expiry.is_expiry_week and not gap_stats.expiry_adjustment < 1.0:
            try:
                from features.gap_analysis import compute_gap_analysis
                gap_stats = compute_gap_analysis(
                    prev_close=nifty_levels.prev_close,
                    expected_open=nifty_levels.expected_open,
                    vix=raw.macro.india_vix.value,
                    is_expiry_week=True,
                )
                logger.info("  Gap analysis recomputed with expiry adjustment")
            except Exception:
                pass  # Keep original gap_stats

    except Exception as e:
        status.mark_degraded("expiry_analysis", str(e))
        sections_degraded += 1
        logger.error(f"[10/15] Expiry analysis FAILED: {e}")

    # ── 11. Contagion chain ──
    try:
        from features.contagion_chain import compute_contagion_chain
        contagion = compute_contagion_chain(raw.macro)
        status.mark_ok("contagion_chain")
        sections_ok += 1
        logger.info("[11/15] Contagion chain: OK")
    except Exception as e:
        status.mark_degraded("contagion_chain", str(e))
        sections_degraded += 1
        logger.error(f"[11/15] Contagion chain FAILED: {e}")

    # ── 12. Confidence score ──
    try:
        from features.confidence_score import compute_confidence_score
        confidence = compute_confidence_score(
            macro=raw.macro,
            fii_dii=raw.fii_dii,
            nifty_levels=nifty_levels,
            options=options,
            gap_stats=gap_stats,
            sector_flows=sector_flows,
            sentiment=sentiment,
            expiry=expiry,
        )
        status.mark_ok("confidence_score")
        sections_ok += 1
        logger.info("[12/15] Confidence score: OK")
    except Exception as e:
        status.mark_degraded("confidence_score", str(e))
        sections_degraded += 1
        logger.error(f"[12/15] Confidence score FAILED: {e}")

    # ── 13. Risk sizing ──
    try:
        from features.risk_sizing import compute_risk_sizing
        risk = compute_risk_sizing(
            nifty_levels=nifty_levels,
            expiry=expiry,
            vix=raw.macro.india_vix.value,
        )
        status.mark_ok("risk_sizing")
        sections_ok += 1
        logger.info("[13/15] Risk sizing: OK")
    except Exception as e:
        status.mark_degraded("risk_sizing", str(e))
        sections_degraded += 1
        logger.error(f"[13/15] Risk sizing FAILED: {e}")

    # ── 14. Events calendar ──
    try:
        from features.events_calendar import compute_events_calendar
        events = compute_events_calendar()
        status.mark_ok("events_calendar")
        sections_ok += 1
        logger.info("[14/15] Events calendar: OK")
    except Exception as e:
        status.mark_degraded("events_calendar", str(e))
        sections_degraded += 1
        logger.error(f"[14/15] Events calendar FAILED: {e}")

    # ── 15. Watchlist queue ──
    try:
        from features.watchlist_queue import compute_watchlist_queue
        watchlist = compute_watchlist_queue(
            nifty_levels=nifty_levels,
            gap_up_candidates=gap_up_candidates,
            expiry=expiry,
        )
        status.mark_ok("watchlist_queue")
        sections_ok += 1
        logger.info("[15/15] Watchlist queue: OK")
    except Exception as e:
        status.mark_degraded("watchlist_queue", str(e))
        sections_degraded += 1
        logger.error(f"[15/15] Watchlist queue FAILED: {e}")

    # ── Build final ComputedFeatures ──
    pipeline_duration = time.time() - pipeline_start

    metadata = ReportMetadata(
        signal_count=len(gap_up_candidates) + len(options.unusual_activity),
        pattern_match_count=sum(p.total_matches for p in pattern_matches_list),
        contagion_chain_count=len(contagion.orders),
        correlation_anomalies=len(correlations.anomalies),
        pipeline_duration=round(pipeline_duration, 2),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        sections_ok=sections_ok,
        sections_degraded=sections_degraded,
    )

    logger.info("=" * 60)
    logger.info(
        f"FEATURE PIPELINE COMPLETE — {sections_ok}/15 OK, "
        f"{sections_degraded}/15 degraded, {pipeline_duration:.1f}s"
    )
    logger.info("=" * 60)

    return ComputedFeatures(
        macro=raw.macro,
        nifty_levels=nifty_levels,
        banknifty_levels=banknifty_levels,
        options=options,
        gap_stats=gap_stats,
        sector_flows=sector_flows,
        correlations=correlations,
        sentiment=sentiment,
        risk=risk,
        confidence_score=confidence,
        gap_up_candidates=gap_up_candidates,
        avoid_list=avoid_flags,
        block_deals=raw.block_deals,
        pattern_matches=pattern_matches_list,
        expiry=expiry,
        events_calendar=events,
        tv_analyst_calls=raw.tv_calls,
        fii_dii_history=raw.fii_dii_history,
        contagion_chain=contagion,
        watchlist_alerts=watchlist,
        metadata=metadata,
    )
