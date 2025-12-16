# controllers/budget.py
"""Budget API endpoints with full CRUD operations."""

import logging
from datetime import datetime
from typing import List, Union

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from .. import models
from ..dependencies import get_db, get_current_budget
from ..schemas import budget as schemas
from ..services import budget as service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/categories/", response_model=schemas.Category, summary="Create a new category")
def create_category(
    category: schemas.CategoryCreate,
    db: Session = Depends(get_db),
    budget_id: int = Depends(get_current_budget)
):
    """Create a new budget category for the current month."""
    logger.info(f"Creating category: {category.name} in budget {budget_id}")

    # Map schema fields to model fields (budget -> budget_amount)
    category_data = category.dict()
    budget_value = category_data.pop('budget', 0)  # Remove 'budget' to avoid conflict with relationship

    db_category = models.Category(
        budget_id=budget_id,
        budget_amount=budget_value,  # Set the column explicitly
        **category_data
    )
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


@router.get("/categories/", response_model=List[schemas.Category], summary="List all categories")
def read_categories(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    budget_id: int = Depends(get_current_budget)
):
    """Retrieve all budget categories with pagination."""
    logger.debug(f"Fetching categories (skip={skip}, limit={limit})")
    
    return db.query(models.Category).filter(
        models.Category.budget_id == budget_id
    ).offset(skip).limit(limit).all()


@router.post("/subcategories/", response_model=schemas.Subcategory, summary="Create a subcategory")
def create_subcategory(
    subcategory: schemas.SubcategoryCreate, 
    db: Session = Depends(get_db),
    budget_id: int = Depends(get_current_budget)
):
    """Create a new subcategory under an existing category."""
    logger.info(f"Creating subcategory: {subcategory.name}")
    
    # Verify category belongs to budget
    category = db.query(models.Category).filter(
        models.Category.id == subcategory.category_id,
        models.Category.budget_id == budget_id
    ).first()
    
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
        
    return service.create_subcategory(db, subcategory)


@router.post("/transactions/", response_model=schemas.Transaction, summary="Create a transaction")
def create_transaction(
    transaction: schemas.TransactionCreate, 
    db: Session = Depends(get_db),
    budget_id: int = Depends(get_current_budget)
):
    """Record a new transaction under a subcategory."""
    logger.info(f"Creating transaction: {transaction.description} (${transaction.amount})")
    
    # Verify via subcategory -> category -> budget
    subcategory = db.query(models.Subcategory).join(models.Category).filter(
        models.Subcategory.id == transaction.subcategory_id,
        models.Category.budget_id == budget_id
    ).first()
    
    if not subcategory:
        raise HTTPException(status_code=404, detail="Subcategory not found")
        
    return service.create_transaction(db, transaction)


def month_to_number(month: str) -> int:
    """Convert month name to number (e.g., 'January' -> 1)."""
    try:
        return datetime.strptime(month, '%B').month
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid month name: {month}")


@router.get("/budget-summary/{year}/{month}", response_model=List[schemas.Category], summary="Get monthly budget summary")
def get_budget_summary(
    year: int,
    month: Union[str, int],
    db: Session = Depends(get_db),
    budget_id: int = Depends(get_current_budget)
):
    """Get complete budget summary with categories, subcategories, and transactions for a given month."""
    month_num = month_to_number(month) if isinstance(month, str) else month
    logger.debug(f"Fetching budget summary for {year}/{month_num}")

    return db.query(models.Category).filter(
        models.Category.year == year,
        models.Category.month == month_num,
        models.Category.budget_id == budget_id
    ).all()


