# models/budget.py
"""SQLAlchemy models for budget tracking."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from ..database import Base


def utc_now():
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)




class Budget(Base):
    """Container for budget data, can be personal or shared."""
    __tablename__ = "budgets"
    __table_args__ = {"schema": "budget_v3"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False) # "Personal", "Family", etc.
    owner_id = Column(String, nullable=False, index=True) # Creator
    created_at = Column(DateTime(timezone=True), default=utc_now)

    members = relationship("BudgetMember", back_populates="budget", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="budget", cascade="all, delete-orphan")


class BudgetMember(Base):
    """Many-to-Many link between Users AND Budgets."""
    __tablename__ = "budget_members"
    __table_args__ = {"schema": "budget_v3"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    budget_id = Column(Integer, ForeignKey("budget_v3.budgets.id"), nullable=False)
    user_id = Column(String, nullable=False, index=True)
    role = Column(String, default="editor") # admin, editor, viewer
    created_at = Column(DateTime(timezone=True), default=utc_now)

    budget = relationship("Budget", back_populates="members")


class BudgetInvitation(Base):
    """Email-based budget invitation with secure token."""
    __tablename__ = "budget_invitations"
    __table_args__ = {"schema": "budget_v3"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    budget_id = Column(Integer, ForeignKey("budget_v3.budgets.id"), nullable=False)
    inviter_id = Column(String, nullable=False, index=True)  # Who sent the invite
    invitee_email = Column(String, nullable=False, index=True)  # Email to invite
    token = Column(String(64), unique=True, nullable=False, index=True)  # Secure token
    role = Column(String, default="editor")  # Role to assign when accepted
    status = Column(String, default="pending")  # pending, accepted, expired, cancelled
    created_at = Column(DateTime(timezone=True), default=utc_now)
    expires_at = Column(DateTime(timezone=True), nullable=False)  # 7 days from creation
    accepted_at = Column(DateTime(timezone=True), nullable=True)

    budget = relationship("Budget", backref="invitations")


class Category(Base):
    """Budget category for organizing spending (e.g., 'Groceries', 'Entertainment')."""
    __tablename__ = "categories"
    __table_args__ = {"schema": "budget_v3"}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    budget_id = Column(Integer, ForeignKey("budget_v3.budgets.id"), nullable=False)
    name = Column(String, nullable=False)
    budget_amount = Column("budget", Float, nullable=False, default=0.0) # Renamed to avoid confusion with table name
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    budget = relationship("Budget", back_populates="categories")
    subcategories = relationship("Subcategory", back_populates="category", cascade="all, delete-orphan")


class Subcategory(Base):
    """Subcategory within a budget category (e.g., 'Fast Food' under 'Groceries')."""
    __tablename__ = "subcategories"
    __table_args__ = {"schema": "budget_v3"}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    allotted = Column(Float, nullable=False, default=0.0)
    category_id = Column(Integer, ForeignKey("budget_v3.categories.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    category = relationship("Category", back_populates="subcategories")
    transactions = relationship("Transaction", back_populates="subcategory", cascade="all, delete-orphan")


class Transaction(Base):
    """Individual transaction/expense entry."""
    __tablename__ = "transactions"
    __table_args__ = {"schema": "budget_v3"}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(DateTime(timezone=True), default=utc_now)
    subcategory_id = Column(Integer, ForeignKey("budget_v3.subcategories.id"), nullable=False)
    
    subcategory = relationship("Subcategory", back_populates="transactions")


