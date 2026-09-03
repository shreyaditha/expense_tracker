"""
routers/expenses.py
-------------------
CRUD for expenses within a group.

Key concept — Splitting logic:
  When you add an expense, you can either:
    (a) Provide no splits → expense is divided EQUALLY among all group members
    (b) Provide explicit splits → each split.share_amount is used as-is

  The validation checks that the sum of splits equals the total expense amount.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.dependencies import get_db, get_current_user
from app.routers.groups import get_group_or_404, require_member

router = APIRouter(tags=["Expenses"])


# ---------------------------------------------------------------------------
# Helper: fetch expense or 404
# ---------------------------------------------------------------------------
def get_expense_or_404(expense_id: int, db: Session) -> models.Expense:
    expense = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found.")
    return expense


# ===========================================================================
# POST /groups/{group_id}/expenses
# ===========================================================================
@router.post("/groups/{group_id}/expenses", response_model=schemas.ExpenseOut, status_code=201)
def create_expense(
    group_id: int,
    data: schemas.ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Add an expense to a group.
    The current user is recorded as the person who paid.

    Splitting modes:
      - No splits provided → equal split among all group members
      - Splits provided    → use the exact amounts given (must sum to total)
    """
    group = get_group_or_404(group_id, db)
    require_member(group, current_user.id)

    member_ids = [m.user_id for m in group.members]

    # --- Determine splits ---
    if not data.splits:
        # Equal split: divide total by number of members
        # round to 2 decimal places to avoid floating point drift
        per_person = round(data.amount / len(member_ids), 2)
        splits = [
            models.ExpenseSplit(user_id=uid, share_amount=per_person)
            for uid in member_ids
        ]
    else:
        # Custom splits: validate all users are group members and amounts sum correctly
        split_user_ids = [s.user_id for s in data.splits]

        for uid in split_user_ids:
            if uid not in member_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User {uid} is not a member of this group.",
                )

        total_split = round(sum(s.share_amount for s in data.splits), 2)
        if total_split != data.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Split amounts ({total_split}) must sum to the total expense amount ({data.amount})."
                ),
            )

        splits = [
            models.ExpenseSplit(user_id=s.user_id, share_amount=s.share_amount)
            for s in data.splits
        ]

    # --- Create the expense record ---
    expense = models.Expense(
        group_id=group_id,
        paid_by=current_user.id,
        title=data.title,
        amount=data.amount,
        description=data.description,
    )
    db.add(expense)
    db.flush()  # populate expense.id without committing

    for split in splits:
        split.expense_id = expense.id
        db.add(split)

    db.commit()
    db.refresh(expense)
    return expense


# ===========================================================================
# GET /groups/{group_id}/expenses
# ===========================================================================
@router.get("/groups/{group_id}/expenses", response_model=list[schemas.ExpenseOut])
def list_expenses(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List all expenses in a group (most recent first)."""
    group = get_group_or_404(group_id, db)
    require_member(group, current_user.id)

    expenses = (
        db.query(models.Expense)
        .filter(models.Expense.group_id == group_id)
        .order_by(models.Expense.created_at.desc())
        .all()
    )
    return expenses


# ===========================================================================
# GET /expenses/{expense_id}
# ===========================================================================
@router.get("/expenses/{expense_id}", response_model=schemas.ExpenseOut)
def get_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get a single expense. Must be a member of the expense's group."""
    expense = get_expense_or_404(expense_id, db)
    require_member(expense.group, current_user.id)
    return expense


# ===========================================================================
# PUT /expenses/{expense_id}
# ===========================================================================
@router.put("/expenses/{expense_id}", response_model=schemas.ExpenseOut)
def update_expense(
    expense_id: int,
    data: schemas.ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Update an expense's title, amount, or description.
    Only the person who originally recorded the expense can edit it.

    Note: Updating the amount does NOT recalculate splits automatically.
    Delete and recreate the expense if you need to change splits.
    """
    expense = get_expense_or_404(expense_id, db)

    if expense.paid_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the person who added the expense can edit it.",
        )

    if data.title is not None:
        expense.title = data.title
    if data.amount is not None:
        expense.amount = data.amount
    if data.description is not None:
        expense.description = data.description

    db.commit()
    db.refresh(expense)
    return expense


# ===========================================================================
# DELETE /expenses/{expense_id}
# ===========================================================================
@router.delete("/expenses/{expense_id}", status_code=204)
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Delete an expense (and all its splits via cascade).
    Only the person who added the expense or the group creator can delete it.
    """
    expense = get_expense_or_404(expense_id, db)

    is_expense_owner = expense.paid_by == current_user.id
    is_group_creator = expense.group.created_by == current_user.id

    if not (is_expense_owner or is_group_creator):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the expense owner or group creator can delete this expense.",
        )

    db.delete(expense)
    db.commit()
