"""Prepare JSON-serializable dicts for all 12 Chart.js charts in the Alpha Edge report."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from features.models import ComputedFeatures

# ── Color Constants ──
GREEN = "#00E87B"
RED = "#FF4757"
AMBER = "#FFB84D"
BLUE = "#4DC9F6"
VIOLET = "#A78BFA"

GREEN_18 = "rgba(0,232,123,0.07)"
RED_18 = "rgba(255,71,87,0.07)"
AMBER_18 = "rgba(255,184,77,0.07)"

GRID_COLOR = "rgba(255,255,255,0.04)"
TEXT_COLOR = "#5A6580"
TOOLTIP_BG = "#1A2540"
TOOLTIP_BORDER = "#253050"

FONT_MONO = "'IBM Plex Mono', monospace"
FONT_SERIF = "'Instrument Serif'"


# ── Helper Functions ──

def mood_color(score: int) -> str:
    """Return CSS variable name for the mood score."""
    if score >= 55:
        return "var(--phosphor)"
    elif score >= 45:
        return "var(--amber)"
    else:
        return "var(--danger)"


def mood_color_hex(score: int) -> str:
    """Return hex color for the mood score (for use in JS/charts)."""
    if score >= 55:
        return GREEN
    elif score >= 45:
        return AMBER
    else:
        return RED


def mood_gradient(score: int) -> str:
    """Return CSS gradient string for the mood score bar.

    Uses CSS var() names to match the inline style in the reference HTML.
    """
    if score >= 55:
        return "linear-gradient(90deg,var(--phosphor),#06d6a0)"
    elif score >= 45:
        return "linear-gradient(90deg,var(--amber),#f59e0b)"
    else:
        return "linear-gradient(90deg,var(--danger),#dc2626)"


def mood_label(score: int) -> str:
    """Return human-readable mood label.

    Thresholds:
      >= 75: Bullish
      >= 55: Moderately Bullish
      >= 45: Neutral
      >= 25: Cautious
       < 25: Bearish
    """
    if score >= 75:
        return "Bullish"
    elif score >= 55:
        return "Moderately Bullish"
    elif score >= 45:
        return "Neutral"
    elif score >= 25:
        return "Cautious"
    else:
        return "Bearish"


def _direction_color(direction: str) -> tuple[str, str]:
    """Return (line_color, fill_color) tuple based on direction."""
    if direction == "up":
        return GREEN, GREEN_18
    elif direction == "down":
        return RED, RED_18
    else:
        return AMBER, AMBER_18


# ── Sparkline Builder (Charts 1-6) ──

def _build_sparkline(canvas_id: str, data: list[float], direction: str) -> dict:
    """Build a single sparkline chart config.

    Reference settings: borderWidth:1.5, pointRadius:0, fill:true, tension:0.4
    """
    line_color, fill_color = _direction_color(direction)
    labels = [str(i) for i in range(len(data))]

    return {
        "canvas_id": canvas_id,
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [{
                "data": data,
                "borderColor": line_color,
                "backgroundColor": fill_color,
                "borderWidth": 1.5,
                "pointRadius": 0,
                "fill": True,
                "tension": 0.4,
            }],
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {"display": False},
                "tooltip": {"enabled": False},
            },
            "scales": {
                "x": {"display": False},
                "y": {"display": False},
            },
        },
    }


def build_sparklines(features: "ComputedFeatures") -> list[dict]:
    """Build 6 sparkline chart configs for the macro mood cards."""
    macro = features.macro
    if macro is None:
        return []

    items = [
        ("sp1", macro.sgx_nifty),
        ("sp2", macro.dow_futures),
        ("sp3", macro.brent_crude),
        ("sp4", macro.usdinr),
        ("sp5", macro.india_vix),
        ("sp6", macro.fii_net),
    ]

    sparklines = []
    for canvas_id, data_point in items:
        data = data_point.sparkline if data_point.sparkline else [0] * 10
        sparklines.append(_build_sparkline(canvas_id, data, data_point.direction))

    return sparklines


# ── Chart 7: Sector Rotation (horizontal bar) ──

def build_sector_chart(features: "ComputedFeatures") -> dict:
    """Build sector rotation horizontal bar chart config.

    Reference: borderRadius:4, barPercentage:0.7
    """
    flows = sorted(features.sector_flows, key=lambda s: abs(s.net_flow), reverse=True)

    labels = [s.name for s in flows]
    values = [s.net_flow for s in flows]
    colors = [GREEN if v >= 0 else RED for v in values]

    return {
        "canvas_id": "sectorChart",
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{
                "data": values,
                "backgroundColor": colors,
                "borderRadius": 4,
                "barPercentage": 0.7,
            }],
        },
        "options": {
            "indexAxis": "y",
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {"display": False},
                "tooltip": {
                    "backgroundColor": TOOLTIP_BG,
                    "borderColor": TOOLTIP_BORDER,
                    "borderWidth": 1,
                    "titleFont": {"family": FONT_MONO, "size": 11},
                    "bodyFont": {"family": FONT_MONO, "size": 11},
                    "callbacks_format": "cr",
                },
            },
            "scales": {
                "x": {
                    "grid": {"color": GRID_COLOR},
                    "ticks": {"color": TEXT_COLOR, "font": {"family": FONT_MONO, "size": 10}},
                },
                "y": {
                    "grid": {"display": False},
                    "ticks": {"color": TEXT_COLOR, "font": {"family": FONT_MONO, "size": 10}},
                },
            },
        },
    }


# ── Chart 8: Contagion Impact (vertical bar) ──

def build_contagion_chart(features: "ComputedFeatures") -> dict:
    """Build contagion impact vertical bar chart config.

    Reference: borderRadius:5, barPercentage:0.65
    """
    chain = features.contagion_chain
    labels = chain.impact_labels if chain.impact_labels else []
    scores = chain.impact_scores if chain.impact_scores else []
    colors = chain.impact_colors if chain.impact_colors else []

    return {
        "canvas_id": "contagionChart",
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{
                "data": scores,
                "backgroundColor": colors,
                "borderRadius": 5,
                "barPercentage": 0.65,
            }],
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {"display": False},
                "tooltip": {
                    "backgroundColor": TOOLTIP_BG,
                    "borderColor": TOOLTIP_BORDER,
                    "borderWidth": 1,
                    "titleFont": {"family": FONT_MONO, "size": 11},
                    "bodyFont": {"family": FONT_MONO, "size": 11},
                },
            },
            "scales": {
                "x": {
                    "grid": {"display": False},
                    "ticks": {"color": TEXT_COLOR, "font": {"family": FONT_MONO, "size": 10}},
                },
                "y": {
                    "grid": {"color": GRID_COLOR},
                    "ticks": {"color": TEXT_COLOR, "font": {"family": FONT_MONO, "size": 10}},
                },
            },
        },
    }


# ── Chart 9: Gap Size Analysis (grouped vertical bar) ──

def build_gap_size_chart(features: "ComputedFeatures") -> dict:
    """Build gap size analysis grouped bar chart config.

    Reference: 5 labels, 2 datasets (Sustain Rate, Gap Fill Rate).
    """
    stats = features.gap_stats

    # Reference labels (5 bins)
    default_labels = [
        "<0.3% Small",
        "0.3-0.5% Mod",
        "0.5-1.0% Med",
        "1.0-1.5% Lrg",
        ">1.5% Mega",
    ]
    labels = stats.size_labels if stats.size_labels else default_labels

    # Ensure 5 values (pad with 0 if needed)
    sustain = stats.sustain_rates if stats.sustain_rates else [0] * len(labels)
    fill = stats.fill_rates if stats.fill_rates else [0] * len(labels)

    return {
        "canvas_id": "gapSizeChart",
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Sustain Rate %",
                    "data": sustain,
                    "backgroundColor": GREEN,
                    "borderRadius": 3,
                },
                {
                    "label": "Gap Fill Rate %",
                    "data": fill,
                    "backgroundColor": RED,
                    "borderRadius": 3,
                },
            ],
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {
                    "display": True,
                    "labels": {
                        "color": TEXT_COLOR,
                        "font": {"family": FONT_MONO, "size": 10},
                        "boxWidth": 10,
                    },
                },
                "tooltip": {
                    "backgroundColor": TOOLTIP_BG,
                    "borderColor": TOOLTIP_BORDER,
                    "borderWidth": 1,
                    "titleFont": {"family": FONT_MONO, "size": 11},
                    "bodyFont": {"family": FONT_MONO, "size": 11},
                },
            },
            "scales": {
                "x": {
                    "grid": {"display": False},
                    "ticks": {"color": TEXT_COLOR, "font": {"family": FONT_MONO, "size": 10}},
                },
                "y": {
                    "grid": {"color": GRID_COLOR},
                    "max": 100,
                    "ticks": {
                        "color": TEXT_COLOR,
                        "font": {"family": FONT_MONO, "size": 10},
                        "callback_format": "pct",
                    },
                },
            },
        },
    }


# ── Chart 10: Gap Expiry Doughnut ──

def build_gap_expiry_chart(features: "ComputedFeatures") -> dict:
    """Build gap expiry doughnut chart config.

    Reference: cutout:"55%", 3 segments [Sustained, Partial Fill, Full Fill].
    """
    stats = features.gap_stats

    return {
        "canvas_id": "gapExpiryChart",
        "type": "doughnut",
        "data": {
            "labels": ["Sustained", "Partial Fill", "Full Fill"],
            "datasets": [{
                "data": [stats.gap_sustained_pct, stats.partial_fill_pct, stats.full_fill_pct],
                "backgroundColor": [GREEN, AMBER, RED],
                "borderWidth": 0,
            }],
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "cutout": "55%",
            "plugins": {
                "legend": {
                    "display": True,
                    "position": "bottom",
                    "labels": {
                        "color": TEXT_COLOR,
                        "font": {"family": FONT_MONO, "size": 10},
                        "boxWidth": 10,
                        "padding": 12,
                    },
                },
                "tooltip": {
                    "backgroundColor": TOOLTIP_BG,
                    "borderColor": TOOLTIP_BORDER,
                    "borderWidth": 1,
                    "titleFont": {"family": FONT_MONO, "size": 11},
                    "bodyFont": {"family": FONT_MONO, "size": 11},
                },
            },
        },
    }


# ── Chart 11: Nifty OI by Strike (grouped vertical bar) ──

def build_oi_chart(features: "ComputedFeatures") -> dict:
    """Build Nifty OI by strike grouped bar chart config.

    Reference: Call OI in RED, Put OI in GREEN (counterintuitive but correct:
    calls = resistance = bearish, puts = support = bullish).
    """
    expiry = features.expiry
    strikes = expiry.oi_strikes if expiry.oi_strikes else []
    call_oi = expiry.call_oi if expiry.call_oi else []
    put_oi = expiry.put_oi if expiry.put_oi else []

    return {
        "canvas_id": "oiChart",
        "type": "bar",
        "data": {
            "labels": strikes,
            "datasets": [
                {
                    "label": "Call OI",
                    "data": call_oi,
                    "backgroundColor": RED,
                    "borderRadius": 2,
                },
                {
                    "label": "Put OI",
                    "data": put_oi,
                    "backgroundColor": GREEN,
                    "borderRadius": 2,
                },
            ],
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {
                    "display": True,
                    "labels": {
                        "color": TEXT_COLOR,
                        "font": {"family": FONT_MONO, "size": 10},
                        "boxWidth": 10,
                    },
                },
                "tooltip": {
                    "backgroundColor": TOOLTIP_BG,
                    "borderColor": TOOLTIP_BORDER,
                    "borderWidth": 1,
                    "titleFont": {"family": FONT_MONO, "size": 11},
                    "bodyFont": {"family": FONT_MONO, "size": 11},
                },
            },
            "scales": {
                "x": {
                    "grid": {"display": False},
                    "ticks": {"color": TEXT_COLOR, "font": {"family": FONT_MONO, "size": 9}},
                },
                "y": {
                    "grid": {"color": GRID_COLOR},
                    "ticks": {
                        "color": TEXT_COLOR,
                        "font": {"family": FONT_MONO, "size": 10},
                        "callback_format": "lakh",
                    },
                },
            },
        },
    }


# ── Chart 12: FII vs DII Flow (grouped vertical bar) ──

def build_fii_chart(features: "ComputedFeatures") -> dict:
    """Build FII vs DII flow grouped bar chart config.

    Reference: FII in RED, DII in GREEN.
    """
    history = features.fii_dii_history
    if history is None:
        dates, fii_net, dii_net = [], [], []
    else:
        dates = history.dates[-8:]
        fii_net = history.fii_net[-8:]
        dii_net = history.dii_net[-8:]

    return {
        "canvas_id": "fiiChart",
        "type": "bar",
        "data": {
            "labels": dates,
            "datasets": [
                {
                    "label": "FII Net",
                    "data": fii_net,
                    "backgroundColor": RED,
                    "borderRadius": 3,
                },
                {
                    "label": "DII Net",
                    "data": dii_net,
                    "backgroundColor": GREEN,
                    "borderRadius": 3,
                },
            ],
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {
                    "display": True,
                    "labels": {
                        "color": TEXT_COLOR,
                        "font": {"family": FONT_MONO, "size": 10},
                        "boxWidth": 10,
                    },
                },
                "tooltip": {
                    "backgroundColor": TOOLTIP_BG,
                    "borderColor": TOOLTIP_BORDER,
                    "borderWidth": 1,
                    "titleFont": {"family": FONT_MONO, "size": 11},
                    "bodyFont": {"family": FONT_MONO, "size": 11},
                    "callbacks_format": "cr",
                },
            },
            "scales": {
                "x": {
                    "grid": {"display": False},
                    "ticks": {"color": TEXT_COLOR, "font": {"family": FONT_MONO, "size": 9}},
                },
                "y": {
                    "grid": {"color": GRID_COLOR},
                    "ticks": {
                        "color": TEXT_COLOR,
                        "font": {"family": FONT_MONO, "size": 10},
                        "callback_format": "cr",
                    },
                },
            },
        },
    }


# ── Master builder ──

def prepare_all_chart_data(features: "ComputedFeatures") -> dict:
    """Build all 12 chart configs and return as a single dict.

    Returns a flat dict keyed by canvas_id for sparklines (sp1-sp6) and
    named keys for the remaining charts.  The template JS iterates over
    the structure: CD.sparklines (list), CD.sector_chart, etc.
    """
    return {
        "sparklines": build_sparklines(features),
        "sector_chart": build_sector_chart(features),
        "contagion_chart": build_contagion_chart(features),
        "gap_size_chart": build_gap_size_chart(features),
        "gap_expiry_chart": build_gap_expiry_chart(features),
        "oi_chart": build_oi_chart(features),
        "fii_chart": build_fii_chart(features),
    }
