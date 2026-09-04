from datetime import datetime, timezone
from math import cos, radians

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import text
from sqlalchemy.orm import Session

from .assistant import SafetyAssistant, SafetyContext
from .database import get_db, init_db
from .models import Incident
from .routing import build_route_variants
from .schemas import (
    IncidentCreate,
    IncidentResponse,
    RouteOption,
    RouteRequest,
    RouteResponse,
    SafetyAnalysis,
)
from .scoring import (
    build_safety_explanation,
    calculate_route_safety_score,
    calculate_safety_score,
    is_location_night,
    risk_level,
)


# =========================================================
# TRONGL API
# =========================================================

app = FastAPI(
    title="TRONGL API",
    description="Safety-focused pedestrian navigation API.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# Startup
# =========================================================

@app.on_event("startup")
def startup():
    try:
        init_db()
    except Exception as exc:
        print(f"Database initialization warning: {exc}")


# =========================================================
# Root
# =========================================================

@app.get("/")
def root():
    return {
        "name": "TRONGL",
        "version": "2.0.0",
        "status": "online",
    }


# =========================================================
# Health check
# =========================================================

@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
        }

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "unavailable",
                "error": str(exc),
            },
        )


# =========================================================
# API status
# =========================================================

@app.get("/api/v1/status")
def status():
    return {
        "service": "TRONGL",
        "api_version": "v2",
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# =========================================================
# CREATE INCIDENT
# =========================================================

@app.post(
    "/api/v1/incidents",
    response_model=IncidentResponse,
)
def create_incident(
    incident_data: IncidentCreate,
    db: Session = Depends(get_db),
):
    """
    Creates a new incident and stores its PostGIS point.
    """

    point = Point(
        incident_data.longitude,
        incident_data.latitude,
    )

    incident = Incident(
        category=incident_data.category,
        description=incident_data.description,
        severity=incident_data.severity,
        latitude=incident_data.latitude,
        longitude=incident_data.longitude,
        location=from_shape(
            point,
            srid=4326,
        ),
        is_active=True,
        created_at=datetime.now(timezone.utc),
        confirmations=0,
        reports_count=1,
    )

    db.add(incident)
    db.commit()
    db.refresh(incident)

    return incident


# =========================================================
# GET INCIDENT
# =========================================================

@app.get(
    "/api/v1/incidents/{incident_id}",
    response_model=IncidentResponse,
)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
):
    incident = (
        db.query(Incident)
        .filter(Incident.id == incident_id)
        .first()
    )

    if incident is None:
        raise HTTPException(
            status_code=404,
            detail="Incident not found.",
        )

    return incident


# =========================================================
# SAFETY ANALYSIS
# =========================================================

@app.get(
    "/api/v1/safety",
    response_model=SafetyAnalysis,
)
def safety_analysis(
    latitude: float,
    longitude: float,
    radius_meters: float = 500,
    db: Session = Depends(get_db),
):
    """
    Calculates safety around a GPS position.
    """

    if not -90 <= latitude <= 90:
        raise HTTPException(
            status_code=400,
            detail="Invalid latitude.",
        )

    if not -180 <= longitude <= 180:
        raise HTTPException(
            status_code=400,
            detail="Invalid longitude.",
        )

    if radius_meters <= 0:
        raise HTTPException(
            status_code=400,
            detail="radius_meters must be greater than 0.",
        )

    if radius_meters > 5000:
        raise HTTPException(
            status_code=400,
            detail="radius_meters cannot exceed 5000.",
        )

    try:
        incidents = (
            db.query(Incident)
            .filter(
                Incident.is_active.is_(True),
                text(
                    """
                    ST_DWithin(
                        location::geography,
                        ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326)::geography,
                        :radius
                    )
                    """
                ).bindparams(
                    longitude=longitude,
                    latitude=latitude,
                    radius=radius_meters,
                ),
            )
            .all()
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Spatial database query failed: {exc}",
        )

    score = calculate_safety_score(
        incidents
    )

    is_night = is_location_night(latitude, longitude)

    advice = SafetyAssistant.generate_advice(
        SafetyContext(
            is_night=is_night,
            incident_types=[incident.category for incident in incidents],
            safety_score=int(score),
        )
    )

    return SafetyAnalysis(
        safety_score=score,
        incident_count=len(incidents),
        risk_level=risk_level(score),
        explanation=build_safety_explanation(
            score,
            len(incidents),
        ),
        advice=advice,
    )


