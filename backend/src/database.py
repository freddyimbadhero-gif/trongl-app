import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# ---------------------------------------------------------
# Database configuration
# ---------------------------------------------------------

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://trongl:trongl_secure_password@db:5432/trongl",
)


# ---------------------------------------------------------
# SQLAlchemy
# ---------------------------------------------------------

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


Base = declarative_base()


# ---------------------------------------------------------
# FastAPI database dependency
# ---------------------------------------------------------

def get_db():
    """
    Provides a database session for a FastAPI request.
    The session is always closed after the request finishes.
    """
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------
# Database initialization
# ---------------------------------------------------------

def init_db():
    """
    Creates all SQLAlchemy tables.

    Models must be imported before calling this function so
    SQLAlchemy knows about all declared tables.
    """
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
