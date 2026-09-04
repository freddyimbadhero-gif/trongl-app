from datetime import datetime, timezone
from math import acos, atan2, cos, degrees, exp, radians, sin, sqrt
from typing import Iterable


# ---------------------------------------------------------
# Incident weights
# ---------------------------------------------------------

CATEGORY_WEIGHTS = {
    "violence": 30.0,
    "harassment": 22.0,
    "theft": 18.0,
    "suspicious_activity": 14.0,
    "accident": 16.0,
    "poor_lighting": 10.0,
    "road_hazard": 8.0,
    "other": 6.0,
}


# ---------------------------------------------------------
# Risk calculation
# ---------------------------------------------------------

def category_weight(category: str) -> float:
    """
    Returns the base risk weight for an incident category.
    """
    return CATEGORY_WEIGHTS.get(
        category.lower(),
        CATEGORY_WEIGHTS["other"],
    )


def severity_multiplier(severity: int) -> float:
    """
    Converts severity 1-5 into a risk multiplier.
    """
    severity = max(1, min(severity, 5))

    return {
        1: 0.5,
        2: 0.75,
        3: 1.0,
        4: 1.35,
        5: 1.75,
    }[severity]


def freshness_multiplier(
    created_at: datetime | None,
    now: datetime | None = None,
) -> float:
    """
    Newer reports have a stronger influence.

    Reports gradually lose influence over time instead of
    disappearing immediately.
    """

    if created_at is None:
        return 1.0

    if now is None:
        now = datetime.now(timezone.utc)

    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    age_hours = max(
        0.0,
        (now - created_at).total_seconds() / 3600,
    )

    # Half-life of approximately 24 hours.
    return exp(-age_hours / 24.0)


def confirmation_multiplier(confirmations: int) -> float:
    """
    Multiple confirmations increase confidence, but with
    diminishing returns.
    """

    confirmations = max(0, confirmations)

    return min(
        1.5,
        1.0 + (confirmations * 0.1),
    )


# ---------------------------------------------------------
# Individual incident risk
# ---------------------------------------------------------

def calculate_incident_risk(
    incident,
    distance_meters: float = 0.0,
    now: datetime | None = None,
) -> float:
    """
    Calculates how much a single incident contributes to
    route risk.

    distance_meters represents the distance between the
    incident and the route segment being evaluated.
    """

    if not getattr(incident, "is_active", True):
        return 0.0

    base = category_weight(
        getattr(incident, "category", "other")
    )

    severity = severity_multiplier(
        getattr(incident, "severity", 1)
    )

    freshness = freshness_multiplier(
        getattr(incident, "created_at", None),
        now,
    )

    confirmations = confirmation_multiplier(
        getattr(incident, "confirmations", 0)
    )

    # Incidents farther from the route have less influence.
    distance_factor = exp(
        -max(0.0, distance_meters) / 100.0
    )

    return (
        base
        * severity
        * freshness
        * confirmations
        * distance_factor
    )


# ---------------------------------------------------------
# Route risk
# ---------------------------------------------------------

def calculate_route_risk(
    incidents: Iterable,
    now: datetime | None = None,
) -> float:
    """
    Calculates total risk for a route from its incidents.
    """

    total_risk = 0.0

    for incident in incidents:
        distance_meters = getattr(
            incident,
            "distance_meters",
            0.0,
        )

        total_risk += calculate_incident_risk(
            incident,
            distance_meters,
            now,
        )

    return total_risk


def calculate_safety_score(
    incidents: Iterable,
    now: datetime | None = None,
) -> float:
    """
    Converts route risk into a 0-100 safety score.

    100 = very safe
    0   = very risky
    """

    risk = calculate_route_risk(
        incidents,
        now,
    )

    # Diminishing-risk curve.
    score = 100.0 * exp(-risk / 100.0)

    return round(
        max(0.0, min(100.0, score)),
        1,
    )


# ---------------------------------------------------------
# Risk level
# ---------------------------------------------------------

def risk_level(score: float) -> str:
    """
    Converts a numerical safety score into a readable level.
    """

    if score >= 85:
        return "low"

    if score >= 70:
        return "moderate"

    if score >= 50:
        return "high"

    return "critical"


# ---------------------------------------------------------
# Explanation
# ---------------------------------------------------------

def build_safety_explanation(
    score: float,
    incident_count: int,
) -> str:
    """
    Creates a simple human-readable explanation.
    """

    level = risk_level(score)

    if incident_count == 0:
        return "Na trase nebyly nalezeny žádné aktivní incidenty."

    if level == "low":
        return (
            f"Trasa má vysoké bezpečnostní skóre {score}/100. "
            f"V okolí bylo nalezeno {incident_count} aktivních "
            f"hlášení, ale jejich celkové riziko je nízké."
        )

    if level == "moderate":
        return (
            f"Bezpečnostní skóre trasy je {score}/100. "
            f"Bylo nalezeno {incident_count} aktivních hlášení."
        )

    if level == "high":
        return (
            f"Trasa má zvýšené riziko se skóre {score}/100. "
            f"Bylo nalezeno {incident_count} aktivních hlášení."
        )

    return (
        f"Trasa má kritické bezpečnostní skóre {score}/100. "
        f"Bylo nalezeno {incident_count} aktivních hlášení."
    )


