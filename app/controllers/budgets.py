# controllers/budgets.py
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import EmailStr
from sqlalchemy.orm import Session

from .. import models
from ..dependencies import get_db
from ..auth import get_current_user, get_user_email
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

@router.put("/{budget_id}", response_model=schemas.Budget, summary="Update budget")
def update_budget(
    budget_id: int,
    update_data: schemas.BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Update a budget (rename). Only admins/owners can update."""

    # Verify budget exists
    budget = db.query(models.Budget).filter(models.Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    # Verify requester is admin/owner
    requester_role = db.query(models.BudgetMember).filter(
        models.BudgetMember.budget_id == budget_id,
        models.BudgetMember.user_id == current_user,
        models.BudgetMember.role.in_(["admin", "owner"])
    ).first()

    if not requester_role and current_user != budget.owner_id:
        raise HTTPException(status_code=403, detail="Only admins can update budgets")

    # Update budget
    if update_data.name is not None:
        budget.name = update_data.name

    db.commit()
    db.refresh(budget)
    return budget

@router.delete("/{budget_id}", summary="Delete budget")
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Delete a budget. Only the owner can delete. Cascades to all related data."""

    # Verify budget exists
    budget = db.query(models.Budget).filter(models.Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    # Only owner can delete
    if current_user != budget.owner_id:
        raise HTTPException(status_code=403, detail="Only the budget owner can delete it")

    # Delete budget (cascades to members, invitations, categories, subcategories, transactions)
    db.delete(budget)
    db.commit()

    return {"message": f"Budget '{budget.name}' deleted successfully"}

@router.post("/{budget_id}/members", response_model=schemas.BudgetMember, summary="Add member to budget")
def add_member(
    budget_id: int,
    user_id_to_add: str = Query(..., description="User ID (UUID) to add to the budget"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Add a user to the budget (Only Admin/Owner can do this)."""
    # Check if budget exists
    budget = db.query(models.Budget).filter(models.Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    # Verify Requester is Admin
    requester_role = db.query(models.BudgetMember).filter(
        models.BudgetMember.budget_id == budget_id,
        models.BudgetMember.user_id == current_user,
        models.BudgetMember.role.in_(["admin", "owner"]) # "owner" isn't in role col default but logic implies
    ).first()

    if not requester_role and current_user != budget.owner_id:
         raise HTTPException(status_code=403, detail="Only admins can add members")

    # Check if user is already a member
    existing_member = db.query(models.BudgetMember).filter(
        models.BudgetMember.budget_id == budget_id,
        models.BudgetMember.user_id == user_id_to_add
    ).first()

    if existing_member:
        raise HTTPException(status_code=400, detail="User is already a member of this budget")

    new_member = models.BudgetMember(
        budget_id=budget_id,
        user_id=user_id_to_add,
        role="editor"
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_member)
    return new_member


# ============= INVITATION ENDPOINTS =============

@router.post("/{budget_id}/invitations", response_model=schemas.BudgetInvitationResponse, summary="Create budget invitation")
def create_invitation(
    budget_id: int,
    email: EmailStr = Body(..., embed=True),
    role: str = Body("editor", embed=True),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Create an email-based invitation to join a budget. Only admins/owners can invite."""

    # 1. Verify budget exists
    budget = db.query(models.Budget).filter(models.Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    # 2. Verify requester is admin/owner
    requester_role = db.query(models.BudgetMember).filter(
        models.BudgetMember.budget_id == budget_id,
        models.BudgetMember.user_id == current_user,
        models.BudgetMember.role.in_(["admin", "owner"])
    ).first()

    if not requester_role and current_user != budget.owner_id:
        raise HTTPException(status_code=403, detail="Only admins can send invitations")

    # 3. Check for existing pending invitation
    existing = db.query(models.BudgetInvitation).filter(
        models.BudgetInvitation.budget_id == budget_id,
        models.BudgetInvitation.invitee_email == email.lower(),
        models.BudgetInvitation.status == "pending",
        models.BudgetInvitation.expires_at > datetime.now(timezone.utc)
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="An active invitation already exists for this email"
        )

    # 4. Generate secure token
    token = secrets.token_urlsafe(48)  # 64 chars

    # 5. Create invitation
    invitation = models.BudgetInvitation(
        budget_id=budget_id,
        inviter_id=current_user,
        invitee_email=email.lower(),
        token=token,
        role=role,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    return invitation


@router.get("/{budget_id}/invitations", response_model=List[schemas.BudgetInvitationResponse], summary="List budget invitations")
def list_invitations(
    budget_id: int,
    status: Optional[str] = Query(None, regex="^(pending|accepted|expired|cancelled)$"),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """List all invitations for a budget. Admins only."""

    # Verify budget exists
    budget = db.query(models.Budget).filter(models.Budget.id == budget_id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    # Verify requester is admin/owner
    requester_role = db.query(models.BudgetMember).filter(
        models.BudgetMember.budget_id == budget_id,
        models.BudgetMember.user_id == current_user,
        models.BudgetMember.role.in_(["admin", "owner"])
    ).first()

    if not requester_role and current_user != budget.owner_id:
        raise HTTPException(status_code=403, detail="Only admins can view invitations")

    query = db.query(models.BudgetInvitation).filter(
        models.BudgetInvitation.budget_id == budget_id
    )

    if status:
        query = query.filter(models.BudgetInvitation.status == status)

    return query.order_by(models.BudgetInvitation.created_at.desc()).all()


@router.delete("/invitations/{invitation_id}", summary="Cancel invitation")
def cancel_invitation(
    invitation_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Cancel a pending invitation. Admins only."""

    invitation = db.query(models.BudgetInvitation).filter(
        models.BudgetInvitation.id == invitation_id
    ).first()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    # Verify requester is admin/owner
    budget = db.query(models.Budget).filter(
        models.Budget.id == invitation.budget_id
    ).first()

    requester_role = db.query(models.BudgetMember).filter(
        models.BudgetMember.budget_id == invitation.budget_id,
        models.BudgetMember.user_id == current_user,
        models.BudgetMember.role.in_(["admin", "owner"])
    ).first()

    if not requester_role and current_user != budget.owner_id:
        raise HTTPException(status_code=403, detail="Only admins can cancel invitations")

    if invitation.status != "pending":
        raise HTTPException(status_code=400, detail="Can only cancel pending invitations")

    invitation.status = "cancelled"
    db.commit()

    return {"message": "Invitation cancelled"}


@router.post("/invitations/accept/{token}", response_model=schemas.BudgetMember, summary="Accept invitation")
def accept_invitation(
    token: str,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
    user_email: str = Depends(get_user_email)
):
    """Accept a budget invitation using the token. User must be authenticated."""

    # 1. Find invitation by token
    invitation = db.query(models.BudgetInvitation).filter(
        models.BudgetInvitation.token == token
    ).first()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invalid invitation token")

    # 2. Check if already accepted
    if invitation.status == "accepted":
        raise HTTPException(status_code=400, detail="Invitation already accepted")

    # 3. Check if cancelled
    if invitation.status == "cancelled":
        raise HTTPException(status_code=400, detail="Invitation has been cancelled")

    # 4. Check expiration
    if invitation.expires_at < datetime.now(timezone.utc):
        invitation.status = "expired"
        db.commit()
        raise HTTPException(status_code=410, detail="Invitation has expired")

    # 5. Verify user's email matches invitation
    if user_email != invitation.invitee_email:
        raise HTTPException(
            status_code=403,
            detail="This invitation was sent to a different email address"
        )

    # 6. Check if already a member
    existing_member = db.query(models.BudgetMember).filter(
        models.BudgetMember.budget_id == invitation.budget_id,
        models.BudgetMember.user_id == current_user
    ).first()

    if existing_member:
        invitation.status = "accepted"
        invitation.accepted_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="You are already a member of this budget"
        )

    # 7. Add user to budget
    new_member = models.BudgetMember(
        budget_id=invitation.budget_id,
        user_id=current_user,
        role=invitation.role
    )
    db.add(new_member)

    # 8. Update invitation status
    invitation.status = "accepted"
    invitation.accepted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(new_member)

    return new_member


@router.get("/invitations/validate/{token}", summary="Validate invitation token")
def validate_invitation(token: str, db: Session = Depends(get_db)):
    """Validate invitation token (public endpoint). Returns invitation details without accepting."""

    invitation = db.query(models.BudgetInvitation).filter(
        models.BudgetInvitation.token == token
    ).first()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invalid invitation token")

    if invitation.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Invitation is {invitation.status}"
        )

    if invitation.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Invitation has expired")

    budget = db.query(models.Budget).filter(
        models.Budget.id == invitation.budget_id
    ).first()

    return {
        "valid": True,
        "budget_name": budget.name,
        "invitee_email": invitation.invitee_email,
        "role": invitation.role,
        "expires_at": invitation.expires_at.isoformat()
    }
