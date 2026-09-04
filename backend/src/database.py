import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# ---------------------------------------------------------
# Database configuration
# ---------------------------------------------------------

def _build_database_url() -> str:
    """
    Builds the SQLAlchemy connection string.

    If DATABASE_URL is set explicitly, it takes priority. Otherwise the
    URL is assembled from the individual POSTGRES_* variables so that
    changing just POSTGRES_PASSWORD (etc.) in .env can't silently drift
    out of sync with a separately hardcoded DATABASE_URL default.
    """
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    user = os.getenv("POSTGRES_USER", "trongl_user")
    password = os.getenv("POSTGRES_PASSWORD", "trongl_secure_password")
    db_name = os.getenv("POSTGRES_DB", "trongl_db")
    # Internal container-to-container port; POSTGRES_PORT in .env only
    # controls the host-side port mapping and is not used here.
    host = os.getenv("POSTGRES_HOST", "db")

    return f"postgresql+psycopg2://{user}:{password}@{host}:5432/{db_name}"


DATABASE_URL = _build_database_url()


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
    Creates all SQLAlchemy tables and ensures PostGIS is available.

    Models must be imported before calling this function so
    SQLAlchemy knows about all declared tables.
    """
    from . import models  # noqa: F401
    from sqlalchemy import text

    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()

    Base.metadata.create_all(bind=engine)
