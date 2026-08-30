from dataclasses import dataclass
from math import atan2, cos, radians, sin, sqrt
from typing import List

from .schemas import Coordinates


# ---------------------------------------------------------
# Route data
# ---------------------------------------------------------

@dataclass
class Route:
    name: str
    path: List[Coordinates]
    distance_km: float
    duration_minutes: float


# ---------------------------------------------------------
# Geographic calculations
# ---------------------------------------------------------

EARTH_RADIUS_KM = 6371.0


def haversine_distance(
    origin: Coordinates,
    destination: Coordinates,
) -> float:
    """
    Returns the straight-line distance between two GPS
    coordinates in kilometres.
    """

    lat1 = radians(origin.latitude)
    lat2 = radians(destination.latitude)

    delta_lat = radians(
        destination.latitude - origin.latitude
    )

    delta_lon = radians(
        destination.longitude - origin.longitude
    )

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(delta_lon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a),
    )

    return EARTH_RADIUS_KM * c


# ---------------------------------------------------------
# Temporary route generator
# ---------------------------------------------------------

def generate_direct_path(
    origin: Coordinates,
    destination: Coordinates,
    points: int = 20,
) -> List[Coordinates]:
    """
    Generates a straight interpolated path between two
    coordinates.

    IMPORTANT:
    This is only a development fallback.

    It is NOT a real pedestrian route.
    """

    points = max(2, points)

    path = []

    for i in range(points):
        ratio = i / (points - 1)

        latitude = (
            origin.latitude
            + (
                destination.latitude
                - origin.latitude
            )
            * ratio
        )

        longitude = (
            origin.longitude
            + (
                destination.longitude
                - origin.longitude
            )
            * ratio
        )

        path.append(
            Coordinates(
                latitude=latitude,
                longitude=longitude,
            )
        )

    return path


# ---------------------------------------------------------
# Development routing provider
# ---------------------------------------------------------

class RoutingProvider:
    """
    Base routing provider.

    The production version can replace this class with
    OpenStreetMap / OSRM / GraphHopper / Valhalla or another
    routing engine.
    """

    async def calculate_routes(
        self,
        origin: Coordinates,
        destination: Coordinates,
    ) -> List[Route]:

        straight_distance = haversine_distance(
            origin,
            destination,
        )

        # Walking speed: approximately 5 km/h.
        duration = (
            straight_distance / 5.0
        ) * 60.0

        path = generate_direct_path(
            origin,
            destination,
        )

        return [
            Route(
                name="standard",
                path=path,
                distance_km=round(
                    straight_distance,
                    3,
                ),
                duration_minutes=round(
                    duration,
                    1,
                ),
            )
        ]


# ---------------------------------------------------------
# TRONGL route scoring
# ---------------------------------------------------------

def calculate_route_score(
    distance_km: float,
    duration_minutes: float,
    safety_score: float,
    safety_weight: float,
) -> float:
    """
    Combines travel time, distance and safety.

    safety_weight:
        0.0 = speed focused
        1.0 = safety focused
    """

    safety_weight = max(
        0.0,
        min(1.0, safety_weight),
    )

    # Normalize the basic travel cost.
    travel_score = (
        distance_km * 0.6
        + duration_minutes * 0.4
    )

    # Convert safety into a risk value.
    safety_risk = 100.0 - safety_score

    return (
        travel_score * (1.0 - safety_weight)
        + safety_risk * safety_weight
    )


# ---------------------------------------------------------
# Route variants
# ---------------------------------------------------------

async def build_route_variants(
    origin: Coordinates,
    destination: Coordinates,
    safety_score: float = 100.0,
) -> List[Route]:

    provider = RoutingProvider()

    base_routes = await provider.calculate_routes(
        origin,
        destination,
    )

    if not base_routes:
        return []

    base = base_routes[0]

    # -----------------------------------------------------
    # Fastest
    # -----------------------------------------------------

    fastest = Route(
        name="fastest",
        path=base.path,
        distance_km=base.distance_km,
        duration_minutes=base.duration_minutes,
    )

    # -----------------------------------------------------
    # Safest
    # -----------------------------------------------------

    safest = Route(
        name="safest",
        path=base.path,
        distance_km=round(
            base.distance_km * 1.15,
            3,
        ),
        duration_minutes=round(
            base.duration_minutes * 1.15,
            1,
        ),
    )

    # -----------------------------------------------------
    # Balanced
    # -----------------------------------------------------

    balanced = Route(
        name="balanced",
        path=base.path,
        distance_km=round(
            base.distance_km * 1.05,
            3,
        ),
        duration_minutes=round(
            base.duration_minutes * 1.05,
            1,
        ),
    )

    return [
        fastest,
        safest,
        balanced,
    ]
