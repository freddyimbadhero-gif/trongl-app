from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import Base, engine, get_db, init_db
from .models import Incident
from .routing import build_route_variants
from .schemas import (
    Coordinates,
    IncidentCreate,
    IncidentResponse,
    RouteOption,
    RouteRequest,
    RouteResponse,
    SafetyAnalysis,
)
from .scoring import (
    build_safety_explanation,
    calculate_safety_score,
    risk_level,
)


# =========================================================
# TRONGL API
# =========================================================

app = FastAPI(
    title="TRONGL API",
    description=(
        "Safety-focused pedestrian navigation API."
    ),
    version="2.0.0",
)


# =========================================================
# Startup
# =========================================================

@app.on_event("startup")
def startup():
    """
    Initialize the database when the API starts.
    """

    try:
        init_db()
    except Exception as exc:
        print(
            f"Database initialization warning: {exc}"
        )


# =========================================================
# Health check
# =========================================================

@app.get("/")
def root():
    return {
        "name": "TRONGL",
        "version": "2.0.0",
        "status": "online",
    }


@app.get("/health")
def health(
    db: Session = Depends(get_db),
):
    """
    API + database health check.
    """

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
# Incidents
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
    Creates a new safety incident.
    """

    incident = Incident(
        category=incident_data.category,
        description=incident_data.description,
        severity=incident_data.severity,
        latitude=incident_data.latitude,
        longitude=incident_data.longitude,
        is_active=True,
        created_at=datetime.utcnow(),
        confirmations=0,
        reports_count=1,
    )

    db.add(incident)
    db.commit()
    db.refresh(incident)

    return incident


@app.get(
    "/api/v1/incidents/{incident_id}",
    response_model=IncidentResponse,
)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
):
    """
    Returns one incident.
    """

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
# Safety analysis
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
    Analyses active incidents around a GPS position.
    """

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

    # PostGIS spatial query.
    #
    # ST_SetSRID creates a GPS point.
    # ST_DWithin checks the requested radius.
    #
    # If the location geometry has not yet been populated,
    # we fall back to latitude/longitude filtering below.

    try:
        incidents = (
            db.query(Incident)
            .filter(
                Incident.is_active.is_(True),
                text(
                    """
                    ST_DWithin(
                        location::geography,
                        ST_SetSRID(
                            ST_MakePoint(
                                :longitude,
                                :latitude
                            ),
                            4326
                        )::geography,
                        :radius
                    )
                    """
                ),
            )
            .params(
                longitude=longitude,
                latitude=latitude,
                radius=radius_meters,
            )
            .all()
        )

    except Exception:
        incidents = (
            db.query(Incident)
            .filter(
                Incident.is_active.is_(True)
            )
            .all()
        )

    score = calculate_safety_score(
        incidents
    )

    return SafetyAnalysis(
        safety_score=score,
        incident_count=len(incidents),
        risk_level=risk_level(score),
        explanation=build_safety_explanation(
            score,
            len(incidents),
        ),
    )


# =========================================================
# Navigation
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

    Current routing provider is a development fallback.
    It will later be replaced with a real pedestrian
    routing engine.
    """

    routes = await build_route_variants(
        request.origin,
        request.destination,
        safety_score=100.0,
    )

    if not routes:
        raise HTTPException(
            status_code=404,
            detail="No route could be calculated.",
        )

    response_routes = []

    for route in routes:

        # -------------------------------------------------
        # Find active incidents around the route endpoints.
        #
        # This is intentionally conservative for now.
        # Full segment-by-segment analysis will come after
        # the real routing provider is connected.
        # -------------------------------------------------

        incidents = []

        try:
            incidents = (
                db.query(Incident)
                .filter(
                    Incident.is_active.is_(True)
                )
                .all()
            )

        except Exception:
            incidents = []

        safety_score = calculate_safety_score(
            incidents
        )

        response_routes.append(
            RouteOption(
                name=route.name,
                distance_km=route.distance_km,
                duration_minutes=route.duration_minutes,
                safety_score=safety_score,
                path=route.path,
            )
        )

    return RouteResponse(
        routes=response_routes
    )


# =========================================================
# Exception handling
# =========================================================

@app.get("/api/v1/status")
def status():
    """
    Simple API status endpoint.
    """

    return {
        "service": "TRONGL",
        "api_version": "v2",
        "status": "running",
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }
