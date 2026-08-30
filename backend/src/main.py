from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime, timedelta

from .database import get_db
from .schemas import RouteRequest, RouteResponse, RouteOption, Coordinates
from .models import IncidentCategory
from .assistant import SafetyAssistant, SafetyContext

app = FastAPI(
    title="TRONGL Safety Navigation API",
    version="1.0.0",
    description="Backend API pro výpočet bezpečných tras, hodnocení incidentů a AI asistenta."
)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "TRONGL Backend"}

# --- 1. VYHLEDÁNÍ A VÝPOČET TRAS ---
@app.post("/api/v1/navigation/routes", response_model=RouteResponse)
def calculate_routes(request: RouteRequest, db: Session = Depends(get_db)):
    query = text("""
        SELECT category, severity_weight, 
               ST_X(location::geometry) as lng, ST_Y(location::geometry) as lat
        FROM incidents
        WHERE is_active = TRUE
          AND ST_DWithin(
                location, 
                ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, 
                500
          );
    """)
    
    incidents = db.execute(query, {"lng": request.origin.lng, "lat": request.origin.lat}).fetchall()
    
    total_penalty = sum([inc.severity_weight for inc in incidents])
    if request.is_night:
        total_penalty += 15
        
    fastest_score = max(30, 100 - total_penalty - 20)
    safest_score = max(50, 100 - (total_penalty // 3))

    mock_path_fast = [request.origin, request.destination]
    mock_path_safe = [
        request.origin, 
        Coordinates(lat=(request.origin.lat + request.destination.lat)/2 + 0.002, 
                    lng=(request.origin.lng + request.destination.lng)/2 + 0.002),
        request.destination
    ]

    routes = [
        RouteOption(
            route_id="route_safest",
            title="🛡️ Nejbezpečnější",
            duration_minutes=22,
            distance_km=1.5,
            safety_score=safest_score,
            summary_reason="Vynechává neosvětlený park a místa s hlášeným rušením.",
            path=mock_path_safe
        ),
        RouteOption(
            route_id="route_fastest",
            title="⚡ Nejrychlejší",
            duration_minutes=17,
            distance_km=1.2,
            safety_score=fastest_score,
            summary_reason="Kratší trasa, ale obsahuje neosvětlené úseky.",
            path=mock_path_fast
        )
    ]

    return RouteResponse(routes=routes)


# --- 2. HLÁŠENÍ INCIDENTU Z MOBILNÍ APLIKACE ---
@app.post("/api/v1/incidents")
def report_incident(
    category: IncidentCategory,
    lat: float,
    lng: float,
    description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    expires_at = datetime.utcnow() + timedelta(hours=4)
    
    severity = 10
    if category == IncidentCategory.crime_violent:
        severity = 30
    elif category == IncidentCategory.lighting_issue:
        severity = 5

    insert_query = text("""
        INSERT INTO incidents (category, description, location, severity_weight, is_active, expires_at)
        VALUES (
            :category, 
            :description, 
            ST_SetSRID(ST_MakePoint(:lng, :lat), 4326), 
            :severity, 
            TRUE, 
            :expires_at
        )
        RETURNING id;
    """)

    result = db.execute(insert_query, {
        "category": category.value,
        "description": description,
        "lng": lng,
        "lat": lat,
        "severity": severity,
        "expires_at": expires_at
    })
    db.commit()
    
    incident_id = result.fetchone()[0]

    return {
        "status": "success",
        "message": "Hlášení bylo úspěšně přijato a započteno do bezpečnostní mapy.",
        "incident_id": str(incident_id)
    }


# --- 3. NOVÉ: ENDPOINT PRO AI BEZPEČNOSTNÍHO ASISTENTA ---
@app.post("/api/v1/assistant/advise")
def get_safety_advice(context: SafetyContext):
    """ Vrátí slovní doporučení a vyhodnocení od AI Bezpečnostního asistenta. """
    advice_text = SafetyAssistant.generate_advice(context)
    return {
        "safety_score": context.safety_score,
        "advice": advice_text
    }
