# controllers/budgets.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..dependencies import get_db
from ..auth import get_current_user
from ..schemas import budget as schemas

router = APIRouter()

@router.post("/", response_model=schemas.Budget, summary="Create a new budget")
def create_budget(
    budget_data: schemas.BudgetCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Create a new budget and add creator as Owner/Admin."""
    # 1. Create Budget
    new_budget = models.Budget(
        name=budget_data.name,
        owner_id=current_user
    )
    db.add(new_budget)
    db.flush() # Generate ID

    # 2. Add Creator as Member
    membership = models.BudgetMember(
        budget_id=new_budget.id,
        user_id=current_user,
        role="admin"
    )
    db.add(membership)
    
    db.commit()
    db.refresh(new_budget)
    return new_budget

@router.get("/", response_model=List[schemas.Budget], summary="List my budgets")
def list_my_budgets(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """List all budgets where the user is a member."""
    return db.query(models.Budget).join(models.BudgetMember).filter(
        models.BudgetMember.user_id == current_user
    ).all()

@router.post("/{budget_id}/members", response_model=schemas.BudgetMember, summary="Add member to budget")
def add_member(
    budget_id: int,
    user_id_to_add: str, # passed as query param for simplicity in MVP
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Add a user to the budget (Only Admin/Owner can do this)."""
    # Verify Requester is Admin
    requester_role = db.query(models.BudgetMember).filter(
        models.BudgetMember.budget_id == budget_id,
        models.BudgetMember.user_id == current_user,
        models.BudgetMember.role.in_(["admin", "owner"]) # "owner" isn't in role col default but logic implies
    ).first()

    if not requester_role and current_user != db.query(models.Budget).get(budget_id).owner_id:
         raise HTTPException(status_code=403, detail="Only admins can add members")

    new_member = models.BudgetMember(
        budget_id=budget_id,
        user_id=user_id_to_add,
        role="editor"
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    return new_member
