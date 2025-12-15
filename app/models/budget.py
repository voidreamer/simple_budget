# models/budget.py
"""SQLAlchemy models for budget tracking."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from ..database import Base


def utc_now():
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class Category(Base):
    """Budget category for organizing spending (e.g., 'Groceries', 'Entertainment')."""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    budget = Column(Float, nullable=False, default=0.0)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    subcategories = relationship("Subcategory", back_populates="category", cascade="all, delete-orphan")


class Subcategory(Base):
    """Subcategory within a budget category (e.g., 'Fast Food' under 'Groceries')."""
    __tablename__ = "subcategories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    allotted = Column(Float, nullable=False, default=0.0)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    category = relationship("Category", back_populates="subcategories")
    transactions = relationship("Transaction", back_populates="subcategory", cascade="all, delete-orphan")


class Transaction(Base):
    """Individual transaction/expense entry."""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(DateTime(timezone=True), default=utc_now)
    subcategory_id = Column(Integer, ForeignKey("subcategories.id"), nullable=False)
    
    subcategory = relationship("Subcategory", back_populates="transactions")