@router.delete("/categories/{category_id}", summary="Delete a category")
def delete_category(
    category_id: int, 
    db: Session = Depends(get_db),
    budget_id: int = Depends(get_current_budget)
):
    """Delete a category and all its subcategories and transactions."""
    logger.info(f"Deleting category: {category_id}")
    category = db.query(models.Category).filter(
        models.Category.id == category_id,
        models.Category.budget_id == budget_id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Delete cascading relationships
    for subcategory in category.subcategories:
        db.query(models.Transaction).filter(models.Transaction.subcategory_id == subcategory.id).delete()
    db.query(models.Subcategory).filter(models.Subcategory.category_id == category_id).delete()

    db.delete(category)
    db.commit()
    return {"status": "success"}


@router.delete("/subcategories/{subcategory_id}", summary="Delete a subcategory")
def delete_subcategory(
    subcategory_id: int, 
    db: Session = Depends(get_db),
    budget_id: int = Depends(get_current_budget)
):
    """Delete a subcategory and all its transactions."""
    logger.info(f"Deleting subcategory: {subcategory_id}")
    subcategory = db.query(models.Subcategory).join(models.Category).filter(
        models.Subcategory.id == subcategory_id,
        models.Category.budget_id == budget_id
    ).first()
    if not subcategory:
        raise HTTPException(status_code=404, detail="Subcategory not found")

    db.query(models.Transaction).filter(models.Transaction.subcategory_id == subcategory_id).delete()
    db.delete(subcategory)
    db.commit()
    return {"status": "success"}


@router.put("/subcategories/{subcategory_id}", response_model=schemas.Subcategory, summary="Update a subcategory")
def update_subcategory(
    subcategory_id: int,
    data: schemas.SubcategoryUpdate,
    db: Session = Depends(get_db),
    budget_id: int = Depends(get_current_budget)
):
    """Update subcategory name or allotted amount."""
    logger.info(f"Updating subcategory {subcategory_id}")
    subcategory = db.query(models.Subcategory).join(models.Category).filter(
        models.Subcategory.id == subcategory_id,
        models.Category.budget_id == budget_id
    ).first()
    if not subcategory:
        raise HTTPException(status_code=404, detail="Subcategory not found")

    if data.allotted is not None:
        subcategory.allotted = data.allotted
    if data.name is not None:
        subcategory.name = data.name

    db.commit()
    db.refresh(subcategory)
    return subcategory


@router.put("/categories/{category_id}", response_model=schemas.Category, summary="Update a category")
def update_category(
    category_id: int,
    data: schemas.CategoryUpdate,
    db: Session = Depends(get_db),
    budget_id: int = Depends(get_current_budget)
):
    """Update category name or budget."""
    logger.info(f"Updating category {category_id}")
    category = db.query(models.Category).filter(
        models.Category.id == category_id,
        models.Category.budget_id == budget_id
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if data.budget is not None:
        category.budget_amount = data.budget
    if data.name is not None:
        category.name = data.name

    db.commit()
    db.refresh(category)
    return category


@router.put("/transactions/{transaction_id}", response_model=schemas.Transaction, summary="Update a transaction")
def update_transaction(
    transaction_id: int,
    data: schemas.TransactionUpdate,
    db: Session = Depends(get_db),
    budget_id: int = Depends(get_current_budget)
):
    """Update transaction details."""
    logger.info(f"Updating transaction {transaction_id}")
    transaction = db.query(models.Transaction).join(models.Subcategory).join(models.Category).filter(
        models.Transaction.id == transaction_id,
        models.Category.budget_id == budget_id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if data.description is not None:
        transaction.description = data.description
    if data.amount is not None:
        transaction.amount = data.amount
    if data.date is not None:
        transaction.date = data.date

    db.commit()
    db.refresh(transaction)
    return transaction


@router.delete("/transactions/{transaction_id}", summary="Delete a transaction")
def delete_transaction(
    transaction_id: int, 
    db: Session = Depends(get_db),
    budget_id: int = Depends(get_current_budget)
):
    """Delete a single transaction."""
    logger.info(f"Deleting transaction: {transaction_id}")
    transaction = db.query(models.Transaction).join(models.Subcategory).join(models.Category).filter(
        models.Transaction.id == transaction_id,
        models.Category.budget_id == budget_id
    ).first()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    db.delete(transaction)
    db.commit()
    return {"status": "success"}

