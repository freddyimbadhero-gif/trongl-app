from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
)

from .database import Base


class IncidentCategory:
    """
    Categories used by TRONGL incident reports.
    """

    VIOLENCE = "violence"
    HARASSMENT = "harassment"
    THEFT = "theft"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    POOR_LIGHTING = "poor_lighting"
    ROAD_HAZARD = "road_hazard"
    ACCIDENT = "accident"
    OTHER = "other"


class Incident(Base):
    """
    A reported safety incident or environmental hazard.
    """

    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)

    category = Column(String(50), nullable=False, index=True)

    description = Column(Text, nullable=True)

    severity = Column(Integer, nullable=False, default=1)

    latitude = Column(Float, nullable=False)

    longitude = Column(Float, nullable=False)

    location = Column(
        Geometry(
            geometry_type="POINT",
            srid=4326,
            spatial_index=True,
        ),
        nullable=True,
    )

    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    expires_at = Column(
        DateTime,
        nullable=True,
    )

    confirmations = Column(
        Integer,
        nullable=False,
        default=0,
    )

    reports_count = Column(
        Integer,
        nullable=False,
        default=1,
    )
