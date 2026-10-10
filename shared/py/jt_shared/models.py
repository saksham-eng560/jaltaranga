"""jt_shared Pydantic models per SHARED_RESOURCES.md."""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class ForecastNode(BaseModel):
    scenario_id: str
    issued_at: str
    station_id: str
    horizon_h: int
    valid_at: str
    level_m: float
    lo_m: float
    hi_m: float
    coverage: float = 0.8
    model: str # e.g. "gat-v1" | "lagreg-v1" | "persistence"


class FloodResponse(BaseModel):
    valid_at: Optional[str] = None
    tif_url: str
    geojson_url: str
    level_m_ref: float


class DepthIndexEntry(BaseModel):
    valid_at: str
    tif: str
    geojson: str
    level_m_ref: float


class ColonyThreshold(BaseModel):
    colony_id: str
    wet_at_level_m: Optional[float] = None
    cutoff_at_level_m: Optional[float] = None
    buffer_m: int = 150


class WhatIfResponse(BaseModel):
    level_m: float
    wet_colonies: List[dict] = Field(default_factory=list)
    cut_colonies: List[dict] = Field(default_factory=list)
    cut_edge_ids: List[str] = Field(default_factory=list)
    flood_geojson_url: Optional[str] = None


class ModelCard(BaseModel):
    name: str
    version: str
    champion: str
    provenance: dict
    splits: dict
    metrics: dict
    caveats: List[str]
