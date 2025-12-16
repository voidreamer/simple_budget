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

from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from .auth import get_current_user
from . import models

def get_current_budget(
    x_budget_id: str = Header(None),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> int:
    """
    Verifies the user is a member of the requested budget context.
    Returns the budget_id if valid.
    """
    if not x_budget_id:
        raise HTTPException(status_code=400, detail="X-Budget-ID header required")

    try:
        budget_id = int(x_budget_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-Budget-ID format")

    # Check membership
    member_record = db.query(models.BudgetMember).filter(
        models.BudgetMember.budget_id == budget_id,
        models.BudgetMember.user_id == current_user
    ).first()

    if not member_record:
        raise HTTPException(status_code=403, detail="Access to this budget denied")
    
    return budget_id