# ---------------------------------------------------------
# Route geometry helpers
# ---------------------------------------------------------

def _point_to_segment_distance_meters(point, start, end) -> float:
    """Approximate GPS point-to-segment distance using a local equirectangular projection."""
    lat0 = radians((start.latitude + end.latitude + point.latitude) / 3.0)
    meters_per_lat = 111_320.0
    meters_per_lon = 111_320.0 * max(0.01, cos(lat0))

    px = point.longitude * meters_per_lon
    py = point.latitude * meters_per_lat
    ax = start.longitude * meters_per_lon
    ay = start.latitude * meters_per_lat
    bx = end.longitude * meters_per_lon
    by = end.latitude * meters_per_lat

    dx = bx - ax
    dy = by - ay
    segment_sq = dx * dx + dy * dy

    if segment_sq == 0:
        return sqrt((px - ax) ** 2 + (py - ay) ** 2)

    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / segment_sq))
    closest_x = ax + t * dx
    closest_y = ay + t * dy
    return sqrt((px - closest_x) ** 2 + (py - closest_y) ** 2)


def distance_to_path_meters(point, path) -> float:
    """Return the shortest distance from a GPS point to a route polyline."""
    if not path:
        return float("inf")
    if len(path) == 1:
        return haversine_point_distance_meters(point, path[0])
    return min(
        _point_to_segment_distance_meters(point, start, end)
        for start, end in zip(path, path[1:])
    )


def haversine_point_distance_meters(a, b) -> float:
    """Haversine distance helper for objects exposing latitude/longitude."""
    lat1 = radians(a.latitude)
    lat2 = radians(b.latitude)
    dlat = lat2 - lat1
    dlon = radians(b.longitude - a.longitude)
    value = (
        sin(dlat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    )
    return 6_371_000.0 * 2 * atan2(sqrt(value), sqrt(max(0.0, 1 - value)))


def calculate_route_safety_score(incidents, path, now=None) -> float:
    """Calculate safety while applying each incident's real distance to the route."""
    for incident in incidents:
        incident.distance_meters = distance_to_path_meters(incident, path)
    return calculate_safety_score(incidents, now)


# ---------------------------------------------------------
# Day / night detection (location-aware)
# ---------------------------------------------------------

CIVIL_TWILIGHT_ELEVATION_DEGREES = -6.0
# Sun elevations at or below this are treated as "night" for safety
# purposes: below ~-6° the sky has lost usable daylight (civil dusk),
# which is a more meaningful cutoff than sunset (0°) for when people
# actually need lighting/caution outdoors.


def solar_elevation_degrees(
    latitude: float,
    longitude: float,
    when: datetime | None = None,
) -> float:
    """
    Approximates the sun's elevation angle (degrees above the horizon)
    at a given GPS position and UTC time, using NOAA's simplified solar
    position formulas. Positive = sun above horizon, negative = below.

    This intentionally skips atmospheric refraction and other minor
    corrections; the accuracy (well within ~1°) is more than enough to
    decide "is it effectively day or night here right now".
    """

    if when is None:
        when = datetime.now(timezone.utc)

    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    when = when.astimezone(timezone.utc)

    day_of_year = when.timetuple().tm_yday
    hour_fraction = when.hour + when.minute / 60.0 + when.second / 3600.0

    # Fractional year, in radians.
    gamma = (2 * 3.141592653589793 / 365.0) * (day_of_year - 1 + (hour_fraction - 12) / 24.0)

    # Equation of time, in minutes.
    eq_time = 229.18 * (
        0.000075
        + 0.001868 * cos(gamma)
        - 0.032077 * sin(gamma)
        - 0.014615 * cos(2 * gamma)
        - 0.040849 * sin(2 * gamma)
    )

    # Solar declination, in radians.
    declination = (
        0.006918
        - 0.399912 * cos(gamma)
        + 0.070257 * sin(gamma)
        - 0.006758 * cos(2 * gamma)
        + 0.000907 * sin(2 * gamma)
        - 0.002697 * cos(3 * gamma)
        + 0.00148 * sin(3 * gamma)
    )

    # True solar time, in minutes (UTC, so no timezone offset term needed).
    time_offset = eq_time + 4.0 * longitude
    true_solar_time = hour_fraction * 60.0 + time_offset

    # Hour angle, in degrees, then radians.
    hour_angle_deg = (true_solar_time / 4.0) - 180.0
    hour_angle = radians(hour_angle_deg)

    lat_rad = radians(latitude)

    cos_zenith = (
        sin(lat_rad) * sin(declination)
        + cos(lat_rad) * cos(declination) * cos(hour_angle)
    )
    cos_zenith = max(-1.0, min(1.0, cos_zenith))
    zenith_deg = degrees(acos(cos_zenith))

    return 90.0 - zenith_deg


def is_location_night(
    latitude: float,
    longitude: float,
    when: datetime | None = None,
) -> bool:
    """
    True when it's effectively dark (at/below civil twilight) at the
    given GPS position and time, rather than guessing from server UTC
    hour alone (which ignores both timezone and season/latitude).
    """
    elevation = solar_elevation_degrees(latitude, longitude, when)
    return elevation <= CIVIL_TWILIGHT_ELEVATION_DEGREES
