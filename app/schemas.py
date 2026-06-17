"""Pydantic models for the /analyse response.

The four task-mandated blocks are typed explicitly (so they appear in the OpenAPI
schema and are validated on the way out). The rich, evolving context blocks
(`meta`, `score_breakdown`, `report`) are typed as open objects on purpose: they
exist to feed report-building and we would rather add fields there without a
breaking schema change. The contract that matters — breakdown, anomalies, score,
recommendation — is locked down.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CategoryStat(BaseModel):
    total: float = Field(..., description="Sum of inflow value in this category (SAR).")
    count: int = Field(..., description="Number of inflow transactions.")
    percentage: float = Field(..., description="Share of total inflow value (%).")


class InflowBreakdown(BaseModel):
    total_inflow: float
    categories: dict[str, CategoryStat]


class Recommendation(BaseModel):
    decision: Literal["trust_reported_revenue", "verify_with_vat_returns", "decline"]
    justification: str


class AnalyseResponse(BaseModel):
    meta: dict[str, Any] = Field(..., description="Parse stats, period, totals, context.")
    inflow_breakdown: InflowBreakdown
    pattern_anomalies: dict[str, Any] = Field(
        ..., description="round_number_bias, identical_amount_repeats, "
        "end_of_month_spike, suspected_intercompany_or_related_party_flows."
    )
    revenue_quality_score: int = Field(..., ge=0, le=100)
    score_breakdown: dict[str, Any] = Field(..., description="Per-component penalty audit.")
    recommendation: Recommendation
    report: dict[str, Any] = Field(..., description="Report-ready extras (series, samples).")


class ErrorResponse(BaseModel):
    detail: str