# =========================================================
# NAVIGATION
# =========================================================

@app.post(
    "/api/v1/navigation/routes",
    response_model=RouteResponse,
)
async def calculate_routes(
    request: RouteRequest,
    db: Session = Depends(get_db),
):
    """
    Calculates route variants.

    The current routing provider is a development
    fallback. A real pedestrian routing provider
    will be connected later.
    """

    candidates = await build_route_variants(
        request.origin,
        request.destination,
    )

    if not candidates:
        raise HTTPException(status_code=404, detail="No route could be calculated.")

    evaluated = []
    for route in candidates:
        min_lat = min(point.latitude for point in route.path)
        max_lat = max(point.latitude for point in route.path)
        min_lon = min(point.longitude for point in route.path)
        max_lon = max(point.longitude for point in route.path)

        corridor_meters = 150.0
        lat_margin = corridor_meters / 111_320.0
        mean_lat = (min_lat + max_lat) / 2.0
        lon_scale = max(0.01, cos(radians(mean_lat)))
        lon_margin = corridor_meters / (111_320.0 * lon_scale)

        incidents = (
            db.query(Incident)
            .filter(
                Incident.is_active.is_(True),
                Incident.latitude >= min_lat - lat_margin,
                Incident.latitude <= max_lat + lat_margin,
                Incident.longitude >= min_lon - lon_margin,
                Incident.longitude <= max_lon + lon_margin,
            )
            .all()
        )

        safety_score = calculate_route_safety_score(incidents, route.path)
        evaluated.append((route, safety_score))

    # Pick labels from the actual candidate routes. Fastest is time-based,
    # safest is safety-score based. Balanced minimizes normalized time and risk.
    fastest = min(evaluated, key=lambda item: item[0].duration_minutes)
    safest = max(evaluated, key=lambda item: item[1])
    min_time = min(item[0].duration_minutes for item in evaluated)
    max_time = max(item[0].duration_minutes for item in evaluated)

    def balanced_key(item):
        route, safety = item
        time_norm = 0.0 if max_time == min_time else (route.duration_minutes - min_time) / (max_time - min_time)
        risk_norm = 1.0 - safety / 100.0
        return 0.45 * time_norm + 0.55 * risk_norm

    balanced = min(evaluated, key=balanced_key)

    # Keep all returned candidates distinct; a candidate may have more than one label
    # in degenerate cases, so prefer fastest/balanced/safest in that order and fill the rest.
    ordered = []
    for label, selected in (("fastest", fastest), ("balanced", balanced), ("safest", safest)):
        if selected not in ordered:
            ordered.append(selected)
        elif len(ordered) < len(evaluated):
            remaining = [x for x in evaluated if x not in ordered]
            if remaining:
                ordered.append(remaining[0])

    # Ensure the response has every available route exactly once.
    for item in evaluated:
        if item not in ordered:
            ordered.append(item)

    label_by_item = {id(fastest): "fastest", id(balanced): "balanced", id(safest): "safest"}
    response_routes = []
    fallback_labels = ["fastest", "balanced", "safest"]
    for index, item in enumerate(ordered):
        route, safety_score = item
        name = label_by_item.get(id(item), fallback_labels[index] if index < 3 else f"alternative_{index}")
        response_routes.append(
            RouteOption(
                name=name,
                distance_km=route.distance_km,
                duration_minutes=route.duration_minutes,
                safety_score=safety_score,
                path=route.path,
            )
        )

    return RouteResponse(
        routes=response_routes
    )
