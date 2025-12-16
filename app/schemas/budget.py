from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List, Optional


class TransactionBase(BaseModel):
    description: str
    amount: float
    date: Optional[datetime] = None

    @field_validator('amount')
    @classmethod
    def amount_must_be_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError('Amount must be non-negative')
        return v


class TransactionCreate(TransactionBase):
    subcategory_id: int


class TransactionUpdate(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = None
    date: Optional[datetime] = None

    @field_validator('amount')
    @classmethod
    def amount_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError('Amount must be non-negative')
        return v

    class Config:
        from_attributes = True


class Transaction(TransactionBase):
    id: int
    subcategory_id: int

    class Config:
        from_attributes = True


class SubcategoryBase(BaseModel):
    name: str
    allotted: float

    @field_validator('allotted')
    @classmethod
    def allotted_must_be_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError('Allotted amount must be non-negative')
        return v


class SubcategoryCreate(SubcategoryBase):
    category_id: int


class SubcategoryUpdate(BaseModel):
    name: Optional[str] = None
    allotted: Optional[float] = None

    @field_validator('allotted')
    @classmethod
    def allotted_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError('Allotted amount must be non-negative')
        return v


class Subcategory(SubcategoryBase):
    id: int
    category_id: int
    transactions: List[Transaction] = []

    class Config:
        from_attributes = True


class CategoryBase(BaseModel):
    name: str
    budget: float

    @field_validator('budget')
    @classmethod
    def budget_must_be_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError('Budget must be non-negative')
        return v


class CategoryCreate(CategoryBase):
    year: Optional[int] = None
    month: Optional[int] = None


class CategoryUpdate(BaseModel):
    """Schema for updating an existing category."""
    name: Optional[str] = None
    budget: Optional[float] = None

    @field_validator('budget')
    @classmethod
    def budget_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError('Budget must be non-negative')
        return v



class BudgetBase(BaseModel):
    name: str

class BudgetCreate(BudgetBase):
    pass

class Budget(BudgetBase):
    id: int
    owner_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class BudgetMemberBase(BaseModel):
    user_id: str
    role: str = "editor"

class BudgetMemberCreate(BudgetMemberBase):
    budget_id: int

class BudgetMember(BudgetMemberBase):
    id: int
    budget_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Update Category to include budget_id instead of assuming context
class Category(BaseModel):
    id: int
    name: str
    budget: float = Field(validation_alias='budget_amount')  # Map from model's budget_amount
    budget_id: int
    year: int
    month: int
    subcategories: List[Subcategory] = []
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

