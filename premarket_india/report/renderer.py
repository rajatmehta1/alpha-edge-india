"""Report renderer — builds template context and renders Jinja2 HTML."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from report.chart_data import (
    mood_color,
    mood_color_hex,
    mood_gradient,
    mood_label,
    prepare_all_chart_data,
)

if TYPE_CHECKING:
    from agents.models import AgentNarratives
    from features.models import ComputedFeatures

TEMPLATE_DIR = Path(__file__).parent / "templates"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


class ReportRenderer:
    """Builds full template context from ComputedFeatures + AgentNarratives,
    renders the Jinja2 template, and saves the HTML report."""

    def __init__(self, output_dir: str | None = None):
        self.output_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=False,
        )
        self.template = self.env.get_template("alpha_edge_report.html.j2")

    # ── Public API ──

    def render(
        self,
        features: "ComputedFeatures",
        narratives: "AgentNarratives",
        chart_data: dict | None = None,
    ) -> str:
        """Render the full report HTML string.

        Args:
            features: Deterministic computed features from the pipeline.
            narratives: AI-generated narrative text from LangGraph agents.
            chart_data: Pre-built chart data dict. If None, built automatically.

        Returns:
            Complete self-contained HTML string.
        """
        if chart_data is None:
            chart_data = prepare_all_chart_data(features)

        ctx = self._build_context(features, narratives, chart_data)
        return self.template.render(**ctx)

    def save(self, html: str) -> str:
        """Save rendered HTML to output directory.

        Returns:
            Absolute path to the saved file.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"alpha_edge_{today}.html"
        filepath = self.output_dir / filename
        filepath.write_text(html, encoding="utf-8")
        return str(filepath.resolve())

    # ── Context Builder ──

    def _build_context(
        self,
        f: "ComputedFeatures",
        n: "AgentNarratives",
        chart_data: dict,
    ) -> dict:
        """Map ALL 17 sections + chrome to template variables."""

        macro = f.macro
        score = f.confidence_score

        # ── Masthead pills ──
        masthead_pills = self._build_masthead_pills(f)

        # ── Macro mood cards (6 items for hero section) ──
        macro_cards = self._build_macro_cards(f)

        # ── Merge stock analyses into gap-up candidates ──
        stock_analysis_map = {sa.ticker: sa for sa in n.stock_analyses}
        gap_up_stocks = []
        for stock in f.gap_up_candidates[:3]:
            sa = stock_analysis_map.get(stock.ticker)
            entry = stock.model_dump()
            if sa:
                entry["catalyst_text"] = sa.catalyst_text
                entry["timing_text"] = sa.timing_text
            gap_up_stocks.append(entry)

        # ── Correlation data ──
        corr = f.correlations

        # ── TV analyst calls with conflict flags ──
        conflict_map = {cf.analyst: cf for cf in n.conflict_flags}
        tv_calls = []
        for call in f.tv_analyst_calls:
            entry = call.model_dump()
            cf = conflict_map.get(call.analyst)
            if cf:
                entry["conflict"] = cf.conflict_reason
            tv_calls.append(entry)

        # ── TV accuracy line from constants ──
        tv_accuracy_line = self._build_tv_accuracy_line()

        # ── Scenarios ──
        scenarios = [s.model_dump() for s in n.scenario_playbook.scenarios]

        # ── Watchlist alerts (merge agent output with feature data) ──
        watchlist = [a.model_dump() for a in n.watchlist_alerts]
        if not watchlist:
            watchlist = [a.model_dump() for a in f.watchlist_alerts]

        # ── FII/DII summary ──
        fii_dii_summary = self._build_fii_dii_summary(f)

        # ── Sector flows (sorted by magnitude) ──
        sector_flows = sorted(
            [sf.model_dump() for sf in f.sector_flows],
            key=lambda s: abs(s.get("net_flow", 0)),
            reverse=True,
        )

        # ── Contagion chain ──
        contagion = f.contagion_chain.model_dump()

        # ── S02 info box texts ──
        nifty_pcr_text = self._build_pcr_text(f.options.pcr_near_atm)
        nifty_options_text = self._build_options_info_text(f)

        # ── Risk narrative ──
        risk_narrative = self._build_risk_narrative(f)

        # ── Build context dict ──
        return {
            # Chrome / metadata
            "report_date": datetime.now().strftime("%d %b %Y"),
            "report_date_long": datetime.now().strftime("%A, %d %B %Y"),
            "generated_at": f.metadata.generated_at or datetime.now().strftime("%H:%M IST"),
            "signal_count": f.metadata.signal_count,
            "sections_ok": f.metadata.sections_ok,
            "sections_degraded": f.metadata.sections_degraded,
            "pipeline_duration": f.metadata.pipeline_duration,
            "pattern_match_count": f.metadata.pattern_match_count,
            "contagion_chain_count": f.metadata.contagion_chain_count,
            "correlation_anomaly_count": f.metadata.correlation_anomalies,

            # Masthead
            "masthead_pills": masthead_pills,

            # Hero
            "macro_cards": macro_cards,
            "confidence_score": score,
            "confidence_label": mood_label(score),
            "confidence_color": mood_color(score),
            "confidence_color_hex": mood_color_hex(score),
            "confidence_gradient": mood_gradient(score),

            # S01 — Narrative
            "narrative_headline": n.narrative.headline,
            "narrative_body": n.narrative.body,
            "narrative_bullets": [b.model_dump() for b in n.narrative.bullets],

            # S02 — Levels
            "nifty_levels": f.nifty_levels.model_dump(),
            "banknifty_levels": f.banknifty_levels.model_dump(),
            "nifty_prev_close": macro.nifty_prev_close if macro else 0,
            "nifty_expected_open": macro.expected_nifty_open if macro else 0,
            "banknifty_prev_close": macro.banknifty_prev_close if macro else 0,
            "banknifty_expected_open": macro.expected_banknifty_open if macro else 0,
            "nifty_pcr_text": nifty_pcr_text,
            "nifty_options_text": nifty_options_text,

            # S03 — Gap-Up Setups
            "gap_up_stocks": gap_up_stocks,

            # S04 — Sector Rotation
            "sector_flows": sector_flows,

            # S05 — Contagion
            "contagion": contagion,

            # S06 — Options Flow
            "unusual_options": [uo.model_dump() for uo in f.options.unusual_activity],
            "options_summary": n.options_summary,
            "pcr_near_atm": f.options.pcr_near_atm,
            "max_pain_nifty": f.options.max_pain_nifty,
            "hv_rank": f.options.hv_rank,

            # S07 — Correlation
            "correlation_assets": corr.assets,
            "correlation_matrix": corr.matrix,
            "correlation_anomalies": [a.model_dump() for a in corr.anomalies],

            # S08 — Block Deals
            "block_deals": [bd.model_dump() for bd in f.block_deals],

            # S09 — Gap Stats
            "gap_stats": f.gap_stats.model_dump(),

            # S10 — Sentiment
            "social_sentiment": f.sentiment.social_items,
            "tv_analyst_calls": tv_calls,
            "tv_accuracy_line": tv_accuracy_line,

            # S11 — Avoid List
            "avoid_list": [af.model_dump() for af in f.avoid_list],

            # S12 — Expiry
            "expiry": f.expiry.model_dump(),

            # S13 — FII/DII
            "fii_dii_summary": fii_dii_summary,

            # S14 — Scenarios
            "scenarios": scenarios,

            # S15 — Watchlist
            "watchlist_alerts": watchlist,

            # S16 — Events
            "events_calendar": [e.model_dump() for e in f.events_calendar],

            # S17 — Risk Sizing
            "risk": f.risk.model_dump(),
            "risk_narrative": risk_narrative,

            # Charts (all 12)
            "chart_data": chart_data,
        }

    # ── Private helpers ──

    def _build_masthead_pills(self, f: "ComputedFeatures") -> list[dict]:
        """Build the masthead info pills matching the reference design.

        Pills use classes: pill-green, pill-red, pill-amber, pill-ice.
        Order:
          1. SGX Nifty with change %
          2. Dow Futures with change %
          3. Brent Crude with change % (inverted logic for India)
          4. USD/INR with value
          5. VIX with value and change %
          6. FII net flow
          7. Conditional: Expiry Wk (pill-amber) if is_expiry_week
        """
        pills = []
        macro = f.macro

        if macro:
            # 1. SGX Nifty
            sgx = macro.sgx_nifty
            sgx_cls = "pill-green" if sgx.change_pct >= 0 else "pill-red"
            sgx_sign = "+" if sgx.change_pct >= 0 else ""
            pills.append({
                "label": f"SGX Nifty {sgx_sign}{sgx.change_pct:.2f}%",
                "class": sgx_cls,
            })

            # 2. Dow Futures
            dow = macro.dow_futures
            dow_cls = "pill-green" if dow.change_pct >= 0 else "pill-red"
            dow_sign = "+" if dow.change_pct >= 0 else ""
            pills.append({
                "label": f"Dow {dow_sign}{dow.change_pct:.2f}%",
                "class": dow_cls,
            })

            # 3. Brent Crude (inverted for India: crude down is green)
            brent = macro.brent_crude
            brent_cls = "pill-green" if brent.change_pct <= 0 else "pill-red"
            brent_sign = "+" if brent.change_pct >= 0 else ""
            pills.append({
                "label": f"Brent {brent_sign}{brent.change_pct:.2f}%",
                "class": brent_cls,
            })

            # 4. USD/INR
            usdinr = macro.usdinr
            pills.append({
                "label": f"USD/INR {usdinr.value:.2f}",
                "class": "pill-amber",
            })

            # 5. VIX (falling VIX is green, rising is red)
            vix = macro.india_vix
            if vix.value > 0:
                vix_cls = "pill-green" if vix.change_pct <= 0 else "pill-red"
                vix_sign = "+" if vix.change_pct >= 0 else ""
                pills.append({
                    "label": f"VIX {vix.value:.1f} ({vix_sign}{vix.change_pct:.1f}%)",
                    "class": vix_cls,
                })

            # 6. FII net flow
            fii = macro.fii_net
            fii_val = fii.value
            fii_cls = "pill-green" if fii_val >= 0 else "pill-red"
            if abs(fii_val) >= 100:
                fii_str = f"{fii_val:+,.0f}Cr"
            else:
                fii_str = f"{fii_val:+,.1f}Cr"
            pills.append({
                "label": f"FII {fii_str}",
                "class": fii_cls,
            })

        # 7. Conditional: Expiry week
        if f.expiry.is_expiry_week:
            pills.append({
                "label": "Expiry Wk",
                "class": "pill-amber",
            })

        return pills

    def _build_macro_cards(self, f: "ComputedFeatures") -> list[dict]:
        """Build the 6 macro mood cards for the hero section.

        Formatting matches the reference:
          - SGX Nifty: "23,542" with delta "158.4 (+0.68%)"
          - Brent Crude: "$72.14" (dollar prefix)
          - FII: "−₹1,280Cr" (rupee prefix, Cr suffix)
          - Direction maps to CSS classes: "up", "down", "flat"
        """
        macro = f.macro
        if macro is None:
            return []

        items = [
            ("SGX Nifty", macro.sgx_nifty, "sp1", "", ""),
            ("Dow Futures", macro.dow_futures, "sp2", "", ""),
            ("Brent Crude", macro.brent_crude, "sp3", "$", ""),
            ("USD/INR", macro.usdinr, "sp4", "", ""),
            ("India VIX", macro.india_vix, "sp5", "", ""),
            ("FII Net", macro.fii_net, "sp6", "", "Cr"),
        ]

        cards = []
        for label, dp, canvas_id, prefix, suffix in items:
            # Format the main value
            value_str = self._format_card_value(dp.value, prefix, suffix)

            # Format the delta string with arrow
            arrow = "\u25B2" if dp.change >= 0 else "\u25BC"  # ▲ or ▼
            sign = "+" if dp.change >= 0 else ""

            if abs(dp.change) >= 1000:
                delta_num = f"{sign}{dp.change:,.0f}"
            elif abs(dp.change) >= 10:
                delta_num = f"{sign}{dp.change:.1f}"
            else:
                delta_num = f"{sign}{dp.change:.2f}"

            pct_str = f"({sign}{dp.change_pct:.2f}%)"
            delta_str = f"{arrow} {delta_num} {pct_str}"

            # Direction maps to template CSS: .mood-card-delta.up / .down / .flat
            direction = dp.direction  # "up", "down", "flat"

            cards.append({
                "label": label,
                "value": value_str,
                "delta": delta_str,
                "pct": "",  # pct is already embedded in delta for cleaner display
                "direction": direction,
                "canvas_id": canvas_id,
                "fresh": dp.fresh,
            })

        return cards

    def _format_card_value(self, value: float, prefix: str, suffix: str) -> str:
        """Format a macro card value with proper comma separators and prefix/suffix.

        Examples:
            23542.0  -> "23,542"
            72.14    -> "$72.14"
            -1280.0  -> "−₹1,280Cr"
        """
        # FII values get rupee symbol and Cr suffix
        if suffix == "Cr":
            sign = "" if value >= 0 else "\u2212"  # − (minus sign)
            abs_val = abs(value)
            if abs_val >= 100:
                formatted = f"{sign}\u20B9{abs_val:,.0f}{suffix}"
            else:
                formatted = f"{sign}\u20B9{abs_val:,.1f}{suffix}"
            return formatted

        # Dollar prefix for Brent
        if prefix == "$":
            return f"${value:.2f}"

        # General: large numbers get comma formatting, small get decimals
        if abs(value) >= 10000:
            return f"{value:,.0f}"
        elif abs(value) >= 100:
            return f"{value:,.1f}"
        else:
            return f"{value:.2f}"

    def _build_fii_dii_summary(self, f: "ComputedFeatures") -> dict:
        """Build FII/DII summary stats for section 13."""
        history = f.fii_dii_history
        if history is None:
            return {
                "fii_today": "N/A",
                "dii_today": "N/A",
                "fii_5d": "N/A",
                "dii_5d": "N/A",
            }

        fii_today = history.fii_net[-1] if history.fii_net else 0
        dii_today = history.dii_net[-1] if history.dii_net else 0
        fii_5d = sum(history.fii_net[-5:]) if history.fii_net else 0
        dii_5d = sum(history.dii_net[-5:]) if history.dii_net else 0

        def fmt_cr(val: float) -> str:
            prefix = "+" if val >= 0 else ""
            return f"{prefix}{val:,.0f} Cr"

        return {
            "fii_today": fmt_cr(fii_today),
            "dii_today": fmt_cr(dii_today),
            "fii_5d": fmt_cr(fii_5d),
            "dii_5d": fmt_cr(dii_5d),
            "fii_today_val": fii_today,
            "dii_today_val": dii_today,
        }

    def _build_tv_accuracy_line(self) -> str:
        """Build the 30-day accuracy line from TV_ANALYSTS constants.

        Returns a string like: "30-day accuracy: Sukhani 61% | Gaba 54% | ..."
        """
        try:
            from config.constants import TV_ANALYSTS
        except ImportError:
            return ""

        parts = []
        # Map full names to short display names
        name_map = {
            "Sudarshan Sukhani": "Sukhani",
            "Prakash Gaba": "Gaba",
            "Kunal Bothra": "Bothra",
            "Rajat Bose": "Bose",
        }

        for full_name, info in TV_ANALYSTS.items():
            short = name_map.get(full_name, full_name.split()[-1])
            acc_pct = int(info.get("accuracy_30d", 0) * 100)
            parts.append(f"{short} {acc_pct}%")

        if not parts:
            return ""

        return "30-day accuracy: " + " | ".join(parts)

    def _build_pcr_text(self, pcr: float) -> str:
        """Build interpretive text for the Nifty PCR value."""
        if pcr > 1.3:
            return f"PCR {pcr:.2f} — Strong put writing, bullish support"
        elif pcr > 1.1:
            return f"PCR {pcr:.2f} — Moderately bullish, put writers in control"
        elif pcr > 0.9:
            return f"PCR {pcr:.2f} — Neutral zone, watch for directional buildup"
        elif pcr > 0.7:
            return f"PCR {pcr:.2f} — Moderately bearish, call writers dominant"
        else:
            return f"PCR {pcr:.2f} — Heavy call writing, bearish pressure"

    def _build_options_info_text(self, f: "ComputedFeatures") -> str:
        """Build summary text for S02 levels info box (options context)."""
        opts = f.options
        parts = []
        if opts.max_pain_nifty > 0:
            parts.append(f"Max Pain: {opts.max_pain_nifty:,.0f}")
        if opts.hv_rank > 0:
            parts.append(f"IV Rank: {opts.hv_rank}")
        if opts.skew != 0:
            skew_dir = "call-heavy" if opts.skew > 0 else "put-heavy"
            parts.append(f"Skew: {skew_dir} ({opts.skew:+.1f})")
        return " | ".join(parts) if parts else ""

    def _build_risk_narrative(self, f: "ComputedFeatures") -> str:
        """Build a concise risk sizing narrative from computed features."""
        risk = f.risk
        parts = []
        if risk.max_risk_text:
            parts.append(risk.max_risk_text)
        if risk.nifty_atr_text:
            parts.append(risk.nifty_atr_text)
        if risk.recommended_lots_text:
            parts.append(risk.recommended_lots_text)
        if risk.expiry_adj_text:
            parts.append(risk.expiry_adj_text)

        if parts:
            return " ".join(parts)

        # Fallback: generate from raw values
        if risk.max_risk_per_trade > 0:
            return (
                f"Max risk per trade: \u20B9{risk.max_risk_per_trade:,.0f}. "
                f"Nifty ATR(14): {risk.nifty_atr:.0f} pts. "
                f"Recommended: {risk.recommended_lots} lot(s)."
            )
        return ""
