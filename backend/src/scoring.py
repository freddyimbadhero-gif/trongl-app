from datetime import datetime, timezone
from math import exp
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
