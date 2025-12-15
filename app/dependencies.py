# app/dependencies.py
"""Centralized dependencies for FastAPI application."""

from .database import SessionLocal


def get_db():
    """Database session dependency.
    
    Yields a database session and ensures it's closed after use.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
