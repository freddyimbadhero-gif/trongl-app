from typing import List, Optional

from pydantic import BaseModel, Field


# =========================================================
# Coordinates
# =========================================================

class Coordinates(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


# =========================================================
# Route request
# =========================================================

class RouteRequest(BaseModel):
    origin: Coordinates
    destination: Coordinates


# =========================================================
# Route option
# =========================================================

class RouteOption(BaseModel):
    name: str

    distance_km: float = Field(
        ...,
        ge=0,
    )

    duration_minutes: float = Field(
        ...,
        ge=0,
    )

    safety_score: float = Field(
        ...,
        ge=0,
        le=100,
    )

    path: List[Coordinates]


# =========================================================
# Route response
# =========================================================

class RouteResponse(BaseModel):
    routes: List[RouteOption]


# =========================================================
# Incident creation
# =========================================================

class IncidentCreate(BaseModel):
    category: str = Field(
        ...,
        min_length=1,
        max_length=50,
    )

    description: Optional[str] = Field(
        default=None,
        max_length=2000,
    )

    severity: int = Field(
        default=1,
        ge=1,
        le=5,
    )

    latitude: float = Field(
        ...,
        ge=-90,
        le=90,
    )

    longitude: float = Field(
        ...,
        ge=-180,
        le=180,
    )


# =========================================================
# Incident response
# =========================================================

class IncidentResponse(BaseModel):
    id: int
    category: str
    description: Optional[str]
    severity: int
    latitude: float
    longitude: float
    is_active: bool
    confirmations: int
    reports_count: int

    class Config:
        from_attributes = True


# =========================================================
# Safety analysis
# =========================================================

class SafetyAnalysis(BaseModel):
    safety_score: float = Field(
        ...,
        ge=0,
        le=100,
    )

    incident_count: int = Field(
        ...,
        ge=0,
    )

    risk_level: str

    explanation: Optional[str] = None
