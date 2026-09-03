"""
routers/balances.py
-------------------
The most interesting part of the app — computing who owes whom.

Two endpoints:
  GET /groups/{id}/balances     → raw net balance per user
  GET /groups/{id}/settlements  → simplified list of payments to clear all debts

============================================================
BALANCE CALCULATION — HOW IT WORKS
============================================================

Given expenses in a group, for each user we compute:

  net_balance = (total they paid for others) - (total they owe across all splits)

Example:
  Alice pays £30 for dinner, split equally among Alice, Bob, Carol (£10 each).
    → Alice paid £30, owes £10   → net = +£20
    → Bob paid £0,   owes £10   → net = -£10
    → Carol paid £0, owes £10   → net = -£10

  A positive net means the group owes THEM money.
  A negative net means THEY owe the group money.

============================================================
DEBT SIMPLIFICATION — THE GREEDY ALGORITHM
============================================================

Raw balances might say: Alice=+20, Bob=-10, Carol=-10.
The naive solution: Bob pays Alice £10, Carol pays Alice £10. (2 transactions)

But in a bigger group, we use a greedy algorithm to minimise transactions:
  1. Sort users into two heaps: creditors (positive) and debtors (negative)
  2. Match the largest debtor with the largest creditor
  3. Transfer min(|debt|, credit) → the one fully settled disappears from the heap
  4. Repeat until all balances are zero

This always produces the minimum number of transactions.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.dependencies import get_db, get_current_user
from app.routers.groups import get_group_or_404, require_member

router = APIRouter(tags=["Balances"])


# ---------------------------------------------------------------------------
# Core logic — compute net balances
# ---------------------------------------------------------------------------

def compute_net_balances(group: models.Group) -> dict[int, float]:
    """
    Return a dict mapping user_id → net_balance for a group.

    Algorithm:
      For each expense in the group:
        - The payer's balance increases by the full expense amount
        - Each split member's balance decreases by their share_amount
    """
    # Initialise every member at 0
    balances: dict[int, float] = {m.user_id: 0.0 for m in group.members}

    for expense in group.expenses:
        payer_id = expense.paid_by

        # Credit the payer for the full amount they fronted
        if payer_id in balances:
            balances[payer_id] += expense.amount

        # Debit each split participant for their share
        for split in expense.splits:
            if split.user_id in balances:
                balances[split.user_id] -= split.share_amount

    # Round to 2 decimal places to eliminate floating point noise
    return {uid: round(bal, 2) for uid, bal in balances.items()}


def simplify_debts(
    balances: dict[int, float],
    user_map: dict[int, models.User],
) -> list[schemas.Settlement]:
    """
    Greedy debt simplification.
    Returns the minimal list of transactions to settle all debts.
    """
    settlements: list[schemas.Settlement] = []

    # Separate into creditors (owed money) and debtors (owe money)
    # We work with mutable copies
    creditors = [(uid, bal) for uid, bal in balances.items() if bal > 0.001]
    debtors = [(uid, -bal) for uid, bal in balances.items() if bal < -0.001]

    # Sort descending by amount so we always process the largest first
    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)

    i, j = 0, 0  # pointer into creditors, debtors

    while i < len(creditors) and j < len(debtors):
        cred_uid, cred_amount = creditors[i]
        debt_uid, debt_amount = debtors[j]

        # The payment is limited by the smaller of the two amounts
        payment = round(min(cred_amount, debt_amount), 2)

        settlements.append(
            schemas.Settlement(
                from_user_id=debt_uid,
                from_user_name=user_map[debt_uid].full_name,
                to_user_id=cred_uid,
                to_user_name=user_map[cred_uid].full_name,
                amount=payment,
            )
        )

        # Reduce both balances by the payment
        creditors[i] = (cred_uid, round(cred_amount - payment, 2))
        debtors[j] = (debt_uid, round(debt_amount - payment, 2))

        # If a balance is fully settled, advance its pointer
        if creditors[i][1] < 0.001:
            i += 1
        if debtors[j][1] < 0.001:
            j += 1

    return settlements


# ===========================================================================
# GET /groups/{group_id}/balances
# ===========================================================================
@router.get("/groups/{group_id}/balances", response_model=schemas.BalanceSummary)
def get_balances(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Compute and return:
      - net_balance per member (positive = owed, negative = owes)
      - simplified settlement list (minimal transactions to clear all debts)
    """
    group = get_group_or_404(group_id, db)
    require_member(group, current_user.id)

    # Build a user_id → User object lookup for name resolution
    user_map: dict[int, models.User] = {m.user_id: m.user for m in group.members}

    # Step 1: compute raw net balances
    net_balances = compute_net_balances(group)

    # Step 2: format as UserBalance list
    balance_list = [
        schemas.UserBalance(
            user_id=uid,
            full_name=user_map[uid].full_name,
            email=user_map[uid].email,
            net_balance=bal,
        )
        for uid, bal in net_balances.items()
    ]

    # Step 3: simplify debts into minimal transactions
    settlements = simplify_debts(net_balances, user_map)

    return schemas.BalanceSummary(
        group_id=group.id,
        group_name=group.name,
        balances=balance_list,
        settlements=settlements,
    )
