from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List

from .database import get_db
from .schemas import RouteRequest, RouteResponse, RouteOption, Coordinates

app = FastAPI(
    title="TRONGL Safety Navigation API",
    version="1.0.0",
    description="Backend API pro výpočet bezpečných tras a hodnocení incidentů."
)

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "TRONGL Backend"}

@app.post("/api/v1/navigation/routes", response_model=RouteResponse)
def calculate_routes(request: RouteRequest, db: Session = Depends(get_db)):
    """
    Vyhodnotí trasu mezi dvěma body a vrátí možnosti (Nejrychlejší vs. Nejbezpečnější)
    včetně spočítaného bezpečnostního skóre z PostGIS databáze.
    """
    
    # 1. Dotaz do PostGIS: Najde všechny aktivní incidenty v okruhu 500m od startu/cíle
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
    
    # 2. Výpočet penalizace (Základ 100)
    total_penalty = sum([inc.severity_weight for inc in incidents])
    if request.is_night:
        total_penalty += 15  # Penalizace za noční hodiny na neosvětlených úsecích
        
    fastest_score = max(30, 100 - total_penalty - 20)  # Kratší cesta riskantnější
    safest_score = max(50, 100 - (total_penalty // 3)) # Bezpečná obchůzka

    # Dummy koordináty pro ukázku (v produkci generuje OSRM engine)
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
            summary_reason="Kratší trasa, ale obsahuje 2 neosvětlené úseky.",
            path=mock_path_fast
        )
    ]

    return RouteResponse(routes=routes)
