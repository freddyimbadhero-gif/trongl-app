from datetime import datetime, timezone
from math import cos, radians

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import text
from sqlalchemy.orm import Session

from .assistant import SafetyAssistant, SafetyContext
from .database import get_db, init_db
from .geocoding import search_places
from .models import Incident
from .routing import build_route_variants
from .schemas import (
    GeocodeResponse,
    IncidentCreate,
    IncidentResponse,
    RouteOption,
    RouteRequest,
    RouteResponse,
    RouteStep,
    SafetyAnalysis,
)
from .seed import seed_demo_incidents
from .scoring import (
    build_safety_explanation,
    calculate_route_safety_score,
    calculate_safety_score,
    is_location_night,
    risk_level,
)


app = FastAPI(
    title="TRONGL API",
    description="Safety-focused pedestrian navigation for Czech Republic.",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    try:
        init_db()
    except Exception as exc:
        print(f"Database initialization warning: {exc}")
        return

    try:
        from .database import SessionLocal
        db = SessionLocal()
        try:
            n = seed_demo_incidents(db)
            if n:
                print(f"Seeded {n} Prague demo incidents.")
            else:
                print("Demo incidents already present — skip seed.")
        finally:
            db.close()
    except Exception as exc:
        print(f"Demo seed warning: {exc}")


@app.get("/")
def root():
    return {"name": "TRONGL", "version": "2.1.0", "status": "online", "region": "CZ"}


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "database": "unavailable", "error": str(exc)},
        )


@app.get("/api/v1/status")
def status():
    return {
        "service": "TRONGL",
        "api_version": "v2.1",
        "status": "running",
        "region": "CZ",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/geocode", response_model=GeocodeResponse)
async def geocode(
    q: str = Query(..., min_length=2, max_length=200),
    latitude: float | None = None,
    longitude: float | None = None,
    limit: int = Query(5, ge=1, le=10),
):
    """Search places in the Czech Republic (Nominatim)."""
    try:
        results = await search_places(
            q, limit=limit, latitude=latitude, longitude=longitude
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Geocoding failed: {exc}")
    return GeocodeResponse(results=results)


@app.post("/api/v1/incidents", response_model=IncidentResponse)
def create_incident(incident_data: IncidentCreate, db: Session = Depends(get_db)):
    point = Point(incident_data.longitude, incident_data.latitude)
    incident = Incident(
        category=incident_data.category,
        description=incident_data.description,
        severity=incident_data.severity,
        latitude=incident_data.latitude,
        longitude=incident_data.longitude,
        location=from_shape(point, srid=4326),
        is_active=True,
        created_at=datetime.now(timezone.utc),
        confirmations=0,
        reports_count=1,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


@app.get("/api/v1/incidents", response_model=list[IncidentResponse])
def list_incidents(
    latitude: float = Query(...),
    longitude: float = Query(...),
    radius_meters: float = Query(800, gt=0, le=5000),
    db: Session = Depends(get_db),
):
    """Active incidents near a position."""
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise HTTPException(status_code=400, detail="Invalid coordinates.")
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
            .order_by(Incident.created_at.desc())
            .limit(50)
            .all()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Spatial query failed: {exc}")
    return incidents


@app.get("/api/v1/incidents/{incident_id}", response_model=IncidentResponse)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found.")
    return incident


@app.get("/api/v1/safety", response_model=SafetyAnalysis)
def safety_analysis(
    latitude: float,
    longitude: float,
    radius_meters: float = 500,
    db: Session = Depends(get_db),
):
    if not -90 <= latitude <= 90:
        raise HTTPException(status_code=400, detail="Invalid latitude.")
    if not -180 <= longitude <= 180:
        raise HTTPException(status_code=400, detail="Invalid longitude.")
    if radius_meters <= 0 or radius_meters > 5000:
        raise HTTPException(status_code=400, detail="radius_meters must be 0–5000.")

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
        raise HTTPException(status_code=500, detail=f"Spatial database query failed: {exc}")

    score = calculate_safety_score(incidents)
    is_night = is_location_night(latitude, longitude)
    advice = SafetyAssistant.generate_advice(
        SafetyContext(
            is_night=is_night,
            incident_types=[i.category for i in incidents],
            safety_score=int(score),
        )
    )
    return SafetyAnalysis(
        safety_score=score,
        incident_count=len(incidents),
        risk_level=risk_level(score),
        explanation=build_safety_explanation(score, len(incidents)),
        advice=advice,
    )


@app.post("/api/v1/navigation/routes", response_model=RouteResponse)
async def calculate_routes(request: RouteRequest, db: Session = Depends(get_db)):
    candidates = await build_route_variants(request.origin, request.destination)
    if not candidates:
        raise HTTPException(status_code=404, detail="No route could be calculated.")

    evaluated = []
    for route in candidates:
        min_lat = min(p.latitude for p in route.path)
        max_lat = max(p.latitude for p in route.path)
        min_lon = min(p.longitude for p in route.path)
        max_lon = max(p.longitude for p in route.path)
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

    fastest = min(evaluated, key=lambda i: i[0].duration_minutes)
    safest = max(evaluated, key=lambda i: i[1])
    min_time = min(i[0].duration_minutes for i in evaluated)
    max_time = max(i[0].duration_minutes for i in evaluated)

    def balanced_key(item):
        route, safety = item
        time_norm = 0.0 if max_time == min_time else (route.duration_minutes - min_time) / (max_time - min_time)
        risk_norm = 1.0 - safety / 100.0
        return 0.45 * time_norm + 0.55 * risk_norm

    balanced = min(evaluated, key=balanced_key)

    ordered = []
    for selected in (fastest, balanced, safest):
        if selected not in ordered:
            ordered.append(selected)
    for item in evaluated:
        if item not in ordered:
            ordered.append(item)

    label_by_id = {id(fastest): "fastest", id(balanced): "balanced", id(safest): "safest"}
    response_routes = []
    fallback_labels = ["fastest", "balanced", "safest"]
    for index, item in enumerate(ordered):
        route, safety_score = item
        name = label_by_id.get(id(item), fallback_labels[index] if index < 3 else f"alternative_{index}")
        steps = getattr(route, "steps", None) or []
        response_routes.append(
            RouteOption(
                name=name,
                distance_km=route.distance_km,
                duration_minutes=route.duration_minutes,
                safety_score=safety_score,
                path=route.path,
                steps=list(steps),
                summary=getattr(route, "summary", None),
            )
        )
    return RouteResponse(routes=response_routes)


@app.post("/api/v1/admin/seed-demo")
def force_seed_demo(db: Session = Depends(get_db)):
    """Force-insert Prague demo incidents even if some data exists (dev only)."""
    from datetime import timedelta
    from .seed import PRAGUE_DEMO_INCIDENTS

    now = datetime.now(timezone.utc)
    created = 0
    for item in PRAGUE_DEMO_INCIDENTS:
        point = Point(item["longitude"], item["latitude"])
        incident = Incident(
            category=item["category"],
            description=item["description"] + " [force seed]",
            severity=item["severity"],
            latitude=item["latitude"],
            longitude=item["longitude"],
            location=from_shape(point, srid=4326),
            is_active=True,
            created_at=now - timedelta(hours=item.get("hours_ago", 1)),
            confirmations=0,
            reports_count=1,
        )
        db.add(incident)
        created += 1
    db.commit()
    return {"created": created}
