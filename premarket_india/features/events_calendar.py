"""Events calendar: curated template events for the trading week."""

from __future__ import annotations

from datetime import datetime, timedelta
from loguru import logger

from config.constants import EXPIRY_DATES_2026
from features.models import CalendarEvent


# ── Curated recurring events ──

_AUTO_SALES_DAY = 1  # 1st of every month

_RBI_MPC_DATES_2026 = [
    "2026-02-05", "2026-02-07",   # Feb policy
    "2026-04-08", "2026-04-10",   # Apr policy
    "2026-06-04", "2026-06-06",   # Jun policy
    "2026-08-05", "2026-08-07",   # Aug policy
    "2026-10-07", "2026-10-09",   # Oct policy
    "2026-12-03", "2026-12-05",   # Dec policy
]

# Known major earnings dates (approximate — typically Q4 results in Apr-May)
_EARNINGS_CALENDAR = {
    "2026-04-14": ["TCS"],
    "2026-04-15": ["INFY"],
    "2026-04-21": ["HDFCBANK"],
    "2026-04-28": ["ICICIBANK", "AXISBANK"],
    "2026-04-30": ["RELIANCE"],
    "2026-05-05": ["SBIN"],
}


def _day_abbr(dt: datetime) -> str:
    """Return 3-letter uppercase day abbreviation."""
    return dt.strftime("%a").upper()[:3]


def _get_week_dates(today: datetime) -> list[datetime]:
    """Get all dates in the current trading week (Mon-Fri)."""
    weekday = today.weekday()
    monday = today - timedelta(days=weekday)
    return [monday + timedelta(days=i) for i in range(5)]


def compute_events_calendar(today: datetime | None = None) -> list[CalendarEvent]:
    """Generate curated event calendar for the current trading week.

    Returns events for Mon-Fri of the week containing `today`.
    """
    logger.info("Computing events calendar")

    if today is None:
        today = datetime.now()

    week_dates = _get_week_dates(today)
    events: list[CalendarEvent] = []

    for dt in week_dates:
        dt_str = dt.strftime("%Y-%m-%d")
        day = _day_abbr(dt)

        # Check auto sales (1st of month)
        if dt.day == _AUTO_SALES_DAY:
            events.append(CalendarEvent(
                day=day,
                time="10:00",
                title="Auto Sales Data",
                description="Monthly auto sales numbers released — impacts MARUTI, M&M, TATAMOTORS, EICHERMOT",
                severity="hi",
            ))

        # Check RBI MPC
        if dt_str in _RBI_MPC_DATES_2026:
            events.append(CalendarEvent(
                day=day,
                time="10:00",
                title="RBI MPC Decision",
                description="Monetary Policy Committee announcement — rate decision + stance",
                severity="hi",
            ))

        # Check F&O expiry
        if dt_str in EXPIRY_DATES_2026:
            events.append(CalendarEvent(
                day=day,
                time="15:30",
                title="F&O Monthly Expiry",
                description="Nifty & BankNifty monthly F&O expiry — expect elevated volatility and pinning",
                severity="hi",
            ))

        # Check weekly expiry (every Thursday)
        if dt.weekday() == 3:  # Thursday
            if dt_str not in EXPIRY_DATES_2026:
                events.append(CalendarEvent(
                    day=day,
                    time="15:30",
                    title="Weekly F&O Expiry",
                    description="Nifty weekly options expiry",
                    severity="med",
                ))

        # Check earnings
        if dt_str in _EARNINGS_CALENDAR:
            tickers = _EARNINGS_CALENDAR[dt_str]
            events.append(CalendarEvent(
                day=day,
                time="Post-Market",
                title=f"Earnings: {', '.join(tickers)}",
                description=f"Q4 FY26 results — watch for gap moves next day",
                severity="hi",
            ))

        # Regular market open reminder for today
        if dt.date() == today.date():
            events.append(CalendarEvent(
                day=day,
                time="09:15",
                title="Market Open",
                description="NSE/BSE regular trading session opens",
                severity="",
            ))

    # Sort by day order (Mon→Fri) then time
    day_order = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4}
    events.sort(key=lambda e: (day_order.get(e.day, 5), e.time))

    return events
