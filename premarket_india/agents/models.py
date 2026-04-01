"""Pydantic models for AI agent outputs."""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class NarrativeBullet(BaseModel):
    icon: str = "M"  # "M" (macro), "F" (flow), "R" (risk), "E" (event)
    text: str = ""


class NarrativeOutput(BaseModel):
    headline: str = ""
    body: str = ""
    bullets: List[NarrativeBullet] = Field(default_factory=list)


class StockAnalysis(BaseModel):
    ticker: str = ""
    catalyst_text: str = ""
    timing_text: str = ""


class OptionsSummary(BaseModel):
    summary: str = ""


class ScenarioItem(BaseModel):
    label: str = ""
    color: str = "var(--phosphor)"
    probability: str = ""
    trigger: str = ""
    actions: str = ""
    exit: str = ""


class ScenarioPlaybook(BaseModel):
    scenarios: List[ScenarioItem] = Field(default_factory=list)


class ConflictFlag(BaseModel):
    analyst: str = ""
    call: str = ""
    conflict_reason: str = ""


class WatchlistAlertOutput(BaseModel):
    time: str = ""
    priority: str = ""
    title: str = ""
    content: str = ""


class AgentNarratives(BaseModel):
    """Combined output from all 6 agents."""
    narrative: NarrativeOutput = Field(default_factory=NarrativeOutput)
    stock_analyses: List[StockAnalysis] = Field(default_factory=list)
    options_summary: str = ""
    scenario_playbook: ScenarioPlaybook = Field(default_factory=ScenarioPlaybook)
    conflict_flags: List[ConflictFlag] = Field(default_factory=list)
    watchlist_alerts: List[WatchlistAlertOutput] = Field(default_factory=list)
